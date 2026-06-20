from __future__ import annotations

from pathlib import Path

from claude_bedrock_idc.io import paths as paths_mod


def test_stage_paths_flat_layout(sample_config):
    sample_config.output.mode = "stage"
    resolved = paths_mod.resolve_paths(sample_config, out_dir_override="/tmp/out")
    assert resolved["aws_config"] == Path("/tmp/out/aws/config")
    assert resolved["claude_code"] == Path("/tmp/out/claude/settings.json")
    assert resolved["cowork_json"] == Path("/tmp/out/cowork/cowork-bedrock.json")
    assert resolved["cowork_reg"].name == "cowork-bedrock.reg"


def test_install_user_scope(sample_config, tmp_path):
    sample_config.output.mode = "install"
    sample_config.claude_code.scope = "user"
    resolved = paths_mod.resolve_paths(sample_config)
    assert resolved["aws_config"] == tmp_path / ".aws" / "config"
    assert resolved["claude_code"] == tmp_path / ".claude" / "settings.json"


def test_install_project_scope(sample_config):
    sample_config.output.mode = "install"
    sample_config.claude_code.scope = "project"
    sample_config.claude_code.project_dir = "/work/repo"
    resolved = paths_mod.resolve_paths(sample_config)
    assert resolved["claude_code"] == Path("/work/repo/.claude/settings.json")


def test_install_local_scope_filename(sample_config):
    sample_config.output.mode = "install"
    sample_config.claude_code.scope = "local"
    sample_config.claude_code.project_dir = "/work/repo"
    resolved = paths_mod.resolve_paths(sample_config)
    assert resolved["claude_code"].name == "settings.local.json"


def test_aws_config_path_override(sample_config):
    sample_config.aws.config_path = "/custom/aws.cfg"
    assert paths_mod.aws_config_path(sample_config) == Path("/custom/aws.cfg")
