from __future__ import annotations

import json
import plistlib

from claude_bedrock_idc.exporters.mobileconfig import build_mobileconfig

_SETTINGS = {
    "inferenceProvider": "bedrock",
    "inferenceCredentialKind": "interactive",
    "inferenceBedrockRegion": "us-east-1",
    "inferenceBedrockSsoStartUrl": "https://x.awsapps.com/start",
    "inferenceBedrockSsoRegion": "us-east-1",
    "inferenceBedrockSsoAccountId": "123456789012",
    "inferenceBedrockSsoRoleName": "Role",
    "inferenceModels": [{"name": "us.anthropic.claude-opus-4-8", "labelOverride": "Opus4.8"}],
    "banner": {"enabled": True, "text": "Internal"},
}


def test_profile_wrapper_and_domain():
    data = build_mobileconfig(_SETTINGS, organization="Org", scope="User")
    parsed = plistlib.loads(data)
    assert parsed["PayloadType"] == "Configuration"
    assert parsed["PayloadIdentifier"] == "com.anthropic.claudefordesktop.profile"
    assert parsed["PayloadOrganization"] == "Org"
    assert parsed["PayloadScope"] == "User"

    inner = parsed["PayloadContent"][0]
    assert inner["PayloadType"] == "com.anthropic.claudefordesktop"
    assert inner["PayloadIdentifier"] == "com.anthropic.claudefordesktop.settings"


def test_scalars_stay_strings():
    inner = plistlib.loads(build_mobileconfig(_SETTINGS))["PayloadContent"][0]
    assert inner["inferenceProvider"] == "bedrock"
    assert inner["inferenceBedrockSsoAccountId"] == "123456789012"


def test_complex_values_json_string_encoded():
    inner = plistlib.loads(build_mobileconfig(_SETTINGS))["PayloadContent"][0]
    # inferenceModels / banner are JSON strings, not nested plist containers.
    assert isinstance(inner["inferenceModels"], str)
    assert json.loads(inner["inferenceModels"]) == _SETTINGS["inferenceModels"]
    assert isinstance(inner["banner"], str)
    assert json.loads(inner["banner"]) == _SETTINGS["banner"]


def test_custom_scope_and_identifier():
    data = build_mobileconfig(_SETTINGS, payload_identifier="com.test.claude", scope="System")
    parsed = plistlib.loads(data)
    assert parsed["PayloadScope"] == "System"
    assert parsed["PayloadIdentifier"] == "com.test.claude.profile"
    assert parsed["PayloadContent"][0]["PayloadType"] == "com.test.claude"


def test_deterministic():
    assert build_mobileconfig(_SETTINGS) == build_mobileconfig(_SETTINGS)
