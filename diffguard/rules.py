# -*- coding: utf-8 -*-
"""DiffGuard · 确定性规则引擎。

内置约 30 条开箱即用的审查规则，覆盖五大类问题：
密钥泄漏（Secret）、危险 API（Danger）、调试残留（Debug）、
代码质量（Quality）、差异卫生（Hygiene）。

所有规则均为纯正则 + 轻量启发式，**零网络请求、零第三方依赖**，
输出为结构化 :class:`Finding`，天然可接入 CI 门禁与 SARIF 报告。

规则可通过内联注释抑制::

    password = "123456"  # diffguard:ignore[DL-S03]
    // diffguard:ignore[DL-P01]
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Callable, Dict, List, Optional, Pattern

__all__ = ["Finding", "Rule", "Severity", "RULES", "SUPPRESS_MARKER"]

SUPPRESS_MARKER = "diffguard:ignore"

SEVERITY_ORDER = {"blocker": 0, "high": 1, "medium": 2, "low": 3, "info": 4}


Severity = str  # "blocker" | "high" | "medium" | "low" | "info"


@dataclass(frozen=True)
class Rule:
    """单条审查规则定义。"""

    rule_id: str
    category: str            # secret / danger / debug / quality / hygiene
    severity: Severity
    pattern: Optional[Pattern[str]]
    message_cn: str
    message_en: str
    suggestion_cn: str = ""
    suggestion_en: str = ""
    languages: frozenset = frozenset()   # 空 = 全部语言；元素如 "py", "js"
    check: Optional[Callable] = None     # 自定义检查函数（可代替 pattern）


@dataclass
class Finding:
    """一条行级审查发现。"""

    file: str
    lineno: int
    rule_id: str
    severity: Severity
    category: str
    message_cn: str
    message_en: str
    suggestion_cn: str = ""
    suggestion_en: str = ""
    line_text: str = ""

    @property
    def sort_key(self):
        return (SEVERITY_ORDER.get(self.severity, 9), self.file, self.lineno)


# ---------------------------------------------------------------------------
# 语言判定
# ---------------------------------------------------------------------------

_EXT_LANG = {
    ".py": "py",
    ".pyw": "py",
    ".js": "js",
    ".jsx": "js",
    ".mjs": "js",
    ".cjs": "js",
    ".ts": "js",
    ".tsx": "js",
}


def detect_language(path: str) -> str:
    lower = path.lower()
    for ext, lang in _EXT_LANG.items():
        if lower.endswith(ext):
            return lang
    return "any"


# ---------------------------------------------------------------------------
# 内置规则表（~30 条）
# ---------------------------------------------------------------------------

def _c(pattern: str) -> Pattern[str]:
    return re.compile(pattern)


RULES: List[Rule] = [
    # === 密钥泄漏（Secret / blocker·high） =================================
    Rule("DL-S01", "secret", "blocker", _c(r"AKIA[0-9A-Z]{16}\b"),
         "疑似 AWS Access Key ID 硬编码在代码中。",
         "Likely hardcoded AWS Access Key ID.",
         "改用环境变量或密钥管理服务，并立即轮换该密钥。",
         "Use environment variables or a secret manager; rotate the key now."),
    Rule("DL-S02", "secret", "blocker",
         _c(r"-----BEGIN (?:RSA |EC |OPENSSH |DSA |PGP )?PRIVATE KEY( BLOCK)?-----"),
         "疑似私钥内容直接提交进仓库。",
         "A private key block appears to be committed.",
         "删除私钥文件并轮换密钥，改用受控的密钥分发方式。",
         "Remove the key, rotate it, and distribute keys via a controlled channel."),
    Rule("DL-S03", "secret", "high",
         _c(r"(?i)\b(api[_-]?key|apikey|secret|password|passwd|pwd|token|access[_-]?token)\b\s*[:=]\s*['\"][^'\"]{8,}['\"]"),
         "疑似硬编码的凭据赋值（密码 / token / API key）。",
         "Likely hardcoded credential assignment (password / token / API key).",
         "将凭据移至环境变量、.env 文件或密钥管理服务。",
         "Move the credential to an environment variable, .env file or secret manager."),
    Rule("DL-S04", "secret", "blocker",
         _c(r"\b(xox[bposar]-[0-9A-Za-z-]{10,}|ghp_[0-9A-Za-z]{30,}|github_pat_[0-9A-Za-z_]{20,}|AIza[0-9A-Za-z_\-]{30,}|sk-[0-9A-Za-z]{20,})\b"),
         "疑似第三方服务令牌（Slack / GitHub / Google / OpenAI）硬编码。",
         "Likely hardcoded third-party service token (Slack / GitHub / Google / OpenAI).",
         "立即从代码中移除并撤销该令牌。",
         "Remove it from code and revoke the token immediately."),

    # === 危险 API（Danger / high） ========================================
    Rule("DL-D01", "danger", "high", _c(r"\beval\s*\("),
         "使用 eval() 动态执行代码，存在注入风险。",
         "eval() executes dynamic code and is prone to injection.",
         "改用显式解析（ast.literal_eval / JSON.parse）或重构逻辑。",
         "Use explicit parsing (ast.literal_eval / JSON.parse) or restructure."),
    Rule("DL-D02", "danger", "high", _c(r"\bexec\s*\("),
         "使用 exec() 动态执行 Python 代码，存在注入风险。",
         "exec() executes dynamic Python code and is prone to injection.",
         "避免动态执行；确需插件化时使用白名单 + 显式模块加载。",
         "Avoid dynamic execution; if needed, use whitelists and explicit module loading.",
         languages=frozenset({"py"})),
    Rule("DL-D03", "danger", "high", _c(r"shell\s*=\s*True"),
         "subprocess 使用 shell=True，命令拼接易导致 Shell 注入。",
         "subprocess with shell=True; string concatenation enables shell injection.",
         "改用参数列表形式（shell=False）并对输入做校验。",
         "Use argument lists (shell=False) and validate inputs."),
    Rule("DL-D04", "danger", "high", _c(r"\bos\.system\s*\("),
         "使用 os.system 执行外部命令，易受 Shell 注入影响。",
         "os.system() invokes a shell and is prone to injection.",
         "改用 subprocess.run 参数列表形式。",
         "Use subprocess.run with an argument list instead."),
    Rule("DL-D05", "danger", "high", _c(r"\bpickle\.loads?\s*\("),
         "反序列化不可信数据使用 pickle，存在任意代码执行风险。",
         "Unpickling untrusted data enables arbitrary code execution.",
         "对外部数据改用 JSON 等安全格式；pickle 仅限可信内部数据。",
         "Use a safe format like JSON for external data; keep pickle for trusted data only.",
         languages=frozenset({"py"}),),
    Rule("DL-D06", "danger", "medium", _c(r"\byaml\.load\s*\((?![^)]*Loader)"),
         "yaml.load 未显式指定 Loader，旧版 PyYAML 存在反序列化风险。",
         "yaml.load without an explicit Loader is unsafe on older PyYAML.",
         "使用 yaml.safe_load() 或显式传 Loader=yaml.SafeLoader。",
         "Use yaml.safe_load() or pass Loader=yaml.SafeLoader.",
         languages=frozenset({"py"}),),
    Rule("DL-D07", "danger", "high", _c(r"verify\s*=\s*False"),
         "禁用 TLS 证书校验（verify=False），存在中间人攻击风险。",
         "TLS verification disabled (verify=False); MITM risk.",
         "修复证书链，或为内网自签证书显式配置受信任的 CA。",
         "Fix the certificate chain or configure a trusted CA for internal certs.",
         languages=frozenset({"py"}),),
    Rule("DL-D08", "danger", "medium",
         _c(r"(?is)\b(select|insert|update|delete)\b[^;\"']*[\"'][^\"']*['\"]?\s*(?:%|\+|\.format|f['\"])"),
         "疑似字符串拼接构造 SQL 语句，存在 SQL 注入风险。",
         "SQL statement appears to be built by string concatenation; injection risk.",
         "改用参数化查询 / 占位符（?、%s 或 ORM 绑定）。",
         "Use parameterized queries or ORM bindings instead."),
    Rule("DL-D09", "danger", "medium", _c(r"\bhashlib\.(md5|sha1)\s*\("),
         "使用弱哈希算法（MD5/SHA-1），不适合口令或安全场景。",
         "Weak hash (MD5/SHA-1) is unsuitable for passwords or security use.",
         "改用 bcrypt / scrypt / argon2（口令）或 SHA-256（通用摘要）。",
         "Use bcrypt/scrypt/argon2 for passwords, or SHA-256 for digests.",
         languages=frozenset({"py"}),),
    Rule("DL-D10", "danger", "high", _c(r"document\.write\s*\("),
         "使用 document.write 输出内容，易导致 XSS 且阻塞解析。",
         "document.write() is XSS-prone and blocks parsing.",
         "改用 DOM API（createElement / textContent）或框架渲染。",
         "Use DOM APIs (createElement / textContent) or framework rendering.",
         languages=frozenset({"js"}),),

    # === 调试残留（Debug） ================================================
    Rule("DL-P01", "debug", "low", _c(r"(?<![.\w])console\.(log|debug|info)\s*\("),
         "疑似调试用 console.log 残留。",
         "Debug console.log statement left in code.",
         "删除或改用结构化日志（如统一 logger）。",
         "Remove it or use a structured logger.",
         languages=frozenset({"js"}),),
    Rule("DL-P02", "debug", "medium", _c(r"^\s*debugger\s*;?\s*$"),
         "调试断点语句 debugger 残留。",
         "debugger statement left in code.",
         "删除 debugger 语句。",
         "Remove the debugger statement.",
         languages=frozenset({"js"}),),
    Rule("DL-P03", "debug", "low", _c(r"(?<![.\w])print\s*\((?![^)]*file\s*=)"),
         "疑似调试用 print 输出（库代码中应使用 logging）。",
         "Debug print() statement (libraries should use logging).",
         "删除或改用 logging 模块。",
         "Remove it or use the logging module.",
         languages=frozenset({"py"}),),
    Rule("DL-P04", "debug", "medium", _c(r"\bbreakpoint\s*\(\s*\)|pdb\.set_trace\s*\("),
         "调试断点 breakpoint()/pdb.set_trace() 残留。",
         "Debug breakpoint breakpoint()/pdb.set_trace() left in code.",
         "删除断点调用。",
         "Remove the breakpoint call.",
         languages=frozenset({"py"}),),
    Rule("DL-P05", "debug", "low", _c(r"(?<![.\w])alert\s*\("),
         "疑似调试用 alert() 残留。",
         "Debug alert() call left in code.",
         "删除或改用 UI 提示组件。",
         "Remove it or use a proper UI notification.",
         languages=frozenset({"js"}),),

    # === 代码质量（Quality） ==============================================
    Rule("DL-Q01", "quality", "info", _c(r"\b(TODO|FIXME|HACK|XXX)\b(?=:|\s|\()"),
         "代码中留有 TODO/FIXME 标记，应在任务系统中跟踪。",
         "TODO/FIXME marker left in code; track it in your issue tracker.",
         "为标记补充 Issue 链接或说明计划。",
         "Attach an issue link or a plan to the marker."),
    Rule("DL-Q02", "quality", "low", None,
         "行长度超过上限，影响可读性与 Code Review。",
         "Line exceeds the length limit, hurting readability.",
         "拆分表达式或调整格式。",
         "Reflow the expression or reformat.",
         check=None),
    Rule("DL-Q03", "quality", "high", _c(r"def\s+\w+\s*\([^)]*=\s*(\[\]|\{\}|set\(\)|dict\(\)|list\(\))"),
         "函数使用可变对象作为默认参数（跨调用共享状态）。",
         "Mutable default argument shared across calls.",
         "默认值改为 None，在函数体内创建新对象。",
         "Default to None and create a fresh object inside the function.",
         languages=frozenset({"py"}),),
    Rule("DL-Q04", "quality", "medium", _c(r"except\s*:\s*(#.*)?$"),
         "裸 except 会吞掉包括 KeyboardInterrupt 在内的所有异常。",
         "Bare except swallows all exceptions, including KeyboardInterrupt.",
         "捕获具体异常类型，必要时 finally 释放资源。",
         "Catch specific exception types and release resources in finally.",
         languages=frozenset({"py"}),),
    Rule("DL-Q05", "quality", "low", _c(r"(?<![!=<>])[!=]=\s*None\b"),
         "与 None 比较应使用 is/is not 而非 ==/!=。",
         "Compare to None with is/is not, not ==/!=.",
         "改写为 ``is None`` / ``is not None``。",
         "Rewrite as ``is None`` / ``is not None``.",
         languages=frozenset({"py"}),),
    Rule("DL-Q06", "quality", "low", _c(r"\bis\s+(True|False)\b(?!\s*(?:not|and|or)\b)"),
         "与布尔字面量比较应使用 == 而非 is（PEP 8）。",
         "Compare boolean literals with ==, not is (PEP 8).",
         "改写为 ``== True`` / 直接作为条件表达式。",
         "Use ``== True`` or the expression directly as a condition.",
         languages=frozenset({"py"}),),
    Rule("DL-Q07", "quality", "low", _c(r"(?<![.\w])var\s+[A-Za-z_$]"),
         "使用 var 声明变量存在作用域陷阱，建议 let/const。",
         "var declarations have scoping pitfalls; prefer let/const.",
         "改用 const（不可变）或 let（可变）。",
         "Use const (immutable) or let (mutable).",
         languages=frozenset({"js"}),),
    Rule("DL-Q08", "quality", "medium", _c(r"random\.(random|randint|choice|uniform)\s*\("),
         "安全场景（token/密码/密钥）不应使用 random 模块。",
         "The random module is not cryptographically secure.",
         "改用 secrets 模块（secrets.token_hex 等）。",
         "Use the secrets module (e.g. secrets.token_hex).",
         languages=frozenset({"py"}),),

    # === 差异卫生（Hygiene，文件级由引擎特殊处理） ==========================
    Rule("DL-H01", "hygiene", "low", None,
         "本次新增行数过多，建议拆分提交以便 Review。",
         "Too many added lines; consider splitting the commit.",
         "按功能模块拆分为多个提交/PR。",
         "Split into smaller commits/PRs by feature."),
    Rule("DL-H02", "hygiene", "low", None,
         "文件末尾缺少换行符。",
         "File does not end with a newline.",
         "在文件末尾补一个换行符。",
         "Add a trailing newline at end of file."),
    Rule("DL-H03", "hygiene", "low", _c(r"\r$"),
         "新增行包含 CR（CRLF 换行），跨平台协作易产生噪音 diff。",
         "Added line contains CR (CRLF), creating noisy diffs.",
         "统一仓库换行符（.gitattributes / editorconfig）。",
         "Normalize line endings via .gitattributes / editorconfig."),
    Rule("DL-H04", "hygiene", "info", _c(r"(?i)\.(min\.js|bundle\.js|\.map|\.pyc|\.DS_Store)$"),
         "疑似构建产物 / 系统文件被提交进仓库。",
         "Likely build artifact / OS file committed.",
         "加入 .gitignore 并从版本控制移除。",
         "Add to .gitignore and untrack the file."),
]


# ---------------------------------------------------------------------------
# 抑制注释
# ---------------------------------------------------------------------------

def suppression_for(line_text: str) -> Optional[set]:
    """返回该行被抑制的规则 ID 集合（None 表示未抑制）。

    支持 ``# diffguard:ignore``（抑制全部）与
    ``# diffguard:ignore[DL-S03,DL-Q01]``（按 ID 抑制）。
    """
    m = re.search(re.escape(SUPPRESS_MARKER) + r"(?:\[([A-Za-z0-9\-,\s]*)\])?", line_text)
    if not m:
        return None
    ids = m.group(1)
    if not ids:
        return set()  # 空 = 抑制所有规则
    return {s.strip() for s in ids.split(",") if s.strip()}
