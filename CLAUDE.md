# Claude Code with Amazon Bedrock and IAM Identity Center

## Project Overview

YAML-driven settings generator that produces Claude Code, AWS CLI, and Cowork (Claude for Desktop) configuration for Amazon Bedrock with IAM Identity Center authentication. You define one `config.yaml` and `run.py` generates all the config files needed to connect Claude tooling to Bedrock via SSO.

## Quick Start

```bash
uv venv && uv pip install -e ".[dev,test]"
cp config.example.yaml config.yaml   # edit the EDIT ME fields
python run.py                        # generates into ./generated/
python run.py --check-only           # validate without writing
```

## Project Structure

```
├── config.example.yaml          # reference config with all options documented
├── config.yaml                  # your local config (gitignored)
├── run.py                       # CLI entry point
├── src/claude_bedrock_idc/
│   ├── config/                  # YAML loading + Pydantic schema
│   ├── mapping/                 # resolve config -> generator inputs
│   ├── generators/              # build output dicts (aws_profile, claude_code, cowork)
│   ├── exporters/               # format converters (mobileconfig, reg)
│   ├── validate/                # cross-target consistency checks
│   ├── io/                      # file writer, path resolution, merge logic
│   └── pipeline.py              # orchestration: load → resolve → generate → validate → write
├── tests/
│   ├── golden/                  # snapshot files for golden-file tests
│   └── fixtures/                # test config fixtures
└── generated/                   # default stage-mode output directory
```

## Development

- **Python**: >=3.10 (CI tests 3.10 + 3.12)
- **Package manager**: uv exclusively
- **Linter**: ruff (`ruff check .` and `ruff format --check .`)
- **Tests**: `uv run pytest` (or `uv run pytest --cov=src/claude_bedrock_idc`)
- **Dependencies**: pydantic >=2, pyyaml >=6 (no boto3/anthropic — this is a config generator, not a runtime client)

## How It Works

1. `config.yaml` is loaded and validated against a Pydantic schema (`config/schema.py`)
2. The resolver (`mapping/resolve.py`) derives `ResolvedInputs` — flattened, cross-referenced values
3. Generators produce in-memory dicts for each enabled target (AWS profile, Claude Code settings, Cowork managed config)
4. Exporters convert Cowork JSON to `.mobileconfig` (macOS) or `.reg` (Windows) when requested
5. Consistency validation checks cross-target agreement (e.g., region matches between AWS and Cowork)
6. Writer stages files to `./generated/` (default) or installs to real paths

## CLI Flags

```
python run.py [config.yaml]          # path to config (default: config.yaml)
  --check-only                       # validate only, write nothing
  --out-dir DIR                      # override output directory
  --mode {stage,install}             # override output.mode
  --cowork-format json,mobileconfig  # override cowork export formats
```

## Notes for Claude Code

- All config fields are documented in `config.example.yaml` — refer to it when adding or changing options
- The pipeline is pure until the write step; generators and validators have no disk I/O
- Golden-file tests in `tests/test_golden.py` compare generated output against `tests/golden/` snapshots — update snapshots when generator output intentionally changes
- Cowork keys map 1:1 to `com.anthropic.claudefordesktop` ADMX/plist policy names; comments in `config.example.yaml` show the exact policy key for each field
