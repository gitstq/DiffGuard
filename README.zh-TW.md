<div align="center">

# 🔍 DiffGuard

**零相依 · 離線優先的 Git 差異確定性程式碼審查引擎**

[简体中文](README.md) | 繁體中文 | [English](README.en.md)

*CLI + Python 函式庫 · 31 條內建規則 · SARIF / JSON / Markdown 報告 · CI 門檻就緒*

</div>

---

## 🎉 介紹

DiffGuard 是一個**純 Python 標準函式庫**實作的確定性程式碼審查引擎：它讀取 Git 差異（暫存區 / 分支 / 補丁檔案），以 31 條內建規則對**每一行新增程式碼**做行級審查，輸出結構化、可定位、可設門檻的審查報告。

與依賴大型語言模型做「機率性審查」的工具不同，DiffGuard 是**確定性**的：相同的輸入永遠得到相同的結果，零網路請求、零第三方相依、零組態即可執行。它特別適合放進**提交前掛鉤**與 **CI 流水線**，把金鑰洩漏、注入風險、除錯殘留這類「機器一定能查出來」的問題擋在合併之前，把昂貴的人力審查留給真正需要思考的問題。

> 💡 名稱由來：Lens（鏡片）—— 幫你在 diff 上裝一枚不放过大模型噪音、只放大真實風險的鏡片。

## ✨ 特性

- 🧩 **零相依**：100% Python 標準函式庫（3.8+），連 `pip install` 都不需要，複製即用。
- 🌐 **離線優先**：不發出一個網路請求，程式碼與 diff 永不出本機，天然適合敏感儲存庫。
- 🎯 **行級精確**：自研 unified diff 解析器，保留新舊兩側行號，發現精確到行。
- 📚 **31 條內建規則**：涵蓋金鑰洩漏、危險 API、除錯殘留、程式碼品質、差異衛生五大類。
- 🚦 **CI 門檻**：`--fail-on blocker,high` 直接以結束代碼接入流水線，無需膠水腳本。
- 📄 **四種報告**：終端機彩色文字 / JSON / SARIF 2.1.0（GitHub Code Scanning 可直接消費）/ Markdown（貼進 PR）。
- 🔇 **精準抑制**：行內 `# diffguard:ignore[規則ID]` 註解，按行、按規則靜音，不污染全域組態。
- 📦 **雙形態**：`diffguard` CLI + `import diffguard` Python 函式庫，還能打包成單一 `.pyz` 檔案隨處執行。
- 🗂️ **整檔掃描**：`diffguard scan src/` 一鍵稽核陌生程式碼庫，不依賴 Git 歷史。
- 🌍 **雙語報告**：中英文報告文案自由切換，團隊協作更順暢。

## 🚀 快速開始

```bash
# 方式一：複製即用（推薦，零安裝）
git clone https://github.com/gitstq/DiffGuard.git
cd DiffGuard
python3 -m diffguard --staged        # 審查你的暫存區改動

# 方式二：pip 安裝
pip install git+https://github.com/gitstq/DiffGuard.git
diffguard --staged

# 方式三：單一檔案 .pyz（下載 Release 後直接執行）
./diffguard-1.0.0.pyz --staged
```

30 秒體驗：在任意檔案裡加一行 `API_KEY = "supersecret123456"` 並 `git add`，然後執行 `python3 -m diffguard --staged`，你會看到一條 ⛔ HIGH 級發現與修復建議，且結束代碼為 `1`。

## 📖 使用指南

### 🛠️ 五種審查來源

| 指令 | 場景 |
|------|------|
| `diffguard` | 審查工作區改動（HEAD vs 工作區） |
| `diffguard --staged` | 提交前檢查暫存區（掛鉤場景最常用） |
| `diffguard --branch main` | 審查當前分支相對 main 的全部改動（PR 場景） |
| `diffguard --diff fix.patch` | 審查補丁檔案（無需 Git 儲存庫） |
| `diffguard scan src/` | 整檔掃描（稽核陌生程式碼庫） |

### 📋 常用選項

```bash
diffguard --staged -f sarif -o report.sarif   # SARIF 報告寫入檔案
diffguard --staged --fail-on blocker,high     # 自訂 CI 門檻
diffguard --staged -f markdown                # 輸出可貼進 PR 的 Markdown
diffguard --staged --locale en                # 英文報告
diffguard --list-rules                        # 列出全部規則
```

### 📚 內建規則一覽（31 條）

**🔐 金鑰洩漏（Secret）**

| 規則 | 嚴重度 | 說明 |
|------|--------|------|
| DL-S01 | 🛑 blocker | 疑似 AWS Access Key ID 硬編碼 |
| DL-S02 | 🛑 blocker | 疑似私鑰內容提交進儲存庫 |
| DL-S03 | ⛔ high | 疑似硬編碼憑證賦值（密碼 / token / API key） |
| DL-S04 | 🛑 blocker | 疑似第三方服務權杖（Slack / GitHub / Google / OpenAI） |

**⚠️ 危險 API（Danger）**

| 規則 | 嚴重度 | 說明 |
|------|--------|------|
| DL-D01 | ⛔ high | `eval()` 動態執行 |
| DL-D02 | ⛔ high | `exec()` 動態執行（Python） |
| DL-D03 | ⛔ high | `subprocess` 使用 `shell=True`（Python） |
| DL-D04 | ⛔ high | `os.system()`（Python） |
| DL-D05 | ⛔ high | `pickle` 反序列化不可信資料（Python） |
| DL-D06 | ⚠️ medium | `yaml.load` 未指定 Loader（Python） |
| DL-D07 | ⛔ high | 停用 TLS 驗證 `verify=False`（Python） |
| DL-D08 | ⚠️ medium | 字串串接組合 SQL |
| DL-D09 | ⚠️ medium | 弱雜湊 MD5 / SHA-1（Python） |
| DL-D10 | ⛔ high | `document.write()`（JS/TS） |

**🐛 除錯殘留（Debug）**

| 規則 | 嚴重度 | 說明 |
|------|--------|------|
| DL-P01 | 🔹 low | `console.log` 殘留（JS/TS） |
| DL-P02 | ⚠️ medium | `debugger` 陳述式（JS/TS） |
| DL-P03 | 🔹 low | `print()` 除錯輸出（Python） |
| DL-P04 | ⚠️ medium | `breakpoint()` / `pdb.set_trace()`（Python） |
| DL-P05 | 🔹 low | `alert()` 殘留（JS/TS） |

**🧪 程式碼品質（Quality）**

| 規則 | 嚴重度 | 說明 |
|------|--------|------|
| DL-Q01 | ℹ️ info | TODO / FIXME 標記 |
| DL-Q02 | 🔹 low | 行長度超限（預設 120，可組態） |
| DL-Q03 | ⛔ high | 可變物件作為預設參數（Python） |
| DL-Q04 | ⚠️ medium | 裸 `except:`（Python） |
| DL-Q05 | 🔹 low | `== None` 應使用 `is None`（Python） |
| DL-Q06 | 🔹 low | `is True` / `is False`（Python，PEP 8） |
| DL-Q07 | 🔹 low | `var` 宣告（JS/TS） |
| DL-Q08 | ⚠️ medium | 安全場景使用 `random` 模組（Python） |

**🧹 差異衛生（Hygiene）**

| 規則 | 嚴重度 | 說明 |
|------|--------|------|
| DL-H01 | 🔹 low | 單次新增行數過多（>500 行），建議拆分提交 |
| DL-H02 | 🔹 low | 檔案結尾缺少換行符 |
| DL-H03 | 🔹 low | CRLF 換行混入 |
| DL-H04 | ℹ️ info | 建置產物 / 系統檔案入庫 |

### 🚦 接入 CI（GitHub Actions 範例）

```yaml
- name: DiffGuard review
  run: |
    pip install git+https://github.com/gitstq/DiffGuard.git
    python -m diffguard --branch origin/main --fail-on blocker,high
```

非零結束代碼即代表存在達到門檻的問題，流水線自動失敗。

### 🔇 抑制誤報

```python
# 示範程式碼，確需硬編碼：按行 + 按規則精準抑制
API_KEY = "supersecret123456"  # diffguard:ignore[DL-S03]
legacy_value = eval(expr)      # diffguard:ignore
```

- `# diffguard:ignore`（JS 用 `//`）：抑制本行全部規則；
- `# diffguard:ignore[DL-S03,DL-Q01]`：只抑制指定規則。

### ⚙️ 專案組態（`.diffguard.json`）

```json
{
  "fail_on": ["blocker", "high"],
  "max_line_length": 120,
  "disabled_rules": ["DL-P03"],
  "ignore_patterns": ["*.min.js", "vendor/*", "tests/*"]
}
```

### 🐍 作為 Python 函式庫使用

```python
from diffguard import parse_unified_diff, Engine, Config

diff_text = open("fix.patch", encoding="utf-8").read()
findings = Engine(Config(max_line_length=100)).review(parse_unified_diff(diff_text))

for f in findings:
    print(f.severity, f.rule_id, f"{f.file}:{f.lineno}", f.message_cn)
```

## 💡 設計迭代

- **v1.0.0**：首發版本。自研 unified diff 解析器（支援新增 / 刪除 / 重新命名 / 二進位 / no-newline 等真實場景）、31 條規則、雙語文案、四種報告格式、CI 門檻、行級抑制、`.diffguard.json` 專案組態、整檔掃描模式、zipapp 單一檔案打包。
- **Roadmap**：規則基線（只報新增問題）、更多語言規則（Go / Java）、`git blame` 歷史加權、編輯器外掛協定。

## 📦 打包部署

```bash
./scripts/build.sh
```

一鍵產出：

| 產物 | 說明 |
|------|------|
| `dist/diffguard-1.0.0.pyz` | 單一檔案可執行，`./diffguard-1.0.0.pyz --staged` 直接執行 |
| `dist/diffguard-1.0.0-source.zip` | 完整原始碼套件（含測試與文件） |
| `dist/SHA256SUMS.txt` | 全部產物的 SHA256 校驗和 |

無建置工具鏈要求，Python 3.8+ 即可完成打包。

## 🤝 貢獻

歡迎 Issue 與 PR！新增規則、修復誤報、補充文件都非常歡迎。請閱讀 [CONTRIBUTING.md](CONTRIBUTING.md) 了解提交規範與規則註冊流程。

## 📄 授權條款

本專案基於 [MIT License](LICENSE) 開源。
