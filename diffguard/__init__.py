# -*- coding: utf-8 -*-
"""DiffGuard — 零依赖、离线优先的 Git 差异确定性代码审查引擎。

纯 Python 标准库实现（Python 3.8+），可作为库嵌入 CI 或编辑器插件::

    from diffguard import parse_unified_diff, Engine

    diffs = parse_unified_diff(diff_text)
    findings = Engine().review(diffs)
"""

__version__ = "1.0.0"

from .diffparser import DiffLine, FileDiff, Hunk, parse_unified_diff
from .engine import Config, Engine
from .gitsource import GitSourceError, collect_diff, get_changed_files
from .reports import (render, render_json, render_markdown, render_sarif,
                      render_text)
from .rules import Finding, Rule, RULES, SUPPRESS_MARKER

__all__ = [
    "__version__",
    "Config", "Engine", "Finding", "Rule", "RULES", "SUPPRESS_MARKER",
    "DiffLine", "FileDiff", "Hunk", "parse_unified_diff",
    "collect_diff", "get_changed_files", "GitSourceError",
    "render", "render_text", "render_json", "render_sarif", "render_markdown",
]
