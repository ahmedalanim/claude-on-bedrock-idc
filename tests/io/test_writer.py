from __future__ import annotations

import json

from claude_bedrock_idc.io import writer


def test_write_json_atomic_and_trailing_newline(tmp_path):
    path = tmp_path / "settings.json"
    writer.write_json(path, {"a": 1}, merge_existing=False, backup=False)
    text = path.read_text(encoding="utf-8")
    assert text.endswith("\n")
    assert json.loads(text) == {"a": 1}
    # 2-space indent.
    assert '  "a": 1' in text


def test_write_json_merges_existing(tmp_path):
    path = tmp_path / "settings.json"
    path.write_text(json.dumps({"env": {"KEEP": "1"}, "old": True}), encoding="utf-8")
    writer.write_json(path, {"env": {"NEW": "2"}}, merge_existing=True, backup=False)
    data = json.loads(path.read_text(encoding="utf-8"))
    assert data["env"] == {"KEEP": "1", "NEW": "2"}
    assert data["old"] is True


def test_write_json_overwrite_when_not_merging(tmp_path):
    path = tmp_path / "settings.json"
    path.write_text(json.dumps({"old": True}), encoding="utf-8")
    writer.write_json(path, {"new": 1}, merge_existing=False, backup=False)
    assert json.loads(path.read_text(encoding="utf-8")) == {"new": 1}


def test_backup_created_on_overwrite(tmp_path):
    path = tmp_path / "settings.json"
    path.write_text("{}", encoding="utf-8")
    writer.write_json(path, {"x": 1}, merge_existing=False, backup=True)
    backups = list(tmp_path.glob("settings.json.bak.*"))
    assert len(backups) == 1


def test_write_ini_section_preserves_siblings(tmp_path):
    path = tmp_path / "config"
    path.write_text("[profile other]\nregion = eu-west-1\n", encoding="utf-8")
    writer.write_ini_section(
        path, "profile p", {"region": "us-east-1"}, merge_existing=True, backup=False
    )
    text = path.read_text(encoding="utf-8")
    assert "[profile other]" in text
    assert "[profile p]" in text


def test_write_text_utf16(tmp_path):
    path = tmp_path / "x.reg"
    writer.write_text(path, "hello", encoding="utf-16-le", backup=False)
    assert path.read_bytes().decode("utf-16-le") == "hello"


def test_write_bytes(tmp_path):
    path = tmp_path / "x.mobileconfig"
    writer.write_bytes(path, b"<plist/>", backup=False)
    assert path.read_bytes() == b"<plist/>"
