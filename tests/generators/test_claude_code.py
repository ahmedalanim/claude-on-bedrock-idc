from __future__ import annotations

from claude_bedrock_idc.generators.claude_code import build_settings
from claude_bedrock_idc.mapping.resolve import resolve


def _settings(config):
    return build_settings(resolve(config))


def test_bedrock_env_and_pins(sample_config):
    s = _settings(sample_config)
    env = s["env"]
    assert env["CLAUDE_CODE_USE_BEDROCK"] == "1"
    assert env["AWS_PROFILE"] == "my-sso-profile"
    assert env["AWS_REGION"] == "us-east-1"
    assert env["ANTHROPIC_DEFAULT_OPUS_MODEL"] == "us.anthropic.claude-opus-4-8"
    assert env["ANTHROPIC_DEFAULT_SONNET_MODEL"] == "us.anthropic.claude-sonnet-4-6"
    assert env["ANTHROPIC_DEFAULT_HAIKU_MODEL"] == "us.anthropic.claude-haiku-4-5-20251001-v1:0"


def test_aws_auth_refresh_top_level_not_in_env(sample_config):
    s = _settings(sample_config)
    assert s["awsAuthRefresh"] == "aws sso login --profile my-sso-profile"
    assert "awsAuthRefresh" not in s["env"]


def test_auto_refresh_false_omits(sample_config):
    sample_config.aws.sso.auto_refresh = False
    s = _settings(sample_config)
    assert "awsAuthRefresh" not in s


def test_model_pin_default(sample_config):
    s = _settings(sample_config)
    assert s["model"] == "us.anthropic.claude-sonnet-4-6"
    sample_config.models.pin_default = False
    assert _settings(sample_config)["model"] == "sonnet"


def test_guardrail_headers(sample_config):
    sample_config.bedrock.guardrail.enabled = True
    sample_config.bedrock.guardrail.identifier = "gr-123"
    sample_config.bedrock.guardrail.version = "1"
    env = _settings(sample_config)["env"]
    headers = env["ANTHROPIC_CUSTOM_HEADERS"]
    assert "X-Amzn-Bedrock-GuardrailIdentifier: gr-123" in headers
    assert "X-Amzn-Bedrock-GuardrailVersion: 1" in headers


def test_optional_extras_only_when_set(sample_config):
    env = _settings(sample_config)["env"]
    assert "ANTHROPIC_BEDROCK_SERVICE_TIER" not in env
    assert "ANTHROPIC_BEDROCK_BASE_URL" not in env
    assert "DISABLE_PROMPT_CACHING" not in env

    sample_config.bedrock.service_tier = "priority"
    sample_config.bedrock.base_url = "https://example"
    sample_config.bedrock.prompt_caching = "disabled"
    env = _settings(sample_config)["env"]
    assert env["ANTHROPIC_BEDROCK_SERVICE_TIER"] == "priority"
    assert env["ANTHROPIC_BEDROCK_BASE_URL"] == "https://example"
    assert env["DISABLE_PROMPT_CACHING"] == "1"


def test_permissions_passthrough_and_empty_omitted(sample_config):
    assert "permissions" not in _settings(sample_config)
    sample_config.claude_code.permissions.allow = ["Bash(npm run test:*)"]
    s = _settings(sample_config)
    assert s["permissions"] == {"allow": ["Bash(npm run test:*)"]}


def test_extra_env_passthrough(sample_config):
    sample_config.claude_code.extra_env = {"FOO": "bar"}
    assert _settings(sample_config)["env"]["FOO"] == "bar"


def test_model_overrides(sample_config):
    sample_config.models.overrides = {"claude-opus-4-6": "arn:aws:bedrock:...:opus"}
    s = _settings(sample_config)
    assert s["modelOverrides"] == {"claude-opus-4-6": "arn:aws:bedrock:...:opus"}
