from langgraph.graph import StateGraph, END
from typing import Literal

from agent.state import WandererState
from agent.nodes.supervisor import supervisor_node
from agent.nodes.intervention import check_intervention_node
from agent.nodes import wander, observe, reflect, engage, report


def route_after_supervisor(state: WandererState) -> Literal[
    "wander", "observe", "reflect", "engage", "generate_report"
]:
    decision = state.get("last_decision", "observe")
    if decision in ["wander", "observe", "reflect", "engage", "generate_report"]:
        return decision
    return "observe"


def build_wanderer_graph(llm):
    """构建完整的自主决策图（支持 LLM 传递给多个节点）"""
    workflow = StateGraph(WandererState)

    workflow.add_node("check_intervention", check_intervention_node)
    workflow.add_node("supervisor", lambda s: supervisor_node(s, llm))

    workflow.add_node("wander", wander.wander_node)
    workflow.add_node("observe", observe.observe_node)

    # 需要 LLM 的节点
    workflow.add_node("reflect", lambda s: reflect.reflect_node(s, llm))
    workflow.add_node("engage", lambda s: engage.engage_node(s, llm))
    workflow.add_node("generate_report", lambda s: report.report_node(s, llm))

    workflow.set_entry_point("check_intervention")
    workflow.add_edge("check_intervention", "supervisor")

    workflow.add_conditional_edges(
        "supervisor",
        route_after_supervisor,
        {
            "wander": "wander",
            "observe": "observe",
            "reflect": "reflect",
            "engage": "engage",
            "generate_report": "generate_report",
        }
    )

    for node in ["wander", "observe", "reflect", "engage", "generate_report"]:
        workflow.add_edge(node, "supervisor")

    return workflow.compile()
