"""Generate the Claude Desktop enterprise managed-config for Bedrock + IAM Identity
Center (the ``com.anthropic.claudefordesktop`` domain).

This is the config that powers Cowork / Claude-for-Desktop "Sign in with AWS". Pure:
returns an in-memory dict — the authoritative JSON deliverable. The optional
``.mobileconfig`` / ``.reg`` wrappers are produced from this dict by the exporters
(which JSON-string-encode the complex values, per the real exports).

Key names, the ``inferenceProvider``/``inferenceCredentialKind`` values, the
``inferenceModels`` object shape and the ``banner`` shape are all confirmed against a
real app Export and the ``com.anthropic.claudefordesktop`` profile manifest / ADMX.
"""

from __future__ import annotations

from typing import Any

from ..mapping.resolve import ResolvedInputs


def _models(resolved_models: list[dict[str, str | None]]) -> list[dict[str, str]]:
    out: list[dict[str, str]] = []
    for m in resolved_models:
        entry: dict[str, str] = {"name": str(m["name"])}
        if m.get("label"):
            entry["labelOverride"] = str(m["label"])
        out.append(entry)
    return out


def _banner(banner: dict[str, Any]) -> dict[str, Any]:
    # Match the key order/names from the real export.
    out: dict[str, Any] = {}
    if banner.get("background_color"):
        out["backgroundColor"] = banner["background_color"]
    if banner.get("text_color"):
        out["textColor"] = banner["text_color"]
    out["enabled"] = bool(banner.get("enabled"))
    out["text"] = banner.get("text")
    if banner.get("link_url"):
        out["linkUrl"] = banner["link_url"]
    return out


def build_cowork(inputs: ResolvedInputs) -> dict[str, Any]:
    """Return the Claude Desktop managed-settings content as a dict.

    ``inferenceCredentialKind`` is always emitted so the credential source is chosen
    deterministically (``interactive`` = in-app AWS sign-in).
    """
    cw = inputs.cowork
    settings: dict[str, Any] = {
        "inferenceProvider": cw.inference_provider,
        "inferenceCredentialKind": cw.credential_kind,
        "inferenceBedrockRegion": cw.bedrock_region,
        "inferenceBedrockSsoStartUrl": cw.sso_start_url,
        "inferenceBedrockSsoRegion": cw.sso_region,
        "inferenceBedrockSsoAccountId": cw.sso_account_id,
        "inferenceBedrockSsoRoleName": cw.sso_role_name,
    }
    if cw.service_tier:
        settings["inferenceBedrockServiceTier"] = cw.service_tier
    settings["inferenceModels"] = _models(cw.models)
    if cw.banner:
        settings["banner"] = _banner(cw.banner)
    return settings
