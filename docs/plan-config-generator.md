# Plan: YAML-Driven Settings Generator for Claude Code + Cowork on 3P (Bedrock + IAM Identity Center), run in GitHub Actions

**Status:** Draft for review
**Author:** Claude Code (Opus 4.8)
**Date:** 2026-06-20

---

## 1. Goal

A **`run` script** (`run.py`) that takes a single YAML configuration file and generates all the settings needed to use Amazon Bedrock with AWS IAM Identity Center (SSO) for:

1. **AWS SSO profile** (`~/.aws/config`) — the `[profile …]` block that IAM Identity Center login depends on. **This is what makes Claude Code's `AWS_PROFILE` / `awsAuthRefresh` actually resolve** (§2.0). Without it, the Claude Code settings point at a profile that doesn't exist.
2. **Claude Code** settings (`settings.json`) — Bedrock + IAM Identity Center.
3. **Cowork on 3P** managed settings — Cowork's third-party Bedrock inference config with interactive "Sign in with AWS" (IAM Identity Center), emitted as a JSON settings blob plus **experimental** `.mobileconfig` / `.reg` scaffolds for MDM (§2.2 / open question 4).

**This is not a CLI tool** and **not** about Claude Desktop. It is one entry-point script (`run.py`) invoked by a **GitHub Actions workflow** (§9). The script is a thin orchestrator over a set of **small, independently unit-testable modules** (§4) — explicitly *not* one big script — so each generator, mapper, and writer can be tested in isolation.

The YAML ships **pre-populated with defaults** from current Claude documentation, so a user only edits a few fields (AWS profile name, region, SSO start URL/account/role, model pins).

> **Scope honesty.** The script generates *config files*; it does not perform AWS-side prerequisites. Enabling Bedrock model access (one-time "use case" submission), attaching the IAM policy, and creating the IAM Identity Center permission set are **manual** and assumed done (documented in README, §8). The script gets you to *correct, consistent settings*; a built-in offline consistency check (`--check-only`, §4.4) verifies internal consistency, but a fully working setup still needs the AWS-side steps and an interactive sign-in on the user's machine.

> **Headless-CI note.** Interactive IAM Identity Center sign-in (the `aws sso login` browser flow and Cowork's device-auth) **cannot complete on a headless Actions runner**. So the workflow's job is to **generate and publish the settings files as artifacts** (offline, no AWS secrets needed) — *not* to authenticate or run inference. Consumers (developer machines / MDM) apply the artifacts and sign in locally. See §9.

The script must be testable locally in fully isolated environments (no real AWS calls, no writes outside a temp dir).

---

## 2. Key research findings (authoritative, from docs)

Sourced from `code.claude.com/docs` (Amazon Bedrock + Settings pages) and `claude.com/docs/cowork/3p/bedrock-aws-sign-in`.

### 2.0 The `~/.aws/config` SSO profile (the missing link for Claude Code)

Claude Code authenticates to Bedrock through the **standard AWS SDK credential chain**. With IAM Identity Center, `AWS_PROFILE=<name>` and `awsAuthRefresh: "aws sso login --profile <name>"` both resolve against a profile block in `~/.aws/config`:

```ini
[profile my-sso-profile]
sso_start_url = https://my-org.awsapps.com/start
sso_region = us-east-1
sso_account_id = 123456789012
sso_role_name = ClaudeCodeBedrockRole
region = us-east-1
output = json
```

If this block is absent, `aws sso login --profile my-sso-profile` fails with *"profile not found"* and Claude Code never gets credentials — so emitting `settings.json` alone is **not** a working setup. The YAML already carries every value above, so the script generates this profile as a first-class target. This is the dependency the rest of §2.1 builds on. Generation uses stdlib `configparser`; it **merges** into an existing `~/.aws/config`, preserving other profiles.

### 2.1 Claude Code → Bedrock + IAM Identity Center

Claude Code reads Bedrock config from the `env` block of `settings.json`, plus a few top-level keys:

- `CLAUDE_CODE_USE_BEDROCK=1` — enables Bedrock.
- `AWS_PROFILE` — the IAM Identity Center profile name in `~/.aws/config`.
- `AWS_REGION` — region for Bedrock (optional if the profile sets one; resolution order `AWS_REGION` → `AWS_DEFAULT_REGION` → profile region → `us-east-1`).
- **Model pins** (recommended for teams; bare aliases otherwise lag):
  - `ANTHROPIC_DEFAULT_OPUS_MODEL` = `us.anthropic.claude-opus-4-8`
  - `ANTHROPIC_DEFAULT_SONNET_MODEL` = `us.anthropic.claude-sonnet-4-6`
  - `ANTHROPIC_DEFAULT_HAIKU_MODEL` = `us.anthropic.claude-haiku-4-5-20251001-v1:0`
  - `us-gov.` prefix for GovCloud; ARNs for application inference profiles.
  - *Note:* Claude Code's **built-in** unpinned Bedrock default is currently Sonnet 4.5 (`us.anthropic.claude-sonnet-4-5-20250929-v1:0`). The plan deliberately pins `sonnet` to **4.6** — pinning *ahead* of the lagging built-in default is the whole point (not a typo).
- **SSO auto-refresh** (top-level, *not* in `env`):
  - `awsAuthRefresh: "aws sso login --profile <profile>"` — runs when Claude Code detects expired credentials.
  - `awsCredentialExport` — alternative when `.aws` can't be modified; outputs JSON credentials. (In practice mutually exclusive with `awsAuthRefresh`.)
- Optional Bedrock extras (emit only when requested): `ANTHROPIC_BEDROCK_BASE_URL`, `ANTHROPIC_BEDROCK_SERVICE_TIER` (`default|flex|priority`), `ANTHROPIC_CUSTOM_HEADERS` for Guardrails, `DISABLE_PROMPT_CACHING`, `ENABLE_PROMPT_CACHING_1H`.
- `modelOverrides` — map model versions to specific inference-profile ARNs.
- `model`, `permissions` — general settings passed through.

**Caveat (docs):** `awsAuthRefresh` can cause an SSO auth loop behind corporate VPN/TLS proxies. The YAML makes it easy to omit `awsAuthRefresh` (user runs `aws sso login` manually).

**Settings file scope** (chosen via YAML `claude_code.scope`, not a CLI flag):

| Scope | Path |
|-------|------|
| user | `~/.claude/settings.json` |
| project | `<project>/.claude/settings.json` |
| local | `<project>/.claude/settings.local.json` |

### 2.2 Cowork on 3P → Bedrock + AWS Sign-in (IAM Identity Center)

Source: `claude.com/docs/cowork/3p/bedrock-aws-sign-in`. Cowork is a separate 3rd-party-platform app that runs Bedrock inference and supports **interactive "Sign in with AWS"** backed by IAM Identity Center — an OAuth device-auth flow that stores encrypted IDC tokens in OS secure storage (Keychain / Windows DPAPI). No AWS CLI or shared bearer token required; CloudTrail records per-user identity.

Config is delivered as **managed app settings**. The doc's **supported** production path: configure in the app's "Configure third-party inference" panel, then click **Export** to produce a `.mobileconfig` (macOS) or `.reg` (Windows) for MDM. Hand-authoring is allowed but the doc documents only the *keys table* below — **not** the `.mobileconfig` `PayloadType`/wrapper or the Windows registry path (confirmed against the live doc).

Keys (verified against the live doc):

| Key | Purpose |
|-----|---------|
| `inferenceBedrockSsoStartUrl` | AWS access portal URL |
| `inferenceBedrockSsoRegion` | IAM Identity Center home region |
| `inferenceBedrockSsoAccountId` | 12-digit AWS account ID where Bedrock is enabled |
| `inferenceBedrockSsoRoleName` | IAM Identity Center permission-set name |
| `inferenceBedrockRegion` | Bedrock runtime region |
| `inferenceModels` | Model list using Bedrock inference-profile IDs |
| `inferenceCredentialKind` | **Pins which credential source is used.** When unset *and* >1 credential configured, precedence is: in-app sign-in → named profile → credential helper → bearer token. |
| `inferenceBedrockProfile` | (alt auth) named AWS profile — not used for the SSO goal |
| `inferenceBedrockBearerToken` | (alt auth) Bedrock API key — not used for the SSO goal |

Behavior the generator must respect:
- **All four `inferenceBedrockSso*` keys are required together** — doc wording: *"If only some of the `inferenceBedrockSso*` keys are set, the app logs a warning and ignores the partial configuration."* The generator validates and fails fast.
- **`inferenceCredentialKind` is pinned to force in-app AWS sign-in** so SSO is chosen deterministically even when a profile/bearer token also exists. ⚠️ The doc names the source ("in-app AWS sign-in") but **not the exact string literal** — placeholder, configurable via `cowork.credential_kind`, confirm from an app Export (open question 5).
- Permission set grants `bedrock:InvokeModel` + `bedrock:InvokeModelWithResponseStream`, session 8–12h; egress to `oidc.<sso-region>.amazonaws.com` and `portal.sso.<sso-region>.amazonaws.com`. (Operator docs; not emitted.)
- `inferenceModels` reuses the same Bedrock inference-profile IDs as the Claude Code pins — the YAML `models` block is the single source of truth across targets.

**Asymmetry:** Cowork uses `inference*`-prefixed managed keys (not `env`/`CLAUDE_CODE_USE_BEDROCK`, not `awsAuthRefresh`). The same logical inputs map to *different key names per target*; the mapping layer (§4) makes this explicit.

**MDM-envelope reality:** the JSON key/value blob is authoritative. The `.mobileconfig`/`.reg` wrappers are **experimental** (doc doesn't specify their structure; supported path is the app's **Export**). JSON is the default Cowork output; wrappers are opt-in, clearly-labeled experimental scaffolds (§5.2, open question 4).

---

## 3. YAML schema (pre-populated defaults)

A single `config.yaml` drives all three targets:

**Two files, one format.** `config.example.yaml` is a committed, untouched reference copy holding the defaults below. `config.yaml` is the **real, committed source of truth** the user edits and the workflow runs against (§9.2). Keeping `config.yaml` in the repo is intentional — none of its fields are secret (SSO start URL, account ID, role name, region are not credentials), so committing it is what lets GitHub Actions regenerate settings on change. If you prefer not to commit it, see open question 1.

```yaml
# config.yaml  (committed; seeded from config.example.yaml)

version: 1

aws:
  profile: my-sso-profile        # AWS_PROFILE + ~/.aws/config [profile <name>]
  region: us-east-1              # AWS_REGION
  write_aws_config: true         # generate/merge the ~/.aws/config profile (§2.0)
  config_path: null              # default ~/.aws/config (or $AWS_CONFIG_FILE)
  sso:
    enabled: true
    start_url: https://my-org.awsapps.com/start
    sso_region: us-east-1
    account_id: "123456789012"
    role_name: ClaudeCodeBedrockRole
    auto_refresh: true           # true -> emit awsAuthRefresh; false -> manual login

bedrock:
  enabled: true                 # -> CLAUDE_CODE_USE_BEDROCK=1
  base_url: null                # optional ANTHROPIC_BEDROCK_BASE_URL
  service_tier: null            # default|flex|priority|null
  prompt_caching: default       # default|disabled|one_hour
  guardrail:
    enabled: false
    identifier: null
    version: null

models:
  opus:   us.anthropic.claude-opus-4-8
  sonnet: us.anthropic.claude-sonnet-4-6
  haiku:  us.anthropic.claude-haiku-4-5-20251001-v1:0
  default: sonnet               # which model family Claude Code defaults to
  pin_default: true             # true -> `model` = resolved ID of `default`
                                # false -> `model` = bare alias "sonnet"
  overrides: {}                 # optional modelOverrides ARNs

claude_code:
  enabled: true
  scope: user                   # user | project | local
  project_dir: null             # required when scope is project/local
  permissions:
    allow: []
    deny: []
  extra_env: {}                 # passthrough env vars
  merge_existing: true          # merge into an existing settings.json vs overwrite

cowork:                         # Cowork on 3P: interactive "Sign in with AWS" (IDC)
  enabled: true
  # SSO keys inherit from aws.sso.* by default; override only if Cowork differs.
  sso_start_url: null           # -> inferenceBedrockSsoStartUrl
  sso_region: null              # -> inferenceBedrockSsoRegion
  sso_account_id: null          # -> inferenceBedrockSsoAccountId
  sso_role_name: null           # -> inferenceBedrockSsoRoleName
  bedrock_region: null          # default aws.region -> inferenceBedrockRegion
  models: []                    # default derived from `models` -> inferenceModels
  credential_kind: aws-sso      # -> inferenceCredentialKind (PLACEHOLDER literal)
  export:
    formats: [json]             # json (authoritative) | mobileconfig | reg (experimental)
    mobileconfig:
      payload_identifier: com.anthropic.cowork.bedrock   # UNVERIFIED placeholder
      organization: My Org
    reg:
      hive: HKLM                # HKLM | HKCU
  merge_existing: true

output:
  mode: stage                   # stage (write into output.dir) | install (real home/app paths)
  dir: ./generated              # used when mode=stage (what CI uploads as an artifact)
  backup: true                  # back up existing files before overwrite (install mode)
```

The only fields a typical user edits are `aws.profile`, `aws.region`, and `aws.sso.*` — these feed all three targets without restating. `output.mode: stage` is the CI-safe default (writes into a directory the workflow uploads); `install` writes to real `~/.aws/config` / `~/.claude/settings.json` paths for a developer machine. **Validation:** when `cowork.enabled`, all four resolved SSO values must be present (partial config is ignored by Cowork).

---

## 4. Architecture (modular — each box is independently unit-testable)

A thin `run.py` entry point orchestrates small single-responsibility modules. No subcommands, no CLI framework — just minimal arg parsing delegating into the package.

```
run.py                          # THIN entry point: parse args -> Pipeline.run(); ~30 lines
src/claude_bedrock_idc/
  config/
    schema.py        # Pydantic models for the YAML (validation + field defaults)
    defaults.py      # canonical default config (single source of truth)
    loader.py        # path -> validated Config (merge embedded defaults), + inheritance resolve
  mapping/
    resolve.py       # pure: Config -> ResolvedInputs (SSO/region/model values resolved once,
                     #   incl. cowork.* inheritance from aws.sso.*). One place; everyone reads it.
  generators/        # each: ResolvedInputs -> in-memory artifact (dict/INI/str). NO disk I/O.
    aws_profile.py   # -> ConfigParser section for ~/.aws/config (§2.0)
    claude_code.py   # -> settings.json dict (env block, awsAuthRefresh, model, ...)
    cowork.py        # -> Cowork managed-settings dict (inferenceBedrock* + credentialKind)
  exporters/         # each: cowork dict -> serialized bytes/str. NO disk I/O. EXPERIMENTAL.
    mobileconfig.py  # -> macOS .mobileconfig (plistlib, full Configuration-profile wrapper)
    reg.py           # -> Windows .reg text (REG_MULTI_SZ for lists, UTF-16LE)
  validate/
    consistency.py   # pure: cross-target checks (AWS_PROFILE <-> profile, SSO completeness)
  io/
    paths.py         # resolve target paths from Config + output.mode (pure: input->Path)
    merge.py         # PURE merge logic: JSON deep-merge + INI section-merge (no disk)
    writer.py        # the ONLY disk-touching module: atomic write, backup; calls merge.py
  pipeline.py        # orchestration: load -> resolve -> generate -> validate -> write/stage
config.example.yaml
docs/plan-config-generator.md   # this file
.github/                        # CI/CD — see §9
```

**Why this shape (testability):**
- **Pure core, single I/O seam.** Every generator/exporter/mapper/validator is a **pure function** (input → value, no disk, no network). Only `io/writer.py` touches the filesystem. So 95% of logic is unit-tested with plain in-memory assertions — no temp dirs, no mocking — and the one I/O module gets focused tests with `tmp_path`.
- **`mapping/resolve.py` centralizes the fan-out.** SSO/region/model values (incl. `cowork.*` inheritance) are resolved exactly once into a `ResolvedInputs` dataclass; each generator consumes that. This is what makes the "single source of truth → three vocabularies" claim *testable* and prevents the targets from drifting.
- **`pipeline.py` is orchestration only** (compose the above), and `run.py` is a ~30-line shell around `pipeline.run()`. Neither contains business logic, so the thin top layer needs only a couple of smoke tests.

### 4.1 Data flow

```
config.yaml ─ loader ─> Config ─ resolve ─> ResolvedInputs
   ResolvedInputs ─ AwsProfileGenerator ─> INI section ─┐
   ResolvedInputs ─ ClaudeCodeGenerator ─> settings dict ┤
   ResolvedInputs ─ CoworkGenerator ─────> cowork dict ──┤
                                          (+ exporters)   │
                                                          ├─ consistency.check() ─ (fail fast)
                                                          └─ writer ─> stage dir  | real paths
```

The AWS-profile and Claude Code generators are **paired**: the profile generator writes the `[profile <name>]` that the Code generator's `AWS_PROFILE`/`awsAuthRefresh` reference — closing the chain to a working login. `consistency.check()` runs **before** any write so a bad config fails the workflow without leaving half-written files.

### 4.2 Key design rules

- **Per-target gating.** The pipeline skips a target when its `enabled` flag is false: `aws.write_aws_config`, `claude_code.enabled`, `cowork.enabled`. Each generator is invoked only when enabled; `consistency.check()` accounts for which targets were produced (e.g., a dangling `AWS_PROFILE` is only an error when Claude Code is enabled). Every `enabled` flag is consumed and has a skip test (§7.2).
- **No network / no AWS calls** anywhere (generation and validation are offline). The script writes config; it does not call `aws sso login` or Bedrock.
- **Deterministic output:** stable key ordering, JSON 2-space indent + trailing newline; INI written deterministically — so artifacts diff cleanly and golden-file tests can assert exact bytes.
- **Merge semantics live in the pure `io/merge.py`** (not in the disk layer), so deep-merge correctness is unit-tested with plain in-memory dicts/`ConfigParser` objects — no `tmp_path`. `writer.py` reads the existing file, hands it to `merge.py`, and writes the result. JSON deep-merges when `merge_existing: true` (the `env` block merges key-by-key); `~/.aws/config` merges at the INI-section level (only the target `[profile <name>]` is touched, other profiles preserved). `output.mode: stage` always writes fresh files into `output.dir`.
- **Safety (install mode):** back up existing file to `<file>.bak.<timestamp>` before overwrite.

### 4.3 `run.py` interface (a script, not a CLI tool)

```
python run.py [CONFIG]              # CONFIG defaults to ./config.yaml
  --out-dir DIR                     # override output.dir (stage mode)
  --mode stage|install              # override output.mode
  --check-only                      # validate + consistency check, write nothing; exit 1 on problem
  --cowork-format json[,mobileconfig,reg]   # override cowork.export.formats
```

Defaults are config-driven; flags are thin overrides for the workflow. There are no subcommands. `run.py` exits non-zero on validation/consistency failure so a GitHub Actions step fails loudly.

### 4.4 Consistency check (`--check-only`, offline)

Run automatically before writing, and runnable standalone for PR CI:
- `[profile <aws.profile>]` carries all five SSO/region keys (`sso_start_url`, `sso_region`, `sso_account_id`, `sso_role_name`, `region`; plus `output = json`) consistent with the YAML.
- Claude Code settings: `CLAUDE_CODE_USE_BEDROCK=1`, `AWS_PROFILE` **matches a generated profile**, and (if set) `awsAuthRefresh`'s `--profile` matches. *(Catches the core gap: settings pointing at a non-existent profile.)*
- Cowork: all four `inferenceBedrockSso*` present and `inferenceCredentialKind` set.
- Emits actionable next steps it cannot perform (e.g., `aws sso login --profile …`, AWS-side model enablement).

---

## 5. Generated output examples

### 5.0 AWS SSO profile (`~/.aws/config`) — generated first

```ini
[profile my-sso-profile]
sso_start_url = https://my-org.awsapps.com/start
sso_region = us-east-1
sso_account_id = 123456789012
sso_role_name = ClaudeCodeBedrockRole
region = us-east-1
output = json
```

### 5.1 Claude Code `settings.json`

```json
{
  "$schema": "https://json.schemastore.org/claude-code-settings.json",
  "awsAuthRefresh": "aws sso login --profile my-sso-profile",
  "model": "us.anthropic.claude-sonnet-4-6",
  "env": {
    "CLAUDE_CODE_USE_BEDROCK": "1",
    "AWS_PROFILE": "my-sso-profile",
    "AWS_REGION": "us-east-1",
    "ANTHROPIC_DEFAULT_OPUS_MODEL": "us.anthropic.claude-opus-4-8",
    "ANTHROPIC_DEFAULT_SONNET_MODEL": "us.anthropic.claude-sonnet-4-6",
    "ANTHROPIC_DEFAULT_HAIKU_MODEL": "us.anthropic.claude-haiku-4-5-20251001-v1:0"
  }
}
```

`model` is the concrete resolved ID of `models.default` (`pin_default: true`), not the bare alias — matching the team-pinning thesis. With `auto_refresh: false`, `awsAuthRefresh` is omitted and the script logs a reminder to run `aws sso login --profile my-sso-profile`.

### 5.2 Cowork on 3P managed settings

JSON form (`cowork-bedrock.json`) — **the authoritative deliverable**:

```json
{
  "inferenceBedrockSsoStartUrl": "https://my-org.awsapps.com/start",
  "inferenceBedrockSsoRegion": "us-east-1",
  "inferenceBedrockSsoAccountId": "123456789012",
  "inferenceBedrockSsoRoleName": "ClaudeCodeBedrockRole",
  "inferenceBedrockRegion": "us-east-1",
  "inferenceCredentialKind": "aws-sso",
  "inferenceModels": [
    "us.anthropic.claude-opus-4-8",
    "us.anthropic.claude-sonnet-4-6",
    "us.anthropic.claude-haiku-4-5-20251001-v1:0"
  ]
}
```

⚠️ `"aws-sso"` for `inferenceCredentialKind` is a placeholder — confirm the literal from an app Export (open question 5).

> **`.mobileconfig` / `.reg` are EXPERIMENTAL.** The live doc specifies the *keys* but **not** the `.mobileconfig` `PayloadType`/wrapper UUIDs nor the Windows registry path/value types; the supported path is the app's own **Export**. The exporters scaffold a best-effort `.mobileconfig` (full Configuration-profile wrapper via `plistlib`, `inferenceModels` as a plist `<array>`) and `.reg` (`inferenceModels` as `REG_MULTI_SZ`), each carrying an "UNVERIFIED placeholder" header. **JSON is the default**; the wrappers are a convenience, not a guarantee.

---

## 6. Dependencies (uv-managed, per CLAUDE.md)

Runtime:
- `pydantic>=2` — schema validation + defaults.
- `pyyaml` — YAML parsing.

That's it — `run.py` uses stdlib `argparse` for its ~3 flags (no CLI framework, no `[project.scripts]` console entry; it's invoked as `python run.py`).

Dev/test (`[project.optional-dependencies]`):
- `dev`: `ruff` (lint + format).
- `test`: `pytest`, `pytest-cov`.

**No new deps for the moving parts:** `~/.aws/config` via stdlib `configparser`; `.mobileconfig` via stdlib `plistlib`; `.reg` plain UTF-16LE text; consistency check reads INI/JSON with the stdlib. No `boto3` (everything is offline).

---

## 7. Test plan (local, isolated, modular)

The modular design (§4) means most tests are **pure unit tests** — call a function, assert the returned dict/string. No network, no AWS, and disk only in the few `io/` and pipeline tests (`tmp_path`).

### 7.1 Isolation harness (`tests/conftest.py`)
- Autouse fixture sets `HOME` to `tmp_path`; clears AWS/Bedrock env vars so dev-shell leakage can't affect output.
- `sample_config` fixture returns the parsed default `Config`; `resolved` fixture returns `ResolvedInputs`.

### 7.2 Unit tests (one file per module)

**`tests/config/` (schema + loader)**
- `config.example.yaml` validates; missing `aws.profile` → error; bad enum (`service_tier: turbo`) → rejected.
- Defaults round-trip: defaults → YAML → load → equal.
- `scope: project` without `project_dir` → error.
- `cowork.enabled` with partial SSO → validation error (all four required).

**`tests/mapping/test_resolve.py`** *(the fan-out, tested once)*
- `cowork.sso_* = null` inherits from `aws.sso.*`; explicit `cowork.*` overrides win.
- `inferenceModels` derived from `models` (IDs + ordering); `bedrock_region` falls back to `aws.region`.
- `pin_default` resolves `model` to a concrete ID vs the bare alias.

**`tests/generators/test_aws_profile.py`**
- Emits `[profile <name>]` with the five SSO/region keys + `output = json` from resolved inputs.
- Merge preserves other profiles; idempotent re-run (no duplicate sections).
- `write_aws_config: false` → no section produced (consistency check then flags the dangling `AWS_PROFILE`).

**`tests/generators/test_claude_code.py`**
- `CLAUDE_CODE_USE_BEDROCK="1"`; `AWS_PROFILE`/`AWS_REGION` populated; all three model pins present.
- `auto_refresh` true/false → `awsAuthRefresh` present/absent with right `--profile`.
- Guardrail → `ANTHROPIC_CUSTOM_HEADERS` with both headers; `service_tier`/`base_url`/caching only when set.
- `permissions` pass through; empty lists omitted. Output is valid JSON.
- `claude_code.enabled: false` → target skipped (mirrors the Cowork skip test).

**`tests/generators/test_cowork.py`**
- Six `inferenceBedrock*` keys + `inferenceCredentialKind` present and mapped correctly; `inferenceCredentialKind` always emitted (deterministic SSO selection).
- **No Claude Code keys** (`env`, `CLAUDE_CODE_USE_BEDROCK`, `awsAuthRefresh`) leak into Cowork output (asymmetry assertion).
- `enabled: false` → skipped.

**`tests/exporters/` (EXPERIMENTAL paths)**
- `.mobileconfig` round-trips via `plistlib.loads`, includes the full Configuration-profile wrapper, `inferenceModels` as plist `<array>`, and the "UNVERIFIED placeholder" comment.
- `.reg` has correct header/hive path, quoted scalars, `REG_MULTI_SZ` for the list, UTF-16LE.
- *(Structure/round-trip only — explicitly not "this is what Cowork accepts," §5.2.)*

**`tests/validate/test_consistency.py`** *(proves the goal, not just serialization)*
- Passes for a fully generated, consistent set.
- **Fails when `settings.json` `AWS_PROFILE` has no matching `[profile …]`** — the core regression guard.
- Fails on partial Cowork SSO or missing `inferenceCredentialKind`.
- SSO values in `~/.aws/config` and Cowork `inferenceBedrockSso*` are mutually consistent when both derive from `aws.sso.*`.

**`tests/io/test_merge.py`** *(pure — no disk)*
- JSON deep-merge: nested `env` keys merge key-by-key; existing siblings preserved; `merge_existing: false` replaces.
- INI section-merge: target `[profile <name>]` updated, other `[profile …]` sections untouched; idempotent.

**`tests/io/test_paths.py` + `test_writer.py`**
- Paths resolve per `output.mode` (stage dir vs real home paths) and `claude_code.scope`; Cowork artifact filenames per format.
- Writer: atomic write (temp + rename), backup on overwrite (install), delegates to `merge.py`, trailing newline / 2-space indent. *(Merge correctness itself is covered by `test_merge.py`; writer tests only the disk seam.)*

**`tests/test_pipeline.py` + `tests/test_run.py`** *(thin smoke)*
- `pipeline.run()` on the default config into `tmp_path` produces all three targets, consistent.
- `run.py --check-only` exits 0 on good config, 1 on inconsistent; `--out-dir`/`--mode`/`--cowork-format` overrides honored; missing config file → clear error + exit 1.

### 7.3 Golden files
- Expected `~/.aws/config` profile / `settings.json` / `cowork-bedrock.json` under `tests/golden/`, byte-compared; update via `--update-golden` env flag.
- **Exception:** `.mobileconfig`/`.reg` get structural/round-trip tests only (unverified envelope, §5.2).

### 7.4 Running
```bash
uv pip install -e ".[test]"
pytest --cov=src/claude_bedrock_idc --cov-report=term-missing   # fully offline
```
Target coverage ≥90% on `config/`, `mapping/`, `generators/`, `validate/`, `io/`.

---

## 8. Implementation phases

1. **Scaffold** `pyproject.toml` (deps, test extras — no console-script), package dirs, `config.example.yaml`.
2. **`config/`** schema + defaults + loader + tests.
3. **`mapping/resolve.py`** (the fan-out / inheritance) + tests — built early since every generator depends on it.
4. **`generators/aws_profile.py`** (INI, section-merge) + tests + golden. **First generator — the dependency Claude Code points at (§2.0).**
5. **`generators/claude_code.py`** (incl. `pin_default`) + tests + golden.
6. **`validate/consistency.py`** + tests — the goal-proving guard (`AWS_PROFILE` ↔ profile; SSO ↔ Cowork).
7. **`generators/cowork.py`** + tests + golden.
8. **`exporters/`** (EXPERIMENTAL `.mobileconfig`/`.reg`) + structural tests; JSON stays authoritative.
9. **`io/`** paths + writer (stage/install, backup, JSON+INI merge) + tests.
10. **`pipeline.py`** + **`run.py`** + smoke tests.
11. **Docs:** README — invocation (`python run.py`), **manual AWS-side prerequisites** (model access, IAM policy, permission set), `awsAuthRefresh` SSO-loop caveat, Cowork supported path = app **Export** (`.mobileconfig`/`.reg` experimental), all-four-SSO-keys rule, `inferenceCredentialKind`, the headless-CI note (§1).
12. **GitHub Actions** workflows (§9).

---

## 9. GitHub Actions (the execution vehicle; free-account-conscious)

Two workflows: **`generate.yml`** runs the script to produce/publish settings (the actual process the user wants), and **`ci.yml`** tests the repo.

### 9.1 Free-tier cost model
- **Public repo → unlimited minutes.** **Private repo → 2,000 min/month**, multipliers **Linux 1× / Windows 2× / macOS 10×**.
- **Rule:** everything on `ubuntu-latest`. Safe because the script is pure Python with no OS-native runtime behavior — the OS-specific bits (Cowork `.mobileconfig` vs `.reg`) are selected by config fields (`export.formats`, `reg.hive`) and tests force those, so Linux exercises all branches.
- Small Python matrix (two versions), `concurrency` cancel, pinned first-party actions, short artifact retention.

### 9.2 `.github/workflows/generate.yml` — run the script, publish settings

Generation is **offline** (no AWS secrets). Output is staged and uploaded as an artifact; consumers apply it and sign in locally (headless-CI note, §1).

```yaml
name: Generate Claude settings
on:
  push:
    branches: [main]
    paths: ["config.yaml", "src/**", "run.py"]
  workflow_dispatch: {}
permissions:
  contents: read
concurrency:
  group: generate-${{ github.ref }}
  cancel-in-progress: true
jobs:
  generate:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: astral-sh/setup-uv@v5
        with: { enable-cache: true }
      - run: uv pip install -e . --system
      - name: Ensure config.yaml exists (seed from example if absent)
        run: test -f config.yaml || cp config.example.yaml config.yaml
      - name: Validate config (offline consistency check)
        run: uv run python run.py config.yaml --check-only
      - name: Generate settings into staging dir
        run: uv run python run.py config.yaml --mode stage --out-dir generated
      - name: Upload settings artifact
        uses: actions/upload-artifact@v4
        with:
          name: claude-settings
          path: generated/
          retention-days: 14
```

Notes:
- **No secrets, no network:** generation never authenticates. If you later want the workflow to *also* run Claude Code/Bedrock in-job, that needs real credentials via GitHub OIDC → `aws-actions/configure-aws-credentials` (role assumption) — **not** `aws sso login`, which can't complete headlessly. Called out as open question 6; out of scope for v1.
- `--check-only` runs first so a bad `config.yaml` fails the run before producing artifacts.

### 9.3 `.github/workflows/ci.yml` — lint + unit tests

```yaml
name: CI
on:
  push: { branches: [main] }
  pull_request: { branches: [main] }
concurrency:
  group: ci-${{ github.ref }}
  cancel-in-progress: true
permissions:
  contents: read
jobs:
  test:
    runs-on: ubuntu-latest
    strategy:
      fail-fast: false
      matrix:
        python-version: ["3.10", "3.12"]   # 3.10 floor (3.8/3.9 are EOL); see note
    steps:
      - uses: actions/checkout@v4
      - uses: astral-sh/setup-uv@v5
        with:
          python-version: ${{ matrix.python-version }}
          enable-cache: true
      - run: uv pip install -e ".[dev,test]" --system
      - run: uv run ruff check . && uv run ruff format --check .
      - run: uv run pytest --cov=src/claude_bedrock_idc --cov-report=term-missing
```

Fully offline; no AWS secrets, no service containers.

> **Python floor:** CLAUDE.md says "Python 3.8+", but 3.8 (and 3.9) are end-of-life. The matrix floors at **3.10** for tooling longevity; set `requires-python = ">=3.10"` in `pyproject.toml` to match. If 3.8 support is a hard requirement, revert both — but pin it deliberately, don't inherit it by accident.

### 9.4 Dependabot (free, no minutes consumed by itself)

```yaml
# .github/dependabot.yml
version: 2
updates:
  - package-ecosystem: github-actions
    directory: "/"
    schedule: { interval: weekly }
  - package-ecosystem: pip
    directory: "/"
    schedule: { interval: weekly }
```

### 9.5 Files added
```
.github/
  workflows/
    generate.yml    # runs run.py -> staged settings artifact (the main process)
    ci.yml          # lint + unit tests, Linux-only, small matrix
  dependabot.yml
```

No release/PyPI workflow — this is a script run in CI, not a published package.

---

## 10. Open questions for reviewer

1. **Output handling in CI:** is **upload-artifact** the right delivery (consumers download + apply), or do you want the workflow to **commit** the generated files back into the repo (e.g., a `generated/` dir), or **install** into the runner for a subsequent in-job step?
2. **`awsCredentialExport` path:** support it as an alternative to `awsAuthRefresh` now, or defer?
3. **Cowork default models:** should `inferenceModels` default to all three pinned profiles (Opus/Sonnet/Haiku), or a narrower list?
4. **[RESOLVED] Cowork MDM envelope:** real app Exports (`Claude.mobileconfig`, `Claude.reg`, `com.anthropic.claudefordesktop.plist`, `Claude.admx`, `identitycenter.json`) were provided. The `.mobileconfig`/`.reg` are now **first-class** (no longer experimental): `PayloadType` `com.anthropic.claudefordesktop`, registry key `HKCU\SOFTWARE\Policies\Claude`, complex values JSON-string-encoded. Generated JSON matches `identitycenter.json` exactly. Also added the real keys: `inferenceProvider`, `inferenceModels` as `{name,labelOverride}` objects, `inferenceBedrockServiceTier`, and `banner`.
5. **[RESOLVED] `inferenceCredentialKind` literal:** confirmed `interactive` (manifest enum: `static` \| `helper-script` \| `interactive` \| `vendor-profile`). Now the default.
6. **In-job inference (future):** do you ever want the workflow to actually *run* Claude Code on Bedrock (requires GitHub OIDC → AWS role assumption, since headless SSO can't sign in), or is generate-and-publish the whole scope?
7. **AWS config writing default:** OK to write/merge `~/.aws/config` by default (`write_aws_config: true`), or make it opt-in for teams that manage that file elsewhere?
8. **Repo visibility:** **public** (unlimited Actions minutes — matrix can grow) or **private** (keep Linux-only, 2-version matrix)?
