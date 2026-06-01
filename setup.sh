#!/bin/bash

# X Wanderer 一键安装脚本
# 用法: bash setup.sh

set -e

echo "========================================"
echo "  X Wanderer - 一键安装脚本"
echo "========================================"

# 检查 Python3
if ! command -v python3 &> /dev/null; then
    echo "❌ 未找到 python3，请先安装 Python 3.10+"
    exit 1
fi

PYTHON_VERSION=$(python3 -c 'import sys; print(".".join(map(str, sys.version_info[:2])))')
echo "✅ 检测到 Python $PYTHON_VERSION"

# 创建虚拟环境
if [ ! -d "venv" ]; then
    echo "📦 创建虚拟环境..."
    python3 -m venv venv
else
    echo "✅ 虚拟环境已存在"
fi

# 激活虚拟环境
source venv/bin/activate

# 升级 pip
echo "📦 升级 pip..."
pip install --upgrade pip -q

# 安装依赖
echo "📦 安装项目依赖..."
pip install -r requirements.txt -q

# 创建必要目录
echo "📁 创建数据目录..."
mkdir -p data/chroma data/sqlite commands

# 创建人类指令文件（如果不存在）
if [ ! -f "commands/human_input.txt" ]; then
    touch commands/human_input.txt
    echo "✅ 已创建 commands/human_input.txt"
fi

# 复制环境变量模板
if [ ! -f ".env" ]; then
    if [ -f ".env.example" ]; then
        cp .env.example .env
        echo "✅ 已复制 .env.example -> .env"
        echo "⚠️  请手动编辑 .env 文件，填入 LLM API Key 和 X Bearer Token"
    else
        echo "⚠️  未找到 .env.example，请手动创建 .env 文件"
    fi
else
    echo "✅ .env 文件已存在"
fi

echo ""
echo "========================================"
echo "✅ 安装完成！"
echo ""
echo "下一步操作："
echo "1. 编辑 .env 文件，填入必要的 API Key"
echo "2. 运行测试：  python3 test_integrity.py"
echo "3. 启动 Agent： python3 main.py"
echo ""
echo "提示：激活虚拟环境命令："
echo "  source venv/bin/activate"
echo "========================================"
