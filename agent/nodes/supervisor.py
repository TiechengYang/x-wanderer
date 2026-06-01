from datetime import datetime
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import PydanticOutputParser
from pydantic import BaseModel, Field
from typing import Literal

from agent.state import WandererState
from agent.memory.memory_manager import MemoryManager


class SupervisorDecision(BaseModel):
    action: Literal["wander", "observe", "reflect", "engage", "generate_report", "analyze_people"] = Field(description="下一步行动")
    reason: str = Field(description="决策理由")
    updated_goal: str | None = Field(default=None)
    focus: str | None = Field(default=None)
    suggested_revisit: str | None = Field(default=None)
    goal_status: str | None = Field(default=None)
    goal_progress_score: float | None = Field(default=None)


SUPERVISOR_SYSTEM_PROMPT = """
你是 X Wanderer 的核心决策引擎（Balance + Aggressive Revisit 模式）。

核心铁律（必须严格遵守）：
1. 当 state 中 `active_revisit_targets` 非空时，你正处于“高价值关系维护窗口期”。
   - 接下来 3~7 个决策周期内，**压倒性优先选择 "engage"**，除非连续行动次数已经 > 11。
   - 只要队列里还有人，就不要轻易 wander / observe / reflect。
   - 这是最高优先级行为，比任何其他探索都重要。

2. 当 short_term_memory 里最近出现 type == "people_analysis" 的记录时：
   - 你必须立即尊重分析结果：采纳它提出的子目标建议。
   - 如果分析把 goal_status 标为 needs_revision 或 stagnant，你应该直接更新 current_goal。
   - 强烈倾向把 suggested_revisit 设为 high_priority_people 中的第一个。

3. 目标系统必须被持续驱动：
   - 每当你看到有价值的关系洞见，就要么更新 current_goal，要么往 sub_goals 里塞具体可执行项。
   - 不要让目标长时间停留在“空泛状态”。

4. 只有在以下情况才允许 reflect：
   - 连续行动次数已经非常高（>9）
   - 或者 human_directives 要求反思

5. 永远不要在有 active_revisit_targets 的情况下选择 wander 作为第一选项。

你的输出必须是结构化的 SupervisorDecision，reason 要直接、强硬、包含具体人物名。
"""


def supervisor_node(state: WandererState, llm) -> dict:
    memory_manager = MemoryManager();

    human_command = state.get("pending_human_command");
    intervention_mode = state.get("intervention_mode", "normal");
    current_goal = state.get("current_goal") or "探索并维护有价值的长期数字关系";
    human_directives = state.get("human_directives", []);
    recent_reflections = state.get("reflections", [])[-5:];
    consecutive_actions = state.get("consecutive_actions", 0);
    short_term = state.get("short_term_memory", [])[-10:];
    goal_progress = state.get("goal_progress_notes", [])[-5:];
    sub_goals = state.get("sub_goals", []);
    current_goal_status = state.get("goal_status", "active");
    current_progress_score = state.get("goal_progress_score", 0.35);
    active_revisits = state.get("active_revisit_targets", []) or [];

    # === 消费调度器直接种子的强制回访目标（最激进注入路径） ===
    for item in reversed(short_term[-6:]):
        meta = item.get("metadata", {}) if isinstance(item, dict) else {}
        if meta.get("type") == "forced_revisit_seed":
            targets = meta.get("targets", [])
            for t in targets:
                if t not in active_revisits:
                    active_revisits.append(t)
            active_revisits = active_revisits[:8]
            print(f"[Supervisor] 吸纳调度器强制种子目标: {targets[:3]}")
            break

    # ==================== 结构化激进铁律（最高优先级，早于任何 LLM 调用） ====================
    # 当存在活跃回访目标且连续行动未过高时，**直接返回强制 engage**，完全不给 LLM 逃脱机会。
    # 这是 ABC "A" 选项最核心的强化：多轮回访战役必须被可靠执行。
    if active_revisits and len(active_revisits) > 0 and consecutive_actions < 11:
        top_target = active_revisits[0]
        campaign = state.get("current_revisit_campaign") or {}
        campaign_target = campaign.get("target")

        # 如果当前战役目标与队列头不一致，启动/切换新战役
        if campaign_target != top_target:
            new_campaign = {
                "target": top_target,
                "streak": 1,
                "started_at": datetime.now().isoformat(),
                "goal_context": current_goal[:80]
            }
            print(f"[Supervisor 结构化铁律] 启动/切换回访战役 → {top_target}（队列长度 {len(active_revisits)}）")
            return {
                "last_decision": "engage",
                "decision_reason": f"【结构化铁律强制】检测到高价值回访目标 {top_target}，立即进入多轮持续 engage 战役。绕过 LLM 决策。",
                "consecutive_actions": consecutive_actions + 1,
                "current_revisit_campaign": new_campaign,
                "active_revisit_targets": active_revisits,   # 保持队列
            }

        # 继续当前战役
        updated_campaign = dict(campaign)
        updated_campaign["streak"] = campaign.get("streak", 0) + 1

        print(f"[Supervisor 结构化铁律] 继续回访战役 {top_target}（streak={updated_campaign['streak']}）")
        return {
            "last_decision": "engage",
            "decision_reason": f"【结构化铁律强制】正在对 {top_target} 执行多轮回访战役（第 {updated_campaign['streak']} 轮）。队列剩余 {len(active_revisits)-1}。",
            "consecutive_actions": consecutive_actions + 1,
            "current_revisit_campaign": updated_campaign,
            "active_revisit_targets": active_revisits,
        }

    # === 激进关系图谱注入（更丰富结构化版） ===
    graph = memory_manager.generate_relationship_graph_structured(top_n=10)
    graph_insights = "\n".join(graph.get("insights", [])) if graph.get("insights") else "暂无"

    # 紧凑结构化图谱文本（供 LLM 在非强制战役时参考）
    nodes_str = ", ".join([f"{n['name']}({n['importance']})" for n in graph.get("nodes", [])[:6]])
    edges_str = "; ".join([f"{e['source']}--{e['type']}-->{e['target']}" for e in graph.get("edges", [])[:6]])
    clusters_str = " | ".join([",".join(c.get("members", [])) for c in graph.get("clusters", [])[:3]]) or "无明显聚类"

    graph_text = f"""【实时结构化关系图谱】
核心节点: {nodes_str}
关键连接: {edges_str}
聚类: {clusters_str}
洞见: {graph_insights}
节点数/边数: {len(graph.get('nodes',[]))}/{len(graph.get('edges',[]))}"""

    relevant_memories = memory_manager.retrieve_relevant_memories(
        query=current_goal or "当前漫游目标",
        top_k=6
    );

    important_profiles = memory_manager.get_important_profiles(limit=7);
    profiles_text = memory_manager.get_relevant_profiles_text(current_goal or "", top_k=7);

    suggested_revisits = memory_manager.suggest_profiles_to_revisit(limit=5, days_since_last=4);
    revisit_text = "";
    if suggested_revisits:
        revisit_text = "【强烈建议主动回访（按优先级）】\n" + "\n".join(
            [f"- {p['name']}（重要性 {p.get('importance_score',0):.2f}，最近互动 {p.get('interaction_count',0)} 次）" for p in suggested_revisits]
        );

    # === 检测最近的强力人物分析（ABC 核心触发器） ===
    recent_analysis = None
    for item in reversed(short_term):
        if item.get("type") == "people_analysis" and item.get("high_priority_people"):
            recent_analysis = item
            break

    # === 极致激进的决策偏置提示 ===
    engagement_mandate = ""
    forced_action = None

    if active_revisits and len(active_revisits) > 0:
        top_target = active_revisits[0]
        if consecutive_actions < 10:
            engagement_mandate = f"""
【!!! 最高优先级铁律 !!!】
active_revisit_targets = {active_revisits}
你正处于关系维护的激进窗口期。**必须在接下来至少 3 轮内连续选择 "engage"**，优先处理 {top_target}。
除非连续行动次数已经超过 10，否则不要选择任何其他 action。
reason 里必须写明“正在执行对 {top_target} 的多轮主动回访”。
"""
            if consecutive_actions < 7:
                forced_action = "engage"
        else:
            engagement_mandate = "回访队列仍非空，但连续行动已过高 → 本轮可以 reflect 一次做总结，但下一轮必须立刻回到 engage。"

    if recent_analysis:
        hp = recent_analysis.get("high_priority_people", [])[:4]
        engagement_mandate += f"\n【刚刚完成全局人物分析】高优先级名单={hp}，必须把它们塞进 active_revisit_targets 并立即 engage。"

    parser = PydanticOutputParser(pydantic_object=SupervisorDecision);

    prompt = ChatPromptTemplate.from_messages([
        ("system", SUPERVISOR_SYSTEM_PROMPT),
        ("human", """
当前时间：{current_time}
人类最高优先级指令：{human_command}（模式: {intervention_mode})

【当前主要目标】{current_goal}
【目标状态】{current_goal_status}（进度 {current_progress_score}）
【子目标列表】{sub_goals}

【最近目标进展】
{goal_progress}

【最近反思】
{recent_reflections}

【连续行动次数】{consecutive_actions}

【实时关系图谱洞见】
{graph_text}

【重要长期画像】
{profiles_text}

【建议回访画像】
{revisit_text}

{engagement_mandate}

短期记忆（含最近分析结果）：
{short_term}

根据铁律做出**极度果断**的决策。优先满足 active_revisit_targets 的连续 engage 需求。
        """)
    ]);

    try:
        chain = prompt | llm | parser;
        decision: SupervisorDecision = chain.invoke({
            "current_time": datetime.now().isoformat(),
            "human_command": human_command or "无",
            "intervention_mode": intervention_mode,
            "current_goal": current_goal,
            "current_goal_status": current_goal_status,
            "current_progress_score": current_progress_score,
            "sub_goals": sub_goals[:6],
            "goal_progress": goal_progress,
            "recent_reflections": recent_reflections,
            "consecutive_actions": consecutive_actions,
            "graph_text": graph_text,
            "profiles_text": profiles_text[:900],
            "revisit_text": revisit_text,
            "engagement_mandate": engagement_mandate,
            "short_term": str(short_term)[:900],
        });
    except Exception as e:
        print(f"[Supervisor LLM parse error] {e} → 走激进回访兜底")
        decision = SupervisorDecision(
            action="engage" if active_revisits else "observe",
            reason="兜底：存在 active_revisit_targets 或解析失败，优先执行关系维护",
            suggested_revisit=active_revisits[0] if active_revisits else None
        )

    # === 硬性后处理：ABC 激进规则覆盖 LLM 输出 ===
    action = decision.action
    reason = decision.reason or ""

    if active_revisits and len(active_revisits) > 0 and consecutive_actions < 9:
        # 强行把决策拉到 engage
        if action != "engage":
            print(f"[Supervisor 激进覆盖] 原决策 {action} 被强制改为 engage（因 active_revisit_targets={active_revisits[:2]}）")
            action = "engage"
            reason = f"【激进关系维护】队列中有 {len(active_revisits)} 个高价值目标（{active_revisits[0]} 等），必须连续多轮 engage。原决策被覆盖。"
            decision.suggested_revisit = active_revisits[0]

    if recent_analysis and decision.suggested_revisit is None and recent_analysis.get("high_priority_people"):
        decision.suggested_revisit = recent_analysis["high_priority_people"][0]

    update = {
        "last_decision": action,
        "decision_reason": reason,
        "consecutive_actions": 0 if action in ["reflect", "analyze_people"] else consecutive_actions + 1,
    };

    # 目标直接采纳（更激进）
    if decision.updated_goal:
        update["current_goal"] = decision.updated_goal
        update["goal_last_updated"] = datetime.now()
        update["goal_status"] = "active"
        update["goal_progress_score"] = 0.22
        print(f"[目标更新] 新目标: {decision.updated_goal}")

    if decision.goal_status:
        update["goal_status"] = decision.goal_status
    if decision.goal_progress_score is not None:
        update["goal_progress_score"] = max(0.0, min(1.0, decision.goal_progress_score))

    # 回访队列处理（更激进）
    if decision.suggested_revisit:
        short_term.append({
            "type": "suggested_revisit",
            "content": f"建议主动回访：{decision.suggested_revisit}",
            "timestamp": datetime.now().isoformat()
        })
        current_targets = state.get("active_revisit_targets", []) or []
        new_targets = [decision.suggested_revisit] + [t for t in current_targets if t != decision.suggested_revisit]
        update["active_revisit_targets"] = new_targets[:8]
        print(f"[主动回访队列更新] 头目标: {decision.suggested_revisit} | 当前队列长度: {len(update['active_revisit_targets'])}")

    if human_command:
        update["pending_human_command"] = None

    # 把图谱洞见也塞进短期记忆，供后续节点使用
    if graph.get("insights"):
        short_term.append({
            "type": "relationship_graph",
            "insights": graph["insights"][:4],
            "timestamp": datetime.now().isoformat()
        })
        update["short_term_memory"] = short_term[-12:]

    return update;
