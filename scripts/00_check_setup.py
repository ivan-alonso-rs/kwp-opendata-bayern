"""Step 00 – check that the working environment is ready.

Usage (from the repository root, with the "kwp" conda environment active):

    python scripts/00_check_setup.py --gemeinde bubenreuth

What it checks, in order:
  1. Python version (>= 3.11)
  2. Required Python packages can be imported, and their versions
  3. GDAL is available and has the GML driver (needed to read CityGML LoD2 in M2)
  4. PROJ knows EPSG:25832 (official CRS of Bavarian geodata)
  5. The municipality configuration loads (config/defaults.yaml + config/<gemeinde>.yaml)
  6. PostGIS: connection, PostgreSQL and PostGIS versions, CREATE privilege

Nothing is written to disk or to the database. Exit code 0 = all checks passed.
"""

from __future__ import annotations

import argparse
import importlib
import sys
import traceback
from pathlib import Path

# Make the local package importable even if "pip install -e ." was not run
# (e.g. when the conda environment was created outside the repository folder).
SRC_DIR = Path(__file__).resolve().parents[1] / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

# Collected results: (check name, passed?, detail)
RESULTS: list[tuple[str, bool, str]] = []


def record(name: str, ok: bool, detail: str = "") -> None:
    RESULTS.append((name, ok, detail))


# ---------------------------------------------------------------- 1. Python
def check_python() -> None:
    v = sys.version_info
    record("Python >= 3.11", v >= (3, 11), f"{v.major}.{v.minor}.{v.micro}")


# ---------------------------------------------------------------- 2. packages
PACKAGES = [
    "geopandas", "shapely", "pyproj", "pyogrio", "rasterio",
    "sqlalchemy", "psycopg2", "geoalchemy2", "yaml", "numpy", "pandas",
]


def check_packages() -> None:
    for name in PACKAGES:
        try:
            mod = importlib.import_module(name)
            record(f"import {name}", True, getattr(mod, "__version__", "ok"))
        except Exception as exc:  # noqa: BLE001 – we want to report any import failure
            record(f"import {name}", False, f"{type(exc).__name__}: {exc}")


# ---------------------------------------------------------------- 3. GDAL
def check_gdal() -> None:
    try:
        import pyogrio

        record("GDAL (via pyogrio)", True, pyogrio.__gdal_version_string__)
        drivers = pyogrio.list_drivers()
        # CityGML LoD2 files are read through GDAL's generic GML driver.
        record("GDAL driver GML (CityGML)", "GML" in drivers, "available" if "GML" in drivers else "missing")
        record("GDAL driver GPKG", "GPKG" in drivers, "available" if "GPKG" in drivers else "missing")
    except Exception as exc:  # noqa: BLE001
        record("GDAL (via pyogrio)", False, f"{type(exc).__name__}: {exc}")


# ---------------------------------------------------------------- 4. PROJ
def check_proj(epsg: int) -> None:
    try:
        from pyproj import CRS, Transformer

        crs = CRS.from_epsg(epsg)
        # Transform a known point (Erlangen city centre, approx.) WGS84 -> EPSG:25832
        # to confirm the transformation pipeline works, not just the CRS lookup.
        x, y = Transformer.from_crs(4326, epsg, always_xy=True).transform(11.004, 49.598)
        plausible = 640_000 < x < 660_000 and 5_490_000 < y < 5_510_000
        record(f"PROJ EPSG:{epsg}", plausible, f"{crs.name}; test point -> ({x:.0f}, {y:.0f})")
    except Exception as exc:  # noqa: BLE001
        record(f"PROJ EPSG:{epsg}", False, f"{type(exc).__name__}: {exc}")


# ---------------------------------------------------------------- 5. config
def check_config(gemeinde: str) -> dict | None:
    try:
        from kwp.config import load_config

        cfg = load_config(gemeinde)
        g = cfg["gemeinde"]
        ags_note = "verified" if g.get("ags_verified") else "NOT verified yet (M1)"
        record("config loads", True, f"{g['name']} | AGS {g.get('ags')} ({ags_note}) | CRS {cfg['crs']}")
        return cfg
    except Exception as exc:  # noqa: BLE001
        record("config loads", False, f"{type(exc).__name__}: {exc}")
        return None


# ---------------------------------------------------------------- 6. PostGIS
def check_postgis() -> None:
    try:
        from sqlalchemy import text

        from kwp.config import load_env
        from kwp.db import describe_target, get_engine

        loaded = load_env()
        if "PGPASSWORD" not in loaded:
            record(".env file", False, "missing or without PGPASSWORD – copy .env.example to .env")
        else:
            record(".env file", True, "loaded (password not shown)")

        engine = get_engine()
        with engine.connect() as con:
            pg = con.execute(text("SHOW server_version")).scalar()
            record("PostgreSQL connection", True, f"{describe_target()} | server {pg}")

            postgis = con.execute(
                text("SELECT extversion FROM pg_extension WHERE extname = 'postgis'")
            ).scalar()
            record("PostGIS extension", postgis is not None,
                   f"version {postgis}" if postgis else "not installed: run CREATE EXTENSION postgis;")

            can_create = con.execute(
                text("SELECT has_database_privilege(current_user, current_database(), 'CREATE')")
            ).scalar()
            record("CREATE privilege (schemas)", bool(can_create), "yes" if can_create else "no")
    except Exception as exc:  # noqa: BLE001
        # Show only the first line: driver errors can be long; never print credentials.
        record("PostgreSQL connection", False, f"{type(exc).__name__}: {str(exc).splitlines()[0]}")


# ---------------------------------------------------------------- report
def main() -> int:
    parser = argparse.ArgumentParser(description="Check the kwp working environment.")
    parser.add_argument("--gemeinde", default="bubenreuth", help="municipality key (config/<key>.yaml)")
    parser.add_argument("--skip-db", action="store_true", help="skip the PostGIS checks")
    args = parser.parse_args()

    check_python()
    check_packages()
    check_gdal()
    cfg = check_config(args.gemeinde)
    check_proj(int(cfg["crs"]) if cfg else 25832)
    if not args.skip_db:
        check_postgis()

    width = max(len(name) for name, _, _ in RESULTS)
    print("\nkwp-opendata-bayern – setup check\n" + "-" * (width + 40))
    for name, ok, detail in RESULTS:
        print(f"{'OK  ' if ok else 'FAIL'}  {name:<{width}}  {detail}")
    failed = [name for name, ok, _ in RESULTS if not ok]
    print("-" * (width + 40))
    print("All checks passed." if not failed else f"{len(failed)} check(s) failed: {', '.join(failed)}")
    return 0 if not failed else 1


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception:  # noqa: BLE001 – last-resort guard so the user sees a clear trace
        traceback.print_exc()
        sys.exit(2)
