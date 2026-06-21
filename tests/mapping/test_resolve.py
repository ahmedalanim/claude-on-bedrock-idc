from __future__ import annotations

from claude_bedrock_idc.mapping.resolve import resolve


def test_cowork_inherits_sso_from_aws(sample_config):
    r = resolve(sample_config)
    assert r.cowork.sso_start_url == sample_config.aws.sso.start_url
    assert r.cowork.sso_region == sample_config.aws.sso.sso_region
    assert r.cowork.sso_account_id == sample_config.aws.sso.account_id
    assert r.cowork.sso_role_name == sample_config.aws.sso.role_name
    assert r.cowork.bedrock_region == sample_config.aws.region


def test_cowork_overrides_win(sample_config):
    sample_config.cowork.sso_start_url = "https://override.awsapps.com/start"
    sample_config.cowork.bedrock_region = "us-west-2"
    r = resolve(sample_config)
    assert r.cowork.sso_start_url == "https://override.awsapps.com/start"
    assert r.cowork.bedrock_region == "us-west-2"


def test_cowork_models_default_to_all_pins(sample_config):
    r = resolve(sample_config)
    assert [m["name"] for m in r.cowork.models] == [
        sample_config.models.opus,
        sample_config.models.sonnet,
        sample_config.models.haiku,
    ]


def test_cowork_models_explicit(sample_config):
    from claude_bedrock_idc.config.schema import CoworkModel

    sample_config.cowork.models = [CoworkModel(name="us.anthropic.claude-sonnet-4-6", label="S")]
    r = resolve(sample_config)
    assert r.cowork.models == [{"name": "us.anthropic.claude-sonnet-4-6", "label": "S"}]


def test_cowork_provider_and_credential_kind(sample_config):
    r = resolve(sample_config)
    assert r.cowork.inference_provider == "bedrock"
    assert r.cowork.credential_kind == "interactive"


def test_cowork_optional_groups_pass_through(sample_config):
    # The new policy groups are pure passthrough (no inheritance/derivation).
    sample_config.cowork.model_discovery_enabled = True
    sample_config.cowork.max_tokens_per_window = 50000
    sample_config.cowork.desktop.cowork_tab_enabled = False
    sample_config.cowork.telemetry.otlp_protocol = "grpc"
    sample_config.cowork.bedrock.profile = "prof"
    sample_config.cowork.managed_mcp_servers = {"servers": []}
    r = resolve(sample_config)
    assert r.cowork.model_discovery_enabled is True
    assert r.cowork.max_tokens_per_window == 50000
    assert r.cowork.desktop.cowork_tab_enabled is False
    assert r.cowork.telemetry.otlp_protocol == "grpc"
    assert r.cowork.bedrock_extra.profile == "prof"
    assert r.cowork.managed_mcp_servers == {"servers": []}


def test_pin_default_true_resolves_concrete_id(sample_config):
    sample_config.models.pin_default = True
    sample_config.models.default = "sonnet"
    r = resolve(sample_config)
    assert r.code_model == sample_config.models.sonnet


def test_pin_default_false_keeps_alias(sample_config):
    sample_config.models.pin_default = False
    sample_config.models.default = "opus"
    r = resolve(sample_config)
    assert r.code_model == "opus"
