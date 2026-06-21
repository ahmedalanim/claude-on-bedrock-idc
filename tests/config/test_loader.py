from __future__ import annotations

import pytest

from claude_bedrock_idc.config.defaults import example_config_path
from claude_bedrock_idc.config.loader import ConfigError, load_config


def _write(tmp_path, text):
    p = tmp_path / "config.yaml"
    p.write_text(text, encoding="utf-8")
    return p


def test_example_config_validates():
    config = load_config(example_config_path())
    assert config.aws.profile == "my-sso-profile"
    assert config.bedrock.enabled is True
    assert config.models.default == "sonnet"


def test_missing_file(tmp_path):
    with pytest.raises(ConfigError, match="not found"):
        load_config(tmp_path / "nope.yaml")


def test_empty_file(tmp_path):
    p = _write(tmp_path, "")
    with pytest.raises(ConfigError, match="empty"):
        load_config(p)


def test_missing_required_field(tmp_path):
    # aws.profile is required
    p = _write(
        tmp_path,
        "aws:\n  sso:\n    start_url: x\n    sso_region: r\n"
        "    account_id: '1'\n    role_name: n\n",
    )
    with pytest.raises(ConfigError, match="validation failed"):
        load_config(p)


def test_bad_enum_rejected(tmp_path):
    text = (
        "aws:\n  profile: p\n  sso:\n    start_url: x\n    sso_region: r\n"
        "    account_id: '1'\n    role_name: n\n"
        "bedrock:\n  service_tier: turbo\n"
    )
    p = _write(tmp_path, text)
    with pytest.raises(ConfigError):
        load_config(p)


def test_unknown_key_forbidden(tmp_path):
    text = (
        "aws:\n  profile: p\n  bogus: 1\n  sso:\n    start_url: x\n    sso_region: r\n"
        "    account_id: '1'\n    role_name: n\n"
    )
    p = _write(tmp_path, text)
    with pytest.raises(ConfigError):
        load_config(p)


def test_project_scope_requires_project_dir(tmp_path):
    text = (
        "aws:\n  profile: p\n  sso:\n    start_url: x\n    sso_region: r\n"
        "    account_id: '1'\n    role_name: n\n"
        "claude_code:\n  scope: project\n"
    )
    p = _write(tmp_path, text)
    with pytest.raises(ConfigError, match="project_dir"):
        load_config(p)


def test_guardrail_requires_ids(tmp_path):
    text = (
        "aws:\n  profile: p\n  sso:\n    start_url: x\n    sso_region: r\n"
        "    account_id: '1'\n    role_name: n\n"
        "bedrock:\n  guardrail:\n    enabled: true\n"
    )
    p = _write(tmp_path, text)
    with pytest.raises(ConfigError):
        load_config(p)


_AWS = (
    "aws:\n  profile: p\n  sso:\n    start_url: x\n    sso_region: r\n"
    "    account_id: '1'\n    role_name: n\n"
)


def test_cowork_new_enum_rejected(tmp_path):
    p = _write(tmp_path, _AWS + "cowork:\n  telemetry:\n    otlp_protocol: ftp\n")
    with pytest.raises(ConfigError):
        load_config(p)


def test_cowork_unknown_group_key_forbidden(tmp_path):
    # extra="forbid" still bites inside the new sub-models.
    p = _write(tmp_path, _AWS + "cowork:\n  desktop:\n    bogus_toggle: true\n")
    with pytest.raises(ConfigError):
        load_config(p)


def test_cowork_new_groups_parse(tmp_path):
    text = _AWS + (
        "cowork:\n"
        "  model_discovery_enabled: true\n"
        "  desktop:\n    cowork_tab_enabled: false\n    allowed_workspace_folders: ['/w']\n"
        "  telemetry:\n    otlp_protocol: grpc\n    desktop_log_level: debug\n"
        "  updates:\n    enforcement_hours: 24\n"
        "  organization:\n    plugin_settings: {a: 1}\n"
    )
    config = load_config(_write(tmp_path, text))
    assert config.cowork.model_discovery_enabled is True
    assert config.cowork.desktop.cowork_tab_enabled is False
    assert config.cowork.desktop.allowed_workspace_folders == ["/w"]
    assert config.cowork.telemetry.otlp_protocol == "grpc"
    assert config.cowork.updates.enforcement_hours == 24
    assert config.cowork.organization.plugin_settings == {"a": 1}
