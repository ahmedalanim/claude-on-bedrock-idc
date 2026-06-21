from __future__ import annotations

import json

from claude_bedrock_idc.config.defaults import example_config_path
from claude_bedrock_idc.pipeline import generate, run


def test_generate_produces_all_targets(sample_config):
    inputs, artifacts = generate(sample_config)
    assert artifacts.aws_profile_section is not None
    assert artifacts.code_settings is not None
    assert artifacts.cowork_settings is not None


def test_claude_code_disabled_skips(sample_config):
    sample_config.claude_code.enabled = False
    _, artifacts = generate(sample_config)
    assert artifacts.code_settings is None


def test_cowork_disabled_skips(sample_config):
    sample_config.cowork.enabled = False
    _, artifacts = generate(sample_config)
    assert artifacts.cowork_settings is None


def test_run_stage_writes_files(tmp_path):
    out = tmp_path / "gen"
    result = run(
        example_config_path(),
        out_dir_override=str(out),
        mode_override="stage",
        cowork_formats_override=["json", "mobileconfig", "reg"],
    )
    assert result.check.ok
    names = {p.name for p in result.written}
    assert {
        "config",
        "settings.json",
        "cowork-bedrock.json",
        "cowork-bedrock.mobileconfig",
        "cowork-bedrock.reg",
    } <= names
    settings = json.loads((out / "claude" / "settings.json").read_text())
    assert settings["env"]["AWS_PROFILE"] == "my-sso-profile"


def test_run_check_only_writes_nothing(tmp_path):
    out = tmp_path / "gen"
    result = run(
        example_config_path(), out_dir_override=str(out), mode_override="stage", check_only=True
    )
    assert result.check.ok
    assert result.written == []
    assert not out.exists()


def test_run_check_only_fails_on_inconsistency(tmp_path):
    # Build a config where Claude Code is enabled but AWS profile generation is off.
    cfg = tmp_path / "config.yaml"
    cfg.write_text(
        "aws:\n  profile: p\n  write_aws_config: false\n  sso:\n    start_url: https://x\n"
        "    sso_region: us-east-1\n    account_id: '123456789012'\n    role_name: Role\n",
        encoding="utf-8",
    )
    result = run(cfg, mode_override="stage", check_only=True)
    assert not result.check.ok
