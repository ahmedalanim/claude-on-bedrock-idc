from __future__ import annotations

from claude_bedrock_idc.generators.aws_profile import PROFILE_KEYS_ORDER, build_profile


def test_section_and_keys(resolved):
    section, values = build_profile(resolved)
    assert section == "profile my-sso-profile"
    assert list(values.keys()) == list(PROFILE_KEYS_ORDER)
    assert values["sso_start_url"] == "https://my-org.awsapps.com/start"
    assert values["sso_region"] == "us-east-1"
    assert values["sso_account_id"] == "123456789012"
    assert values["sso_role_name"] == "ClaudeCodeBedrockRole"
    assert values["region"] == "us-east-1"
    assert values["output"] == "json"
