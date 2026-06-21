"""Offline cross-target consistency checks.

Runs against the *generated artifacts* (in-memory dicts/INI section), before any
write, so an inconsistent config fails the workflow without leaving half-written
files. No network, no AWS calls.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from ..mapping.resolve import ResolvedInputs

# In-scope sensitive managed-config keys (pfm_sensitive in the manifest). If any of
# these are present in the generated Cowork settings, config.yaml is secret-bearing.
_SENSITIVE_KEYS = (
    "inferenceBedrockBearerToken",
    "inferenceCustomHeaders",
    "otlpHeaders",
    "otlpResourceAttributes",
    "managedMcpServers",
)


@dataclass
class CheckResult:
    errors: list[str] = field(default_factory=list)
    next_steps: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.errors


def check(
    inputs: ResolvedInputs,
    *,
    aws_profile_section: tuple[str, dict[str, str]] | None,
    code_settings: dict | None,
    cowork_settings: dict | None,
) -> CheckResult:
    """Validate that the generated artifacts are mutually consistent.

    Each generated-or-None argument reflects whether that target was enabled.
    """
    result = CheckResult()
    config = inputs.config

    profile_name = inputs.aws.profile
    have_profile = aws_profile_section is not None

    # --- Claude Code <-> AWS profile chain -------------------------------------
    if code_settings is not None:
        env = code_settings.get("env", {})
        if env.get("CLAUDE_CODE_USE_BEDROCK") != "1" and config.bedrock.enabled:
            result.errors.append(
                "claude_code: CLAUDE_CODE_USE_BEDROCK is not '1' but bedrock.enabled is true"
            )

        aws_profile = env.get("AWS_PROFILE")
        if not aws_profile:
            result.errors.append("claude_code: env.AWS_PROFILE is missing")
        elif not have_profile:
            result.errors.append(
                f"claude_code: AWS_PROFILE='{aws_profile}' but no ~/.aws/config profile is "
                "generated (aws.write_aws_config is false). Enable it or create the "
                "profile manually."
            )
        elif aws_profile != profile_name:
            result.errors.append(
                f"claude_code: AWS_PROFILE='{aws_profile}' does not match generated "
                f"profile '{profile_name}'"
            )

        auth_refresh = code_settings.get("awsAuthRefresh")
        if auth_refresh and aws_profile and aws_profile not in auth_refresh:
            result.errors.append(
                f"claude_code: awsAuthRefresh ('{auth_refresh}') does not reference "
                f"AWS_PROFILE '{aws_profile}'"
            )

        if not have_profile:
            result.next_steps.append(
                f"Create an ~/.aws/config [profile {profile_name}] block, or set "
                "aws.write_aws_config: true."
            )

    # --- Cowork: all four SSO keys + credential kind ---------------------------
    if cowork_settings is not None:
        sso_keys = [
            "inferenceBedrockSsoStartUrl",
            "inferenceBedrockSsoRegion",
            "inferenceBedrockSsoAccountId",
            "inferenceBedrockSsoRoleName",
        ]
        missing = [k for k in sso_keys if not cowork_settings.get(k)]
        if missing:
            result.errors.append(
                "cowork: incomplete SSO config (Cowork ignores partial config). Missing: "
                + ", ".join(missing)
            )
        if not cowork_settings.get("inferenceCredentialKind"):
            result.errors.append(
                "cowork: inferenceCredentialKind must be set to force in-app AWS sign-in"
            )

        # Sensitive-data notice (non-fatal; CheckResult has no warnings channel, so it
        # rides next_steps). Default IDC sign-in needs none of these, so config.yaml
        # stays commit-safe unless an operator opts into one of them.
        present_sensitive = [k for k in _SENSITIVE_KEYS if cowork_settings.get(k)]
        if present_sensitive:
            result.next_steps.append(
                "cowork: config now carries secret(s) ("
                + ", ".join(present_sensitive)
                + "). Do not commit config.yaml; template these or inject via your "
                "MDM/secret store."
            )

    # --- SSO values shared between AWS profile and Cowork must agree -----------
    if have_profile and cowork_settings is not None:
        _, prof = aws_profile_section
        pairs = [
            ("sso_start_url", "inferenceBedrockSsoStartUrl"),
            ("sso_region", "inferenceBedrockSsoRegion"),
            ("sso_account_id", "inferenceBedrockSsoAccountId"),
            ("sso_role_name", "inferenceBedrockSsoRoleName"),
        ]
        for prof_key, cow_key in pairs:
            if prof.get(prof_key) and cowork_settings.get(cow_key):
                if prof.get(prof_key) != cowork_settings.get(cow_key):
                    result.errors.append(
                        f"sso mismatch: ~/.aws/config {prof_key}='{prof[prof_key]}' != "
                        f"Cowork {cow_key}='{cowork_settings[cow_key]}'"
                    )

    # --- Always-useful manual next steps --------------------------------------
    if inputs.aws.auto_refresh is False and code_settings is not None:
        result.next_steps.append(
            f"Run `aws sso login --profile {profile_name}` before starting Claude Code."
        )
    result.next_steps.append(
        "Ensure AWS-side prerequisites are done: Bedrock model access, IAM policy, "
        "IAM Identity Center permission set."
    )

    return result
