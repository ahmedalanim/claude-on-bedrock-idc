"""Load and validate a YAML config file into a :class:`Config`."""

from __future__ import annotations

from pathlib import Path

import yaml
from pydantic import ValidationError

from .schema import Config


class ConfigError(Exception):
    """Raised when a config file cannot be read or fails validation."""


def load_config(path: str | Path) -> Config:
    """Read ``path``, parse YAML, and validate into a :class:`Config`.

    Raises :class:`ConfigError` with a readable message on any failure.
    """
    p = Path(path)
    if not p.is_file():
        raise ConfigError(f"config file not found: {p}")
    try:
        raw = yaml.safe_load(p.read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:  # pragma: no cover - passthrough formatting
        raise ConfigError(f"invalid YAML in {p}: {exc}") from exc
    if raw is None:
        raise ConfigError(f"config file is empty: {p}")
    if not isinstance(raw, dict):
        raise ConfigError(f"config root must be a mapping, got {type(raw).__name__}")
    try:
        return Config.model_validate(raw)
    except ValidationError as exc:
        raise ConfigError(f"config validation failed for {p}:\n{exc}") from exc
