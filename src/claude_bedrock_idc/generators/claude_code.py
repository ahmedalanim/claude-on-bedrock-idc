"""Generate the Claude Code ``settings.json`` dict for Bedrock + IAM Identity Center.

Pure: returns an in-memory dict. Key placement follows the Claude Code docs —
``awsAuthRefresh`` / ``model`` / ``modelOverrides`` / ``permissions`` are top-level,
while ``CLAUDE_CODE_USE_BEDROCK`` / ``AWS_*`` / model pins live in the ``env`` block.
"""

from __future__ import annotations

from typing import Any

from ..mapping.resolve import ResolvedInputs

SCHEMA_URL = "https://json.schemastore.org/claude-code-settings.json"


def build_settings(inputs: ResolvedInputs) -> dict[str, Any]:
    """Return the Claude Code ``settings.json`` content as a dict."""
    config = inputs.config
    aws = inputs.aws
    bedrock = config.bedrock

    env: dict[str, str] = {}
    if bedrock.enabled:
        env["CLAUDE_CODE_USE_BEDROCK"] = "1"
    env["AWS_PROFILE"] = aws.profile
    env["AWS_REGION"] = aws.region

    # Model pins (recommended for stable team deployments).
    env["ANTHROPIC_DEFAULT_OPUS_MODEL"] = inputs.model_pins["opus"]
    env["ANTHROPIC_DEFAULT_SONNET_MODEL"] = inputs.model_pins["sonnet"]
    env["ANTHROPIC_DEFAULT_HAIKU_MODEL"] = inputs.model_pins["haiku"]

    # Optional Bedrock extras — only emit when explicitly configured.
    if bedrock.base_url:
        env["ANTHROPIC_BEDROCK_BASE_URL"] = bedrock.base_url
    if bedrock.service_tier:
        env["ANTHROPIC_BEDROCK_SERVICE_TIER"] = bedrock.service_tier
    if bedrock.prompt_caching == "disabled":
        env["DISABLE_PROMPT_CACHING"] = "1"
    elif bedrock.prompt_caching == "one_hour":
        env["ENABLE_PROMPT_CACHING_1H"] = "1"
    if bedrock.guardrail.enabled:
        env["ANTHROPIC_CUSTOM_HEADERS"] = (
            f"X-Amzn-Bedrock-GuardrailIdentifier: {bedrock.guardrail.identifier}\n"
            f"X-Amzn-Bedrock-GuardrailVersion: {bedrock.guardrail.version}"
        )

    # Passthrough env (last so users can override).
    env.update(config.claude_code.extra_env)

    settings: dict[str, Any] = {"$schema": SCHEMA_URL}

    if aws.auto_refresh:
        settings["awsAuthRefresh"] = f"aws sso login --profile {aws.profile}"

    settings["model"] = inputs.code_model

    if config.models.overrides:
        settings["modelOverrides"] = dict(config.models.overrides)

    perms = config.claude_code.permissions
    perm_block: dict[str, list[str]] = {}
    if perms.allow:
        perm_block["allow"] = list(perms.allow)
    if perms.deny:
        perm_block["deny"] = list(perms.deny)
    if perm_block:
        settings["permissions"] = perm_block

    settings["env"] = env
    return settings
