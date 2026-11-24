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


# ---------- detect_fields (automatic search inside a zip) ------------------
def test_detect_fields_in_nested_zip(tmp_path):
    """The official zip may keep shapefiles in a sub-folder; detection must find them."""
    import zipfile

    gpd = pytest.importorskip("geopandas")
    from shapely.geometry import box

    from kwp.ags import detect_fields, suggest_ags_field

    shp_dir = tmp_path / "shp"
    shp_dir.mkdir()
    gpd.GeoDataFrame(
        {"OBJID": ["A1", "A2"], "GEN": ["Bubenreuth", "Hemhofen"], "AGS": ["09572119", "09572130"]},
        geometry=[box(0, 0, 1, 1), box(1, 0, 2, 1)], crs=25832,
    ).to_file(shp_dir / "gemeinde.shp")
    zpath = tmp_path / "verwaltung.zip"
    with zipfile.ZipFile(zpath, "w") as zf:
        for f in shp_dir.iterdir():
            zf.write(f, arcname=f"daten/{f.name}")      # nested folder on purpose

    guesses = detect_fields(zpath, "Bubenreuth")
    best = suggest_ags_field(guesses)
    assert best is not None
    assert (best.name_field, best.ags_field) == ("GEN", "AGS")
    r = verify_ags(best.dataset, "Bubenreuth", "09572119", best.name_field, best.ags_field,
                   layer=best.layer)
    assert r.matches
