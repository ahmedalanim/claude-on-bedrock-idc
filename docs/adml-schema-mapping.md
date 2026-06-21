# ADML Policy Key to schema.py Mapping

Audit of every `com.anthropic.claudefordesktop` policy key in `Claude.adml` against
`src/claude_bedrock_idc/config/schema.py` and `generators/cowork.py`.

Last verified: 2026-06-21

## In-scope Bedrock policies

| ADML policy key | Schema field | Enum values |
|---|---|---|
| `inferenceProvider` | `CoworkConfig.inference_provider` | ADML: gateway\|anthropic\|bedrock\|vertex\|foundry. Schema: `Literal["bedrock"]` (scoped) |
| `inferenceCredentialKind` | `CoworkConfig.credential_kind` | `static\|helper-script\|interactive\|vendor-profile` |
| `inferenceBedrockRegion` | `CoworkConfig.bedrock_region` | string |
| `inferenceBedrockSsoStartUrl` | `CoworkConfig.sso_start_url` | string |
| `inferenceBedrockSsoRegion` | `CoworkConfig.sso_region` | string |
| `inferenceBedrockSsoAccountId` | `CoworkConfig.sso_account_id` | string |
| `inferenceBedrockSsoRoleName` | `CoworkConfig.sso_role_name` | string |
| `inferenceBedrockServiceTier` | `CoworkConfig.service_tier` | `flex\|priority` |
| `inferenceBedrockBaseUrl` | `CoworkBedrockExtraConfig.base_url` | string |
| `inferenceBedrockProfile` | `CoworkBedrockExtraConfig.profile` | string |
| `inferenceBedrockAwsDir` | `CoworkBedrockExtraConfig.aws_dir` | string |
| `inferenceBedrockBearerToken` | `CoworkBedrockExtraConfig.bearer_token` | string [SENSITIVE] |
| `inferenceCustomHeaders` | `CoworkConfig.custom_headers` | string [SENSITIVE] |
| `modelDiscoveryEnabled` | `CoworkConfig.model_discovery_enabled` | bool |
| `inferenceModels` | `CoworkConfig.models` (list of `CoworkModel`) | JSON array |
| `inferenceMaxTokensPerWindow` | `CoworkConfig.max_tokens_per_window` | int |
| `inferenceTokenWindowHours` | `CoworkConfig.token_window_hours` | int |
| `inferenceCredentialHelper` | `CoworkCredentialHelperConfig.command` | string |
| `inferenceCredentialHelperTtlSec` | `CoworkCredentialHelperConfig.ttl_sec` | int (default 3600) |
| `inferenceCredentialHelperTimeoutSec` | `CoworkCredentialHelperConfig.timeout_sec` | int (default 60) |
| `inferenceCredentialHelperSilentRefreshEnabled` | `CoworkCredentialHelperConfig.silent_refresh` | bool (default true) |
| `isDesktopExtensionEnabled` | `CoworkDesktopConfig.extensions_enabled` | bool (default true) |
| `isDesktopExtensionSignatureRequired` | `CoworkDesktopConfig.extension_signature_required` | bool (default false) |
| `isLocalDevMcpEnabled` | `CoworkDesktopConfig.local_dev_mcp_enabled` | bool (default true) |
| `coworkTabEnabled` | `CoworkDesktopConfig.cowork_tab_enabled` | bool (default true) |
| `isClaudeCodeForDesktopEnabled` | `CoworkDesktopConfig.claude_code_tab_enabled` | bool (default true) |
| `autoModeEnabled` | `CoworkDesktopConfig.auto_mode_enabled` | bool (default false) |
| `disableDeepLinkRegistration` | `CoworkDesktopConfig.deep_link_registration_disabled` | bool (default false) |
| `disableDeploymentModeChooser` | `CoworkDesktopConfig.deployment_mode_chooser_disabled` | bool (default false) |
| `coworkEgressAllowedHosts` | `CoworkDesktopConfig.egress_allowed_hosts` | string |
| `allowedWorkspaceFolders` | `CoworkDesktopConfig.allowed_workspace_folders` | list[str] |
| `otlpEndpoint` | `CoworkTelemetryConfig.otlp_endpoint` | string |
| `otlpProtocol` | `CoworkTelemetryConfig.otlp_protocol` | `http/protobuf\|http/json\|grpc` |
| `otlpHeaders` | `CoworkTelemetryConfig.otlp_headers` | string [SENSITIVE] |
| `otlpResourceAttributes` | `CoworkTelemetryConfig.otlp_resource_attributes` | string [SENSITIVE] |
| `otlpDesktopLogLevel` | `CoworkTelemetryConfig.desktop_log_level` | `off\|error\|warn\|info\|debug` |
| `disableEssentialTelemetry` | `CoworkTelemetryConfig.disable_essential` | bool (default false) |
| `disableNonessentialTelemetry` | `CoworkTelemetryConfig.disable_nonessential` | bool (default false) |
| `disableNonessentialServices` | `CoworkTelemetryConfig.disable_nonessential_services` | bool (default false) |
| `autoUpdaterEnforcementHours` | `CoworkUpdatesConfig.enforcement_hours` | int |
| `disableAutoUpdates` | `CoworkUpdatesConfig.disable_auto_updates` | bool (default false) |
| `deploymentOrganizationUuid` | `CoworkOrganizationConfig.uuid` | string |
| `organizationPluginsUrl` | `CoworkOrganizationConfig.plugins_url` | string |
| `orgPluginSettings` | `CoworkOrganizationConfig.plugin_settings` | JSON object |
| `managedMcpServers` | `CoworkConfig.managed_mcp_servers` | JSON object [SENSITIVE] |
| `disabledBuiltinTools` | `CoworkToolsConfig.disabled_builtin` | list[str] |
| `builtinToolPolicy` | `CoworkToolsConfig.builtin_policy` | JSON object |
| `bootstrapEnabled` | `CoworkBootstrapConfig.enabled` | bool (default true) |
| `bootstrapUrl` | `CoworkBootstrapConfig.url` | string |
| `bootstrapOidc` | `CoworkBootstrapConfig.oidc` | JSON object |
| `claudeAiImport` | `CoworkConfig.claude_ai_import` | JSON object |
| `banner` | `CoworkConfig.banner` (`BannerConfig`) | JSON object |

## Out-of-scope providers (correctly excluded)

Non-Bedrock inference providers are out of scope for this project. The following 20
ADML keys are intentionally not represented in schema.py:

- **Anthropic**: `inferenceAnthropicApiKey`
- **Gateway**: `inferenceGatewayBaseUrl`, `inferenceGatewayApiKey`, `inferenceGatewayAuthScheme`, `inferenceGatewayOidc`
- **Vertex**: `inferenceVertexProjectId`, `inferenceVertexRegion`, `inferenceVertexCredentialsFile`, `inferenceVertexOAuthClientId`, `inferenceVertexOAuthClientSecret`, `inferenceVertexOAuthScopes`, `inferenceVertexWorkforceAudience`, `inferenceVertexWorkforceUserProject`, `inferenceVertexWorkforceOidc`, `inferenceVertexBaseUrl`
- **Foundry**: `inferenceFoundryResource`, `inferenceFoundryApiKey`, `inferenceFoundryTenantId`, `inferenceFoundryClientId`
