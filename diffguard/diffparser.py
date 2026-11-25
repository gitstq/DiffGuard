# -*- coding: utf-8 -*-
"""DiffGuard · 统一 diff 解析器。

纯标准库实现，把 ``git diff`` / ``git diff --staged`` 的输出或任意
unified diff 补丁文件解析为结构化的 :class:`FileDiff` / :class:`Hunk` /
:class:`DiffLine` 对象，供规则引擎做行级审查。

设计要点：
- 不依赖 git 可执行文件（也可直接喂补丁文本）；
- 保留新旧两侧行号，便于精确到行的审查报告；
- 容错：二进制文件、重命名、模式变更等特殊头部不会使解析器崩溃。
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import List, Optional

__all__ = ["DiffLine", "Hunk", "FileDiff", "parse_unified_diff"]

_HUNK_HEADER = re.compile(r"^@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@")
_FILE_HEADER = re.compile(r"^\+\+\+ b?/?(.*)$")
_OLD_FILE_HEADER = re.compile(r"^--- (?:a?/?(.*))$")
_BINARY_RE = re.compile(r"^Binary files .* differ")
_GIT_DIFF_START = re.compile(r"^diff --git")


@dataclass
class DiffLine:
    """差异中的单行内容。

    Attributes:
        kind: ``add``（新增）、``del``（删除）、``ctx``（上下文）。
        old_lineno: 旧文件中的行号（新增行与 no-newline 行为 None）。
        new_lineno: 新文件中的行号（删除行为 None）。
        text: 去掉前缀符号后的行内容（不含换行符）。
    """

    kind: str
    old_lineno: Optional[int]
    new_lineno: Optional[int]
    text: str

    @property
    def is_added(self) -> bool:
        return self.kind == "add"


@dataclass
class Hunk:
    """一个差异块（hunk），由 @ 头部界定。"""

    old_start: int
    new_start: int
    lines: List[DiffLine] = field(default_factory=list)

    @property
    def added_lines(self) -> List[DiffLine]:
        return [ln for ln in self.lines if ln.is_added]


@dataclass
class FileDiff:
    """单个文件的差异。"""

    old_path: str
    new_path: str
    hunks: List[Hunk] = field(default_factory=list)
    is_binary: bool = False
    is_new: bool = False
    is_deleted: bool = False
    is_rename: bool = False
    no_newline_at_eof: bool = False

    @property
    def added_lines(self) -> List[DiffLine]:
        return [ln for h in self.hunks for ln in h.added_lines]

    @property
    def path(self) -> str:
        return self.new_path or self.old_path


def _parse_hunk_header(line: str) -> Optional[tuple]:
    m = _HUNK_HEADER.match(line)
    if not m:
        return None
    old_start = int(m.group(1))
    old_count = int(m.group(2)) if m.group(2) is not None else 1
    new_start = int(m.group(3))
    new_count = int(m.group(4)) if m.group(4) is not None else 1
    return old_start, old_count, new_start, new_count


def parse_unified_diff(text: str) -> List[FileDiff]:
    """解析 unified diff 文本，返回 :class:`FileDiff` 列表。

    支持标准 ``git diff`` 输出以及常见的 ``diff -u`` 输出。
    解析器对异常行保持宽容（跳过而非抛错），确保面对真实仓库
    中的重命名、二进制、mode change 等场景都能稳定工作。
    """
    diffs: List[FileDiff] = []
    current: Optional[FileDiff] = None
    current_hunk: Optional[Hunk] = None
    old_no = new_no = 0

    for raw in text.splitlines():
        line = raw.rstrip("\r")

        # --- 新文件块开始 -------------------------------------------------
        m = _GIT_DIFF_START.match(line)
        if m:
            current = FileDiff(old_path="", new_path="")
            diffs.append(current)
            current_hunk = None
            continue

        if line.startswith("new file mode"):
            if current:
                current.is_new = True
            continue
        if line.startswith("deleted file mode"):
            if current:
                current.is_deleted = True
            continue
        if line.startswith("rename from"):
            if current:
                current.is_rename = True
                current.old_path = line[len("rename from "):].strip()
            continue
        if line.startswith("rename to"):
            if current:
                current.is_rename = True
                current.new_path = line[len("rename to "):].strip()
            continue
        if _BINARY_RE.match(line) or line.startswith("GIT binary patch"):
            if current:
                current.is_binary = True
            current_hunk = None
            continue

        m = _OLD_FILE_HEADER.match(line)
        if m and (current is not None or text.startswith(line)):
            path = m.group(1).strip()
            if path != "/dev/null":
                if current is None:
                    current = FileDiff(old_path="", new_path="")
                    diffs.append(current)
                current.old_path = path
            current_hunk = None
            continue

        m = _FILE_HEADER.match(line)
        if m and current is not None:
            path = m.group(1).strip()
            if path == "/dev/null":
                current.is_deleted = True
            else:
                current.new_path = path
            current_hunk = None
            continue

        header = _parse_hunk_header(line)
        if header and current is not None:
            old_start, _, new_start, _ = header
            current_hunk = Hunk(old_start=old_start, new_start=new_start)
            current.hunks.append(current_hunk)
            old_no, new_no = old_start, new_start
            continue

        # --- hunk 内容行 ---------------------------------------------------
        if current_hunk is None:
            continue
        if line.startswith("\\ No newline at end of file"):
            current.no_newline_at_eof = True
            continue
        if line.startswith("+"):
            current_hunk.lines.append(
                DiffLine("add", None, new_no, line[1:])
            )
            new_no += 1
        elif line.startswith("-"):
            current_hunk.lines.append(
                DiffLine("del", old_no, None, line[1:])
            )
            old_no += 1
        elif line.startswith(" "):
            current_hunk.lines.append(
                DiffLine("ctx", old_no, new_no, line[1:])
            )
            old_no += 1
            new_no += 1
        # 其他未知行（空行、指令行）直接忽略，保持解析器鲁棒。

    # 清理没有路径信息、没有内容且非二进制的空块
    return [d for d in diffs if d.path or d.hunks or d.is_binary]
