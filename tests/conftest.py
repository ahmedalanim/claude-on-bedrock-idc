"""Shared fixtures + isolation harness.

Every test runs with HOME pointed at a temp dir and AWS/Bedrock env vars cleared,
so neither the dev shell nor a real ~/.aws can leak into generated output.
"""

from __future__ import annotations

import pytest

from claude_bedrock_idc.config.defaults import example_config_path
from claude_bedrock_idc.config.loader import load_config
from claude_bedrock_idc.config.schema import Config
from claude_bedrock_idc.mapping.resolve import ResolvedInputs, resolve

_LEAKY_ENV = (
    "HOME",
    "AWS_PROFILE",
    "AWS_REGION",
    "AWS_DEFAULT_REGION",
    "AWS_CONFIG_FILE",
    "AWS_SHARED_CREDENTIALS_FILE",
    "CLAUDE_CODE_USE_BEDROCK",
)


@pytest.fixture(autouse=True)
def _isolate_env(tmp_path, monkeypatch):
    for var in _LEAKY_ENV:
        monkeypatch.delenv(var, raising=False)
    monkeypatch.setenv("HOME", str(tmp_path))
    yield


@pytest.fixture
def sample_config() -> Config:
    return load_config(example_config_path())


@pytest.fixture
def resolved(sample_config: Config) -> ResolvedInputs:
    return resolve(sample_config)
