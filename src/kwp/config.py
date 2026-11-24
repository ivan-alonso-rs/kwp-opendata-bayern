"""Load and merge YAML configuration and the local .env file.

Design:
- config/defaults.yaml holds settings shared by all municipalities.
- config/<gemeinde>.yaml holds municipality-specific settings and overrides defaults.
- .env (git-ignored) holds secrets such as the database password.

Nothing in this module touches the network or the database.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import yaml

# Repository root = two levels above this file (src/kwp/config.py -> repo/)
REPO_ROOT = Path(__file__).resolve().parents[2]
CONFIG_DIR = REPO_ROOT / "config"


def _deep_merge(base: dict, override: dict) -> dict:
    """Return a new dict where keys of `override` replace those of `base`.

    Nested dicts are merged recursively, so a municipality file can override a
    single value (e.g. one threshold) without repeating the whole section.
    """
    merged = dict(base)
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = _deep_merge(merged[key], value)
        else:
            merged[key] = value
    return merged


def _read_yaml(path: Path) -> dict:
    with path.open(encoding="utf-8") as fh:
        return yaml.safe_load(fh) or {}


def available_gemeinden() -> list[str]:
    """List municipality keys for which a config file exists.

    defaults.yaml and sources.yaml are shared files, not municipalities.
    """
    shared = {"defaults", "sources"}
    return sorted(p.stem for p in CONFIG_DIR.glob("*.yaml") if p.stem not in shared)


def load_config(gemeinde: str) -> dict[str, Any]:
    """Load defaults + municipality config and check the minimum required keys.

    Raises FileNotFoundError if the municipality has no config file and
    ValueError if required keys are missing.
    """
    gemeinde = gemeinde.lower()
    path = CONFIG_DIR / f"{gemeinde}.yaml"
    if not path.exists():
        raise FileNotFoundError(
            f"No config for '{gemeinde}'. Available: {', '.join(available_gemeinden())}"
        )

    cfg = _deep_merge(_read_yaml(CONFIG_DIR / "defaults.yaml"), _read_yaml(path))

    required = [("gemeinde", "name"), ("gemeinde", "key"), ("crs",)]
    for keys in required:
        node: Any = cfg
        for k in keys:
            if not isinstance(node, dict) or k not in node:
                raise ValueError(f"Missing config key: {'.'.join(keys)} in {path.name}")
            node = node[k]
    return cfg


def load_env(path: Path | None = None) -> dict[str, str]:
    """Read KEY=VALUE pairs from .env into os.environ (without overwriting).

    A tiny parser is used on purpose to avoid an extra dependency. Lines starting
    with '#' and empty lines are ignored. Existing environment variables win, so
    a value set in the shell is never silently replaced.
    """
    path = path or REPO_ROOT / ".env"
    loaded: dict[str, str] = {}
    if not path.exists():
        return loaded
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key, value = key.strip(), value.strip().strip('"').strip("'")
        os.environ.setdefault(key, value)
        loaded[key] = value
    return loaded
