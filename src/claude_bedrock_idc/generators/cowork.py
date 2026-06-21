"""Generate the Claude Desktop enterprise managed-config for Bedrock + IAM Identity
Center (the ``com.anthropic.claudefordesktop`` domain).

This is the config that powers Cowork / Claude-for-Desktop "Sign in with AWS". Pure:
returns an in-memory dict — the authoritative JSON deliverable. The optional
``.mobileconfig`` / ``.reg`` wrappers are produced from this dict by the exporters
(which JSON-string-encode the complex values, per the real exports).

Key names, the ``inferenceProvider``/``inferenceCredentialKind`` values, the
``inferenceModels`` object shape and the ``banner`` shape are all confirmed against a
real app Export and the ``com.anthropic.claudefordesktop`` profile manifest / ADMX.

Coverage: every policy in ``Claude.admx`` / ``com.anthropic.claudefordesktop.plist``
*except* the non-Bedrock inference providers (anthropic/gateway/vertex/foundry), which
are out of scope for this Bedrock + IDC project. The seven core Bedrock keys
(``inferenceProvider``, ``inferenceCredentialKind``, ``inferenceBedrockRegion`` and the
four ``inferenceBedrockSso*`` keys) are emitted unconditionally; every other policy is
emitted only when its config field is set, so the default output is minimal and stable.
"""

from __future__ import annotations

from typing import Any

from ..mapping.resolve import ResolvedCowork, ResolvedInputs


def _models(resolved_models: list[dict[str, str | None]]) -> list[dict[str, str]]:
    out: list[dict[str, str]] = []
    for m in resolved_models:
        entry: dict[str, str] = {"name": str(m["name"])}
        if m.get("label"):
            entry["labelOverride"] = str(m["label"])
        out.append(entry)
    return out


def _banner(banner: dict[str, Any]) -> dict[str, Any]:
    # Match the key order/names from the real export.
    out: dict[str, Any] = {}
    if banner.get("background_color"):
        out["backgroundColor"] = banner["background_color"]
    if banner.get("text_color"):
        out["textColor"] = banner["text_color"]
    out["enabled"] = bool(banner.get("enabled"))
    out["text"] = banner.get("text")
    if banner.get("link_url"):
        out["linkUrl"] = banner["link_url"]
    return out


def _put(settings: dict[str, Any], key: str, value: Any) -> None:
    """Emit ``key`` only when ``value`` is set (None and empty list/dict are omitted)."""
    if value is None:
        return
    if isinstance(value, (list, dict)) and not value:
        return
    settings[key] = value


def _bedrock_extras(settings: dict[str, Any], cw: ResolvedCowork) -> None:
    b = cw.bedrock_extra
    _put(settings, "inferenceBedrockBearerToken", b.bearer_token)
    _put(settings, "inferenceBedrockBaseUrl", b.base_url)
    _put(settings, "inferenceBedrockProfile", b.profile)
    _put(settings, "inferenceBedrockAwsDir", b.aws_dir)


def _inference_common(settings: dict[str, Any], cw: ResolvedCowork) -> None:
    _put(settings, "inferenceCustomHeaders", cw.custom_headers)
    _put(settings, "modelDiscoveryEnabled", cw.model_discovery_enabled)
    _put(settings, "inferenceMaxTokensPerWindow", cw.max_tokens_per_window)
    _put(settings, "inferenceTokenWindowHours", cw.token_window_hours)


def _credential_helper(settings: dict[str, Any], cw: ResolvedCowork) -> None:
    h = cw.credential_helper
    _put(settings, "inferenceCredentialHelper", h.command)
    _put(settings, "inferenceCredentialHelperTtlSec", h.ttl_sec)
    _put(settings, "inferenceCredentialHelperTimeoutSec", h.timeout_sec)
    _put(settings, "inferenceCredentialHelperSilentRefreshEnabled", h.silent_refresh)


def _desktop(settings: dict[str, Any], cw: ResolvedCowork) -> None:
    d = cw.desktop
    _put(settings, "isDesktopExtensionEnabled", d.extensions_enabled)
    _put(settings, "isDesktopExtensionSignatureRequired", d.extension_signature_required)
    _put(settings, "isLocalDevMcpEnabled", d.local_dev_mcp_enabled)
    _put(settings, "coworkTabEnabled", d.cowork_tab_enabled)
    _put(settings, "isClaudeCodeForDesktopEnabled", d.claude_code_tab_enabled)
    _put(settings, "autoModeEnabled", d.auto_mode_enabled)
    _put(settings, "disableDeepLinkRegistration", d.deep_link_registration_disabled)
    _put(settings, "disableDeploymentModeChooser", d.deployment_mode_chooser_disabled)
    _put(settings, "coworkEgressAllowedHosts", d.egress_allowed_hosts)
    _put(settings, "allowedWorkspaceFolders", list(d.allowed_workspace_folders))


def _telemetry(settings: dict[str, Any], cw: ResolvedCowork) -> None:
    t = cw.telemetry
    _put(settings, "otlpEndpoint", t.otlp_endpoint)
    _put(settings, "otlpProtocol", t.otlp_protocol)
    _put(settings, "otlpHeaders", t.otlp_headers)
    _put(settings, "otlpResourceAttributes", t.otlp_resource_attributes)
    _put(settings, "otlpDesktopLogLevel", t.desktop_log_level)
    _put(settings, "disableEssentialTelemetry", t.disable_essential)
    _put(settings, "disableNonessentialTelemetry", t.disable_nonessential)
    _put(settings, "disableNonessentialServices", t.disable_nonessential_services)


def _updates(settings: dict[str, Any], cw: ResolvedCowork) -> None:
    u = cw.updates
    _put(settings, "autoUpdaterEnforcementHours", u.enforcement_hours)
    _put(settings, "disableAutoUpdates", u.disable_auto_updates)


def _org_tools(settings: dict[str, Any], cw: ResolvedCowork) -> None:
    o = cw.organization
    _put(settings, "deploymentOrganizationUuid", o.uuid)
    _put(settings, "organizationPluginsUrl", o.plugins_url)
    _put(settings, "orgPluginSettings", o.plugin_settings)
    _put(settings, "managedMcpServers", cw.managed_mcp_servers)
    _put(settings, "disabledBuiltinTools", list(cw.tools.disabled_builtin))
    _put(settings, "builtinToolPolicy", cw.tools.builtin_policy)


def _bootstrap(settings: dict[str, Any], cw: ResolvedCowork) -> None:
    b = cw.bootstrap
    _put(settings, "bootstrapEnabled", b.enabled)
    _put(settings, "bootstrapUrl", b.url)
    _put(settings, "bootstrapOidc", b.oidc)
    _put(settings, "claudeAiImport", cw.claude_ai_import)


def build_cowork(inputs: ResolvedInputs) -> dict[str, Any]:
    """Return the Claude Desktop managed-settings content as a dict.

    The seven core Bedrock keys are emitted unconditionally (``inferenceCredentialKind``
    is always present so the credential source is chosen deterministically —
    ``interactive`` = in-app AWS sign-in). Every optional policy group is appended only
    for keys whose config field is set, so the default Bedrock + IDC output is unchanged.
    """
    cw = inputs.cowork

    # --- Core Bedrock keys: always emitted (current behavior) ------------------
    settings: dict[str, Any] = {
        "inferenceProvider": cw.inference_provider,
        "inferenceCredentialKind": cw.credential_kind,
        "inferenceBedrockRegion": cw.bedrock_region,
        "inferenceBedrockSsoStartUrl": cw.sso_start_url,
        "inferenceBedrockSsoRegion": cw.sso_region,
        "inferenceBedrockSsoAccountId": cw.sso_account_id,
        "inferenceBedrockSsoRoleName": cw.sso_role_name,
    }
    if cw.service_tier:
        settings["inferenceBedrockServiceTier"] = cw.service_tier
    _bedrock_extras(settings, cw)
    settings["inferenceModels"] = _models(cw.models)

    # --- Optional policy groups: omit-when-unset -------------------------------
    _inference_common(settings, cw)
    _credential_helper(settings, cw)
    _desktop(settings, cw)
    _telemetry(settings, cw)
    _updates(settings, cw)
    _org_tools(settings, cw)
    _bootstrap(settings, cw)

    # --- Banner last (matches the real export) ---------------------------------
    if cw.banner:
        settings["banner"] = _banner(cw.banner)
    return settings
