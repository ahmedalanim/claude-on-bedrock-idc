from __future__ import annotations

from claude_bedrock_idc.io.merge import deep_merge_dict, merge_ini_section


def test_deep_merge_nested_env_preserves_siblings():
    base = {"env": {"EXISTING": "1", "AWS_PROFILE": "old"}, "model": "x"}
    incoming = {"env": {"AWS_PROFILE": "new", "AWS_REGION": "r"}, "awsAuthRefresh": "cmd"}
    result = deep_merge_dict(base, incoming)
    assert result["env"] == {"EXISTING": "1", "AWS_PROFILE": "new", "AWS_REGION": "r"}
    assert result["model"] == "x"
    assert result["awsAuthRefresh"] == "cmd"


def test_deep_merge_does_not_mutate_base():
    base = {"env": {"A": "1"}}
    deep_merge_dict(base, {"env": {"B": "2"}})
    assert base == {"env": {"A": "1"}}


def test_ini_section_added_to_empty():
    text = merge_ini_section(None, "profile p", {"region": "us-east-1", "output": "json"})
    assert "[profile p]" in text
    assert "region = us-east-1" in text


def test_ini_preserves_other_sections():
    existing = "[profile other]\nregion = eu-west-1\n\n"
    text = merge_ini_section(existing, "profile p", {"region": "us-east-1"})
    assert "[profile other]" in text
    assert "region = eu-west-1" in text
    assert "[profile p]" in text


def test_ini_replaces_target_section():
    existing = "[profile p]\nregion = old\nstale = yes\n"
    text = merge_ini_section(existing, "profile p", {"region": "new"})
    assert "region = new" in text
    assert "stale" not in text


def test_ini_idempotent():
    once = merge_ini_section(None, "profile p", {"region": "r"})
    twice = merge_ini_section(once, "profile p", {"region": "r"})
    assert once == twice
