from datetime import datetime
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import PydanticOutputParser
from pydantic import BaseModel, Field
from typing import Literal

from agent.state import WandererState
from agent.memory.memory_manager import MemoryManager


class SupervisorDecision(BaseModel):
    action: Literal["wander", "observe", "reflect", "engage", "generate_report"] = Field(description="下一步行动")
    reason: str = Field(description="决策理由")
    updated_goal: str | None = Field(default=None)
    focus: str | None = Field(default=None)
    suggested_revisit: str | None = Field(default=None)
    goal_status: str | None = Field(default=None)
    goal_progress_score: float | None = Field(default=None, description="当前目标完成度评分 0.0~1.0")


SUPERVISOR_SYSTEM_PROMPT = """
你是一个有长期规划能力和关系意识的数字漫游者。

你非常擅长以下几点：
- 主动维护与重要画像的关系（当有高价值但长期未互动的画像时，优先考虑 engage 或 observe 进行回访）。
- 持续评估目标进展，并给出合理的完成度评分。
- 在必要时主动细化目标或提出子目标。
- 平衡探索（wander/observe）、维护（engage）、内省（reflect）和总结（generate_report）。

决策原则（强化版）：
- 如果存在高重要性画像且很久未互动 → 强烈倾向于 engage 或 observe 进行回访。
- 连续行动较多时优先 reflect。
- 目标停滞（stagnant）时优先 reflect 或 generate_report 进行复盘。
- 人类指令永远最高优先级。
"""


def supervisor_node(state: WandererState, llm) -> dict:
    memory_manager = MemoryManager()

    human_command = state.get("pending_human_command")
    intervention_mode = state.get("intervention_mode", "normal")
    current_goal = state.get("current_goal")
    human_directives = state.get("human_directives", [])
    recent_reflections = state.get("reflections", [])[-4:]
    consecutive_actions = state.get("consecutive_actions", 0)
    short_term = state.get("short_term_memory", [])[-6:]
    goal_progress = state.get("goal_progress_notes", [])[-3:]
    sub_goals = state.get("sub_goals", [])
    current_goal_status = state.get("goal_status", "active")
    current_progress_score = state.get("goal_progress_score", 0.4)

    relevant_memories = memory_manager.retrieve_relevant_memories(
        query=current_goal or "当前漫游目标",
        top_k=8
    )

    important_profiles = memory_manager.get_important_profiles(limit=6)
    profiles_text = memory_manager.get_relevant_profiles_text(current_goal or "", top_k=6)

    suggested_revisits = memory_manager.suggest_profiles_to_revisit(limit=4, days_since_last=5)
    revisit_text = ""
    if suggested_revisits:
        revisit_text = "当前强烈建议主动回访的画像（很久未互动但重要性高）：\n"
        for p in suggested_revisits:
            revisit_text += f"- {p['name']}（{p['type']}，重要性 {p['importance_score']:.2f}）\n"

    parser = PydanticOutputParser(pydantic_object=SupervisorDecision)

    prompt = ChatPromptTemplate.from_messages([
        ("system", SUPERVISOR_SYSTEM_PROMPT),
        ("human", """
当前时间：{current_time}
人类最高优先级指令：{human_command}（模式: {intervention_mode}）

【当前主要目标】
{current_goal}

【当前目标状态】
{current_goal_status}
当前完成度评分：{current_progress_score}

【子目标】
{sub_goals}

【最近目标进展】
{goal_progress}

【最近重要反思】
{recent_reflections}

【连续行动次数】{consecutive_actions}

【相关长期记忆】
{relevant_memories}

【重要长期画像】
{profiles_text}

【建议回访的画像】
{revisit_text}

短期记忆最新内容：
{short_term}

请做出平衡且更主动的决策。
特别注意：
- 如果存在高价值画像很久未互动，优先考虑 engage 或 observe 进行回访。
- 请评估当前目标的完成度并给出合理评分（0.0~1.0）。
- 如有必要，可更新目标状态或提出子目标。
        """)
    ])

    chain = prompt | llm | parser

    decision: SupervisorDecision = chain.invoke({
        "current_time": datetime.now().isoformat(),
        "human_command": human_command or "无",
        "intervention_mode": intervention_mode,
        "current_goal": current_goal,
        "current_goal_status": current_goal_status,
        "current_progress_score": current_progress_score,
        "sub_goals": sub_goals,
        "goal_progress": goal_progress,
        "recent_reflections": recent_reflections,
        "consecutive_actions": consecutive_actions,
        "relevant_memories": str(relevant_memories)[:1300],
        "profiles_text": profiles_text,
        "revisit_text": revisit_text,
        "short_term": str(short_term)[:900],
    })

    update = {
        "last_decision": decision.action,
        "decision_reason": decision.reason,
        "consecutive_actions": 0 if decision.action == "reflect" else consecutive_actions + 1,
    }

    if decision.updated_goal:
        update["current_goal"] = decision.updated_goal
        update["goal_last_updated"] = datetime.now()
        update["goal_status"] = "active"
        update["goal_progress_score"] = 0.3
        print(f"[目标更新] 新目标: {decision.updated_goal}")

    if decision.goal_status:
        update["goal_status"] = decision.goal_status
        print(f"[目标状态] 更新为: {decision.goal_status}")

    if decision.goal_progress_score is not None:
        update["goal_progress_score"] = max(0.0, min(1.0, decision.goal_progress_score))

    if decision.suggested_revisit:
        short_term.append({
            "type": "suggested_revisit",
            "content": f"建议主动回访：{decision.suggested_revisit}",
            "timestamp": datetime.now().isoformat()
        })
        update["short_term_memory"] = short_term[-18:]
        update["active_revisit_targets"] = [decision.suggested_revisit] + state.get("active_revisit_targets", [])
        print(f"[主动回访建议] {decision.suggested_revisit}")

    if human_command:
        update["pending_human_command"] = None

    return update
