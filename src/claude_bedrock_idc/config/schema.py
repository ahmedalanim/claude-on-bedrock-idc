"""Pydantic models for the YAML configuration.

The schema validates the input file and supplies field-level defaults. Cross-field
defaults that depend on other sections (e.g. Cowork inheriting from aws.sso.*) are
resolved later in mapping/resolve.py, not here, so this module stays a pure
description of the document shape.
"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class _Base(BaseModel):
    model_config = ConfigDict(extra="forbid")


class SsoConfig(_Base):
    enabled: bool = True
    start_url: str
    sso_region: str
    account_id: str
    role_name: str
    auto_refresh: bool = True


class AwsConfig(_Base):
    profile: str
    region: str = "us-east-1"
    write_aws_config: bool = True
    config_path: str | None = None
    sso: SsoConfig


class GuardrailConfig(_Base):
    enabled: bool = False
    identifier: str | None = None
    version: str | None = None

    @model_validator(mode="after")
    def _require_ids_when_enabled(self) -> GuardrailConfig:
        if self.enabled and (not self.identifier or not self.version):
            raise ValueError("guardrail.enabled requires identifier and version")
        return self


class BedrockConfig(_Base):
    enabled: bool = True
    base_url: str | None = None
    service_tier: Literal["default", "flex", "priority"] | None = None
    prompt_caching: Literal["default", "disabled", "one_hour"] = "default"
    guardrail: GuardrailConfig = Field(default_factory=GuardrailConfig)


class ModelsConfig(_Base):
    opus: str = "us.anthropic.claude-opus-4-8"
    sonnet: str = "us.anthropic.claude-sonnet-4-6"
    haiku: str = "us.anthropic.claude-haiku-4-5-20251001-v1:0"
    default: Literal["opus", "sonnet", "haiku"] = "sonnet"
    pin_default: bool = True
    overrides: dict[str, str] = Field(default_factory=dict)

    def resolved_id(self, family: str) -> str:
        return {"opus": self.opus, "sonnet": self.sonnet, "haiku": self.haiku}[family]


class PermissionsConfig(_Base):
    allow: list[str] = Field(default_factory=list)
    deny: list[str] = Field(default_factory=list)


class ClaudeCodeConfig(_Base):
    enabled: bool = True
    scope: Literal["user", "project", "local"] = "user"
    project_dir: str | None = None
    permissions: PermissionsConfig = Field(default_factory=PermissionsConfig)
    extra_env: dict[str, str] = Field(default_factory=dict)
    merge_existing: bool = True

    @model_validator(mode="after")
    def _require_project_dir(self) -> ClaudeCodeConfig:
        if self.scope in ("project", "local") and not self.project_dir:
            raise ValueError(f"claude_code.project_dir is required when scope is '{self.scope}'")
        return self


class MobileconfigExport(_Base):
    # Domain confirmed from a real app Export (com.anthropic.claudefordesktop manifest).
    payload_identifier: str = "com.anthropic.claudefordesktop"
    organization: str = "My Org"
    scope: Literal["User", "System"] = "User"


class RegExport(_Base):
    # Confirmed from the Claude.admx / exported Claude.reg: key SOFTWARE\Policies\Claude.
    hive: Literal["HKCU", "HKLM"] = "HKCU"


class CoworkExport(_Base):
    formats: list[Literal["json", "mobileconfig", "reg"]] = Field(default_factory=lambda: ["json"])
    mobileconfig: MobileconfigExport = Field(default_factory=MobileconfigExport)
    reg: RegExport = Field(default_factory=RegExport)


class CoworkModel(_Base):
    name: str
    label: str | None = None  # -> labelOverride in the managed config


class BannerConfig(_Base):
    enabled: bool = False
    text: str | None = None
    text_color: str | None = None
    background_color: str | None = None
    link_url: str | None = None

    @model_validator(mode="after")
    def _require_text_when_enabled(self) -> BannerConfig:
        if self.enabled and not self.text:
            raise ValueError("cowork.banner.enabled requires text")
        return self


# --- Optional managed-policy groups (com.anthropic.claudefordesktop) -----------
# Every field below defaults to None/empty and is emitted only when explicitly set,
# so the default Bedrock + IDC output is unchanged. Field -> policy-key mappings are
# documented in config.example.yaml and docs/plan-cowork-policies.md. The non-Bedrock
# inference providers (anthropic/gateway/vertex/foundry) are intentionally out of scope.


class CoworkDesktopConfig(_Base):
    """Desktop app surface toggles. bool|None: None omits the key (app keeps its own default)."""

    extensions_enabled: bool | None = None  # isDesktopExtensionEnabled
    extension_signature_required: bool | None = None  # isDesktopExtensionSignatureRequired
    local_dev_mcp_enabled: bool | None = None  # isLocalDevMcpEnabled
    cowork_tab_enabled: bool | None = None  # coworkTabEnabled
    claude_code_tab_enabled: bool | None = None  # isClaudeCodeForDesktopEnabled
    auto_mode_enabled: bool | None = None  # autoModeEnabled
    deep_link_registration_disabled: bool | None = None  # disableDeepLinkRegistration
    deployment_mode_chooser_disabled: bool | None = None  # disableDeploymentModeChooser
    egress_allowed_hosts: str | None = None  # coworkEgressAllowedHosts
    allowed_workspace_folders: list[str] = Field(default_factory=list)  # allowedWorkspaceFolders


class CoworkTelemetryConfig(_Base):
    """OpenTelemetry export + telemetry/service kill-switches."""

    otlp_endpoint: str | None = None  # otlpEndpoint
    otlp_protocol: Literal["http/protobuf", "http/json", "grpc"] | None = None  # otlpProtocol
    otlp_headers: str | None = None  # otlpHeaders [SENSITIVE]
    otlp_resource_attributes: str | None = None  # otlpResourceAttributes [SENSITIVE]
    desktop_log_level: Literal["off", "error", "warn", "info", "debug"] | None = (
        None  # otlpDesktopLogLevel
    )
    disable_essential: bool | None = None  # disableEssentialTelemetry
    disable_nonessential: bool | None = None  # disableNonessentialTelemetry
    disable_nonessential_services: bool | None = None  # disableNonessentialServices


class CoworkUpdatesConfig(_Base):
    enforcement_hours: int | None = None  # autoUpdaterEnforcementHours
    disable_auto_updates: bool | None = None  # disableAutoUpdates


class CoworkCredentialHelperConfig(_Base):
    """helper-script credential source (used when credential_kind == 'helper-script')."""

    command: str | None = None  # inferenceCredentialHelper
    ttl_sec: int | None = None  # inferenceCredentialHelperTtlSec
    timeout_sec: int | None = None  # inferenceCredentialHelperTimeoutSec
    silent_refresh: bool | None = None  # inferenceCredentialHelperSilentRefreshEnabled


class CoworkBedrockExtraConfig(_Base):
    """Bedrock keys beyond the SSO/region set already on CoworkConfig."""

    base_url: str | None = None  # inferenceBedrockBaseUrl
    profile: str | None = None  # inferenceBedrockProfile
    aws_dir: str | None = None  # inferenceBedrockAwsDir
    bearer_token: str | None = None  # inferenceBedrockBearerToken [SENSITIVE]


class CoworkOrganizationConfig(_Base):
    uuid: str | None = None  # deploymentOrganizationUuid
    plugins_url: str | None = None  # organizationPluginsUrl
    plugin_settings: dict[str, Any] | None = None  # orgPluginSettings (free-form JSON)


class CoworkToolsConfig(_Base):
    disabled_builtin: list[str] = Field(default_factory=list)  # disabledBuiltinTools
    builtin_policy: dict[str, Any] | None = None  # builtinToolPolicy (free-form JSON)


class CoworkBootstrapConfig(_Base):
    enabled: bool | None = None  # bootstrapEnabled
    url: str | None = None  # bootstrapUrl
    oidc: dict[str, Any] | None = None  # bootstrapOidc (free-form JSON)


class CoworkConfig(_Base):
    enabled: bool = True
    inference_provider: Literal["bedrock"] = "bedrock"
    # Valid kinds from the manifest: static | helper-script | interactive | vendor-profile.
    # "interactive" = in-app AWS sign-in (IAM Identity Center).
    credential_kind: Literal["static", "helper-script", "interactive", "vendor-profile"] = (
        "interactive"
    )
    sso_start_url: str | None = None
    sso_region: str | None = None
    sso_account_id: str | None = None
    sso_role_name: str | None = None
    bedrock_region: str | None = None
    service_tier: Literal["flex", "priority"] | None = None
    models: list[CoworkModel] = Field(default_factory=list)
    banner: BannerConfig = Field(default_factory=BannerConfig)

    # --- Optional policy groups (all omit-when-unset) ---
    custom_headers: str | None = None  # inferenceCustomHeaders [SENSITIVE]
    model_discovery_enabled: bool | None = None  # modelDiscoveryEnabled
    max_tokens_per_window: int | None = None  # inferenceMaxTokensPerWindow
    token_window_hours: int | None = None  # inferenceTokenWindowHours
    managed_mcp_servers: dict[str, Any] | None = None  # managedMcpServers [SENSITIVE]
    claude_ai_import: dict[str, Any] | None = None  # claudeAiImport (free-form JSON)
    desktop: CoworkDesktopConfig = Field(default_factory=CoworkDesktopConfig)
    telemetry: CoworkTelemetryConfig = Field(default_factory=CoworkTelemetryConfig)
    updates: CoworkUpdatesConfig = Field(default_factory=CoworkUpdatesConfig)
    credential_helper: CoworkCredentialHelperConfig = Field(
        default_factory=CoworkCredentialHelperConfig
    )
    bedrock: CoworkBedrockExtraConfig = Field(default_factory=CoworkBedrockExtraConfig)
    organization: CoworkOrganizationConfig = Field(default_factory=CoworkOrganizationConfig)
    tools: CoworkToolsConfig = Field(default_factory=CoworkToolsConfig)
    bootstrap: CoworkBootstrapConfig = Field(default_factory=CoworkBootstrapConfig)

    export: CoworkExport = Field(default_factory=CoworkExport)
    merge_existing: bool = True


class OutputConfig(_Base):
    mode: Literal["stage", "install"] = "stage"
    dir: str = "./generated"
    backup: bool = True


class Config(_Base):
    version: int = 1
    aws: AwsConfig
    bedrock: BedrockConfig = Field(default_factory=BedrockConfig)
    models: ModelsConfig = Field(default_factory=ModelsConfig)
    claude_code: ClaudeCodeConfig = Field(default_factory=ClaudeCodeConfig)
    cowork: CoworkConfig = Field(default_factory=CoworkConfig)
    output: OutputConfig = Field(default_factory=OutputConfig)
