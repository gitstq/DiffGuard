# 🤝 贡献指南 / Contributing

感谢关注 DiffGuard！欢迎以任何形式参与贡献：报告问题、完善规则、修复缺陷、补充文档。

## 🛠️ 本地开发

```bash
git clone https://github.com/gitstq/DiffGuard.git
cd DiffGuard
python3 -m unittest discover -s tests -v   # 运行测试（零依赖，无需安装）
python3 -m diffguard --staged               # 用 DiffGuard 审查你自己的改动
```

## 📏 约定

- **提交信息**遵循 Angular 规范：`feat:` / `fix:` / `docs:` / `refactor:` / `test:` / `chore:`。
- **新增规则**请同步：
  1. 在 `diffguard/rules.py` 的 `RULES` 表中注册（含中英文双语文案与修复建议）；
  2. 在 `tests/test_diffguard.py` 中补充命中用例与抑制用例；
  3. 在三份 README 的规则表中登记。
- **代码风格**：仅使用 Python 标准库（这是本项目的核心卖点，请勿引入第三方依赖）；
  中文注释与文档字符串，行宽 ≤ 120。
- **自测**：提交前确保 `python3 -m unittest discover -s tests` 全绿，
  且 `diffguard --staged` 对自己的改动无 blocker/high 发现。

## 🐛 反馈缺陷

请在 Issue 中附上：可复现的最小 diff 片段、期望行为与实际行为、运行环境（Python 版本 / 操作系统）。
