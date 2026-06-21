# Claude on Bedrock with IAM Identity Center — settings generator

Generate the settings needed to use **Amazon Bedrock with AWS IAM Identity Center
(SSO)** from a single YAML file, for:

1. **AWS SSO profile** (`~/.aws/config`) — the `[profile …]` block IAM Identity
   Center login depends on.
2. **Claude Code** (`settings.json`) — Bedrock + SSO.
3. **Cowork on 3P** — managed settings (the `inferenceBedrock*` keys), authoritative
   JSON plus *experimental* `.mobileconfig` / `.reg` scaffolds for MDM.

This is a **script** (`run.py`), not a CLI tool, designed to run in a GitHub Actions
workflow. It is modular (config / mapping / generators / exporters / validate / io /
pipeline) so each piece is unit-tested in isolation.

---

## How to run

### 1. Install

The project uses [`uv`](https://github.com/astral-sh/uv) (see `CLAUDE.md`).

```bash
uv venv                          # create .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
uv pip install -e ".[dev,test]"  # runtime + lint + test deps
```

Runtime needs only `pydantic` and `pyyaml`; everything else (INI, plist, .reg
generation) is the Python standard library.

### 2. Create your config

```bash
cp config.example.yaml config.yaml
```

Edit the fields marked `# EDIT ME` in `config.yaml` — at minimum `aws.profile`,
`aws.region`, and the `aws.sso.*` block. None of these are secrets, so `config.yaml`
is safe to commit (and committing it is what lets the GitHub Actions workflow pick
up changes). See [Configuration reference](#configuration-reference) below for every
key.

### 3. Generate

```bash
# Validate only — writes nothing, exits non-zero if the config is inconsistent.
python run.py config.yaml --check-only

# Stage mode (default): write all artifacts into ./generated (what CI uploads).
python run.py config.yaml --mode stage --out-dir generated

# Install mode: write straight to ~/.aws/config and ~/.claude/settings.json
# (merges into existing files, backing them up first).
python run.py config.yaml --mode install

# Choose Cowork output formats (json is authoritative; the others are experimental).
python run.py config.yaml --cowork-format json,mobileconfig,reg
```

If `config` is omitted it defaults to `./config.yaml`.

| Flag | Purpose |
|------|---------|
| `--mode {stage,install}` | `stage` writes into `--out-dir`; `install` writes to real home/app paths. Overrides `output.mode`. |
| `--out-dir DIR` | Staging directory (stage mode). Overrides `output.dir`. |
| `--check-only` | Run validation + consistency check only; write nothing. Exit 1 on any problem. |
| `--cowork-format LIST` | Comma-separated subset of `json,mobileconfig,reg`. Overrides `cowork.export.formats`. |

**What you get (stage mode):**

```
generated/
  aws/config                       # the [profile <name>] block
  claude/settings.json             # Claude Code settings
  cowork/cowork-bedrock.json       # authoritative Cowork managed settings
  cowork/cowork-bedrock.mobileconfig   # only if requested (experimental)
  cowork/cowork-bedrock.reg            # only if requested (experimental)
```

### What it does and does not do

- **Does:** write correct, internally-consistent config files; merge into an existing
  `~/.aws/config` (preserving other profiles) and `settings.json` (deep-merging the
  `env` block).
- **Does not:** perform AWS-side prerequisites or authenticate. You must separately:
  - enable **Bedrock model access** (one-time "use case" submission per account),
  - attach an **IAM policy** granting `bedrock:InvokeModel*` + inference-profile reads,
  - create the **IAM Identity Center permission set** referenced by `role_name`,
  - run `aws sso login --profile <name>` (or rely on Claude Code's `awsAuthRefresh`).

The offline consistency check (`--check-only`, also run automatically before every
write) verifies the generated files agree with each other — e.g. that Claude Code's
`AWS_PROFILE` matches a profile that actually gets generated.

---

## How to test

```bash
# Full suite (fully offline — no network, no AWS, no writes outside tmp dirs)
pytest

# With coverage
pytest --cov=src/claude_bedrock_idc --cov-report=term-missing

# A single module's tests
pytest tests/generators/test_claude_code.py

# Lint + format (as CI runs them)
ruff check .
ruff format --check .
```

Tests are isolated via `tests/conftest.py`, which points `$HOME` at a temp dir and
clears AWS/Bedrock env vars so nothing leaks in from your shell. Most tests are pure
unit tests on the in-memory artifacts; only the `io/` and pipeline tests touch disk
(through `tmp_path`).

**Golden files** (`tests/golden/`) byte-compare the authoritative outputs
(`aws_config.ini`, `settings.json`, `cowork-bedrock.json`). If you intentionally
change output, regenerate them:

```bash
CBIDC_UPDATE_GOLDEN=1 pytest tests/test_golden.py
```

The `.mobileconfig` / `.reg` wrappers are intentionally *not* golden-compared (their
envelope is unverified); they get structural/round-trip tests in `tests/exporters/`.

---

## Configuration reference

Every key in `config.example.yaml`, what it maps to, and why it exists.

### `aws` — AWS SSO profile + Claude Code AWS env

| Key | Default | Meaning |
|-----|---------|---------|
| `aws.profile` | `my-sso-profile` | Profile name. Becomes the `~/.aws/config` `[profile <name>]` header **and** Claude Code's `AWS_PROFILE`. The two must match — that's the link that makes `aws sso login --profile <name>` work. |
| `aws.region` | `us-east-1` | Bedrock runtime region → Claude Code `AWS_REGION`, the profile's `region`, and Cowork's `inferenceBedrockRegion` (unless overridden). |
| `aws.write_aws_config` | `true` | Whether to generate/merge the `~/.aws/config` profile. Set `false` if another tool manages that file — but then Claude Code's `AWS_PROFILE` must already exist, or the consistency check fails. |
| `aws.config_path` | `null` | Override the `~/.aws/config` location (else `$AWS_CONFIG_FILE` or the default). |

### `aws.sso` — IAM Identity Center details

These are **not secrets** (they're discovery metadata, not credentials).

| Key | Maps to | Meaning |
|-----|---------|---------|
| `sso.enabled` | — | Reserved toggle for the SSO profile (kept for forward-compat). |
| `sso.start_url` | profile `sso_start_url`, Cowork `inferenceBedrockSsoStartUrl` | Your AWS access portal URL, e.g. `https://my-org.awsapps.com/start`. |
| `sso.sso_region` | profile `sso_region`, Cowork `inferenceBedrockSsoRegion` | The **home region** of your IAM Identity Center instance (may differ from `aws.region`). |
| `sso.account_id` | profile `sso_account_id`, Cowork `inferenceBedrockSsoAccountId` | 12-digit AWS account ID where Bedrock is enabled. |
| `sso.role_name` | profile `sso_role_name`, Cowork `inferenceBedrockSsoRoleName` | The IAM Identity Center **permission-set** name to assume. |
| `sso.auto_refresh` | Claude Code `awsAuthRefresh` | `true` emits `awsAuthRefresh: "aws sso login --profile <name>"` so Claude Code re-logs in when creds expire. Set `false` behind corporate VPN/TLS proxies (which can cause an SSO loop) and sign in manually. |

### `bedrock` — Claude Code Bedrock behavior

| Key | Default | Meaning |
|-----|---------|---------|
| `bedrock.enabled` | `true` | Emits `CLAUDE_CODE_USE_BEDROCK=1` in `settings.json` `env`. |
| `bedrock.base_url` | `null` | Optional `ANTHROPIC_BEDROCK_BASE_URL` for a custom endpoint/gateway. |
| `bedrock.service_tier` | `null` | `default` \| `flex` \| `priority` → `ANTHROPIC_BEDROCK_SERVICE_TIER` (latency/cost trade-off). |
| `bedrock.prompt_caching` | `default` | `default` (5-min) \| `disabled` (`DISABLE_PROMPT_CACHING=1`) \| `one_hour` (`ENABLE_PROMPT_CACHING_1H=1`, billed higher). |
| `bedrock.guardrail.enabled` | `false` | When true, emits `ANTHROPIC_CUSTOM_HEADERS` with the Guardrail identifier+version. Requires `identifier` and `version`. |
| `bedrock.guardrail.identifier` / `.version` | `null` | Bedrock Guardrail ID and published version. |

### `models` — model pinning

| Key | Default | Meaning |
|-----|---------|---------|
| `models.opus` | `us.anthropic.claude-opus-4-8` | Opus inference-profile ID → `ANTHROPIC_DEFAULT_OPUS_MODEL`. |
| `models.sonnet` | `us.anthropic.claude-sonnet-4-6` | Sonnet ID → `ANTHROPIC_DEFAULT_SONNET_MODEL`. (Pinned *ahead* of Claude Code's built-in Bedrock default of Sonnet 4.5 — intentional.) |
| `models.haiku` | `us.anthropic.claude-haiku-4-5-20251001-v1:0` | Haiku ID → `ANTHROPIC_DEFAULT_HAIKU_MODEL`. |
| `models.default` | `sonnet` | Which family Claude Code's top-level `model` uses. |
| `models.pin_default` | `true` | `true` → `model` is the **concrete ID** of `default` (recommended for teams; bare aliases on Bedrock can lag/be unavailable). `false` → `model` is the bare alias (`"sonnet"`). |
| `models.overrides` | `{}` | Optional `modelOverrides` map (model version → inference-profile ARN). |
| (all three IDs) | | Also become Cowork's `inferenceModels` list (single source of truth). For GovCloud use the `us-gov.` prefix. |

### `claude_code` — settings.json placement & extras

| Key | Default | Meaning |
|-----|---------|---------|
| `claude_code.enabled` | `true` | Whether to generate `settings.json` at all. |
| `claude_code.scope` | `user` | `user` → `~/.claude/settings.json`; `project` → `<dir>/.claude/settings.json`; `local` → `<dir>/.claude/settings.local.json`. |
| `claude_code.project_dir` | `null` | Required when scope is `project` or `local`. |
| `claude_code.permissions.allow` / `.deny` | `[]` | Pass-through Claude Code permission rules. Empty lists are omitted from output. |
| `claude_code.extra_env` | `{}` | Extra `env` vars merged into `settings.json` (applied last, so they can override). |
| `claude_code.merge_existing` | `true` | Deep-merge into an existing `settings.json`/`~/.aws/config` instead of replacing. |

### `cowork` — Claude Desktop enterprise managed config

Generates the `com.anthropic.claudefordesktop` managed config that powers
Cowork / Claude-for-Desktop **"Sign in with AWS"** (IAM Identity Center). Key names
and formats are confirmed against a real app **Export** and the `Claude.admx` /
profile-manifest (`.plist`) — not placeholders. SSO fields inherit the `aws.sso.*`
values; set them only if the app targets a different portal/account than the CLI.

| Key | Maps to | Meaning |
|-----|---------|---------|
| `cowork.enabled` | — | Whether to generate the managed config. |
| `cowork.inference_provider` | `inferenceProvider` | `bedrock` for this project (the manifest also allows `gateway`/`anthropic`/`vertex`/`foundry`). |
| `cowork.credential_kind` | `inferenceCredentialKind` | One of `static` \| `helper-script` \| `interactive` \| `vendor-profile`. Default **`interactive`** = in-app AWS sign-in. Always emitted so the source is chosen deterministically. |
| `cowork.sso_start_url` / `sso_region` / `sso_account_id` / `sso_role_name` | the four `inferenceBedrockSso*` keys | Override the inherited `aws.sso.*` values. **All four must resolve** or the app ignores the config (the consistency check enforces this). |
| `cowork.bedrock_region` | `inferenceBedrockRegion` | Defaults to `aws.region`. |
| `cowork.service_tier` | `inferenceBedrockServiceTier` | `flex` \| `priority` \| `null`. |
| `cowork.models` | `inferenceModels` | List of `{name, label}`; `label` → `labelOverride`. Defaults to the three `models.*` pins (name only). |
| `cowork.banner.*` | `banner` | Optional org banner (`enabled`, `text`, `text_color`→`textColor`, `background_color`→`backgroundColor`, `link_url`→`linkUrl`). `text` required when enabled. |
| `cowork.export.formats` | — | Which artifacts to emit: `json` (authoritative), `mobileconfig` (macOS), `reg` (Windows). |
| `cowork.export.mobileconfig.payload_identifier` / `.organization` / `.scope` | profile fields | `payload_identifier` defaults to `com.anthropic.claudefordesktop`; `scope` is `User` \| `System`. |
| `cowork.export.reg.hive` | — | `HKCU` (default) \| `HKLM`. The key path is `SOFTWARE\Policies\Claude`. |
| `cowork.merge_existing` | `true` | Deep-merge into an existing managed-config JSON. |

**Output formats (matching the real Export):**
- **JSON** (`cowork-bedrock.json`) — native types: `inferenceModels` is an array of
  objects, `banner` is a nested object.
- **`.mobileconfig`** — a Configuration profile; complex values (`inferenceModels`,
  `banner`) are **JSON-string-encoded** inside `<string>` elements; `PayloadType`
  `com.anthropic.claudefordesktop`, `PayloadScope` `User`/`System`.
- **`.reg`** — `[HKEY_*\SOFTWARE\Policies\Claude]`, every value a quoted `REG_SZ`
  string (complex values JSON-string-encoded), written UTF-16LE with BOM.

> **Why Cowork keys look different from Claude Code:** Claude Code reads
> `env`/`awsAuthRefresh`; the desktop managed config reads `inference*`-prefixed keys.
> The same logical inputs (SSO URL, region, account, role, models) map to different
> key names per target — `mapping/resolve.py` does this fan-out once so the targets
> can't drift.

### `output` — where artifacts go

| Key | Default | Meaning |
|-----|---------|---------|
| `output.mode` | `stage` | `stage` writes everything under `output.dir` (CI-safe, what gets uploaded); `install` writes to real `~/.aws/config` / `~/.claude/…` paths. |
| `output.dir` | `./generated` | Staging directory (stage mode). |
| `output.backup` | `true` | In `install` mode, back up existing files to `<file>.bak.<timestamp>` before overwriting. |

---

## GitHub Actions

- **`.github/workflows/generate.yml`** runs the script and uploads the generated
  settings as an artifact. Generation is **offline** — no AWS secrets. Interactive
  IAM Identity Center sign-in can't complete on a headless runner, so the workflow
  only *generates and publishes*; consumers download the artifact and sign in locally.
- **`.github/workflows/ci.yml`** runs lint + tests (Linux-only, small Python matrix,
  free-tier-conscious).

---

## Notes on the Claude Desktop managed config

- The four `inferenceBedrockSso*` keys must all be present or the app ignores the
  config — enforced by the consistency check.
- `inferenceCredentialKind` defaults to `interactive` (in-app AWS sign-in) and is
  always emitted so the credential source is chosen deterministically.
- Key names, the `PayloadType` (`com.anthropic.claudefordesktop`), the registry path
  (`SOFTWARE\Policies\Claude`), and the JSON-string encoding of complex values in the
  `.mobileconfig`/`.reg` are all confirmed against a real app **Export** and the
  `Claude.admx` policy file — they are not placeholders.
- The JSON blob is the canonical source of truth; the `.mobileconfig` and `.reg` are
  exact re-serializations of it for MDM (macOS configuration profile / Windows Group
  Policy). You can also produce these from the app's own "Configure third-party
  inference" → **Export**.
