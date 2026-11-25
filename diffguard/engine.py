# -*- coding: utf-8 -*-
"""DiffGuard · 审查引擎。

把 :mod:`diffguard.rules` 中的规则应用到 :mod:`diffguard.diffparser`
解析出的差异上，产出 :class:`diffguard.rules.Finding` 列表。

同时支持「整文件扫描」模式（scan）：把目标文件合成为全量新增差异后
复用同一套规则，便于审计陌生代码库。
"""

from __future__ import annotations

import fnmatch
from dataclasses import dataclass, field
from typing import Iterable, List, Optional, Sequence

from .diffparser import DiffLine, FileDiff
from .rules import RULES, Finding, Rule, SUPPRESS_MARKER, detect_language, suppression_for

__all__ = ["Config", "Engine"]

FILE_ADDED_LINE_LIMIT = 500  # DL-H01 阈值


@dataclass
class Config:
    """审查配置，可由 ``.diffguard.json`` 加载。"""

    max_line_length: int = 120
    disabled_rules: Sequence[str] = ()
    ignore_patterns: Sequence[str] = ()   # fnmatch 通配，匹配文件路径
    fail_on: Sequence[str] = ("blocker", "high")
    locale: str = "cn"                    # "cn" | "en"

    @classmethod
    def from_file(cls, path: str) -> "Config":
        import json
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        known = {k: v for k, v in data.items() if k in cls.__dataclass_fields__}
        return cls(**known)


class Engine:
    """规则审查引擎。"""

    def __init__(self, config: Optional[Config] = None) -> None:
        self.config = config or Config()

    # ------------------------------------------------------------------
    # 公共入口
    # ------------------------------------------------------------------
    def review(self, diffs: Iterable[FileDiff]) -> List[Finding]:
        findings: List[Finding] = []
        for fd in diffs:
            if fd.is_binary:
                continue
            if self._ignored(fd.path):
                continue
            findings.extend(self._review_file(fd))
        findings.sort(key=lambda f: f.sort_key)
        return findings

    def review_files(self, paths: Iterable[str], root: str = "") -> List[Finding]:
        """整文件扫描模式：把每个文件合成为「全量新增」差异再审查。"""
        import os
        diffs: List[FileDiff] = []
        for p in paths:
            full = os.path.join(root, p) if root and not os.path.isabs(p) else p
            if not os.path.isfile(full):
                continue
            try:
                with open(full, "r", encoding="utf-8", errors="replace") as f:
                    text = f.read()
            except OSError:
                continue
            fd = FileDiff(old_path="/dev/null", new_path=p, is_new=True)
            hunk_lines = []
            no_nl = False
            for i, line in enumerate(text.splitlines(), start=1):
                stripped = line.rstrip("\r")
                if line.endswith("\r") and i == len(text.splitlines()):
                    pass
                hunk_lines.append(DiffLine("add", None, i, stripped))
            if not text.endswith("\n") and text:
                no_nl = True
            from .diffparser import Hunk
            hunk = Hunk(old_start=1, new_start=1, lines=hunk_lines)
            fd.hunks = [hunk]
            fd.no_newline_at_eof = no_nl
            diffs.append(fd)
        return self.review(diffs)

    def gate(self, findings: Sequence[Finding]) -> bool:
        """CI 门禁：是否存在达到 fail_on 阈值的发现。"""
        from .rules import SEVERITY_ORDER
        if not self.config.fail_on:
            return True
        max_block = max(SEVERITY_ORDER.get(s, 9) for s in self.config.fail_on)
        return all(SEVERITY_ORDER.get(f.severity, 9) > max_block for f in findings)

    # ------------------------------------------------------------------
    # 内部实现
    # ------------------------------------------------------------------
    def _ignored(self, path: str) -> bool:
        for pat in self.config.ignore_patterns:
            if fnmatch.fnmatch(path, pat) or fnmatch.fnmatch(path, pat.rstrip("/")):
                return True
        return False

    def _disabled(self, rule_id: str) -> bool:
        return rule_id in set(self.config.disabled_rules)

    def _review_file(self, fd: FileDiff) -> List[Finding]:
        findings: List[Finding] = []
        lang = detect_language(fd.path)
        rules = [r for r in RULES if not self._disabled(r.rule_id)]
        added = fd.added_lines

        for line in added:
            suppress = suppression_for(line.text)
            lineno = line.new_lineno or 1
            for rule in rules:
                if rule.rule_id in {"DL-H01", "DL-H02"}:
                    continue  # 文件级规则单独处理
                if suppress is not None and (not suppress or rule.rule_id in suppress):
                    continue
                if rule.languages and lang not in rule.languages and lang != "any":
                    continue
                if rule.rule_id == "DL-Q02":
                    if len(line.text) > self.config.max_line_length:
                        findings.append(self._make(rule, fd, lineno, line.text))
                    continue
                if rule.pattern is not None and rule.pattern.search(line.text):
                    findings.append(self._make(rule, fd, lineno, line.text))

        # 文件级：新增行数过多
        if added and len(added) > FILE_ADDED_LINE_LIMIT:
            rule = next(r for r in rules if r.rule_id == "DL-H01")
            findings.append(
                self._make(rule, fd, added[0].new_lineno or 1, "")
            )
        # 文件级：文件末尾缺换行（新增文件或追加过内容时提示）
        if fd.no_newline_at_eof and not fd.is_deleted and fd.hunks:
            rule = next(r for r in rules if r.rule_id == "DL-H02")
            lineno = fd.hunks[-1].lines[-1].new_lineno or 1
            findings.append(self._make(rule, fd, lineno, ""))

        return findings

    def _make(self, rule: Rule, fd: FileDiff, lineno: int, line_text: str) -> Finding:
        return Finding(
            file=fd.path,
            lineno=lineno,
            rule_id=rule.rule_id,
            severity=rule.severity,
            category=rule.category,
            message_cn=rule.message_cn,
            message_en=rule.message_en,
            suggestion_cn=rule.suggestion_cn,
            suggestion_en=rule.suggestion_en,
            line_text=line_text,
        )
