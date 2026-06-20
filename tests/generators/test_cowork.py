from __future__ import annotations

from claude_bedrock_idc.config.schema import CoworkModel
from claude_bedrock_idc.generators.cowork import build_cowork
from claude_bedrock_idc.mapping.resolve import resolve


def _cowork(config):
    return build_cowork(resolve(config))


def test_all_keys_present(sample_config):
    c = _cowork(sample_config)
    assert c["inferenceProvider"] == "bedrock"
    assert c["inferenceCredentialKind"] == "interactive"
    assert c["inferenceBedrockRegion"] == "us-east-1"
    assert c["inferenceBedrockSsoStartUrl"] == "https://my-org.awsapps.com/start"
    assert c["inferenceBedrockSsoRegion"] == "us-east-1"
    assert c["inferenceBedrockSsoAccountId"] == "123456789012"
    assert c["inferenceBedrockSsoRoleName"] == "ClaudeCodeBedrockRole"


def test_models_are_objects(sample_config):
    c = _cowork(sample_config)
    assert c["inferenceModels"][0] == {"name": "us.anthropic.claude-opus-4-8"}
    assert all("name" in m for m in c["inferenceModels"])


def test_model_label_override(sample_config):
    sample_config.cowork.models = [
        CoworkModel(name="us.anthropic.claude-opus-4-8", label="Opus4.8")
    ]
    c = _cowork(sample_config)
    assert c["inferenceModels"] == [
        {"name": "us.anthropic.claude-opus-4-8", "labelOverride": "Opus4.8"}
    ]


def test_credential_kind_configurable(sample_config):
    sample_config.cowork.credential_kind = "vendor-profile"
    assert _cowork(sample_config)["inferenceCredentialKind"] == "vendor-profile"


def test_service_tier_only_when_set(sample_config):
    assert "inferenceBedrockServiceTier" not in _cowork(sample_config)
    sample_config.cowork.service_tier = "priority"
    assert _cowork(sample_config)["inferenceBedrockServiceTier"] == "priority"


def test_banner_only_when_enabled(sample_config):
    assert "banner" not in _cowork(sample_config)
    sample_config.cowork.banner.enabled = True
    sample_config.cowork.banner.text = "Internal Use Only"
    sample_config.cowork.banner.background_color = "#111A97"
    sample_config.cowork.banner.text_color = "#ECECEF"
    sample_config.cowork.banner.link_url = "https://internal.com"
    banner = _cowork(sample_config)["banner"]
    assert banner == {
        "backgroundColor": "#111A97",
        "textColor": "#ECECEF",
        "enabled": True,
        "text": "Internal Use Only",
        "linkUrl": "https://internal.com",
    }


def test_no_claude_code_keys_leak(sample_config):
    c = _cowork(sample_config)
    for key in ("env", "CLAUDE_CODE_USE_BEDROCK", "awsAuthRefresh", "AWS_PROFILE"):
        assert key not in c
