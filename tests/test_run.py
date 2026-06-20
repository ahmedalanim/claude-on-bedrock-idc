from __future__ import annotations

import run as run_module
from claude_bedrock_idc.config.defaults import example_config_path


def test_run_main_stage(tmp_path, capsys):
    out = tmp_path / "gen"
    rc = run_module.main([str(example_config_path()), "--mode", "stage", "--out-dir", str(out)])
    assert rc == 0
    captured = capsys.readouterr()
    assert "Generated" in captured.out
    assert (out / "claude" / "settings.json").exists()


def test_run_main_check_only(tmp_path, capsys):
    rc = run_module.main([str(example_config_path()), "--check-only"])
    assert rc == 0
    assert "Consistency check passed" in capsys.readouterr().out


def test_run_main_missing_config(capsys):
    rc = run_module.main(["does-not-exist.yaml"])
    assert rc == 1
    assert "error:" in capsys.readouterr().err


def test_run_main_cowork_format_override(tmp_path):
    out = tmp_path / "gen"
    rc = run_module.main(
        [
            str(example_config_path()),
            "--mode",
            "stage",
            "--out-dir",
            str(out),
            "--cowork-format",
            "json",
        ]
    )
    assert rc == 0
    assert (out / "cowork" / "cowork-bedrock.json").exists()
    assert not (out / "cowork" / "cowork-bedrock.reg").exists()
