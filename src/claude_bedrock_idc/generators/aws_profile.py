"""Generate the ~/.aws/config ``[profile <name>]`` block for IAM Identity Center.

Pure: returns the profile section name and its key/value mapping. Writing/merging
into the real file is the writer's job.
"""

from __future__ import annotations

from ..mapping.resolve import ResolvedInputs

PROFILE_KEYS_ORDER = (
    "sso_start_url",
    "sso_region",
    "sso_account_id",
    "sso_role_name",
    "region",
    "output",
)


def build_profile(inputs: ResolvedInputs) -> tuple[str, dict[str, str]]:
    """Return ``("profile <name>", {key: value, ...})`` for ~/.aws/config.

    The section name uses the ``profile <name>`` form expected by the AWS CLI in
    ``~/.aws/config`` (the literal header becomes ``[profile <name>]``).
    """
    aws = inputs.aws
    section = f"profile {aws.profile}"
    values = {
        "sso_start_url": aws.sso_start_url,
        "sso_region": aws.sso_region,
        "sso_account_id": aws.sso_account_id,
        "sso_role_name": aws.sso_role_name,
        "region": aws.region,
        "output": "json",
    }
    # Deterministic key order.
    ordered = {k: values[k] for k in PROFILE_KEYS_ORDER}
    return section, ordered
