from datetime import datetime
from agent.state import WandererState
from agent.memory.memory_manager import MemoryManager


def reflect_node(state: WandererState, llm=None) -> dict:
    """
    重度记忆核心节点（重要关系总结 + 目标评估增强版）
    定期系统性回顾重要画像，生成关系总结
    """
    memory_manager = MemoryManager()

    current_goal = state.get("current_goal", "")
    short_term_memory = state.get("short_term_memory", [])[-8:]
    recent_reflections = state.get("reflections", [])[-4:]
    consecutive_actions = state.get("consecutive_actions", 0)
    goal_progress = state.get("goal_progress_notes", [])
    sub_goals = state.get("sub_goals", [])

    # 获取重要画像
    important_profiles = memory_manager.get_important_profiles(limit=10)
    profiles_text = ""
    if important_profiles:
        profiles_text = "你当前积累的最重要长期印象：\n"
        for p in important_profiles:
            insights = "; ".join(p["key_insights"][:3]) if p["key_insights"] else "暂无"
            profiles_text += f"- {p['name']}（{p['type']}）：{p['summary']} | 关键印象：{insights}\n"

    reflection_prompt = f"""
你是一个正在进行长期数字漫游的 AI。

当前主要目标：
{current_goal}

子目标：
{sub_goals}

最近目标进展记录：
{goal_progress[-3:] if goal_progress else "暂无"}

最近连续行动次数：{consecutive_actions}

最近的短期记忆：
{short_term_memory}

最近的反思：
{recent_reflections}

{profiles_text}

请完成以下任务：

【常规反思 + 目标评估】
1. 总结最近最有价值的观察和洞见。
2. 评估这些活动对当前目标的实际推进情况。
3. 思考这些观察与你积累的长期画像的关联。

【重要关系总结】（必须完成此部分）
请挑选 3-5 个你认为目前最重要的长期印象（人物或话题），为每个写一段结构化的关系总结，包含：
- 当前印象
- 为什么它对你重要
- 最近是否有新观察/互动
- 是否建议未来更多关注或回访

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

    reflections = state.get("reflections", [])
    reflections.append(reflection_content)

    # 更新目标进展
    new_progress = f"[{datetime.now().strftime('%m-%d')}] 完成了重要关系回顾与目标评估。"
    goal_progress.append(new_progress)

    return {
        "last_decision": "reflect",
        "decision_reason": "完成了高质量反思（含重要关系总结 + 目标评估），更新了长期记忆和目标进展。",
        "reflections": reflections[-12:],
        "goal_progress_notes": goal_progress[-12:],
        "consecutive_actions": 0,
    }
