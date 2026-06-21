#!/usr/bin/env python3
"""Entry point: generate Claude Code + Cowork-on-3P settings from a YAML config.

This is a thin script (not a CLI tool): it parses a config path plus a few
override flags and delegates to the pipeline. Intended to be invoked by a GitHub
Actions workflow as `python run.py config.yaml`.
"""

from __future__ import annotations

import argparse
import sys

from claude_bedrock_idc.config.loader import ConfigError
from claude_bedrock_idc.pipeline import run


def _parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="run.py",
        description="Generate Bedrock + IAM Identity Center settings from a YAML config.",
    )
    parser.add_argument(
        "config",
        nargs="?",
        default="config.yaml",
        help="path to config YAML (default: config.yaml)",
    )
    parser.add_argument("--out-dir", default=None, help="override output.dir (stage mode)")
    parser.add_argument(
        "--mode", choices=["stage", "install"], default=None, help="override output.mode"
    )
    parser.add_argument("--check-only", action="store_true", help="validate only; write nothing")
    parser.add_argument(
        "--cowork-format",
        default=None,
        help="comma-separated subset of json,mobileconfig,reg (overrides config)",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(sys.argv[1:] if argv is None else argv)

    cowork_formats = args.cowork_format.split(",") if args.cowork_format else None

    try:
        result = run(
            args.config,
            check_only=args.check_only,
            out_dir_override=args.out_dir,
            mode_override=args.mode,
            cowork_formats_override=cowork_formats,
        )
    except ConfigError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    check = result.check
    if not check.ok:
        print("Consistency check FAILED:", file=sys.stderr)
        for err in check.errors:
            print(f"  - {err}", file=sys.stderr)
        return 1

    if args.check_only:
        print("Consistency check passed (no files written).")
    else:
        print(f"Generated {len(result.written)} file(s):")
        for path in result.written:
            print(f"  - {path}")

    if check.next_steps:
        print("\nNext steps (manual, not performed by this script):")
        for step in check.next_steps:
            print(f"  * {step}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
