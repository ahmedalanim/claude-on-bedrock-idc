"""Wrap the Claude Desktop managed-config dict into a Windows .reg file.

Format confirmed against a real exported ``Claude.reg`` and the ``Claude.admx``
policy definitions:

- key path ``HKEY_CURRENT_USER\\SOFTWARE\\Policies\\Claude`` (or HKLM)
- every value is a quoted ``REG_SZ`` string
- complex values (``inferenceModels`` / ``banner``) are **JSON-string-encoded** and
  embedded as escaped strings (not ``REG_MULTI_SZ``)

The file is written by the writer as UTF-16LE with a BOM, which RegEdit requires.
"""

from __future__ import annotations

import json
from typing import Any

_HIVE_FULL = {"HKLM": "HKEY_LOCAL_MACHINE", "HKCU": "HKEY_CURRENT_USER"}
_KEY_SUFFIX = r"SOFTWARE\Policies\Claude"


def _escape(value: str) -> str:
    # Order matters: escape backslashes before quotes.
    return value.replace("\\", "\\\\").replace('"', '\\"')


def _value_literal(value: Any) -> str:
    if isinstance(value, (dict, list)):
        text = json.dumps(value, separators=(",", ":"), ensure_ascii=False)
    elif isinstance(value, bool):
        text = "true" if value else "false"
    else:
        text = str(value)
    return f'"{_escape(text)}"'


def build_reg(settings: dict[str, Any], *, hive: str = "HKCU") -> str:
    """Return a Windows .reg file body carrying ``settings`` under the Claude policy key."""
    key_path = f"{_HIVE_FULL[hive]}\\{_KEY_SUFFIX}"

    lines = ["Windows Registry Editor Version 5.00", "", f"[{key_path}]"]
    for key, value in settings.items():
        lines.append(f'"{key}"={_value_literal(value)}')
    # .reg files conventionally use CRLF.
    return "\r\n".join(lines) + "\r\n"
