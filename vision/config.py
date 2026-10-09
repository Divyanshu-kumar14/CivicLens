"""Vision config loader (shared root config.yaml)."""
from __future__ import annotations

import yaml


def load_config(path: str = "config.yaml") -> dict:
    """Load the shared YAML config. Raises FileNotFoundError with a hint."""
    try:
        with open(path) as fh:
            return yaml.safe_load(fh)
    except FileNotFoundError as exc:
        raise FileNotFoundError(
            f"Config not found: {path} (copy .env.example / see config.yaml at repo root)"
        ) from exc
