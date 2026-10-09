"""Agent config loader — root config.yaml with env overlay."""
from __future__ import annotations

import os

import yaml

_config: dict | None = None


def load_agent_config(path: str | None = None) -> dict:
    """Load shared config (cached). Discovery: arg > CIVICLENS_CONFIG > config.yaml."""
    global _config
    if _config is not None:
        return _config
    resolved = path or os.getenv("CIVICLENS_CONFIG", "config.yaml")
    try:
        with open(resolved) as fh:
            _config = yaml.safe_load(fh) or {}
    except FileNotFoundError as exc:
        raise FileNotFoundError(f"Config not found: {resolved}") from exc
    return _config


def get_section(name: str, default: dict | None = None) -> dict:
    """Return one top-level config section (e.g. 'severity', 'dedup')."""
    return load_agent_config().get(name, default or {})
