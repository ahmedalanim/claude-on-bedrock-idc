"""Byte-for-byte golden comparison for the authoritative deliverables.

The .mobileconfig/.reg wrappers are intentionally excluded (unverified envelope);
they get structural/round-trip tests in tests/exporters/ instead.

Set CBIDC_UPDATE_GOLDEN=1 to rewrite the golden files from current output.
"""

from __future__ import annotations

import json
import os
from pathlib import Path

from claude_bedrock_idc.config.loader import load_config
from claude_bedrock_idc.generators import aws_profile, claude_code, cowork
from claude_bedrock_idc.io.merge import merge_ini_section
from claude_bedrock_idc.mapping.resolve import resolve

GOLDEN = Path(__file__).parent / "golden"
FIXTURES = Path(__file__).parent / "fixtures"
_UPDATE = os.environ.get("CBIDC_UPDATE_GOLDEN") == "1"


def _compare(name: str, actual: str):
    path = GOLDEN / name
    if _UPDATE:
        path.write_text(actual, encoding="utf-8")
    assert actual == path.read_text(encoding="utf-8"), f"golden mismatch: {name}"


def test_aws_config_golden(sample_config):
    inputs = resolve(sample_config)
    section, values = aws_profile.build_profile(inputs)
    text = merge_ini_section(None, section, values)
    _compare("aws_config.ini", text)


def test_settings_golden(sample_config):
    inputs = resolve(sample_config)
    text = json.dumps(claude_code.build_settings(inputs), indent=2, ensure_ascii=False) + "\n"
    _compare("settings.json", text)


def test_cowork_json_golden(sample_config):
    inputs = resolve(sample_config)
    text = json.dumps(cowork.build_cowork(inputs), indent=2, ensure_ascii=False) + "\n"
    _compare("cowork-bedrock.json", text)


def test_cowork_full_golden():
    # Broad-coverage fixture: every optional policy group populated. Proves the full
    # 52-key surface serializes (and locks its key ordering) without disturbing the
    # default cowork-bedrock.json golden above.
    config = load_config(FIXTURES / "config-full.yaml")
    inputs = resolve(config)
    text = json.dumps(cowork.build_cowork(inputs), indent=2, ensure_ascii=False) + "\n"
    _compare("cowork-full.json", text)
