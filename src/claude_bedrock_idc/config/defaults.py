"""Locate the canonical default config shipped with the package.

The single source of truth for defaults is ``config.example.yaml`` at the repo
root, mirrored by the field defaults in :mod:`schema`. This helper finds it so
tests and tooling can load the documented defaults.
"""

from __future__ import annotations

from pathlib import Path

EXAMPLE_FILENAME = "config.example.yaml"


def example_config_path() -> Path:
    """Return the path to the shipped ``config.example.yaml`` (repo root)."""
    # src/claude_bedrock_idc/config/defaults.py -> repo root is parents[3]
    return Path(__file__).resolve().parents[3] / EXAMPLE_FILENAME
