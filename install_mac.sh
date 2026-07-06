#!/bin/bash
# Toolix macOS 一键安装脚本
# 用法:
#   bash install_mac.sh             # 装到 /Applications(可能提示 sudo 密码)
#   bash install_mac.sh --user      # 装到 ~/Applications(无需 sudo)
#   INSTALL_DIR=/path bash install_mac.sh   # 自定义安装目录
# 产物: <安装目录>/Toolix.app    可重复运行(幂等),再次运行即更新到最新代码。

set -euo pipefail

# ---------- 彩色输出 ----------
if [[ -t 1 ]]; then
    C_CYAN=$'\033[36m'; C_GREEN=$'\033[32m'; C_YELLOW=$'\033[33m'
    C_RED=$'\033[31m'; C_BOLD=$'\033[1m'; C_RST=$'\033[0m'
else
    C_CYAN=""; C_GREEN=""; C_YELLOW=""; C_RED=""; C_BOLD=""; C_RST=""
fi

step() { echo "${C_CYAN}${C_BOLD}=== $* ===${C_RST}"; }
ok()   { echo "${C_GREEN}✓ $*${C_RST}"; }
warn() { echo "${C_YELLOW}! $*${C_RST}" >&2; }
die()  { echo "${C_RED}✗ $*${C_RST}" >&2; exit 1; }

# ---------- 脚本目录(项目根)----------
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# ---------- 0. 平台检测 ----------
step "平台检测"
if [[ "$(uname)" != "Darwin" ]]; then
    die "此脚本仅用于 macOS。Windows 请用 build.ps1。"
fi
ok "macOS $(sw_vers -productVersion 2>/dev/null || echo '')"

# ---------- 1. 解析参数 / 安装目录 ----------
INSTALL_DIR="${INSTALL_DIR:-}"
USER_INSTALL=0
for arg in "$@"; do
    case "$arg" in
        --user) USER_INSTALL=1 ;;
        -h|--help) sed -n '2,8p' "${BASH_SOURCE[0]}"; exit 0 ;;
        *) die "未知参数: $arg(可用: --user)" ;;
    esac
done
if [[ -z "$INSTALL_DIR" ]]; then
    if [[ "$USER_INSTALL" -eq 1 ]]; then
        INSTALL_DIR="$HOME/Applications"
    else
        INSTALL_DIR="/Applications"
    fi
fi
APP_PATH="$INSTALL_DIR/Toolix.app"

# ---------- 2. Python 检测 ----------
step "检测 Python 3.10+"
if ! command -v python3 >/dev/null 2>&1; then
    die "未找到 python3。请先安装: brew install python@3.11"
fi
PY_VER=$(python3 -c 'import sys; print("%d.%d" % sys.version_info[:2])')
PY_MAJOR="${PY_VER%%.*}"; PY_MINOR="${PY_VER#*.}"
if [[ "$PY_MAJOR" -lt 3 || ( "$PY_MAJOR" -eq 3 && "$PY_MINOR" -lt 10 ) ]]; then
    die "Python $PY_VER 版本过低,需要 3.10+(代码用了 PEP 604 union 语法)。请: brew install python@3.11"
fi
ok "Python $PY_VER"

# ---------- 3. 建 venv ----------
step "准备虚拟环境 (.venv)"
if [[ ! -d ".venv" ]]; then
    python3 -m venv .venv
    ok "已创建 .venv"
else
    ok ".venv 已存在,复用"
fi
# activate 脚本在 set -u 下偶尔因未设变量报错,临时放宽
set +u
# shellcheck disable=SC1091
source .venv/bin/activate
set -u

# ---------- 4. 装依赖 ----------
step "安装依赖"
pip install --upgrade pip --quiet
pip install -r requirements.txt --quiet
pip install pyinstaller --quiet
ok "依赖就绪"

# ---------- 5. 杀旧进程 ----------
step "清理旧进程"
if killall Toolix 2>/dev/null; then
    ok "已结束运行中的 Toolix"
else
    ok "无运行中的 Toolix"
fi

# ---------- 6. 打包 ----------
step "PyInstaller 打包 (--onedir --windowed)"
# 不用 Toolix.spec(那是 Windows 的 icon.ico)。命令与 build_mac.sh 一致。
# TODO: mac dock 图标(.icns)暂未提供,运行时窗口图标由 main.py:_make_icon() 提供。
pyinstaller -y --onedir --windowed \
    --name "Toolix" \
    --exclude-module PyQt5 \
    main.py
BUILT_APP="$SCRIPT_DIR/dist/Toolix/Toolix.app"
if [[ ! -d "$BUILT_APP" ]]; then
    die "打包未生成 $BUILT_APP"
fi
ok "已生成 $BUILT_APP"

# ---------- 7. 安装到目标目录 ----------
step "安装到 $APP_PATH"
mkdir -p "$INSTALL_DIR" 2>/dev/null || true
if [[ -d "$APP_PATH" ]]; then
    if [[ -w "$INSTALL_DIR" ]]; then
        rm -rf "$APP_PATH"
    else
        warn "$INSTALL_DIR 需要管理员权限,将提示输入密码"
        sudo rm -rf "$APP_PATH"
    fi
fi
if [[ -w "$INSTALL_DIR" ]]; then
    cp -R "$BUILT_APP" "$INSTALL_DIR/"
else
    warn "$INSTALL_DIR 需要管理员权限,将提示输入密码"
    sudo cp -R "$BUILT_APP" "$INSTALL_DIR/"
fi
ok "已安装: $APP_PATH"

# ---------- 8. 去 Gatekeeper 隔离 ----------
step "去除 quarantine 标记(避免 Gatekeeper 拦截未签名 app)"
# 自建未签名 app 首次打开会被 Gatekeeper 拦;去掉 quarantine 即可直接 open。
if [[ -w "$APP_PATH" ]]; then
    xattr -dr com.apple.quarantine "$APP_PATH" 2>/dev/null || true
else
    sudo xattr -dr com.apple.quarantine "$APP_PATH" 2>/dev/null || true
fi
ok "已处理"

# ---------- 9. 启动 ----------
step "启动 Toolix"
open "$APP_PATH"

echo ""
echo "${C_GREEN}${C_BOLD}✓ 安装完成${C_RST}"
echo "  位置: $APP_PATH"
echo "  首次启动会弹出「配置目录选择」对话框 —— 选一个目录存放 toolix.json。"
echo "  之后想改配置路径:在面板搜索框输入 ${C_BOLD}setting${C_RST} 回车。"
echo "  重新运行本脚本即可更新到最新版。"
