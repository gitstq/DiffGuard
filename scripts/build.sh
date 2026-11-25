#!/usr/bin/env bash
# DiffGuard 一键打包脚本 · 产出可直接运行的 .pyz（zipapp）与源码 zip
# 用法: ./scripts/build.sh          （零依赖，仅需要 Python 3.8+）
set -euo pipefail

cd "$(dirname "$0")/.."
VERSION=$(python3 -c "import diffguard; print(diffguard.__version__)")  # diffguard:ignore[DL-P03]
DIST="dist"
PYZ="diffguard-${VERSION}.pyz"
ZIP="diffguard-${VERSION}-source.zip"

echo "==> 打包 diffguard ${VERSION}"
rm -rf "$DIST" && mkdir -p "$DIST"

# 1) zipapp：单文件可执行，零安装（stage 目录 = 包 + 根级 __main__.py）
STAGE=$(mktemp -d)
cp -r diffguard "$STAGE/diffguard"
cat > "$STAGE/__main__.py" <<'EOF'
from diffguard.cli import main
raise SystemExit(main())
EOF
python3 -m zipapp "$STAGE" -p "/usr/bin/env python3" -o "$DIST/$PYZ"
rm -rf "$STAGE"
chmod +x "$DIST/$PYZ"

# 2) 源码 zip（含 tests / 文档 / 配置；需要 git 仓库，否则跳过）
if git rev-parse --git-dir > /dev/null 2>&1; then
    git archive --format=zip --prefix="diffguard-${VERSION}/" -o "$DIST/$ZIP" HEAD
else
    echo "    (非 git 仓库，跳过源码 zip)"
fi

# 3) SHA256 校验和（对实际存在的产物）
( cd "$DIST" && sha256sum *.pyz *.zip > SHA256SUMS.txt 2>/dev/null || sha256sum *.pyz > SHA256SUMS.txt )

echo "==> 产物:"
ls -la "$DIST"
echo "==> 冒烟验证:"
"$DIST/$PYZ" --version
"$DIST/$PYZ" --list-rules | head -3
echo "==> 打包完成 ✅"
