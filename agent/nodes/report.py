from datetime import datetime
from agent.state import WandererState
from agent.memory.memory_manager import MemoryManager


def report_node(state: WandererState, llm=None) -> dict:
    """
    智能报告生成节点（使用 LLM）
    """
    memory_manager = MemoryManager()
    current_goal = state.get("current_goal", "")
    reflections = state.get("reflections", [])[-8:]
    short_term = state.get("short_term_memory", [])[-6:]

    if llm and reflections:
        prompt = f"""
你是一个数字漫游者 AI。

当前漫游目标：{current_goal}

以下是你最近的几次重要反思：
{chr(10).join(['- ' + r for r in reflections[-5:]])}

最近的短期观察：
{short_term}

请生成一份结构化的阶段性漫游报告，包含以下部分：
1. 目标回顾
2. 核心洞见（2-4 条）
3. 值得持续关注的主题
4. 下一步建议

报告要简洁、专业、有洞察力，使用中文。
"""

        try:
            response = llm.invoke(prompt)
            report_content = response.content.strip()
        except Exception as e:
            report_content = f"报告生成失败：{e}"
    else:
        # 降级方案
        report_content = f"""【数字漫游阶段报告】{datetime.now().strftime('%Y-%m-%d %H:%M')}

当前目标：{current_goal}

近期关键反思数量：{len(reflections)}
短期记忆条目：{len(short_term)}

（LLM 不可用，使用简化报告）
"""

    # 存入记忆
    memory_manager.add_episodic_memory(
        content=report_content,
        metadata={"type": "report", "timestamp": datetime.now().isoformat()}
    )

    print("\n" + "=" * 60)
    print(report_content)
    print("=" * 60 + "\n")

    return {
        "last_decision": "generate_report",
        "decision_reason": "已生成高质量阶段性漫游报告。",
        "pending_report": report_content
    }
