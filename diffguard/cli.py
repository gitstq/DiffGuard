# -*- coding: utf-8 -*-
"""DiffGuard · 命令行入口。

用法::

    diffguard                    # 审查工作区 diff（HEAD vs 工作区）
    diffguard --staged           # 审查暂存区（提交前检查）
    diffguard --branch main      # 审查当前分支相对 main 的全部改动
    diffguard scan src/          # 整文件扫描（审计陌生代码）
    diffguard --diff fix.patch   # 审查补丁文件
"""

from __future__ import annotations

import argparse
import os
import sys
from typing import List

from . import __version__
from .engine import Config, Engine
from .gitsource import GitSourceError, collect_diff, get_changed_files
from .reports import render

EXIT_CLEAN = 0
EXIT_FINDINGS = 1
EXIT_ERROR = 2


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="diffguard",
        description="DiffGuard — 零依赖、离线优先的 Git 差异确定性代码审查引擎。",
    )
    p.add_argument("--version", action="version", version=f"diffguard {__version__}")
    src = p.add_mutually_exclusive_group()
    src.add_argument("--staged", action="store_true", help="审查暂存区改动（提交前检查）")
    src.add_argument("--branch", metavar="REF", help="审查当前分支相对 REF（merge-base）的改动")
    src.add_argument("--diff", metavar="FILE", help="审查 unified diff 补丁文件")
    p.add_argument("paths", nargs="*", help="scan 模式下要扫描的文件或目录")
    p.add_argument("--scan", action="store_true", help="整文件扫描模式（忽略 diff）")
    p.add_argument("--format", "-f", choices=["text", "json", "sarif", "markdown"],
                   default="text", help="输出格式（默认 text）")
    p.add_argument("--fail-on", metavar="SEVS", default=None,
                   help="CI 门禁阈值，如 blocker,high（默认读取配置文件）")
    p.add_argument("--config", metavar="FILE", help="配置文件路径（默认 ./.diffguard.json）")
    p.add_argument("--no-color", action="store_true", help="关闭终端彩色输出")
    p.add_argument("--output", "-o", metavar="FILE", help="结果写入文件（默认 stdout）")
    p.add_argument("--locale", choices=["cn", "en"], default=None, help="报告语言")
    p.add_argument("--list-rules", action="store_true", help="列出全部规则并退出")
    return p


def _load_config(args: argparse.Namespace) -> Config:
    config_path = args.config
    if config_path and os.path.isfile(config_path):
        config = Config.from_file(config_path)
    else:
        default = os.path.join(os.getcwd(), ".diffguard.json")
        config = Config.from_file(default) if os.path.isfile(default) else Config()
    if args.fail_on is not None:
        config.fail_on = [s.strip() for s in args.fail_on.split(",") if s.strip()]
    if args.locale:
        config.locale = args.locale
    return config


def _expand_scan_paths(paths: List[str]) -> List[str]:
    import fnmatch

    skip_dirs = {".git", "node_modules", "__pycache__", ".venv", "venv", "dist", "build"}
    ignore_ext = (".pyc", ".min.js", ".map", ".lock", ".png", ".jpg", ".gif", ".ico",
                  ".woff", ".woff2", ".ttf", ".zip", ".gz", ".pdf", ".so", ".bin")
    files: List[str] = []
    for base in paths or ["."]:
        if os.path.isfile(base):
            files.append(base)
            continue
        for root, dirs, names in os.walk(base):
            dirs[:] = [d for d in dirs if d not in skip_dirs]
            for name in names:
                if name.endswith(ignore_ext) or fnmatch.fnmatch(name, "*.min.js"):
                    continue
                files.append(os.path.join(root, name))
    return sorted(files)


def main(argv: List[str] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    config = _load_config(args)

    from .rules import RULES
    if args.list_rules:
        for r in RULES:
            print(f"{r.rule_id}\t{r.severity}\t{r.category}\t"
                  f"{r.message_cn}")
        return EXIT_CLEAN

    engine = Engine(config)

    try:
        if args.scan or (args.paths and not (args.staged or args.branch or args.diff)):
            files = _expand_scan_paths(args.paths)
            findings = engine.review_files(files)
            summary = {"files": len(files), "added_lines": _count_lines(files)}
        else:
            diffs = collect_diff(staged=args.staged, branch=args.branch,
                                 diff_file=args.diff)
            findings = engine.review(diffs)
            added = sum(len(d.added_lines) for d in diffs)
            summary = {"files": len(diffs), "added_lines": added}
    except (GitSourceError, FileNotFoundError) as exc:
        print(f"❌ {exc}", file=sys.stderr)
        return EXIT_ERROR

    text = render(findings, args.format, config=config,
                  color=(not args.no_color and args.format == "text"
                         and sys.stdout.isatty()),
                  locale=config.locale, summary=summary)

    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            f.write(text)
    else:
        sys.stdout.write(text)

    return EXIT_CLEAN if engine.gate(findings) else EXIT_FINDINGS


def _count_lines(files: List[str]) -> int:
    total = 0
    for p in files:
        try:
            with open(p, "r", encoding="utf-8", errors="replace") as f:
                total += sum(1 for _ in f)
        except OSError:
            continue
    return total


if __name__ == "__main__":
    sys.exit(main())
