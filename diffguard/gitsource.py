# -*- coding: utf-8 -*-
"""DiffGuard · Git 数据源适配器。

从 ``git`` 命令获取差异（staged / branch / 工作区），也支持直接读取
unified diff 补丁文件。对「不在 Git 仓库中运行」的场景给出明确错误，
而不是抛出令人困惑的异常。
"""

from __future__ import annotations

import subprocess
from typing import List, Optional

from .diffparser import FileDiff, parse_unified_diff

__all__ = ["collect_diff", "get_changed_files"]


class GitSourceError(RuntimeError):
    """git 命令执行失败或当前目录不是 Git 仓库。"""


def _run_git(args: List[str]) -> str:
    try:
        proc = subprocess.run(
            ["git"] + args,
            capture_output=True, text=True, encoding="utf-8", errors="replace",
        )
    except FileNotFoundError as exc:  # git 未安装
        raise GitSourceError("git 可执行文件未找到，DiffGuard 需要 git 获取差异。") from exc
    if proc.returncode != 0:
        err = (proc.stderr or "").strip()
        if "not a git repository" in err.lower():
            raise GitSourceError("当前目录不是 Git 仓库，无法获取差异。")
        raise GitSourceError(f"git {' '.join(args)} 执行失败：{err}")
    return proc.stdout


def collect_diff(staged: bool = False, branch: Optional[str] = None,
                 diff_file: Optional[str] = None) -> List[FileDiff]:
    """按来源收集差异并解析为 :class:`FileDiff` 列表。

    Args:
        staged: 审查暂存区（index vs HEAD），CI 提交前检查最常用。
        branch: 与指定分支的 merge-base 比较，用于 PR 审查。
        diff_file: 直接读取 unified diff 补丁文件（无需 git 仓库）。
    """
    if diff_file:
        with open(diff_file, "r", encoding="utf-8", errors="replace") as f:
            return parse_unified_diff(f.read())
    if branch:
        merge_base = _run_git(["merge-base", "HEAD", branch]).strip()
        out = _run_git(["diff", "--no-color", merge_base])
    elif staged:
        out = _run_git(["diff", "--no-color", "--staged"])
    else:
        out = _run_git(["diff", "--no-color", "HEAD"])
    return parse_unified_diff(out)


def get_changed_files(staged: bool = False, branch: Optional[str] = None) -> List[str]:
    """获取有变更的文件路径（供 scan / 报告摘要使用）。"""
    if branch:
        merge_base = _run_git(["merge-base", "HEAD", branch]).strip()
        out = _run_git(["diff", "--name-only", merge_base])
    elif staged:
        out = _run_git(["diff", "--name-only", "--staged"])
    else:
        out = _run_git(["diff", "--name-only", "HEAD"])
    return [line for line in out.splitlines() if line.strip()]
