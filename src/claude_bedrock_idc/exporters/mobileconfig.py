"""Wrap the Claude Desktop managed-config dict into a macOS .mobileconfig profile.

Format confirmed against a real app Export (``com.anthropic.claudefordesktop``):

- inner payload ``PayloadType`` = ``com.anthropic.claudefordesktop``
- inner ``PayloadIdentifier`` = ``<payload_identifier>.settings``
- outer ``PayloadType`` = ``Configuration``, ``PayloadIdentifier`` = ``<id>.profile``
- ``PayloadScope`` (``User`` or ``System``) on the outer profile
- **complex values (lists/dicts) are JSON-string-encoded**, not nested plist
  containers — i.e. ``inferenceModels`` / ``banner`` appear as ``<string>`` JSON.
"""

from __future__ import annotations

import json
import plistlib
import uuid
from typing import Any


def _deterministic_uuid(seed: str) -> str:
    return str(uuid.uuid5(uuid.NAMESPACE_URL, f"claudefordesktop/{seed}"))


def _flatten(value: Any) -> Any:
    """Scalars pass through; lists/dicts become compact JSON strings (per the export)."""
    if isinstance(value, (dict, list)):
        return json.dumps(value, separators=(",", ":"), ensure_ascii=False)
    return value


def build_mobileconfig(
    settings: dict[str, Any],
    *,
    payload_identifier: str = "com.anthropic.claudefordesktop",
    organization: str = "My Org",
    scope: str = "User",
) -> bytes:
    """Return a .mobileconfig (XML plist) carrying ``settings`` as a managed payload."""
    inner_payload: dict[str, Any] = {
        "PayloadType": payload_identifier,
        "PayloadIdentifier": f"{payload_identifier}.settings",
        "PayloadUUID": _deterministic_uuid("settings"),
        "PayloadVersion": 1,
        "PayloadDisplayName": "Claude Desktop",
    }
    for key, value in settings.items():
        inner_payload[key] = _flatten(value)

    profile: dict[str, Any] = {
        "PayloadContent": [inner_payload],
        "PayloadDisplayName": "Claude Desktop Third-Party Inference",
        "PayloadIdentifier": f"{payload_identifier}.profile",
        "PayloadType": "Configuration",
        "PayloadUUID": _deterministic_uuid("profile"),
        "PayloadVersion": 1,
        "PayloadOrganization": organization,
        "PayloadScope": scope,
    }
    return plistlib.dumps(profile, sort_keys=False)
