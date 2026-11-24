"""Verification of the Amtlicher Gemeindeschlüssel (AGS) against official boundaries.

>>> TO BE WRITTEN BY IVAN (authorship share, see AUTHORS.md) <<<
The signature, the return type and the tests (tests/test_ags.py) are fixed;
the body of `verify_ags` is yours. Run `pytest tests/test_ags.py -v` until green.

Why this check exists
---------------------
The AGS selects which LoD2 tiles and which district files are downloaded. A wrong
AGS silently produces a model of the wrong municipality. The value in the config
comes from the LDBV LoD2 index (gemeinde.kml); this function confirms it against
a second official product, the ALKIS Verwaltungsgebiete, on the local machine.
The final decision (setting `ags_verified: true` in the config) stays with a person.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path


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


def normalize_ags(value) -> str:
    """Bring a key from a data file into the 8-digit AGS form, as a string.

    Specification (all covered by tests):
    - int 9572119        -> "09572119"   (leading zero lost when stored as number)
    - str " 09572119 "   -> "09572119"   (whitespace)
    - str "095720000119" -> "09572119"   (12-digit Regionalschlüssel ARS:
                                          AGS = ARS[0:5] + ARS[9:12]; the digits
                                          5–8 are the Verband/Gemeindeverband key)
    - a 7-digit value (number that lost its leading zero) is left-padded with "0"
    - non-digits, or any length other than 7, 8 or 12 digits -> ValueError
    """
    raise NotImplementedError("Ivan: implement normalize_ags")


def verify_ags(
    boundaries: str | Path,
    gemeinde_name: str,
    expected_ags: str,
    name_field: str,
    ags_field: str,
    layer: str | None = None,
) -> AgsCheck:
    """Look up `gemeinde_name` in the boundaries file and compare its AGS.

    Parameters
    ----------
    boundaries   path to a .shp/.gpkg, or a GDAL virtual path for a zip such as
                 "/vsizip/C:/.../alkis-verwaltung.zip" (pyogrio.read_dataframe
                 accepts both). Keep /vsizip/ paths as str: Path() on Windows
                 would turn the forward slashes into backslashes.
    gemeinde_name exact name as in the config, e.g. "Bubenreuth".
    expected_ags  8-digit AGS from the config.
    name_field, ags_field, layer  column/layer names; they come from
                 config/sources.yaml because they depend on the provider's file.

    Specification:
    - read only the two columns needed (pyogrio: columns=[...], read_geometry=False
      — faster, and geometry is not needed here);
    - compare names exactly after stripping whitespace (no fuzzy matching: a
      municipality called "Bubenreuth" must not match "Bubenreuther Weiher");
    - normalise every AGS found with `normalize_ags`, drop duplicates, sort;
    - matches = normalize_ags(expected_ags) in found_ags;
    - name not found -> AgsCheck with found_ags=[] and matches=False (no exception:
      the calling script decides what to print).
    """
    raise NotImplementedError("Ivan: implement verify_ags")
