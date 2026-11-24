"""Tests for kwp.download that need no network.

The metalink fragment below is copied from the real LDBV file for Bubenreuth
(https://geodaten.bayern.de/odd/a/lod2/citygml/meta/metalink/09572119.meta4,
published 2026-11-17), shortened to two tiles.
"""

import hashlib
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from kwp.download import parse_metalink, sha256_file  # noqa: E402

SAMPLE = """<?xml version="1.0" encoding="UTF-8"?>
<metalink xmlns="urn:ietf:params:xml:ns:metalink">
  <generator>BVV-MetaLinker</generator>
  <published>2026-11-17T22:09:37Z</published>
  <file name="644_5496.gml">
    <size>71898946</size>
    <hash type="sha-256">7252503e23539be188d0ace266d9b3253f746837601bf038cf48e6bb8f2c1bf1</hash>
    <url>https://download1.bayernwolke.de/a/lod2/citygml/644_5496.gml</url>
    <url>https://download2.bayernwolke.de/a/lod2/citygml/644_5496.gml</url>
  </file>
  <file name="644_5500.gml">
    <size>34042533</size>
    <hash type="sha-256">17d95539b2d952c62c69001fc7e986d7e9fcf16e0bea99634f6941a809b752be</hash>
    <url>https://download1.bayernwolke.de/a/lod2/citygml/644_5500.gml</url>
    <url>https://download2.bayernwolke.de/a/lod2/citygml/644_5500.gml</url>
  </file>
</metalink>
"""


def test_parse_metalink_reads_all_fields():
    published, files = parse_metalink(SAMPLE)
    assert published == "2026-11-17T22:09:37Z"
    assert [f.name for f in files] == ["644_5496.gml", "644_5500.gml"]
    assert files[0].size == 71898946
    assert files[0].sha256.startswith("7252503e")
    assert len(files[0].urls) == 2  # both mirrors kept, in order


def test_parse_metalink_rejects_path_in_name():
    evil = SAMPLE.replace('name="644_5496.gml"', 'name="../../evil.gml"')
    with pytest.raises(ValueError):
        parse_metalink(evil)


def test_sha256_file(tmp_path):
    p = tmp_path / "x.bin"
    p.write_bytes(b"kwp" * 1000)
    assert sha256_file(p) == hashlib.sha256(b"kwp" * 1000).hexdigest()
