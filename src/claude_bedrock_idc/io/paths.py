"""Resolve target output paths from the config and output mode. Pure: input -> Path.

In ``stage`` mode every artifact is written under ``output.dir`` with a flat,
predictable layout (what CI uploads as an artifact). In ``install`` mode artifacts
go to their real home/app locations.
"""

from __future__ import annotations

from pathlib import Path

from ..config.schema import Config


def _home() -> Path:
    return Path.home()


def aws_config_path(config: Config) -> Path:
    """Real ~/.aws/config path (respects aws.config_path override)."""
    if config.aws.config_path:
        return Path(config.aws.config_path).expanduser()
    return _home() / ".aws" / "config"


def claude_settings_path(config: Config) -> Path:
    """Real Claude Code settings.json path for the configured scope."""
    scope = config.claude_code.scope
    if scope == "user":
        return _home() / ".claude" / "settings.json"
    project = Path(config.claude_code.project_dir).expanduser()  # validated non-null
    filename = "settings.local.json" if scope == "local" else "settings.json"
    return project / ".claude" / filename


def staged_paths(config: Config, out_dir: Path) -> dict[str, Path]:
    """Flat staging layout under ``out_dir`` for all artifacts."""
    return {
        "aws_config": out_dir / "aws" / "config",
        "claude_code": out_dir / "claude" / "settings.json",
        "cowork_json": out_dir / "cowork" / "cowork-bedrock.json",
        "cowork_mobileconfig": out_dir / "cowork" / "cowork-bedrock.mobileconfig",
        "cowork_reg": out_dir / "cowork" / "cowork-bedrock.reg",
    }


def installed_paths(config: Config) -> dict[str, Path]:
    """Real install locations. Cowork artifacts have no canonical install path,
    so they are placed next to the config dir under ~/.claude for the operator to
    hand to MDM."""
    cowork_dir = _home() / ".claude" / "cowork"
    return {
        "aws_config": aws_config_path(config),
        "claude_code": claude_settings_path(config),
        "cowork_json": cowork_dir / "cowork-bedrock.json",
        "cowork_mobileconfig": cowork_dir / "cowork-bedrock.mobileconfig",
        "cowork_reg": cowork_dir / "cowork-bedrock.reg",
    }


def resolve_paths(config: Config, out_dir_override: str | None = None) -> dict[str, Path]:
    """Return the artifact->Path map for the active output mode."""
    if config.output.mode == "stage":
        out_dir = Path(out_dir_override or config.output.dir).expanduser()
        return staged_paths(config, out_dir)
    return installed_paths(config)
