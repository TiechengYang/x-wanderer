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
VERSION="v0.4.1-alpha"

echo ""
echo "即将发布/更新仓库: $REPO_NAME ($VISIBILITY) 版本 $VERSION"

# 生成干净发布版本
echo ""
echo "📦 正在生成干净发布版本 (release/x_wanderer_${VERSION}) ..."
RELEASE_DIR="release/x_wanderer_${VERSION}"
rm -rf "$RELEASE_DIR"
mkdir -p "$RELEASE_DIR"

cp -r agent config platforms commands utils "$RELEASE_DIR/"
cp main.py main_dryrun.py setup.sh test_integrity.py publish_to_github.sh requirements.txt .env.example .gitignore README.md 使用手册.md VERSION.md "$RELEASE_DIR/" 2>/dev/null || true

# 额外复制新增的验证脚本
cp test_verify_aggressive.py "$RELEASE_DIR/" 2>/dev/null || true

echo "✅ 发布版本已准备: $RELEASE_DIR"

# 初始化 Git（如需要）
if [ ! -d ".git" ]; then
    echo "🔧 初始化 Git..."
    git init
    git add .
    git commit -m "Initial commit: X Wanderer ${VERSION} (ABC 结构化铁律强化版)"
fi

# 创建并推送 / 更新
echo ""
echo "🚀 正在推送更新到 GitHub..."

# 先确保远程存在
if ! git remote get-url origin &>/dev/null; then
    USER=$(gh api user --jq .login)
    git remote add origin "https://github.com/$USER/$REPO_NAME.git" 2>/dev/null || true
fi

git add .
git commit -m "chore: v0.4.1-alpha 核心逻辑重新梳理清理版

- 移除过度工程化的理想目标画像生成和复杂偏好定制上下文（用户反馈臃肿）
- 聚焦核心：analyze_people 激进驱动 + Supervisor 结构化铁律早返回强制多轮战役
- 清理 state、engage、supervisor、memory_manager 中的冗余字段和逻辑
- 文档同步更新，强调干净、果断的关系维护主循环
- 干运行现在能更清晰演示铁律强制行为" || echo "没有新变更或 commit 失败"

if gh repo create "$REPO_NAME" $VISIBILITY --source=. --remote=origin --push 2>/dev/null; then
    echo ""
    echo "========================================"
    echo "✅ 新仓库创建并发布成功！"
    USER=$(gh api user --jq .login)
    echo "仓库地址: https://github.com/$USER/$REPO_NAME"
    echo "========================================"
else
    echo "仓库已存在，推送更新..."
    git push -u origin main || git push -u origin master || git push
    echo ""
    echo "✅ 代码已推送到 GitHub"
    USER=$(gh api user --jq .login)
    echo "仓库地址: https://github.com/$USER/$REPO_NAME"
    echo "建议手动在 GitHub 创建 Release: ${VERSION}"
fi
