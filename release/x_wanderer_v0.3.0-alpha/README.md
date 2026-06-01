# X Wanderer - 数字漫游者 Agent（当前保存状态）

## 项目保存状态

本项目已保存为 **v0.3.0-alpha（123 完整版）**，核心能力已较为完整。

详细版本说明请查看：**VERSION.md**

---

## 一键操作（推荐）

### 一键安装环境

```bash
bash setup.sh
```

### 一键发布到 GitHub（最推荐）

```bash
bash publish_to_github.sh
```

这个脚本会自动完成：
- 生成干净的发布版本
- 初始化 Git（如需要）
- 使用 GitHub CLI 创建仓库
- 直接推送代码
- 可选创建 Release

**前提条件**：需要先安装 GitHub CLI 并登录：
```bash
brew install gh
gh auth login
```

---

## 其他常用命令

- 完整性测试：`python3 test_integrity.py`
- 干运行模式（无需 API Key）：`python3 main_dryrun.py`
- 正式运行：`python3 main.py`

使用手册请阅读：**使用手册.md**

---

项目已进入相对成熟的迭代阶段。
