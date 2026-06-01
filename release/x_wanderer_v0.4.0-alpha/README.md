# X Wanderer - 数字漫游者 Agent（ABC 结构化铁律强化版）

## v0.4.0-alpha 重大强化（本次更新重点）

**核心突破**：从“倾向于多轮回访”进化到**“结构化铁律强制多轮回访战役”** —— 一旦分析出高价值目标，就几乎不可能逃脱连续多轮 engage。

### 1. 结构化铁律 + 早返回机制（最激进改动）
- Supervisor 在函数最开始就检查 `active_revisit_targets`
- 只要队列非空 + 连续行动未过高 → **直接 return 强制 "engage"**，完全不调用 LLM、不走提示词
- 同时维护显式 `current_revisit_campaign`（target + streak），让战役状态成为一等公民

### 2. 更强的 analyze → 目标 → 行动闭环
- `analyze_people`（极致激进版）会：
  - 一次性把所有高优先级人物灌入回访队列（最多8个）
  - 直接重写 `current_goal` + 大量注入具体子目标
  - 把 `goal_status` 设为 `needs_revision`，进度分拉到极低
- Engage 每轮成功互动后**立即自动写入结构化关系总结**，供下一次分析使用

### 3. Scheduler 直接种子注入
- 不再只是建议做分析
- 检测到高价值 stale 画像时，会直接通过 `seed_forced_revisit_targets` 把它们推进系统

### 4. 可观测性大幅提升
- 干运行仪表盘现在会高亮显示“当前回访战役：xxx | 已连续 N 轮”
- 新增 `test_verify_aggressive.py` 可快速验证整个激进链路

---

## 历史 123 优化（已包含）

**1. 更激进的连续主动回访**  
**2. 更强大的关系图谱可视化**  
**3. 智能条件触发人物分析**

---

**当前 Agent 已经具备“发现高价值关系后会强迫自己持续维护多轮”的激进性格。**

这是目前为止最接近“有长期社交战略”的版本。

### 快速开始

```bash
# 测试模式（强烈推荐先看效果）
python3 main_dryrun.py

# 手动触发最强链路
echo "/analyze_people" > commands/human_input.txt
python3 main_dryrun.py
```

真实运行请先 `bash setup.sh` 并配置 `.env`。
