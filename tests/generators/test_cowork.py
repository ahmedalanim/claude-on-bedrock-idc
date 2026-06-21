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


# --- Optional policy groups: omit-when-unset by default, emitted when set -----------

# The default config sets none of the new keys, so the output is exactly the core set.
_DEFAULT_KEYS = {
    "inferenceProvider",
    "inferenceCredentialKind",
    "inferenceBedrockRegion",
    "inferenceBedrockSsoStartUrl",
    "inferenceBedrockSsoRegion",
    "inferenceBedrockSsoAccountId",
    "inferenceBedrockSsoRoleName",
    "inferenceModels",
}


def test_default_emits_only_core_keys(sample_config):
    assert set(_cowork(sample_config)) == _DEFAULT_KEYS


def test_seven_core_keys_emitted_even_when_null(sample_config):
    # The resolver normally fills SSO via inheritance; null them and the keys still appear
    # (unconditional), so the managed-config shape never silently changes.
    sample_config.aws.sso.start_url = ""
    sample_config.cowork.sso_start_url = None
    c = _cowork(sample_config)
    assert "inferenceBedrockSsoStartUrl" in c


def test_desktop_toggles(sample_config):
    d = sample_config.cowork.desktop
    d.extensions_enabled = False
    d.local_dev_mcp_enabled = False
    d.cowork_tab_enabled = True
    d.allowed_workspace_folders = ["/work", "/src"]
    c = _cowork(sample_config)
    assert c["isDesktopExtensionEnabled"] is False
    assert c["isLocalDevMcpEnabled"] is False
    assert c["coworkTabEnabled"] is True
    assert c["allowedWorkspaceFolders"] == ["/work", "/src"]
    # Unset toggles stay absent.
    assert "autoModeEnabled" not in c


def test_empty_lists_omitted(sample_config):
    sample_config.cowork.desktop.allowed_workspace_folders = []
    sample_config.cowork.tools.disabled_builtin = []
    c = _cowork(sample_config)
    assert "allowedWorkspaceFolders" not in c
    assert "disabledBuiltinTools" not in c


def test_telemetry_keys(sample_config):
    t = sample_config.cowork.telemetry
    t.otlp_endpoint = "https://collector:4318"
    t.otlp_protocol = "grpc"
    t.desktop_log_level = "debug"
    t.disable_nonessential = True
    c = _cowork(sample_config)
    assert c["otlpEndpoint"] == "https://collector:4318"
    assert c["otlpProtocol"] == "grpc"
    assert c["otlpDesktopLogLevel"] == "debug"
    assert c["disableNonessentialTelemetry"] is True


def test_updates_and_helper_ints(sample_config):
    sample_config.cowork.updates.enforcement_hours = 72
    sample_config.cowork.credential_helper.command = "/usr/local/bin/cred"
    sample_config.cowork.credential_helper.ttl_sec = 1800
    c = _cowork(sample_config)
    assert c["autoUpdaterEnforcementHours"] == 72
    assert c["inferenceCredentialHelper"] == "/usr/local/bin/cred"
    assert c["inferenceCredentialHelperTtlSec"] == 1800


def test_bedrock_extras(sample_config):
    b = sample_config.cowork.bedrock
    b.profile = "my-prof"
    b.bearer_token = "secret-token"
    c = _cowork(sample_config)
    assert c["inferenceBedrockProfile"] == "my-prof"
    assert c["inferenceBedrockBearerToken"] == "secret-token"


def test_common_inference_keys(sample_config):
    sample_config.cowork.custom_headers = "X-Org: acme"
    sample_config.cowork.model_discovery_enabled = True
    sample_config.cowork.max_tokens_per_window = 100000
    c = _cowork(sample_config)
    assert c["inferenceCustomHeaders"] == "X-Org: acme"
    assert c["modelDiscoveryEnabled"] is True
    assert c["inferenceMaxTokensPerWindow"] == 100000


def test_org_tools_and_json_blobs(sample_config):
    sample_config.cowork.organization.uuid = "org-123"
    sample_config.cowork.organization.plugin_settings = {"a": {"enabled": True}}
    sample_config.cowork.managed_mcp_servers = {"servers": [{"name": "x"}]}
    sample_config.cowork.tools.disabled_builtin = ["web_search"]
    sample_config.cowork.tools.builtin_policy = {"bash": "deny"}
    c = _cowork(sample_config)
    assert c["deploymentOrganizationUuid"] == "org-123"
    # Free-form JSON blobs stay nested in the authoritative JSON.
    assert c["orgPluginSettings"] == {"a": {"enabled": True}}
    assert c["managedMcpServers"] == {"servers": [{"name": "x"}]}
    assert c["disabledBuiltinTools"] == ["web_search"]
    assert c["builtinToolPolicy"] == {"bash": "deny"}


def test_bootstrap_and_import(sample_config):
    sample_config.cowork.bootstrap.enabled = False
    sample_config.cowork.bootstrap.url = "https://bootstrap"
    sample_config.cowork.claude_ai_import = {"mode": "off"}
    c = _cowork(sample_config)
    assert c["bootstrapEnabled"] is False
    assert c["bootstrapUrl"] == "https://bootstrap"
    assert c["claudeAiImport"] == {"mode": "off"}


def test_banner_stays_last(sample_config):
    # Banner is the final key even when later-group keys are also set.
    sample_config.cowork.banner.enabled = True
    sample_config.cowork.banner.text = "Internal"
    sample_config.cowork.bootstrap.url = "https://bootstrap"
    sample_config.cowork.desktop.cowork_tab_enabled = True
    keys = list(_cowork(sample_config))
    assert keys[-1] == "banner"
