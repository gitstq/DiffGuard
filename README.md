<div align="center">

# 🔍 DiffGuard

**零依赖 · 离线优先的 Git 差异确定性代码审查引擎**

简体中文 | [繁體中文](README.zh-TW.md) | [English](README.en.md)

*CLI + Python 库 · 31 条内置规则 · SARIF / JSON / Markdown 报告 · CI 门禁就绪*

</div>

---

## 🎉 介绍

DiffGuard 是一个**纯 Python 标准库**实现的确定性代码审查引擎：它读取 Git 差异（暂存区 / 分支 / 补丁文件），用 31 条内置规则对**每一行新增代码**做行级审查，输出结构化、可定位、可门禁的审查报告。

与依赖大模型做「概率性审查」的工具不同，DiffGuard 是**确定性**的：同样的输入永远得到同样的结果，零网络请求、零第三方依赖、零配置即可运行。它特别适合放在**提交前钩子**和 **CI 流水线**里，把密钥泄漏、注入风险、调试残留这类「机器一定能查出来」的问题拦在合并之前，把昂贵的人力审查留给真正需要思考的问题。

> 💡 名字来源：Lens（透镜）—— 帮你在 diff 上装一枚不放过大模型噪音、只放大真实风险的透镜。

## ✨ 特性

- 🧩 **零依赖**：100% Python 标准库（3.8+），`pip install` 都不需要，克隆即用。
- 🌐 **离线优先**：不发一个网络请求，代码与 diff 永不出本机，天然适合敏感仓库。
- 🎯 **行级精确**：自研 unified diff 解析器，保留新旧两侧行号，发现精确到行。
- 📚 **31 条内置规则**：覆盖密钥泄漏、危险 API、调试残留、代码质量、差异卫生五大类。
- 🚦 **CI 门禁**：`--fail-on blocker,high` 直接以退出码接入流水线，无需胶水脚本。
- 📄 **四种报告**：终端彩色文本 / JSON / SARIF 2.1.0（GitHub Code Scanning 可直接消费）/ Markdown（贴进 PR）。
- 🔇 **精准抑制**：行内 `# diffguard:ignore[规则ID]` 注释，按行、按规则消音，不污染全局配置。
- 📦 **双形态**：`diffguard` CLI + `import diffguard` Python 库，还能打成单个 `.pyz` 文件随处运行。
- 🗂️ **整文件扫描**：`diffguard scan src/` 一键审计陌生代码库，不依赖 Git 历史。
- 🌍 **双语报告**：中英文报告文案随意切换，团队协作更顺畅。

## 🚀 快速开始

```bash
# 方式一：克隆即用（推荐，零安装）
git clone https://github.com/gitstq/DiffGuard.git
cd DiffGuard
python3 -m diffguard --staged        # 审查你的暂存区改动

# 方式二：pip 安装
pip install git+https://github.com/gitstq/DiffGuard.git
diffguard --staged

# 方式三：单文件 .pyz（下载 Release 后直接运行）
./diffguard-1.0.0.pyz --staged
```

30 秒体验：往任意文件里加一行 `API_KEY = "supersecret123456"` 并 `git add`，然后运行 `python3 -m diffguard --staged`，你会看到一条 ⛔ HIGH 级发现和修复建议，且退出码为 `1`。

## 📖 使用指南

### 🛠️ 五种审查来源

| 命令 | 场景 |
|------|------|
| `diffguard` | 审查工作区改动（HEAD vs 工作区） |
| `diffguard --staged` | 提交前检查暂存区（钩子场景最常用） |
| `diffguard --branch main` | 审查当前分支相对 main 的全部改动（PR 场景） |
| `diffguard --diff fix.patch` | 审查补丁文件（无需 Git 仓库） |
| `diffguard scan src/` | 整文件扫描（审计陌生代码库） |

### 📋 常用选项

```bash
diffguard --staged -f sarif -o report.sarif   # SARIF 报告写入文件
diffguard --staged --fail-on blocker,high     # 自定义 CI 门禁阈值
diffguard --staged -f markdown                # 输出可粘贴进 PR 的 Markdown
diffguard --staged --locale en                # 英文报告
diffguard --list-rules                        # 列出全部规则
```

### 📚 内置规则一览（31 条）

**🔐 密钥泄漏（Secret）**

| 规则 | 严重度 | 说明 |
|------|--------|------|
| DL-S01 | 🛑 blocker | 疑似 AWS Access Key ID 硬编码 |
| DL-S02 | 🛑 blocker | 疑似私钥内容提交进仓库 |
| DL-S03 | ⛔ high | 疑似硬编码凭据赋值（密码 / token / API key） |
| DL-S04 | 🛑 blocker | 疑似第三方服务令牌（Slack / GitHub / Google / OpenAI） |

**⚠️ 危险 API（Danger）**

| 规则 | 严重度 | 说明 |
|------|--------|------|
| DL-D01 | ⛔ high | `eval()` 动态执行 |
| DL-D02 | ⛔ high | `exec()` 动态执行（Python） |
| DL-D03 | ⛔ high | `subprocess` 使用 `shell=True`（Python） |
| DL-D04 | ⛔ high | `os.system()`（Python） |
| DL-D05 | ⛔ high | `pickle` 反序列化不可信数据（Python） |
| DL-D06 | ⚠️ medium | `yaml.load` 未指定 Loader（Python） |
| DL-D07 | ⛔ high | 禁用 TLS 校验 `verify=False`（Python） |
| DL-D08 | ⚠️ medium | 字符串拼接构造 SQL |
| DL-D09 | ⚠️ medium | 弱哈希 MD5 / SHA-1（Python） |
| DL-D10 | ⛔ high | `document.write()`（JS/TS） |

**🐛 调试残留（Debug）**

| 规则 | 严重度 | 说明 |
|------|--------|------|
| DL-P01 | 🔹 low | `console.log` 残留（JS/TS） |
| DL-P02 | ⚠️ medium | `debugger` 语句（JS/TS） |
| DL-P03 | 🔹 low | `print()` 调试输出（Python） |
| DL-P04 | ⚠️ medium | `breakpoint()` / `pdb.set_trace()`（Python） |
| DL-P05 | 🔹 low | `alert()` 残留（JS/TS） |

**🧪 代码质量（Quality）**

| 规则 | 严重度 | 说明 |
|------|--------|------|
| DL-Q01 | ℹ️ info | TODO / FIXME 标记 |
| DL-Q02 | 🔹 low | 行长度超限（默认 120，可配置） |
| DL-Q03 | ⛔ high | 可变对象作为默认参数（Python） |
| DL-Q04 | ⚠️ medium | 裸 `except:`（Python） |
| DL-Q05 | 🔹 low | `== None` 应使用 `is None`（Python） |
| DL-Q06 | 🔹 low | `is True` / `is False`（Python，PEP 8） |
| DL-Q07 | 🔹 low | `var` 声明（JS/TS） |
| DL-Q08 | ⚠️ medium | 安全场景使用 `random` 模块（Python） |

**🧹 差异卫生（Hygiene）**

| 规则 | 严重度 | 说明 |
|------|--------|------|
| DL-H01 | 🔹 low | 单次新增行数过多（>500 行），建议拆分提交 |
| DL-H02 | 🔹 low | 文件末尾缺少换行符 |
| DL-H03 | 🔹 low | CRLF 换行混入 |
| DL-H04 | ℹ️ info | 构建产物 / 系统文件入库 |

### 🚦 接入 CI（GitHub Actions 示例）

```yaml
- name: DiffGuard review
  run: |
    pip install git+https://github.com/gitstq/DiffGuard.git
    python -m diffguard --branch origin/main --fail-on blocker,high
```

非零退出码即代表存在达到阈值的问题，流水线自动失败。

### 🔇 抑制误报

```python
# 演示代码，确需硬编码：按行 + 按规则精准抑制
API_KEY = "supersecret123456"  # diffguard:ignore[DL-S03]
legacy_value = eval(expr)      # diffguard:ignore
```

- `# diffguard:ignore`（JS 用 `//`）：抑制本行全部规则；
- `# diffguard:ignore[DL-S03,DL-Q01]`：只抑制指定规则。

### ⚙️ 项目配置（`.diffguard.json`）

```json
{
  "fail_on": ["blocker", "high"],
  "max_line_length": 120,
  "disabled_rules": ["DL-P03"],
  "ignore_patterns": ["*.min.js", "vendor/*", "tests/*"]
}
```

### 🐍 作为 Python 库使用

```python
from diffguard import parse_unified_diff, Engine, Config

diff_text = open("fix.patch", encoding="utf-8").read()
findings = Engine(Config(max_line_length=100)).review(parse_unified_diff(diff_text))

for f in findings:
    print(f.severity, f.rule_id, f"{f.file}:{f.lineno}", f.message_cn)
```

## 💡 设计迭代

- **v1.0.0**：首发版本。自研 unified diff 解析器（支持新增 / 删除 / 重命名 / 二进制 / no-newline 等真实场景）、31 条规则、双语文案、四种报告格式、CI 门禁、行级抑制、`.diffguard.json` 项目配置、整文件扫描模式、zipapp 单文件打包。
- **Roadmap**：规则基线（只报新增问题）、更多语言规则（Go / Java）、`git blame` 历史加权、编辑器插件协议。

## 📦 打包部署

```bash
./scripts/build.sh
```

一键产出：

| 产物 | 说明 |
|------|------|
| `dist/diffguard-1.0.0.pyz` | 单文件可执行，`./diffguard-1.0.0.pyz --staged` 直接运行 |
| `dist/diffguard-1.0.0-source.zip` | 完整源码包（含测试与文档） |
| `dist/SHA256SUMS.txt` | 全部产物的 SHA256 校验和 |

无构建工具链要求，Python 3.8+ 即可完成打包。

## 🤝 贡献

欢迎 Issue 与 PR！新增规则、修复误报、补充文档都非常欢迎。请阅读 [CONTRIBUTING.md](CONTRIBUTING.md) 了解提交规范与规则注册流程。

## 📄 协议

本项目基于 [MIT License](LICENSE) 开源。
