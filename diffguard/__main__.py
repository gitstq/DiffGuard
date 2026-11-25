# -*- coding: utf-8 -*-
"""DiffGuard · 命令行入口（``python -m diffguard`` 及 zipapp .pyz 运行）。

使用绝对导入以同时支持包运行与 zipapp 单文件运行。
"""

from diffguard.cli import main

if __name__ == "__main__":
    raise SystemExit(main())
