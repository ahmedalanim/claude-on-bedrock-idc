from __future__ import annotations

from claude_bedrock_idc.pipeline import generate, validate
from claude_bedrock_idc.validate import consistency


def test_passes_for_consistent_config(sample_config):
    inputs, artifacts = generate(sample_config)
    result = validate(inputs, artifacts)
    assert result.ok, result.errors


def test_fails_when_profile_missing_but_code_enabled(sample_config):
    # Claude Code enabled but no ~/.aws/config profile generated -> dangling AWS_PROFILE.
    sample_config.aws.write_aws_config = False
    inputs, artifacts = generate(sample_config)
    result = validate(inputs, artifacts)
    assert not result.ok
    assert any("no ~/.aws/config profile" in e for e in result.errors)


def test_fails_on_partial_cowork_sso(resolved):
    # Hand-craft an incomplete cowork settings dict.
    cowork_settings = {
        "inferenceBedrockSsoStartUrl": "https://x",
        "inferenceBedrockSsoRegion": "",  # missing
        "inferenceBedrockSsoAccountId": "1",
        "inferenceBedrockSsoRoleName": "r",
        "inferenceCredentialKind": "aws-sso",
    }
    result = consistency.check(
        resolved, aws_profile_section=None, code_settings=None, cowork_settings=cowork_settings
    )
    assert not result.ok
    assert any("incomplete SSO" in e for e in result.errors)


def test_fails_when_credential_kind_missing(resolved):
    cowork_settings = {
        "inferenceBedrockSsoStartUrl": "https://x",
        "inferenceBedrockSsoRegion": "r",
        "inferenceBedrockSsoAccountId": "1",
        "inferenceBedrockSsoRoleName": "n",
        "inferenceCredentialKind": "",
    }
    result = consistency.check(
        resolved, aws_profile_section=None, code_settings=None, cowork_settings=cowork_settings
    )
    assert not result.ok
    assert any("inferenceCredentialKind" in e for e in result.errors)


def test_detects_sso_mismatch(sample_config):
    sample_config.cowork.sso_account_id = "999999999999"  # differs from aws.sso.account_id
    inputs, artifacts = generate(sample_config)
    result = validate(inputs, artifacts)
    assert not result.ok
    assert any("sso mismatch" in e for e in result.errors)


def test_next_steps_for_manual_login(sample_config):
    sample_config.aws.sso.auto_refresh = False
    inputs, artifacts = generate(sample_config)
    result = validate(inputs, artifacts)
    assert result.ok
    assert any("aws sso login" in s for s in result.next_steps)
