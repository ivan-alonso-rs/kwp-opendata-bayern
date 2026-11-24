"""M1 – Download the open data for one municipality and log every file.

Usage (from the repository root, environment `kwp` active):

    python scripts/01_download.py --gemeinde bubenreuth --dry-run   # plan only
    python scripts/01_download.py --gemeinde bubenreuth             # download
    python scripts/01_download.py --gemeinde bubenreuth --only lod2 # one source
    python scripts/01_download.py --gemeinde bubenreuth --with-dlm  # + Basis-DLM (1.9 GB)
    python scripts/01_download.py --gemeinde bubenreuth --accept-ags # accept a matching AGS

Order of work:
  1. Verwaltungsgebiete (63 MB, all of Bavaria) -> AGS check (kwp.ags.verify_ags)
  2. LoD2 tiles of the municipality via its metalink (SHA-256 checked per tile)
  3. ALKIS Tatsächliche Nutzung of the district
  4. Zensus 2022 100 m grid tables (whole of Germany, shared between municipalities)
  5. Basis-DLM only with --with-dlm
Everything is written to data/raw/ and recorded in data/raw/manifest.json.

Who decides what:
  automated   downloads, resume, checksums, manifest, finding the AGS columns,
              comparing the AGS
  person      accepting the AGS result: only when you pass --accept-ags does the
              script write `ags_verified: true` into config/<gemeinde>.yaml

Exit codes: 0 = done, 1 = a download failed, 2 = configuration problem.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

# Make `import kwp` work even without `pip install -e .` (same as 00_check_setup.py)
SRC_DIR = Path(__file__).resolve().parents[1] / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

import yaml  # noqa: E402

from kwp.config import CONFIG_DIR, REPO_ROOT, load_config  # noqa: E402
from kwp.download import (  # noqa: E402
    Manifest,
    RemoteFile,
    download_file,
    make_session,
    parse_metalink,
    remote_size,
)

SOURCE_ORDER = ["verwaltung", "lod2", "alkis_tn", "zensus2022", "basis_dlm"]


def load_sources() -> dict:
    with (CONFIG_DIR / "sources.yaml").open(encoding="utf-8") as fh:
        return yaml.safe_load(fh)


def target_dir(raw_root: Path, gemeinde_key: str, src: dict) -> Path:
    """gemeinde-scoped files go under the municipality, the rest under _shared/."""
    base = raw_root / gemeinde_key if src["scope"] == "gemeinde" else raw_root / "_shared"
    return base / src["target"]


def plan_files(session, key: str, src: dict, ags: str) -> tuple[list[RemoteFile], dict]:
    """Turn one entry of sources.yaml into the concrete list of files to fetch.

    Returns (files, extra manifest fields). For LoD2 this downloads the small
    metalink (a few kB) even in --dry-run, because only it knows the tiles.
    """
    fmt = {"ags": ags, "lkr": ags[:5]}
    if key == "lod2":
        url = src["metalink_url"].format(**fmt)
        r = session.get(url, timeout=(15, 60))
        r.raise_for_status()
        published, files = parse_metalink(r.text)
        return files, {"metalink_url": url, "metalink_published": published}
    if key == "zensus2022":
        files = [RemoteFile(name=f"{stem}.zip", urls=[src["base_url"] + f"{stem}.zip"])
                 for stem in src["tables"]]
        return files, {}
    url = src["url"].format(**fmt)
    return [RemoteFile(name=url.rsplit("/", 1)[-1], urls=[url])], {}


def check_ags(cfg: dict, src: dict, zip_path: Path, accept: bool) -> bool:
    """Confirm the AGS of the config against ALKIS Verwaltungsgebiete.

    1. If sources.yaml says where to look (member/name_field/ags_field), use it.
       Otherwise detect it (kwp.ags.detect_fields) and print what was found.
    2. Compare. Print a clear verdict.
    3. Only with --accept-ags AND a match: set ags_verified: true in the config.
       Without the flag the config is never changed (the decision is a person's).
    Returns False only when the official file shows a DIFFERENT key: then the
    other downloads would fetch the wrong municipality, so main() stops.
    """
    from kwp.ags import detect_fields, suggest_ags_field, verify_ags

    name, ags = cfg["gemeinde"]["name"], cfg["gemeinde"]["ags"]
    if src.get("member") and src.get("name_field") and src.get("ags_field"):
        dataset = f"/vsizip/{zip_path.as_posix()}/{src['member']}"
        layer, name_field, ags_field = src.get("layer"), src["name_field"], src["ags_field"]
    else:
        print("\n  AGS check: detecting file and columns in the official zip ...")
        guesses = detect_fields(zip_path, name)
        for g in guesses:
            print(f"    candidate: {g.dataset.split('.zip/', 1)[-1]} | layer {g.layer} | "
                  f"name column {g.name_field} | key column {g.ags_field}")
        best = suggest_ags_field(guesses)
        if best is None:
            print(f"  AGS check: name {name!r} not found in any layer.")
            return True
        dataset, layer = best.dataset, best.layer
        name_field, ags_field = best.name_field, best.ags_field
        member = dataset.split(".zip/", 1)[-1]
        print("  chosen. To skip detection next time, put in config/sources.yaml (verwaltung):")
        print(f"    member: {member}\n    layer: {layer}\n"
              f"    name_field: {name_field}\n    ags_field: {ags_field}")

    res = verify_ags(dataset, name, ags, name_field, ags_field, layer=layer)
    cfg_file = CONFIG_DIR / f"{cfg['gemeinde']['key']}.yaml"
    if res.matches:
        print(f"\n  AGS check OK: {name} = {ags} in ALKIS Verwaltungsgebiete.")
        if cfg["gemeinde"].get("ags_verified"):
            return True
        if accept:
            text = cfg_file.read_text(encoding="utf-8")
            if "ags_verified: false" in text:
                cfg_file.write_text(text.replace("ags_verified: false", "ags_verified: true", 1),
                                    encoding="utf-8")
                print(f"  --accept-ags: set ags_verified: true in {cfg_file.name}")
        else:
            print("  -> to accept, run again with --accept-ags (or edit the config by hand)")
        return True
    elif res.found:
        print(f"\n  AGS check FAILED: config says {ags}, official file says {res.found_ags}.")
        print("  -> stopping: fix gemeinde.ags in the config before downloading anything else.")
        return False
    else:
        print(f"\n  AGS check: name {name!r} not found in column {name_field!r}.")
    return True


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--gemeinde", required=True)
    ap.add_argument("--dry-run", action="store_true", help="show what would be downloaded")
    ap.add_argument("--only", choices=SOURCE_ORDER, action="append",
                    help="download only these sources (repeatable)")
    ap.add_argument("--with-dlm", action="store_true", help="also download Basis-DLM (1.9 GB)")
    ap.add_argument("--accept-ags", action="store_true",
                    help="if the AGS check matches, set ags_verified: true in the config")
    args = ap.parse_args()

    try:
        cfg = load_config(args.gemeinde)
        sources_cfg = load_sources()
    except (FileNotFoundError, ValueError) as exc:
        print(f"Config error: {exc}")
        return 2

    ags = cfg["gemeinde"].get("ags")
    if not ags or len(str(ags)) != 8:
        print(f"Config error: gemeinde.ags must be an 8-digit string, got {ags!r}")
        return 2
    ags = str(ags)

    raw_root = REPO_ROOT / cfg["paths"]["raw"]
    manifest = Manifest.load(raw_root / "manifest.json")
    session = make_session()
    attribution = sources_cfg["attribution"]

    keys = args.only or SOURCE_ORDER
    print(f"Gemeinde {cfg['gemeinde']['name']} (AGS {ags}, "
          f"verified: {cfg['gemeinde'].get('ags_verified')}) -> {raw_root}")

    failures = 0
    for key in keys:
        src = sources_cfg["sources"][key]
        if src.get("optional") and not args.with_dlm and not args.only:
            print(f"\n[{key}] skipped (optional, use --with-dlm)")
            continue
        print(f"\n[{key}] {src['title']} – licence {src['license']}")
        try:
            files, extra = plan_files(session, key, src, ags)
        except Exception as exc:  # network or parse error: report and continue
            print(f"  could not resolve file list: {exc}")
            failures += 1
            continue

        dest = target_dir(raw_root, cfg["gemeinde"]["key"], src)
        if args.dry_run:
            total = 0
            for f in files:
                size = f.size or remote_size(session, f.urls[0])
                total += size or 0
                print(f"  {f.name:70s} {size / 1e6 if size else float('nan'):8.1f} MB"
                      f"  sha256: {'yes' if f.sha256 else 'no'}")
            print(f"  -> {dest}  (known size {total / 1e6:.1f} MB)")
            continue

        for f in files:
            try:
                res = download_file(session, f, dest)
            except RuntimeError as exc:
                print(f"  ERROR: {exc}")
                failures += 1
                continue
            state = "already present" if res.skipped else "downloaded"
            check = "SHA-256 checked" if res.verified else "SHA-256 recorded"
            print(f"  {f.name}: {state}, {res.bytes / 1e6:.1f} MB, {check}")
            manifest.record(raw_root, res, key, src, attribution[src["attribution"]], extra)
            manifest.save()  # save after every file: a crash never loses the log

        if key == "verwaltung":
            zip_path = dest / files[0].name
            if zip_path.exists() and not check_ags(cfg, src, zip_path, args.accept_ags):
                manifest.save()
                return 2

    print(f"\nManifest: {manifest.path}  ({len(manifest.entries)} files logged)")
    if failures:
        print(f"{failures} problem(s) – run the same command again to resume.")
        return 1
    print("Done.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
