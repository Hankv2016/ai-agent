#!/usr/bin/env bash
# AI 对话客户端 启动脚本（Linux / macOS）
#
# 用法：
#   ./run.sh                交互式选择 GUI / CLI
#   ./run.sh gui            直接启动图形界面
#   ./run.sh cli -i         命令行交互模式
#   ./run.sh cli "问题"      单次问答
#   ./run.sh -m gpt-4 -k sk-xxx "问题"   透传参数给 CLI（-m/-u/-k/-i 等）
#
# 说明：首参数为 gui/cli 时用于选择模式；其余（含 -i/-m/问题文本）会透传给 cli.py。
set -u

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

PYTHON="${PYTHON:-python3}"

# ---------- 依赖检查 ----------
if ! "$PYTHON" -c "import PyQt5, openai" >/dev/null 2>&1; then
    echo "[提示] 未检测到依赖 (PyQt5 / openai)。"
    read -r -p "是否现在安装依赖？(y/N) " ans
    case "$ans" in
        y|Y) "$PYTHON" -m pip install -r requirements.txt ;;
        *) echo "请先执行: $PYTHON -m pip install -r requirements.txt"; exit 1 ;;
    esac
fi

# ---------- 参数解析 ----------
MODE=""
if [ $# -gt 0 ]; then
    case "$1" in
        gui) MODE="gui" ;;
        cli) MODE="cli"; shift ;;
        *)   MODE="cli" ;;   # 其余（含 -i/-m/问题文本）按 CLI 透传
    esac
fi

if [ -z "$MODE" ]; then
    echo "选择模式:"
    echo "  [1] GUI"
    echo "  [2] CLI interactive"
    read -r -p "输入 1 或 2: " choice
    case "$choice" in
        1) MODE="gui" ;;
        2) MODE="cli"; set -- -i ;;
        *) echo "无效输入"; exit 1 ;;
    esac
fi

if [ "$MODE" = "gui" ]; then
    "$PYTHON" gui.py
else
    "$PYTHON" cli.py "$@"
fi
