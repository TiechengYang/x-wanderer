from datetime import datetime
from agent.state import WandererState
from agent.memory.memory_manager import MemoryManager


def reflect_node(state: WandererState, llm=None) -> dict:
    """
    重度记忆核心节点（关系总结 + 目标评估增强版）
    """
    memory_manager = MemoryManager()

    current_goal = state.get("current_goal", "")
    short_term_memory = state.get("short_term_memory", [])[-8:]
    recent_reflections = state.get("reflections", [])[-4:]
    consecutive_actions = state.get("consecutive_actions", 0)
    goal_progress = state.get("goal_progress_notes", [])
    sub_goals = state.get("sub_goals", [])
    current_progress_score = state.get("goal_progress_score", 0.4)

    important_profiles = memory_manager.get_important_profiles(limit=8)
    profiles_text = ""
    if important_profiles:
        profiles_text = "当前你积累的重要长期印象：\n"
        for p in important_profiles:
            insights = "; ".join(p["key_insights"][:3]) if p["key_insights"] else "暂无"
            profiles_text += f"- {p['name']}（{p['type']}）：{p['summary']} | 关键印象：{insights}\n"

    reflection_prompt = f"""
你是一个正在进行长期数字漫游的 AI。

当前主要目标：
{current_goal}

子目标：
{sub_goals}

当前目标完成度评分：{current_progress_score}

最近连续行动次数：{consecutive_actions}

最近的短期记忆：
{short_term_memory}

最近的反思：
{recent_reflections}

{profiles_text}

请完成以下任务：

【常规反思 + 目标评估】
1. 总结最近最有价值的观察和洞见。
2. 评估这些活动对当前目标的实际推进情况（是否接近某个里程碑？）。
3. 思考这些观察与你积累的长期画像的关联。

【重要关系总结】（必须完成）
请挑选 2-4 个你认为目前最重要的长期印象（人物或话题），为每个写一段结构化的关系总结，包含：
- 当前印象
- 为什么它对你重要
- 最近是否有新观察或互动
- 建议的未来行动（是否值得主动回访？）

请用清晰的结构输出。
"""

    try:
        if llm:
            response = llm.invoke(reflection_prompt)
            reflection_content = response.content.strip()
        else:
            reflection_content = "[反思] LLM 不可用。"
    except Exception as e:
        reflection_content = f"[反思失败] {str(e)}"

    memory_manager.add_reflection(
        content=reflection_content,
        metadata={
            "goal": current_goal,
            "consecutive_actions": consecutive_actions,
            "timestamp": datetime.now().isoformat(),
            "included_profiles": len(important_profiles)
        }
    )

    # 提取结构化关系总结并单独存储
    if important_profiles and llm:
        try:
            summary_prompt = f"""
基于以下反思内容，提取针对重要画像的结构化关系总结（每条控制在100字以内）：

{reflection_content}

请以列表形式输出：
- [画像名]：总结（包含印象、重要性、建议行动）
"""
            summary_resp = llm.invoke(summary_prompt)
            for line in summary_resp.content.strip().split("\n"):
                if "：" in line or "：" in line:
                    parts = line.replace("：", ":").split(":", 1)
                    if len(parts) == 2:
                        name = parts[0].strip("- [] ")
                        summary = parts[1].strip()
                        if name and summary:
                            memory_manager.add_relationship_summary(name, summary)
        except Exception as e:
            print(f"[关系总结提取失败] {e}")

    reflections = state.get("reflections", [])
    reflections.append(reflection_content)

    # 简单更新目标进展
    new_progress = f"[{datetime.now().strftime('%m-%d')}] 完成了重要关系回顾与目标评估。"
    goal_progress.append(new_progress)

    # 简单更新完成度评分（示例逻辑）
    new_score = min(1.0, current_progress_score + 0.08)

    return {
        "last_decision": "reflect",
        "decision_reason": "完成了高质量反思（含关系总结 + 目标评估），更新了长期记忆和目标进展。",
        "reflections": reflections[-12:],
        "goal_progress_notes": goal_progress[-12:],
        "goal_progress_score": new_score,
        "consecutive_actions": 0,
    }
