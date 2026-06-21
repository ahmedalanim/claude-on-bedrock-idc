# Plan: Full ADMX / plist Policy Coverage for the Cowork Managed-Config Generator

**Status:** Revised after agent review
**Author:** Claude Code (Opus 4.8)
**Date:** 2026-06-21

---

## 1. Goal

Extend the Cowork / Claude-for-Desktop managed-config generator so `config.example.yaml`,
the Pydantic schema, the resolver, and `build_cowork()` can express **every** policy defined in the
two authoritative enterprise-management sources:

- `Claude.admx` — Windows Group Policy definitions (`SOFTWARE\Policies\Claude`).
- `com.anthropic.claudefordesktop.plist` — the macOS profile manifest (`pfm_subkeys`).

Both files describe the **same** `com.anthropic.claudefordesktop` policy surface in two vocabularies.
The plist is the superset (the ADMX is identical minus the MDM `Payload*` envelope keys), so the
plist `pfm_subkeys` list is the spec we implement against.

### 1.1 Gap analysis

The plist defines **71** policy keys (excluding the six `Payload*` MDM-envelope keys, which the
`.mobileconfig` exporter already synthesizes). `build_cowork()` today emits **10**:

`inferenceProvider`, `inferenceCredentialKind`, `inferenceBedrockRegion`,
`inferenceBedrockSsoStartUrl`, `inferenceBedrockSsoRegion`, `inferenceBedrockSsoAccountId`,
`inferenceBedrockSsoRoleName`, `inferenceBedrockServiceTier`, `inferenceModels`, `banner`.

**61 keys are unsupported.** Per the scope decision (open-Q2), this plan adds **52** of them — every
policy *except* the 19 non-Bedrock provider keys (anthropic/gateway/vertex/foundry, group G), which are
**deferred**. The project stays strictly Bedrock + IDC, so `inference_provider` is **not** widened
(stays `Literal["bedrock"]`). All telemetry, updates, desktop toggles, MCP/tools/org/plugins,
bootstrap, credential-helper, Bedrock extras, and the common inference keys are in scope.

### 1.2 Guiding constraints

- **The default Bedrock + IDC output must not change.** Every new key is optional and emitted
  **only when explicitly set** (None / empty ⇒ omitted). The golden `cowork-bedrock.json` for the
  shipped `config.example.yaml` stays byte-for-byte identical. New behavior is purely additive.
- **`extra="forbid"` stays on.** Every key is a typed field; no opaque passthrough bag — except the
  handful of policies whose *internal* JSON shape is undocumented (see §4.3), which are typed as
  free-form `dict`/`list` values but still live in named fields.
- **Single source of truth preserved.** Bedrock SSO/region still inherit from `aws.sso.*` via the
  resolver; nothing about that fan-out changes.
- **This stays a Bedrock + IDC project.** The non-Bedrock providers (anthropic/gateway/vertex/foundry)
  are **deferred** (open-Q2); `inference_provider` stays `Literal["bedrock"]`. They can be added later
  without reworking this change.

---

## 2. The 71-key inventory (grouped)

Grouped by concern, with the config field that will drive each. `bool|None` and `*|None` defaults
mean "omit unless set". `[S]` marks **sensitive** keys (`pfm_sensitive` in the manifest).

> **On-the-wire note.** Keys typed below as "JSON array"/"JSON object" are `pfm_type=string` in the
> manifest — their managed-config value is a JSON **string**, not a native plist array/object (exactly
> as `inferenceModels`/`banner` work today). In the authoritative JSON deliverable they remain nested;
> the `.mobileconfig`/`.reg` exporters JSON-string-encode them via the existing `_flatten` /
> `_value_literal`.

### A. Desktop surface toggles → `cowork.desktop`
| Policy key | Type | Config field |
|---|---|---|
| `isDesktopExtensionEnabled` | bool | `desktop.extensions_enabled` |
| `isDesktopExtensionSignatureRequired` | bool | `desktop.extension_signature_required` |
| `isLocalDevMcpEnabled` | bool | `desktop.local_dev_mcp_enabled` |
| `coworkTabEnabled` | bool | `desktop.cowork_tab_enabled` |
| `isClaudeCodeForDesktopEnabled` | bool | `desktop.claude_code_tab_enabled` |
| `autoModeEnabled` | bool | `desktop.auto_mode_enabled` |
| `disableDeepLinkRegistration` | bool | `desktop.deep_link_registration_disabled` |
| `disableDeploymentModeChooser` | bool | `desktop.deployment_mode_chooser_disabled` |
| `coworkEgressAllowedHosts` | string | `desktop.egress_allowed_hosts` |
| `allowedWorkspaceFolders` | JSON array | `desktop.allowed_workspace_folders` (`list[str]`) |

### B. Telemetry (OpenTelemetry) → `cowork.telemetry`
| Policy key | Type | Config field |
|---|---|---|
| `otlpEndpoint` | string | `telemetry.otlp_endpoint` |
| `otlpProtocol` | enum `http/protobuf\|http/json\|grpc` | `telemetry.otlp_protocol` |
| `otlpHeaders` `[S]` | string | `telemetry.otlp_headers` |
| `otlpResourceAttributes` `[S]` | string | `telemetry.otlp_resource_attributes` |
| `otlpDesktopLogLevel` | enum `off\|error\|warn\|info\|debug` | `telemetry.desktop_log_level` |
| `disableEssentialTelemetry` | bool | `telemetry.disable_essential` |
| `disableNonessentialTelemetry` | bool | `telemetry.disable_nonessential` |
| `disableNonessentialServices` | bool | `telemetry.disable_nonessential_services` |

### C. Updates → `cowork.updates`
| Policy key | Type | Config field |
|---|---|---|
| `autoUpdaterEnforcementHours` | int | `updates.enforcement_hours` |
| `disableAutoUpdates` | bool | `updates.disable_auto_updates` |

### D. Inference — common → `cowork.*` (mostly existing)
| Policy key | Type | Config field |
|---|---|---|
| `inferenceProvider` | enum (5) | `inference_provider` *(existing)* |
| `inferenceCredentialKind` | enum (4) | `credential_kind` *(existing)* |
| `inferenceModels` | JSON array | `models` *(existing)* |
| `inferenceCustomHeaders` `[S]` | string | `custom_headers` |
| `modelDiscoveryEnabled` | bool | `model_discovery_enabled` |
| `inferenceMaxTokensPerWindow` | int | `max_tokens_per_window` |
| `inferenceTokenWindowHours` | int | `token_window_hours` |

### E. Inference — credential helper → `cowork.credential_helper`
| Policy key | Type | Config field |
|---|---|---|
| `inferenceCredentialHelper` | string | `credential_helper.command` |
| `inferenceCredentialHelperTtlSec` | int | `credential_helper.ttl_sec` |
| `inferenceCredentialHelperTimeoutSec` | int | `credential_helper.timeout_sec` |
| `inferenceCredentialHelperSilentRefreshEnabled` | bool | `credential_helper.silent_refresh` |

### F. Inference — Bedrock → `cowork.*` (existing) + `cowork.bedrock` (new extras)
| Policy key | Type | Config field |
|---|---|---|
| `inferenceBedrockRegion` | string | `bedrock_region` *(existing, inherits `aws.region`)* |
| `inferenceBedrockSsoStartUrl` | string | `sso_start_url` *(existing)* |
| `inferenceBedrockSsoRegion` | string | `sso_region` *(existing)* |
| `inferenceBedrockSsoAccountId` | string | `sso_account_id` *(existing)* |
| `inferenceBedrockSsoRoleName` | string | `sso_role_name` *(existing)* |
| `inferenceBedrockServiceTier` | enum `flex\|priority` | `service_tier` *(existing)* |
| `inferenceBedrockBaseUrl` | string | `bedrock.base_url` |
| `inferenceBedrockProfile` | string | `bedrock.profile` |
| `inferenceBedrockAwsDir` | string | `bedrock.aws_dir` |
| `inferenceBedrockBearerToken` `[S]` | string | `bedrock.bearer_token` |

### G. Inference — other providers → **DEFERRED (out of scope)**
*Per open-Q2, the 19 non-Bedrock provider keys are **not** implemented in this change. Listed here only
so the inventory stays complete. Deferring them means `inference_provider` stays `Literal["bedrock"]`
and no `cowork.providers` sub-model is added.*

- **anthropic (1):** `inferenceAnthropicApiKey` `[S]`
- **gateway (4):** `inferenceGatewayBaseUrl`, `inferenceGatewayApiKey` `[S]`,
  `inferenceGatewayAuthScheme` (enum `auto|x-api-key|bearer|sso`), `inferenceGatewayOidc`
- **vertex (10):** `inferenceVertexProjectId`, `inferenceVertexRegion`, `inferenceVertexCredentialsFile`,
  `inferenceVertexOAuthClientId`, `inferenceVertexOAuthClientSecret` `[S]`,
  `inferenceVertexOAuthScopes`, `inferenceVertexWorkforceAudience`,
  `inferenceVertexWorkforceUserProject`, `inferenceVertexWorkforceOidc`, `inferenceVertexBaseUrl`
- **foundry (4):** `inferenceFoundryResource`, `inferenceFoundryApiKey` `[S]`,
  `inferenceFoundryTenantId`, `inferenceFoundryClientId`

### H. Org / plugins / MCP / tools → `cowork.organization`, `cowork.tools`, `cowork.managed_mcp_servers`
| Policy key | Type | Config field |
|---|---|---|
| `deploymentOrganizationUuid` | string | `organization.uuid` |
| `organizationPluginsUrl` | string | `organization.plugins_url` |
| `orgPluginSettings` | JSON object | `organization.plugin_settings` (free-form dict) |
| `managedMcpServers` `[S]` | JSON object | `managed_mcp_servers` (free-form dict) |
| `disabledBuiltinTools` | JSON array | `tools.disabled_builtin` (`list[str]`) |
| `builtinToolPolicy` | JSON object | `tools.builtin_policy` (free-form dict) |

### I. Bootstrap / import → `cowork.bootstrap`, `cowork.claude_ai_import`
| Policy key | Type | Config field |
|---|---|---|
| `bootstrapEnabled` | bool | `bootstrap.enabled` |
| `bootstrapUrl` | string | `bootstrap.url` |
| `bootstrapOidc` | JSON object | `bootstrap.oidc` (free-form dict) |
| `claudeAiImport` | JSON object | `claude_ai_import` (free-form dict) |

### J. Banner → `cowork.banner` *(existing)*
`banner` (JSON object) — unchanged.

---

## 3. Design decisions (for approval)

1. **Grouped, additive schema (recommended).** New keys live in named sub-models
   (`desktop`, `telemetry`, `updates`, `credential_helper`, `bedrock`, `providers`, `organization`,
   `tools`, `bootstrap`) under `cowork`. The existing top-level Bedrock fields stay put — no breaking
   rename — so the default golden file is untouched. *Alternative: one flat list of 71 keys (rejected —
   unreadable, and would force a churny rename of the existing fields).*
   **Scope corollary (open-Q2 = Bedrock-only):** `CoworkConfig.inference_provider` stays
   `Literal["bedrock"]` and **no `cowork.providers` sub-model is added** (group G deferred).
   `inferenceBedrockServiceTier` stays its own `Literal["flex","priority"]` and is **not** unified with
   the existing `bedrock.service_tier` (`default|flex|priority`) — different enums, kept separate.

2. **Omit-when-unset emission (recommended).** A key is written only when its field is non-null
   (and non-empty for list/dict). `bool|None` fields default to `None`, so we never emit the app's own
   defaults (e.g. we don't force `isDesktopExtensionEnabled=true`). Keeps output minimal and the
   default golden stable. *Alternative: always emit with the manifest `pfm_default` — rejected as
   redundant and risk-increasing (we'd be asserting defaults we don't own).*

3. **Sensitive keys: supported but null by default, never in the example.** The 5 in-scope `[S]` keys
   (`inferenceBedrockBearerToken`, `inferenceCustomHeaders`, `otlpHeaders`, `otlpResourceAttributes`,
   `managedMcpServers`; the other 4 sensitive keys live in deferred group G) are modeled but left `null` in
   `config.example.yaml`, with a header note that setting any of them makes `config.yaml`
   **secret-bearing** (so the "safe to commit" invariant in the file header no longer holds). A new
   consistency *warning* fires when a sensitive value is present. *(This project's default path —
   `credential_kind: interactive` IDC sign-in — needs none of these.)*

4. **Undocumented JSON blobs → free-form typed fields.** `orgPluginSettings`, `managedMcpServers`,
   `builtinToolPolicy`, `bootstrapOidc`, `claudeAiImport` have no documented inner schema. They're
   typed as `dict[str, Any] | None` (free-form) and passed straight through. `disabledBuiltinTools`
   and `allowedWorkspaceFolders` are `list[str]`. These stay nested objects/arrays in the authoritative
   JSON and are JSON-string-encoded by the `.mobileconfig`/`.reg` exporters (existing `_flatten` /
   `_value_literal` already handle this).

5. **`.reg` correctness for bool/int (recommended).** The ADMX models booleans (`enabledValue`/
   `disabledValue` `decimal` 1/0) and integers (`<decimal>` elements) as **REG_DWORD**. `reg.py` today
   has a bool branch that emits the quoted strings `"true"`/`"false"` (`REG_SZ`) — *wrong* for a
   `decimal` policy, not merely absent. `_value_literal` will instead emit `dword:XXXXXXXX` for
   `bool`/`int` (booleans → `dword:00000001`/`00000000`); strings and JSON blobs stay `REG_SZ`.
   **Order matters:** check `bool` *before* `int` (`bool` ⊂ `int` in Python). **Provably safe:** no
   currently-emitted top-level key is a bool or int (`inferenceModels` is a list → `REG_SZ` JSON;
   `banner.enabled` is nested *inside* the JSON `banner` blob, also `REG_SZ`), so no existing value
   changes. The `.mobileconfig` path already emits native `<true/>`/`<integer>` via `plistlib`
   (no change).

---

## 4. Implementation

### 4.1 `config/schema.py`
Add sub-models (all `_Base`, `extra="forbid"`), each field `… | None = None` unless noted:

- `CoworkDesktopConfig` — 8 bools + `egress_allowed_hosts: str|None` + `allowed_workspace_folders: list[str] = []`.
- `CoworkTelemetryConfig` — `otlp_protocol: Literal[...]|None`, `desktop_log_level: Literal[...]|None`, others str/bool.
- `CoworkUpdatesConfig` — `enforcement_hours: int|None`, `disable_auto_updates: bool|None`.
- `CoworkCredentialHelperConfig` — `command: str|None`, `ttl_sec/timeout_sec: int|None`, `silent_refresh: bool|None`.
- `CoworkBedrockExtraConfig` — `base_url/profile/aws_dir/bearer_token: str|None`.
- `CoworkOrganizationConfig` — `uuid/plugins_url: str|None`, `plugin_settings: dict|None`.
- `CoworkToolsConfig` — `disabled_builtin: list[str] = []`, `builtin_policy: dict|None`.
- `CoworkBootstrapConfig` — `enabled: bool|None`, `url: str|None`, `oidc: dict|None`.

Extend `CoworkConfig` with: the eight sub-models above as `Field(default_factory=…)`, plus the flat
common keys `custom_headers: str|None`, `model_discovery_enabled: bool|None`,
`max_tokens_per_window/token_window_hours: int|None`, `managed_mcp_servers: dict|None`,
`claude_ai_import: dict|None`. `inference_provider` **stays `Literal["bedrock"]`** (group G deferred).
All existing fields unchanged. List/dict defaults use `Field(default_factory=list/dict)` (never bare
`[]`/`{}`).

### 4.2 `mapping/resolve.py`
`ResolvedCowork` gains the new fields. Most are pure passthrough from `config.cowork.*` (no
inheritance/derivation), so `resolve()` mostly copies them across. The only derived values remain the
existing ones (SSO inheritance from `aws.sso.*`, default model list). `ResolvedCowork` stays
`frozen=True`; any mutable defaults use `field(default_factory=…)`, never bare `[]`/`{}` (a frozen
dataclass rejects mutable class-level defaults). **Recommended (resolving open-Q1):** explicit fields
for the typed groups (common, bedrock, desktop, telemetry, updates, credential_helper) and a single
`extra: dict[str, Any]` holding the free-form JSON blobs — avoids a sprawl of flat frozen fields with
no validation payoff for passthrough values.

### 4.3 `generators/cowork.py`
Refactor `build_cowork()` to assemble the dict in **plist key order** (so golden diffs stay readable),
via small per-group helpers that each return only the keys whose source field is set:

```
_core()              # inferenceProvider, inferenceCredentialKind (always)
_bedrock()           # region, sso*, serviceTier (existing) + baseUrl/profile/awsDir/bearerToken
_inference_common()  # customHeaders, modelDiscovery, models, maxTokens*, tokenWindow*
_credential_helper() # the 4 helper keys
_desktop()           # 8 bools + egress + workspaceFolders
_telemetry()         # otlp* + disable*Telemetry/Services
_updates()           # enforcementHours, disableAutoUpdates
_org_tools()         # deploymentOrgUuid, pluginsUrl, orgPluginSettings, managedMcpServers,
                     #   disabledBuiltinTools, builtinToolPolicy
_bootstrap()         # bootstrap* + claudeAiImport
_banner()            # existing
```

**The 7 core keys stay unconditional.** `inferenceProvider`, `inferenceCredentialKind`,
`inferenceBedrockRegion`, and the four `inferenceBedrockSso*` keys are emitted **always — even when
`None`** (exactly today's behavior; in practice non-null via SSO inheritance). The omit-when-null rule
applies **only to the new keys**. `_core()` and `_bedrock()` must hard-code these 7 as unconditional
and gate only the *added* Bedrock extras (`baseUrl`/`profile`/`awsDir`/`bearerToken`/`serviceTier`).
The final dict ordering follows the plist for stable golden diffs.

### 4.4 `validate/consistency.py`
`CheckResult` has only `errors` and `next_steps` — **no `warnings` field**. Route the new non-fatal
notices through **`next_steps`** (lower-churn; matches existing usage). Gated on
`cowork_settings is not None`:
- **Sensitive-data notice** (next_steps): if any in-scope `[S]` key is present, note that `config.yaml`
  now carries secrets and should not be committed / should be templated.
- Existing Bedrock-SSO-completeness and SSO↔profile checks unchanged. *(No provider-coherence check —
  group G deferred, so `bedrock` is the only provider.)*

### 4.5 `exporters/reg.py`
`_value_literal`: check **`bool` before `int`** (`bool` ⊂ `int`); emit
`dword:00000001`/`dword:00000000` for `bool`, `dword:%08x` for `int`; keep `REG_SZ` (quoted, JSON for
dict/list) for everything else. `build_reg` line format becomes `"key"=dword:...` vs `"key"="..."`
accordingly. `mobileconfig.py` unchanged (plistlib native types).

### 4.6 `config.example.yaml`
Append the new grouped sections, fully commented, every value `null`/`[]` so the **generated default
output is unchanged**. As shipped the file stays commit-safe (all sensitive keys null); amend the
header to keep the "safe to commit" guarantee **conditional** — "non-secret *unless you populate the
optional sensitive keys* (`bedrock.bearer_token`, the provider API keys, `otlp_headers`, …)" — rather
than retracting it outright. Each key carries its policy name in a trailing comment (as today).

---

## 5. Tests

- **`tests/generators/test_cowork.py`** — new cases: each group emits its keys only when set; correct
  policy-key names/values; omit-when-null; plist ordering; sensitive keys flow through; free-form JSON
  blobs nest correctly.
- **`tests/config/test_loader.py`** — `config.example.yaml` still validates; new enums reject bad
  values (`telemetry.otlp_protocol: ftp`, `gateway.auth_scheme: basic`); `extra="forbid"` still bites.
- **`tests/mapping/test_resolve.py`** — new passthrough fields resolve; Bedrock SSO inheritance and
  default-model derivation unchanged.
- **`tests/exporters/test_reg.py`** — bool→`dword:00000001`, int→`dword:`, string/JSON→`REG_SZ`.
- **`tests/exporters/test_mobileconfig.py`** — new bool/int keys round-trip as native plist types.
- **`tests/validate/test_consistency.py`** — sensitive-data and provider-coherence warnings fire.
- **Golden (`tests/golden/`)** — **`cowork-bedrock.json` must be unchanged** (proves additivity); add a
  second fixture config exercising a broad set of the new keys, with its own golden, regenerated via
  `CBIDC_UPDATE_GOLDEN=1` and eyeballed against the plist.

---

## 6. Phasing

1. Schema sub-models + `CoworkConfig` extension + loader test (validate example still parses).
2. `config.example.yaml` grouped sections (all null) — confirm default golden unchanged.
3. `resolve.py` `ResolvedCowork` extension + resolve tests.
4. `build_cowork()` refactor into ordered group helpers + generator tests.
5. `reg.py` dword support + exporter tests.
6. `consistency.py` warnings + tests.
7. Second "full coverage" golden fixture + golden test.
8. Docs: README Cowork section — table of all supported policy groups; sensitive-key caveat.

---

## 7. Open questions — resolved in review (confirm at approval)

1. **[RESOLVED] `ResolvedCowork` shape:** hybrid — explicit fields for the typed groups (common,
   bedrock, desktop, telemetry, updates, credential_helper) + a single `extra: dict[str, Any]` for the
   free-form JSON blobs and secondary providers. Avoids ~50 flat frozen fields. (§4.2)
2. **[DECIDED — Bedrock-only] Other providers (anthropic/gateway/vertex/foundry):** group G's **19
   keys are deferred**. `inference_provider` stays `Literal["bedrock"]`; no `cowork.providers`
   sub-model. In-scope coverage is **52 of 71** keys. (A follow-up can add group G later by widening the
   enum + adding the sub-model — no rework of this change required.)
3. **[RESOLVED] Sensitive keys:** model them, default null, never in the example, note when set.
   Shipped file stays commit-safe. (§3.3)
4. **[RESOLVED] `.reg` dword change:** make it — correct per ADMX `<decimal>` semantics and provably
   cannot alter any currently-emitted value. (§3.5 / §4.5)
5. **[RESOLVED] `bootstrapEnabled` default:** omit-unless-set; do not emit the manifest's `true`
   default. (omit-when-unset rule, §3.2)
