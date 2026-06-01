#!/bin/bash

# ======================================================
# X Wanderer - 一键生成并发布到 GitHub (非交互最终版)
# ======================================================

set -e

echo "========================================"
echo "  X Wanderer - 一键发布到 GitHub"
echo "========================================"
echo ""

# 确保 gh 已安装
if ! command -v gh &> /dev/null; then
    echo "❌ 未检测到 gh"
    if [[ "$(uname -s)" == "Darwin" ]] && command -v brew &> /dev/null; then
        echo "正在使用 Homebrew 安装 gh..."
        brew install gh
    else
        echo "请手动安装 gh 后再运行"
        exit 1
    fi
fi

echo "✅ GitHub CLI 已安装"

# 确保已登录
if ! gh auth status &> /dev/null; then
    echo "正在登录 GitHub..."
    gh auth login
fi

echo "✅ 已登录: $(gh api user --jq .login)"

# 使用固定推荐值（一键模式）
REPO_NAME="x-wanderer"
VISIBILITY="--public"

echo ""
echo "即将发布仓库: $REPO_NAME ($VISIBILITY)"

# 生成干净发布版本
echo ""
echo "📦 正在生成干净发布版本..."
RELEASE_DIR="release/x_wanderer_v0.3.0-alpha"
rm -rf "$RELEASE_DIR"
mkdir -p "$RELEASE_DIR"

cp -r agent config platforms commands utils "$RELEASE_DIR/"
cp main.py main_dryrun.py setup.sh test_integrity.py publish_to_github.sh requirements.txt .env.example .gitignore README.md 使用手册.md VERSION.md "$RELEASE_DIR/" 2>/dev/null || true

echo "✅ 发布版本已准备: $RELEASE_DIR"

# 初始化 Git
if [ ! -d ".git" ]; then
    echo "🔧 初始化 Git..."
    git init
    git add .
    git commit -m "Initial commit: X Wanderer v0.3.0-alpha (123完整版 + 主动画像系统)"
fi

# 创建并推送
echo ""
echo "🚀 正在创建 GitHub 仓库并推送..."

if gh repo create "$REPO_NAME" $VISIBILITY --source=. --remote=origin --push; then
    echo ""
    echo "========================================"
    echo "✅ 发布成功！"
    USER=$(gh api user --jq .login)
    echo "仓库地址: https://github.com/$USER/$REPO_NAME"
    echo "========================================"
else
    echo "⚠️ 可能仓库已存在，尝试推送..."
    git push -u origin main || git push -u origin master
fi
