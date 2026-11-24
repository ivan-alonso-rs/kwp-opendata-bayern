"""Tests for kwp.ags – the target for Ivan's implementation.

They build a tiny synthetic boundaries file, so they need no download and no
real data. Field names "NAME"/"AGS" are invented here; the real ones come from
config/sources.yaml once the official shapefile has been inspected.
"""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from kwp.ags import normalize_ags, verify_ags  # noqa: E402


# ---------- normalize_ags --------------------------------------------------
@pytest.mark.parametrize(
    "raw, expected",
    [
        (9572119, "09572119"),          # stored as integer
        ("09572119", "09572119"),
        (" 09572130 ", "09572130"),     # whitespace
        ("095720000119", "09572119"),   # 12-digit ARS -> AGS
    ],
)
def test_normalize_ags(raw, expected):
    assert normalize_ags(raw) == expected


@pytest.mark.parametrize("raw", ["0957", "abcdefgh", "0957211900"])
def test_normalize_ags_rejects_bad_input(raw):
    with pytest.raises(ValueError):
        normalize_ags(raw)


# ---------- verify_ags -----------------------------------------------------
@pytest.fixture
def boundaries(tmp_path):
    gpd = pytest.importorskip("geopandas")
    from shapely.geometry import box

    gdf = gpd.GeoDataFrame(
        {
            "NAME": ["Bubenreuth", "Hemhofen", "Bubenreuther Weiher"],
            "AGS": [9572119, 9572130, 99999999],   # integers on purpose
        },
        geometry=[box(0, 0, 1, 1), box(1, 0, 2, 1), box(2, 0, 3, 1)],
        crs=25832,
    )
    path = tmp_path / "gemeinden.gpkg"
    gdf.to_file(path, layer="gemeinden", driver="GPKG")
    return path


def test_verify_ags_match(boundaries):
    r = verify_ags(boundaries, "Bubenreuth", "09572119", "NAME", "AGS", layer="gemeinden")
    assert r.matches and r.found_ags == ["09572119"]


def test_verify_ags_mismatch(boundaries):
    r = verify_ags(boundaries, "Hemhofen", "09572119", "NAME", "AGS", layer="gemeinden")
    assert r.found and not r.matches and r.found_ags == ["09572130"]


def test_verify_ags_not_found(boundaries):
    r = verify_ags(boundaries, "Erlangen", "09562000", "NAME", "AGS", layer="gemeinden")
    assert not r.found and not r.matches
