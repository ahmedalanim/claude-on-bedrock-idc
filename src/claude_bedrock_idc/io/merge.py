"""Pure merge logic — no disk I/O.

Kept separate from the writer so deep-merge correctness is unit-tested with plain
in-memory structures.
"""

from __future__ import annotations

import configparser
from copy import deepcopy
from typing import Any


def deep_merge_dict(base: dict[str, Any], incoming: dict[str, Any]) -> dict[str, Any]:
    """Recursively merge ``incoming`` into a copy of ``base``.

    Nested dicts merge key-by-key; non-dict values in ``incoming`` overwrite.
    ``base`` is not mutated.
    """
    result = deepcopy(base)
    for key, value in incoming.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = deep_merge_dict(result[key], value)
        else:
            result[key] = deepcopy(value)
    return result


def merge_ini_section(
    existing_text: str | None,
    section: str,
    values: dict[str, str],
) -> str:
    """Return INI text with ``[section]`` set to ``values``, other sections kept.

    ``existing_text`` may be ``None`` (no prior file). The target section is fully
    replaced with ``values``; all other sections are preserved verbatim in order.
    """
    parser = configparser.ConfigParser()
    # Preserve key case (AWS keys are lowercase but be safe).
    parser.optionxform = str  # type: ignore[assignment]
    if existing_text:
        parser.read_string(existing_text)

    if parser.has_section(section):
        parser.remove_section(section)
    parser.add_section(section)
    for key, value in values.items():
        parser.set(section, key, value)

    from io import StringIO

    buf = StringIO()
    parser.write(buf)
    # configparser writes a trailing blank line after each section; normalize to a
    # single trailing newline for deterministic output.
    return buf.getvalue().rstrip("\n") + "\n"
