"""Resolve the config into a single, flat set of inputs the generators share.

This is the one place the "single source of truth -> many vocabularies" fan-out
happens: SSO/region/model values (including Cowork's inheritance from aws.sso.*)
are computed once into a :class:`ResolvedInputs` dataclass. Every generator reads
from this, so the targets cannot drift. Pure function, no I/O.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from ..config.schema import Config


@dataclass(frozen=True)
class ResolvedAws:
    profile: str
    region: str
    sso_start_url: str
    sso_region: str
    sso_account_id: str
    sso_role_name: str
    auto_refresh: bool
    write_aws_config: bool


@dataclass(frozen=True)
class ResolvedCowork:
    inference_provider: str
    credential_kind: str
    sso_start_url: str
    sso_region: str
    sso_account_id: str
    sso_role_name: str
    bedrock_region: str
    service_tier: str | None
    # Each entry is {"name": <id>, "label": <optional display label or None>}.
    models: list[dict[str, str | None]]
    banner: dict[str, object] | None


@dataclass(frozen=True)
class ResolvedInputs:
    config: Config
    aws: ResolvedAws
    # Concrete model id the Claude Code `model` key should carry (or bare alias).
    code_model: str
    cowork: ResolvedCowork
    model_pins: dict[str, str] = field(default_factory=dict)


def resolve(config: Config) -> ResolvedInputs:
    """Compute :class:`ResolvedInputs` from a validated :class:`Config`."""
    sso = config.aws.sso

    aws = ResolvedAws(
        profile=config.aws.profile,
        region=config.aws.region,
        sso_start_url=sso.start_url,
        sso_region=sso.sso_region,
        sso_account_id=sso.account_id,
        sso_role_name=sso.role_name,
        auto_refresh=sso.auto_refresh,
        write_aws_config=config.aws.write_aws_config,
    )

    # Model pins map family -> concrete inference-profile id.
    model_pins = {
        "opus": config.models.opus,
        "sonnet": config.models.sonnet,
        "haiku": config.models.haiku,
    }
    default_family = config.models.default
    code_model = (
        config.models.resolved_id(default_family) if config.models.pin_default else default_family
    )

    # Cowork inherits SSO/region from aws.* unless explicitly overridden, and its
    # model list defaults to all configured pins (deterministic order).
    cw = config.cowork
    if cw.models:
        cowork_models: list[dict[str, str | None]] = [
            {"name": m.name, "label": m.label} for m in cw.models
        ]
    else:
        cowork_models = [
            {"name": model_pins["opus"], "label": None},
            {"name": model_pins["sonnet"], "label": None},
            {"name": model_pins["haiku"], "label": None},
        ]

    banner = None
    if cw.banner.enabled:
        banner = {
            "background_color": cw.banner.background_color,
            "text_color": cw.banner.text_color,
            "enabled": True,
            "text": cw.banner.text,
            "link_url": cw.banner.link_url,
        }

    cowork = ResolvedCowork(
        inference_provider=cw.inference_provider,
        credential_kind=cw.credential_kind,
        sso_start_url=cw.sso_start_url or sso.start_url,
        sso_region=cw.sso_region or sso.sso_region,
        sso_account_id=cw.sso_account_id or sso.account_id,
        sso_role_name=cw.sso_role_name or sso.role_name,
        bedrock_region=cw.bedrock_region or config.aws.region,
        service_tier=cw.service_tier,
        models=cowork_models,
        banner=banner,
    )

    return ResolvedInputs(
        config=config,
        aws=aws,
        code_model=code_model,
        cowork=cowork,
        model_pins=model_pins,
    )
