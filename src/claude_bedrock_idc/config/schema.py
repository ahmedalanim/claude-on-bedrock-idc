"""Pydantic models for the YAML configuration.

The schema validates the input file and supplies field-level defaults. Cross-field
defaults that depend on other sections (e.g. Cowork inheriting from aws.sso.*) are
resolved later in mapping/resolve.py, not here, so this module stays a pure
description of the document shape.
"""

from __future__ import annotations

from typing import Literal

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
