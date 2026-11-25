# -*- coding: utf-8 -*-
"""DiffGuard · 报告生成器。

支持四种输出格式：
- ``text``     终端友好（默认，自动彩色，可 --no-color 关闭）
- ``json``     机器可读，供其他工具消费
- ``sarif``    SARIF 2.1.0，供 GitHub Code Scanning / IDE 使用
- ``markdown`` 适合粘贴到 PR / Issue 的评审报告
"""

from __future__ import annotations

import json
from typing import List, Optional

from .engine import Config
from .rules import Finding, SEVERITY_ORDER

__all__ = ["render", "render_text", "render_json", "render_sarif", "render_markdown"]

_SEV_SYMBOL = {"blocker": "🛑", "high": "⛔", "medium": "⚠️", "low": "🔹", "info": "ℹ️"}
_SEV_COLOR = {
    "blocker": "\033[1;31m", "high": "\033[0;31m", "medium": "\033[0;33m",
    "low": "\033[0;36m", "info": "\033[0;90m",
}
_RESET = "\033[0m"
_BOLD = "\033[1m"
_DIM = "\033[2m"


def render(findings: List[Finding], fmt: str, config: Optional[Config] = None,
           color: bool = True, locale: str = "cn", summary: Optional[dict] = None) -> str:
    if fmt == "json":
        return render_json(findings, summary=summary)
    if fmt == "sarif":
        return render_sarif(findings)
    if fmt == "markdown":
        return render_markdown(findings, locale=locale, summary=summary)
    return render_text(findings, color=color, locale=locale)


# ---------------------------------------------------------------------------
# text
# ---------------------------------------------------------------------------

def render_text(findings: List[Finding], color: bool = True, locale: str = "cn") -> str:
    lines: List[str] = []
    def paint(s: str, code: str) -> str:
        return f"{code}{s}{_RESET}" if color else s

    header = "DiffGuard 发现 %d 个问题" % len(findings) if locale == "cn" \
        else "DiffGuard found %d issue(s)" % len(findings)
    lines.append(paint(f"=== {header} ===", _BOLD))
    lines.append("")

    current_file = None
    for f in findings:
        if f.file != current_file:
            current_file = f.file
            lines.append(paint(f"📄 {f.file}", _BOLD))
        sym = _SEV_SYMBOL.get(f.severity, "•")
        sev = paint(f.severity.upper().ljust(7), _SEV_COLOR.get(f.severity, ""))
        msg = f.message_cn if locale == "cn" else f.message_en
        sug = f.suggestion_cn if locale == "cn" else f.suggestion_en
        lines.append(f"  {sym} {sev} {f.rule_id} :{f.lineno}  {msg}")
        if line := f.line_text.strip()[:160]:
            lines.append(f"     {paint('| ' + line, _DIM)}")
        if sug:
            lines.append(f"     {paint('💡 ' + sug, _DIM)}")
        lines.append("")

    if not findings:
        lines.append("✅ " + ("未发现问题，差异审查通过。" if locale == "cn"
                              else "No issues found; diff review passed."))
        lines.append("")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# json
# ---------------------------------------------------------------------------

def render_json(findings: List[Finding], summary: Optional[dict] = None) -> str:
    payload = {
        "tool": "diffguard",
        "version": __import__("diffguard").__version__,
        "findings": [
            {
                "file": f.file,
                "line": f.lineno,
                "rule_id": f.rule_id,
                "severity": f.severity,
                "category": f.category,
                "message_cn": f.message_cn,
                "message_en": f.message_en,
                "suggestion_cn": f.suggestion_cn,
                "suggestion_en": f.suggestion_en,
                "line_text": f.line_text,
            }
            for f in findings
        ],
    }
    if summary:
        payload["summary"] = summary
    return json.dumps(payload, ensure_ascii=False, indent=2)


# ---------------------------------------------------------------------------
# sarif 2.1.0
# ---------------------------------------------------------------------------

def render_sarif(findings: List[Finding]) -> str:
    rules_map = {}
    results = []
    for f in findings:
        rules_map.setdefault(f.rule_id, {
            "id": f.rule_id,
            "shortDescription": {"text": f.message_en},
            "properties": {"category": f.category},
        })
        results.append({
            "ruleId": f.rule_id,
            "level": _sarif_level(f.severity),
            "message": {"text": f"{f.message_en} {f.suggestion_en}".strip()},
            "locations": [{
                "physicalLocation": {
                    "artifactLocation": {"uri": f.file.replace("\\", "/")},
                    "region": {"startLine": f.lineno},
                }
            }],
        })
    sarif = {
        "$schema": "https://json.schemastore.org/sarif-2.1.0.json",
        "version": "2.1.0",
        "runs": [{
            "tool": {
                "driver": {
                    "name": "DiffGuard",
                    "informationUri": "https://github.com/gitstq/DiffGuard",
                    "rules": sorted(rules_map.values(), key=lambda r: r["id"]),
                }
            },
            "results": results,
        }],
    }
    return json.dumps(sarif, ensure_ascii=False, indent=2)


def _sarif_level(severity: str) -> str:
    if severity in ("blocker", "high"):
        return "error"
    if severity == "medium":
        return "warning"
    return "note"


# ---------------------------------------------------------------------------
# markdown
# ---------------------------------------------------------------------------

def render_markdown(findings: List[Finding], locale: str = "cn",
                    summary: Optional[dict] = None) -> str:
    is_cn = locale == "cn"
    out: List[str] = []
    out.append(f"# 📋 DiffGuard {'代码审查报告' if is_cn else 'Code Review Report'}")
    out.append("")
    if summary:
        out.append(f"> 审查范围：**{summary.get('files', 0)}** 个文件 / "
                   f"**{summary.get('added_lines', 0)}** 行新增代码"
                   if is_cn else
                   f"> Scope: **{summary.get('files', 0)}** file(s) / "
                   f"**{summary.get('added_lines', 0)}** added line(s)")
        out.append("")
    if not findings:
        out.append("✅ " + ("未发现问题，差异审查通过。" if is_cn
                            else "No issues found; diff review passed."))
        return "\n".join(out) + "\n"

    # 按严重度统计
    stats: dict = {}
    for f in findings:
        stats[f.severity] = stats.get(f.severity, 0) + 1
    parts = [f"{_SEV_SYMBOL[s]} {s} × {stats[s]}" for s in SEVERITY_ORDER if s in stats]
    out.append(("严重度分布：" if is_cn else "Severity: ") + " ｜ ".join(parts))
    out.append("")

    for f in findings:
        msg = f.message_cn if is_cn else f.message_en
        sug = f.suggestion_cn if is_cn else f.suggestion_en
        out.append(f"- {_SEV_SYMBOL.get(f.severity, '•')} "
                   f"`{f.rule_id}` **{f.file}:{f.lineno}** — {msg}")
        if f.line_text.strip():
            code = f.line_text.strip()[:160].replace("`", "'")
            out.append(f"  - > `{code}`")
        if sug:
            out.append(f"  - 💡 {sug}")
    return "\n".join(out) + "\n"
