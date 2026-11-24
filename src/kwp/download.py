"""Download helpers for open geodata (milestone M1).

What this module does:
- parse an IETF Metalink 4 file (RFC 5854), as published by the LDBV per municipality;
- download a file in chunks, resumable (".part" file + HTTP Range), with mirrors;
- compute and check SHA-256 checksums;
- keep a manifest (data/raw/manifest.json) recording, for every file, its URL,
  download time, size, checksum, licence and attribution.

What it does NOT do:
- it never extracts archives (that happens in M2, on purpose: downloaded files
  are untrusted input and are only opened by GDAL/pyogrio, never executed);
- it never sends any data anywhere: only HTTP GET/HEAD to the official servers.
"""

from __future__ import annotations

import hashlib
import json
import time
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

import requests

METALINK_NS = {"ml": "urn:ietf:params:xml:ns:metalink"}
CHUNK = 1024 * 1024          # 1 MiB per read: low memory use, frequent progress output
TIMEOUT = (15, 120)          # (connect, read) seconds
RETRIES_PER_URL = 3
USER_AGENT = "kwp-opendata-bayern/0.1 (+https://github.com/ivan-alonso-rs/kwp-opendata-bayern)"


# --------------------------------------------------------------------------- #
# Metalink
# --------------------------------------------------------------------------- #
@dataclass
class RemoteFile:
    """One file announced by a metalink (or built by hand for a plain URL)."""

    name: str
    urls: list[str]
    size: int | None = None
    sha256: str | None = None


def parse_metalink(xml_text: str) -> tuple[str | None, list[RemoteFile]]:
    """Return (published timestamp, list of files) from a Metalink 4 document.

    Only SHA-256 hashes are kept: that is what the LDBV publishes, and weaker
    hashes (MD5, SHA-1) are not worth checking.
    """
    root = ET.fromstring(xml_text)
    published = root.findtext("ml:published", default=None, namespaces=METALINK_NS)
    files: list[RemoteFile] = []
    for f in root.findall("ml:file", METALINK_NS):
        size_txt = f.findtext("ml:size", default=None, namespaces=METALINK_NS)
        sha = None
        for h in f.findall("ml:hash", METALINK_NS):
            if h.get("type", "").lower() == "sha-256":
                sha = (h.text or "").strip().lower()
        urls = [(u.text or "").strip() for u in f.findall("ml:url", METALINK_NS) if u.text]
        name = f.get("name")
        if not name or not urls:
            raise ValueError("Metalink entry without name or URL")
        # Defence in depth: a file name must not contain a path.
        if Path(name).name != name:
            raise ValueError(f"Unsafe file name in metalink: {name!r}")
        files.append(RemoteFile(name=name, urls=urls,
                                size=int(size_txt) if size_txt else None, sha256=sha))
    return published, files


# --------------------------------------------------------------------------- #
# Checksums
# --------------------------------------------------------------------------- #
def sha256_file(path: Path) -> str:
    """SHA-256 of a file, read in chunks so that 2 GB files do not fill the RAM."""
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for block in iter(lambda: fh.read(CHUNK), b""):
            h.update(block)
    return h.hexdigest()


# --------------------------------------------------------------------------- #
# HTTP
# --------------------------------------------------------------------------- #
def make_session() -> requests.Session:
    s = requests.Session()
    s.headers["User-Agent"] = USER_AGENT
    return s


def remote_size(session: requests.Session, url: str) -> int | None:
    """Size in bytes from a HEAD request, or None if the server does not say."""
    try:
        r = session.head(url, timeout=TIMEOUT, allow_redirects=True)
        r.raise_for_status()
        cl = r.headers.get("Content-Length")
        return int(cl) if cl else None
    except requests.RequestException:
        return None


@dataclass
class DownloadResult:
    path: Path
    url: str
    bytes: int
    sha256: str
    verified: bool                     # True = matched a published checksum
    skipped: bool                      # True = file was already complete
    last_modified: str | None = None


def _progress(done: int, total: int | None, name: str) -> None:
    mb = done / 1e6
    if total:
        print(f"\r  {name}: {mb:8.1f} / {total / 1e6:.1f} MB ({100 * done / total:5.1f} %)",
              end="", flush=True)
    else:
        print(f"\r  {name}: {mb:8.1f} MB", end="", flush=True)


def download_file(session: requests.Session, remote: RemoteFile, dest_dir: Path) -> DownloadResult:
    """Download `remote` into `dest_dir`, resuming and switching mirrors if needed.

    Logic:
    1. If the final file exists and its hash matches the published one -> skip.
       (If no hash is published, an existing file of the expected size is kept.)
    2. Otherwise download into <name>.part. If a .part exists, ask the server to
       continue from its length (HTTP Range). A server that ignores Range answers
       200 instead of 206; then we start from zero.
    3. After the download, compare the SHA-256 with the published one. A mismatch
       deletes the .part and tries the next mirror.
    4. Only a complete, checked file is renamed to its final name, so a file with
       the final name is never half-written.
    """
    dest_dir.mkdir(parents=True, exist_ok=True)
    final = dest_dir / remote.name
    part = dest_dir / (remote.name + ".part")

    if final.exists():
        digest = sha256_file(final)
        size_ok = remote.size is None or final.stat().st_size == remote.size
        if (remote.sha256 and digest == remote.sha256) or (not remote.sha256 and size_ok):
            return DownloadResult(final, remote.urls[0], final.stat().st_size, digest,
                                  verified=bool(remote.sha256), skipped=True)
        print(f"  {remote.name}: existing file does not match, downloading again")
        final.unlink()

    last_error: Exception | None = None
    for url in remote.urls:
        for attempt in range(1, RETRIES_PER_URL + 1):
            try:
                offset = part.stat().st_size if part.exists() else 0
                headers = {"Range": f"bytes={offset}-"} if offset else {}
                with session.get(url, headers=headers, stream=True, timeout=TIMEOUT) as r:
                    if r.status_code == 416:          # .part already complete or bigger
                        part.unlink(missing_ok=True)
                        raise IOError("server rejected range, restarting")
                    r.raise_for_status()
                    if offset and r.status_code != 206:
                        offset = 0                    # Range ignored: start over
                    mode = "ab" if offset else "wb"
                    total = remote.size or (int(r.headers["Content-Length"]) + offset
                                            if r.headers.get("Content-Length") else None)
                    done = offset
                    with part.open(mode) as fh:
                        for block in r.iter_content(CHUNK):
                            fh.write(block)
                            done += len(block)
                            _progress(done, total, remote.name)
                    last_modified = r.headers.get("Last-Modified")
                print()

                digest = sha256_file(part)
                if remote.sha256 and digest != remote.sha256:
                    part.unlink()
                    raise IOError(f"SHA-256 mismatch for {remote.name}")
                if remote.size is not None and part.stat().st_size != remote.size:
                    part.unlink()
                    raise IOError(f"size mismatch for {remote.name}")
                part.replace(final)
                return DownloadResult(final, url, final.stat().st_size, digest,
                                      verified=bool(remote.sha256), skipped=False,
                                      last_modified=last_modified)
            except (requests.RequestException, IOError) as exc:
                last_error = exc
                wait = 2 ** attempt
                print(f"\n  {remote.name}: attempt {attempt} on {url} failed ({exc}); "
                      f"retry in {wait} s")
                time.sleep(wait)
    raise RuntimeError(f"Could not download {remote.name}: {last_error}")


# --------------------------------------------------------------------------- #
# Manifest
# --------------------------------------------------------------------------- #
@dataclass
class Manifest:
    """JSON log of every raw file: what, from where, when, which licence.

    Keys are paths relative to data/raw/ with forward slashes, so the manifest
    reads the same on Windows and Linux. The manifest is git-ignored together
    with data/raw/, but it is what a reviewer asks for: "which data exactly?".
    """

    path: Path
    entries: dict[str, dict] = field(default_factory=dict)

    @classmethod
    def load(cls, path: Path) -> "Manifest":
        if path.exists():
            return cls(path, json.loads(path.read_text(encoding="utf-8")))
        return cls(path)

    def record(self, raw_root: Path, result: DownloadResult, source_key: str,
               source: dict, attribution: str, extra: dict | None = None) -> None:
        rel = result.path.relative_to(raw_root).as_posix()
        entry = {
            "source": source_key,
            "title": source.get("title"),
            "provider": source.get("provider"),
            "product_page": source.get("product_page"),
            "url": result.url,
            "license": source.get("license"),
            "attribution": attribution,
            "bytes": result.bytes,
            "sha256": result.sha256,
            "sha256_checked_against_publisher": result.verified,
            "server_last_modified": result.last_modified,
        }
        if not result.skipped or rel not in self.entries:
            entry["downloaded_at_utc"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
        else:
            entry["downloaded_at_utc"] = self.entries[rel].get("downloaded_at_utc")
            entry["server_last_modified"] = (result.last_modified
                                             or self.entries[rel].get("server_last_modified"))
        if extra:
            entry.update(extra)
        self.entries[rel] = entry

    def save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.path.with_suffix(".json.tmp")
        tmp.write_text(json.dumps(self.entries, indent=2, ensure_ascii=False, sort_keys=True),
                       encoding="utf-8")
        tmp.replace(self.path)
