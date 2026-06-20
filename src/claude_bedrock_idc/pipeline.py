"""Orchestration: load -> resolve -> generate -> validate -> write/stage.

This module composes the pure modules and the single I/O seam. It holds no
business logic of its own beyond wiring and per-target enable gating.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from .config.loader import load_config
from .config.schema import Config
from .exporters import mobileconfig as mobileconfig_exporter
from .exporters import reg as reg_exporter
from .generators import aws_profile, claude_code, cowork
from .io import paths as paths_mod
from .io import writer
from .mapping.resolve import ResolvedInputs, resolve
from .validate import consistency
from .validate.consistency import CheckResult


@dataclass
class GeneratedArtifacts:
    """In-memory artifacts produced by the generators (before any write)."""

    aws_profile_section: tuple[str, dict[str, str]] | None = None
    code_settings: dict | None = None
    cowork_settings: dict | None = None


@dataclass
class RunResult:
    inputs: ResolvedInputs
    artifacts: GeneratedArtifacts
    check: CheckResult
    written: list[Path] = field(default_factory=list)


def generate(config: Config) -> tuple[ResolvedInputs, GeneratedArtifacts]:
    """Run the resolver and all enabled generators. Pure (no disk)."""
    inputs = resolve(config)
    artifacts = GeneratedArtifacts()

    if config.aws.write_aws_config:
        artifacts.aws_profile_section = aws_profile.build_profile(inputs)
    if config.claude_code.enabled:
        artifacts.code_settings = claude_code.build_settings(inputs)
    if config.cowork.enabled:
        artifacts.cowork_settings = cowork.build_cowork(inputs)

    return inputs, artifacts


def validate(inputs: ResolvedInputs, artifacts: GeneratedArtifacts) -> CheckResult:
    return consistency.check(
        inputs,
        aws_profile_section=artifacts.aws_profile_section,
        code_settings=artifacts.code_settings,
        cowork_settings=artifacts.cowork_settings,
    )


def _write(
    config: Config, artifacts: GeneratedArtifacts, out_dir_override: str | None
) -> list[Path]:
    targets = paths_mod.resolve_paths(config, out_dir_override)
    backup = config.output.backup and config.output.mode == "install"
    written: list[Path] = []

    if artifacts.aws_profile_section is not None:
        section, values = artifacts.aws_profile_section
        path = targets["aws_config"]
        writer.write_ini_section(
            path, section, values, merge_existing=config.claude_code.merge_existing, backup=backup
        )
        written.append(path)

    if artifacts.code_settings is not None:
        path = targets["claude_code"]
        writer.write_json(
            path,
            artifacts.code_settings,
            merge_existing=config.claude_code.merge_existing,
            backup=backup,
        )
        written.append(path)

    if artifacts.cowork_settings is not None:
        formats = config.cowork.export.formats
        if "json" in formats:
            path = targets["cowork_json"]
            writer.write_json(
                path,
                artifacts.cowork_settings,
                merge_existing=config.cowork.merge_existing,
                backup=backup,
            )
            written.append(path)
        if "mobileconfig" in formats:
            data = mobileconfig_exporter.build_mobileconfig(
                artifacts.cowork_settings,
                payload_identifier=config.cowork.export.mobileconfig.payload_identifier,
                organization=config.cowork.export.mobileconfig.organization,
                scope=config.cowork.export.mobileconfig.scope,
            )
            path = targets["cowork_mobileconfig"]
            writer.write_bytes(path, data, backup=backup)
            written.append(path)
        if "reg" in formats:
            text = reg_exporter.build_reg(
                artifacts.cowork_settings, hive=config.cowork.export.reg.hive
            )
            path = targets["cowork_reg"]
            # RegEdit requires UTF-16LE with a BOM.
            writer.write_text(path, "﻿" + text, encoding="utf-16-le", backup=backup)
            written.append(path)

    return written


def run(
    config_path: str | Path,
    *,
    check_only: bool = False,
    out_dir_override: str | None = None,
    mode_override: str | None = None,
    cowork_formats_override: list[str] | None = None,
) -> RunResult:
    """Full pipeline. Applies CLI flag overrides, validates, then writes unless check_only."""
    config = load_config(config_path)

    if mode_override:
        config.output.mode = mode_override  # type: ignore[assignment]
    if cowork_formats_override:
        config.cowork.export.formats = cowork_formats_override  # type: ignore[assignment]

    inputs, artifacts = generate(config)
    result = validate(inputs, artifacts)

    written: list[Path] = []
    if not check_only and result.ok:
        written = _write(config, artifacts, out_dir_override)

    return RunResult(inputs=inputs, artifacts=artifacts, check=result, written=written)
