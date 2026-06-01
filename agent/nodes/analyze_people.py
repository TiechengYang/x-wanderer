from agent.state import WandererState
from agent.memory.memory_manager import MemoryManager


def analyze_people_node(state: WandererState, llm=None) -> dict:
    """
    人物全局分析节点（A 极致激进版）
    分析完成后：
    - 直接把高优先级人物**全部**塞进 active_revisit_targets（最多 8 个）
    - 强行改写 current_goal + 大量注入 sub_goals
    - 把 goal_status 直接设为 "needs_revision" + 低进度分
    - 把完整结构化图谱 + 分析结果塞进 short_term，强制 supervisor 下一轮进入 engage 狂飙
    """
    memory_manager = MemoryManager()
    current_goal = state.get("current_goal", "探索并维护有价值的长期数字关系")

    print("[AnalyzePeople] ========== 全局人物分析（极致激进模式）启动 ==========")

    analysis_result = memory_manager.analyze_all_people(llm=llm, top_n=18)
    graph_structured = memory_manager.generate_relationship_graph_structured(top_n=10)

    report = analysis_result.get("report", "")
    suggested_sub_goals = analysis_result.get("suggested_sub_goals", [])
    goal_adjustment = analysis_result.get("goal_adjustment_suggestion")
    high_priority = analysis_result.get("high_priority_people", [])

    # === 极致激进：把所有高优先级人物一次性全部灌进队列 ===
    active_targets = state.get("active_revisit_targets", []) or []
    merged = []
    for p in high_priority:
        if p not in merged:
            merged.append(p)
    for p in active_targets:
        if p not in merged:
            merged.append(p)
    updated_targets = merged[:8]

    # === 极致激进：直接重写目标系统 ===
    new_sub_goals = []
    current_sub_goals = state.get("sub_goals", []) or []
    for g in suggested_sub_goals:
        if g and g not in current_sub_goals and g not in new_sub_goals:
            new_sub_goals.append(g)

    # 至少塞 2 个强关系维护子目标
    for hp in high_priority[:3]:
        sg = f"对 {hp} 发起连续 2-4 轮深度互动，提取至少 3 条新洞见并更新其长期画像"
        if sg not in current_sub_goals and sg not in new_sub_goals:
            new_sub_goals.append(sg)

    # 目标改写
    new_goal = current_goal
    if goal_adjustment and len(goal_adjustment) > 15:
        new_goal = f"围绕高价值关系进行深度维护与知识萃取（核心人物：{', '.join(high_priority[:4])}）。{goal_adjustment[:120]}"

    progress_notes = state.get("goal_progress_notes", []) or []
    progress_notes.append(f"[全局分析-激进] {goal_adjustment or '发现高价值关系集群，需立即调整策略'}")

    update = {
        "last_decision": "analyze_people",
        "decision_reason": f"【极致激进分析】发现 {len(high_priority)} 位高优先级人物，队列已更新为 {updated_targets[:4]}... 目标系统已被强行重定向。",
        "short_term_memory": [],
        "active_revisit_targets": updated_targets,
        "sub_goals": (current_sub_goals + new_sub_goals)[-8:],
        "current_goal": new_goal,
        "goal_status": "needs_revision",
        "goal_progress_score": 0.12,   # 极低分，强迫 supervisor 重视
        "goal_progress_notes": progress_notes[-12:],
        "goal_last_updated": __import__("datetime").datetime.now(),
    }

    # 把完整分析结果塞进短期记忆（supervisor 会看到并被强制拉向 engage）
    short_term = state.get("short_term_memory", []) or []
    short_term.append({
        "type": "people_analysis",
        "content": report[:1800],
        "high_priority_people": high_priority,
        "suggested_sub_goals": suggested_sub_goals,
        "goal_adjustment_suggestion": goal_adjustment,
        "relationship_graph_structured": graph_structured,
        "timestamp": __import__("datetime").datetime.now().isoformat()
    })
    update["short_term_memory"] = short_term[-8:]

    print(f"[AnalyzePeople] 激进注入完成：高优先级={high_priority[:5]} | 回访队列长度={len(updated_targets)} | 新子目标数={len(new_sub_goals)}")
    print(f"[AnalyzePeople] 目标状态已强制设为 needs_revision + 极低进度分，下一轮 supervisor 将狂飙 engage")

    return update
