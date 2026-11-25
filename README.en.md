<div align="center">

# 🔍 DiffGuard

**Zero-Dependency, Offline-First Deterministic Code Review Engine for Git Diffs**

[简体中文](README.md) | [繁體中文](README.zh-TW.md) | English

*CLI + Python library · 31 built-in rules · SARIF / JSON / Markdown reports · CI gate ready*

</div>

---

## 🎉 Introduction

DiffGuard is a deterministic code review engine built on the **pure Python standard library**: it reads Git diffs (staged changes / branches / patch files), reviews **every added line** against 31 built-in rules, and produces structured, line-precise, gate-ready review findings.

Unlike tools that rely on large language models for "probabilistic review", DiffGuard is **deterministic**: the same input always yields the same output, with zero network requests, zero third-party dependencies, and zero required configuration. It shines in **pre-commit hooks** and **CI pipelines**, catching machine-detectable issues — leaked secrets, injection risks, leftover debug code — before they merge, and saving expensive human review for the questions that actually require judgment.

> 💡 The name: Lens — a magnifier for your diff that amplifies real risk, not LLM noise.

## ✨ Features

- 🧩 **Zero dependencies**: 100% Python standard library (3.8+); you don't even need `pip install` — clone and run.
- 🌐 **Offline-first**: not a single network request; your code and diffs never leave the machine — perfect for sensitive repositories.
- 🎯 **Line-level precision**: a hand-written unified diff parser that tracks both old and new line numbers.
- 📚 **31 built-in rules**: secrets, dangerous APIs, debug leftovers, code quality, and diff hygiene.
- 🚦 **CI gate**: `--fail-on blocker,high` plugs straight into pipelines via exit codes — no glue scripts.
- 📄 **Four report formats**: colored terminal text / JSON / SARIF 2.1.0 (consumable by GitHub Code Scanning) / Markdown (paste into a PR).
- 🔇 **Precise suppression**: inline `# diffguard:ignore[rule-id]` comments mute findings per line and per rule, without polluting global config.
- 📦 **Two form factors**: the `diffguard` CLI and the `import diffguard` library — plus a single `.pyz` file you can run anywhere.
- 🗂️ **Full-file scan**: `diffguard scan src/` audits unfamiliar codebases without any Git history.
- 🌍 **Bilingual reports**: switch between Chinese and English report text to keep mixed teams aligned.

## 🚀 Quick Start

```bash
# Option 1: clone and run (recommended, zero install)
git clone https://github.com/gitstq/DiffGuard.git
cd DiffGuard
python3 -m diffguard --staged        # review your staged changes

# Option 2: install with pip
pip install git+https://github.com/gitstq/DiffGuard.git
diffguard --staged

# Option 3: single-file .pyz (download from Releases, run directly)
./diffguard-1.0.0.pyz --staged
```

30-second tour: add a line `API_KEY = "supersecret123456"` to any file, `git add` it, then run `python3 -m diffguard --staged` — you'll get one ⛔ HIGH finding with a fix suggestion, and exit code `1`.

## 📖 Usage Guide

### 🛠️ Five Review Sources

| Command | Scenario |
|---------|----------|
| `diffguard` | Review working-tree changes (HEAD vs worktree) |
| `diffguard --staged` | Pre-commit check of the index (the hook favorite) |
| `diffguard --branch main` | Review everything on this branch vs `main` (PR scenario) |
| `diffguard --diff fix.patch` | Review a patch file (no Git repo required) |
| `diffguard scan src/` | Full-file scan (audit an unfamiliar codebase) |

### 📋 Common Options

```bash
diffguard --staged -f sarif -o report.sarif   # write a SARIF report
diffguard --staged --fail-on blocker,high     # customize the CI gate threshold
diffguard --staged -f markdown                # Markdown you can paste into a PR
diffguard --staged --locale en                # English report text
diffguard --list-rules                        # list all rules
```

### 📚 Built-in Rules (31)

**🔐 Secrets**

| Rule | Severity | Description |
|------|----------|-------------|
| DL-S01 | 🛑 blocker | Likely hardcoded AWS Access Key ID |
| DL-S02 | 🛑 blocker | A private key block appears to be committed |
| DL-S03 | ⛔ high | Likely hardcoded credential assignment (password / token / API key) |
| DL-S04 | 🛑 blocker | Likely third-party service token (Slack / GitHub / Google / OpenAI) |

**⚠️ Dangerous APIs**

| Rule | Severity | Description |
|------|----------|-------------|
| DL-D01 | ⛔ high | `eval()` dynamic execution |
| DL-D02 | ⛔ high | `exec()` dynamic execution (Python) |
| DL-D03 | ⛔ high | `subprocess` with `shell=True` (Python) |
| DL-D04 | ⛔ high | `os.system()` (Python) |
| DL-D05 | ⛔ high | Unpickling untrusted data with `pickle` (Python) |
| DL-D06 | ⚠️ medium | `yaml.load` without an explicit Loader (Python) |
| DL-D07 | ⛔ high | TLS verification disabled, `verify=False` (Python) |
| DL-D08 | ⚠️ medium | SQL built by string concatenation |
| DL-D09 | ⚠️ medium | Weak hash MD5 / SHA-1 (Python) |
| DL-D10 | ⛔ high | `document.write()` (JS/TS) |

**🐛 Debug Leftovers**

| Rule | Severity | Description |
|------|----------|-------------|
| DL-P01 | 🔹 low | `console.log` leftovers (JS/TS) |
| DL-P02 | ⚠️ medium | `debugger` statement (JS/TS) |
| DL-P03 | 🔹 low | `print()` debug output (Python) |
| DL-P04 | ⚠️ medium | `breakpoint()` / `pdb.set_trace()` (Python) |
| DL-P05 | 🔹 low | `alert()` leftovers (JS/TS) |

**🧪 Code Quality**

| Rule | Severity | Description |
|------|----------|-------------|
| DL-Q01 | ℹ️ info | TODO / FIXME markers |
| DL-Q02 | 🔹 low | Line exceeds length limit (default 120, configurable) |
| DL-Q03 | ⛔ high | Mutable default argument (Python) |
| DL-Q04 | ⚠️ medium | Bare `except:` (Python) |
| DL-Q05 | 🔹 low | `== None` should be `is None` (Python) |
| DL-Q06 | 🔹 low | `is True` / `is False` (Python, PEP 8) |
| DL-Q07 | 🔹 low | `var` declarations (JS/TS) |
| DL-Q08 | ⚠️ medium | `random` module used in security contexts (Python) |

**🧹 Diff Hygiene**

| Rule | Severity | Description |
|------|----------|-------------|
| DL-H01 | 🔹 low | Too many added lines in one change (>500); consider splitting |
| DL-H02 | 🔹 low | File does not end with a newline |
| DL-H03 | 🔹 low | CRLF line endings mixed in |
| DL-H04 | ℹ️ info | Build artifacts / OS files committed |

### 🚦 Wire into CI (GitHub Actions example)

```yaml
- name: DiffGuard review
  run: |
    pip install git+https://github.com/gitstq/DiffGuard.git
    python -m diffguard --branch origin/main --fail-on blocker,high
```

A non-zero exit code means findings reached the threshold, failing the pipeline automatically.

### 🔇 Suppressing False Positives

```python
# Demo code where hardcoding is truly required: per-line, per-rule suppression
API_KEY = "supersecret123456"  # diffguard:ignore[DL-S03]
legacy_value = eval(expr)      # diffguard:ignore
```

- `# diffguard:ignore` (`//` in JS): suppress all rules on this line;
- `# diffguard:ignore[DL-S03,DL-Q01]`: suppress only the listed rules.

### ⚙️ Project Config (`.diffguard.json`)

```json
{
  "fail_on": ["blocker", "high"],
  "max_line_length": 120,
  "disabled_rules": ["DL-P03"],
  "ignore_patterns": ["*.min.js", "vendor/*", "tests/*"]
}
```

### 🐍 Using as a Python Library

```python
from diffguard import parse_unified_diff, Engine, Config

diff_text = open("fix.patch", encoding="utf-8").read()
findings = Engine(Config(max_line_length=100)).review(parse_unified_diff(diff_text))

for f in findings:
    print(f.severity, f.rule_id, f"{f.file}:{f.lineno}", f.message_en)
```

## 💡 Design & Iteration

- **v1.0.0**: initial release. Hand-written unified diff parser (handles additions / deletions / renames / binaries / no-newline and other real-world cases), 31 rules, bilingual report text, four report formats, CI gate, per-line suppression, `.diffguard.json` project config, full-file scan mode, and zipapp single-file packaging.
- **Roadmap**: rule baselines (report only new findings), more language rules (Go / Java), `git blame` history weighting, editor plugin protocol.

## 📦 Packaging & Deployment

```bash
./scripts/build.sh
```

One command produces:

| Artifact | Description |
|----------|-------------|
| `dist/diffguard-1.0.0.pyz` | Single-file executable: `./diffguard-1.0.0.pyz --staged` |
| `dist/diffguard-1.0.0-source.zip` | Full source package (tests & docs included) |
| `dist/SHA256SUMS.txt` | SHA256 checksums for all artifacts |

No build toolchain required — Python 3.8+ is enough.

## 🤝 Contributing

Issues and PRs are welcome! Adding rules, fixing false positives, and improving docs are all appreciated. See [CONTRIBUTING.md](CONTRIBUTING.md) for commit conventions and the rule registration workflow.

## 📄 License

Licensed under the [MIT License](LICENSE).
