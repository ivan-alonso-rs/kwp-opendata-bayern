"""Verification of the Amtlicher Gemeindeschlüssel (AGS) against official boundaries.

Why this check exists
---------------------
The AGS selects which LoD2 tiles and which district files are downloaded. A wrong
AGS silently produces a model of the wrong municipality. The value in the config
comes from the LDBV LoD2 index (gemeinde.kml); this module confirms it against a
second official product, the ALKIS Verwaltungsgebiete, on the local machine.

Who decides
-----------
- automated: finding the right file, layer and columns; comparing the keys;
- person:    accepting the result (flag --accept-ags in 01_download.py, which
             sets `ags_verified: true` in the config). The code never sets it alone.
"""

from __future__ import annotations

import re
import zipfile
from dataclasses import dataclass, field
from pathlib import Path

VECTOR_SUFFIXES = (".shp", ".gpkg")


@dataclass
class AgsCheck:
    """Result of the check. `matches` is the only field the script acts on."""

    gemeinde_name: str
    expected_ags: str
    found_ags: list[str] = field(default_factory=list)   # all AGS found under that name
    matches: bool = False                                # expected_ags in found_ags

    @property
    def found(self) -> bool:
        return bool(self.found_ags)


@dataclass
class FieldGuess:
    """Where the municipality name and its key were found inside a zip."""

    dataset: str        # GDAL path, e.g. /vsizip/C:/.../alkis-verwaltung.zip/x/gemeinde.shp
    layer: str | None
    name_field: str
    ags_field: str


# --------------------------------------------------------------------------- #
# 1. Normalising keys
# --------------------------------------------------------------------------- #
def normalize_ags(value) -> str:
    """Bring a key from a data file into the 8-digit AGS form, as a string.

    AGS structure (8 digits):  LL R KK GGG
        LL  Land (09 = Bayern)   R  Regierungsbezirk (5 = Mittelfranken)
        KK  Kreis (72 = Erlangen-Höchstadt)   GGG  Gemeinde (119 = Bubenreuth)
    ARS structure (12 digits): LL R KK VVVV GGG – adds the 4-digit
        Gemeindeverband (VVVV) before the municipality number.
    Hence AGS = ARS[0:5] + ARS[9:12].

    Rules:
    - 7 digits  -> left-pad with "0" (a number stored as integer loses the
                   leading zero of Land codes 01–09, e.g. 9572119)
    - 8 digits  -> unchanged
    - 12 digits -> converted from ARS as above
    - anything else -> ValueError (better to stop than to compare garbage)
    """
    s = str(value).strip()
    if s.endswith(".0"):          # numbers read from DBF files sometimes come as floats
        s = s[:-2]
    if not s.isdigit():
        raise ValueError(f"not a numeric key: {value!r}")
    if len(s) == 7:
        return "0" + s
    if len(s) == 8:
        return s
    if len(s) == 12:
        return s[:5] + s[9:]
    raise ValueError(f"key has {len(s)} digits, expected 7, 8 or 12: {value!r}")


def _try_normalize(value) -> str | None:
    try:
        return normalize_ags(value)
    except ValueError:
        return None


# --------------------------------------------------------------------------- #
# 2. Checking one known dataset/columns
# --------------------------------------------------------------------------- #
def verify_ags(
    boundaries: str | Path,
    gemeinde_name: str,
    expected_ags: str,
    name_field: str,
    ags_field: str,
    layer: str | None = None,
) -> AgsCheck:
    """Look up `gemeinde_name` in the boundaries dataset and compare its AGS.

    boundaries: path to a .shp/.gpkg, or a GDAL virtual path such as
    "/vsizip/C:/.../alkis-verwaltung.zip/folder/file.shp". Keep /vsizip/ paths as
    str: Path() on Windows would turn the forward slashes into backslashes.

    Only the two needed columns are read and no geometry (read_geometry=False):
    a municipality boundary has thousands of vertices we do not need here.
    Names are compared exactly after stripping spaces – no fuzzy matching, so
    "Bubenreuth" never matches "Bubenreuther Weiher".
    """
    import pyogrio

    df = pyogrio.read_dataframe(
        str(boundaries), layer=layer, columns=[name_field, ags_field], read_geometry=False
    )
    names = df[name_field].astype(str).str.strip()
    hits = df.loc[names == gemeinde_name.strip(), ags_field]
    found = sorted({k for k in (_try_normalize(v) for v in hits) if k})
    return AgsCheck(
        gemeinde_name=gemeinde_name,
        expected_ags=expected_ags,
        found_ags=found,
        matches=normalize_ags(expected_ags) in found,
    )


# --------------------------------------------------------------------------- #
# 3. Finding dataset and columns automatically
# --------------------------------------------------------------------------- #
def vector_members(zip_path: Path) -> list[str]:
    """GDAL paths of every .shp/.gpkg inside a zip, including sub-folders.

    Opening each member explicitly (/vsizip/<zip>/<member>) is more robust than
    opening the zip as a whole, which fails when files sit in a sub-folder.
    Only the zip's table of contents is read here – nothing is extracted.
    """
    with zipfile.ZipFile(zip_path) as zf:
        members = [m for m in zf.namelist() if m.lower().endswith(VECTOR_SUFFIXES)]
    return [f"/vsizip/{zip_path.as_posix()}/{m}" for m in sorted(members)]


def detect_fields(zip_path: Path, gemeinde_name: str) -> list[FieldGuess]:
    """Find every (dataset, layer, name column, key column) where the name occurs.

    Heuristic, in plain words:
    1. for every vector file and layer in the zip, read the attribute table only;
    2. a *name column* is a text column containing exactly `gemeinde_name`;
    3. a *key column* is a column whose value in those rows is a valid AGS/ARS
       (7, 8 or 12 digits, see normalize_ags);
    4. return all combinations found, so the caller can show them to a person.
    Typically this finds one layer of municipalities. If it finds several (e.g.
    also a Verwaltungsgemeinschaft with the same name), the script prints all.
    """
    import pandas as pd
    import pyogrio

    guesses: list[FieldGuess] = []
    for dataset in vector_members(zip_path):
        for layer, _geom in pyogrio.list_layers(dataset):
            df = pyogrio.read_dataframe(dataset, layer=layer, read_geometry=False)
            # object = classic pandas text column; is_string_dtype covers pandas >= 3
            text_cols = [c for c in df.columns
                         if df[c].dtype == object or pd.api.types.is_string_dtype(df[c])]
            for name_col in text_cols:
                rows = df[df[name_col].astype(str).str.strip() == gemeinde_name]
                if rows.empty:
                    continue
                for key_col in df.columns:
                    if key_col == name_col:
                        continue
                    if all(_try_normalize(v) for v in rows[key_col]):
                        guesses.append(FieldGuess(dataset, layer, name_col, key_col))
    return guesses


def suggest_ags_field(guesses: list[FieldGuess]) -> FieldGuess | None:
    """Prefer a key column whose name looks like a key (ags, ars, sch, schluessel).

    If no column name looks like a key, the first guess is returned. The choice
    is printed by the script, so a person can see and overrule it.
    """
    if not guesses:
        return None
    pattern = re.compile(r"(ags|ars|sch|schl|key|kenn)", re.IGNORECASE)
    for g in guesses:
        if pattern.search(g.ags_field):
            return g
    return guesses[0]
