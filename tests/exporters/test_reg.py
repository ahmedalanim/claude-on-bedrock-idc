from __future__ import annotations

from claude_bedrock_idc.exporters.reg import build_reg

_SETTINGS = {
    "inferenceProvider": "bedrock",
    "inferenceCredentialKind": "interactive",
    "inferenceBedrockSsoStartUrl": "https://x.awsapps.com/start",
    "inferenceModels": [{"name": "a", "labelOverride": "A"}],
}


def test_header_and_key_path_hkcu():
    text = build_reg(_SETTINGS, hive="HKCU")
    assert text.startswith("Windows Registry Editor Version 5.00")
    assert r"[HKEY_CURRENT_USER\SOFTWARE\Policies\Claude]" in text


def test_hklm_hive():
    text = build_reg(_SETTINGS, hive="HKLM")
    assert r"[HKEY_LOCAL_MACHINE\SOFTWARE\Policies\Claude]" in text


def test_scalar_quoted():
    text = build_reg(_SETTINGS)
    assert '"inferenceProvider"="bedrock"' in text
    assert '"inferenceCredentialKind"="interactive"' in text


def test_list_is_json_string_not_multi_sz():
    text = build_reg(_SETTINGS)
    # JSON-string-encoded with escaped quotes, matching the real export.
    assert '"inferenceModels"="[{\\"name\\":\\"a\\",\\"labelOverride\\":\\"A\\"}]"' in text
    assert "hex(7)" not in text


def test_crlf_line_endings():
    assert "\r\n" in build_reg(_SETTINGS)
