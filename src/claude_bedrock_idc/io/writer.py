"""The only disk-touching module: atomic writes, backups, and merge orchestration.

Merge *logic* lives in :mod:`merge`; this module reads existing files, delegates,
and writes results atomically.
"""

from __future__ import annotations

import json
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from . import merge


def _atomic_write_bytes(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=str(path.parent), prefix=f".{path.name}.", suffix=".tmp")
    try:
        with os.fdopen(fd, "wb") as fh:
            fh.write(data)
        os.replace(tmp, path)
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)


def _backup(path: Path) -> Path | None:
    if not path.exists():
        return None
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    dest = path.with_name(f"{path.name}.bak.{stamp}")
    dest.write_bytes(path.read_bytes())
    return dest


def write_json(path: Path, content: dict[str, Any], *, merge_existing: bool, backup: bool) -> None:
    """Write ``content`` as pretty JSON, optionally deep-merging into an existing file."""
    final = content
    if merge_existing and path.exists():
        try:
            existing = json.loads(path.read_text(encoding="utf-8"))
            if isinstance(existing, dict):
                final = merge.deep_merge_dict(existing, content)
        except (json.JSONDecodeError, OSError):
            final = content
    if backup:
        _backup(path)
    text = json.dumps(final, indent=2, ensure_ascii=False) + "\n"
    _atomic_write_bytes(path, text.encode("utf-8"))


def write_ini_section(
    path: Path,
    section: str,
    values: dict[str, str],
    *,
    merge_existing: bool,
    backup: bool,
) -> None:
    """Write/merge a single INI ``[section]`` into ``path``, preserving siblings."""
    existing = None
    if merge_existing and path.exists():
        try:
            existing = path.read_text(encoding="utf-8")
        except OSError:
            existing = None
    if backup:
        _backup(path)
    text = merge.merge_ini_section(existing, section, values)
    _atomic_write_bytes(path, text.encode("utf-8"))


def write_text(path: Path, text: str, *, encoding: str = "utf-8", backup: bool) -> None:
    """Write raw text (used for .reg as utf-16-le, .mobileconfig handled via bytes)."""
    if backup:
        _backup(path)
    _atomic_write_bytes(path, text.encode(encoding))


def write_bytes(path: Path, data: bytes, *, backup: bool) -> None:
    if backup:
        _backup(path)
    _atomic_write_bytes(path, data)
