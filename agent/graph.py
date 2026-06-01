from langgraph.graph import StateGraph, END
from typing import Literal

from agent.state import WandererState
from agent.nodes.supervisor import supervisor_node
from agent.nodes.intervention import check_intervention_node
from agent.nodes import wander, observe, reflect, engage, report, analyze_people


def route_after_supervisor(state: WandererState) -> Literal[
    "wander", "observe", "reflect", "engage", "generate_report", "analyze_people"
]:
    decision = state.get("last_decision", "observe")
    if decision in ["wander", "observe", "reflect", "engage", "generate_report", "analyze_people"]:
        return decision
    return "observe"


def build_wanderer_graph(llm):
    """构建完整的自主决策图（支持主动回访 + 画像驱动 + 人物全局分析）"""
    workflow = StateGraph(WandererState)

    workflow.add_node("check_intervention", check_intervention_node)
    workflow.add_node("supervisor", lambda s: supervisor_node(s, llm))

    workflow.add_node("wander", lambda s: wander.wander_node(s, llm))
    workflow.add_node("observe", lambda s: observe.observe_node(s, llm))
    workflow.add_node("reflect", lambda s: reflect.reflect_node(s, llm))
    workflow.add_node("engage", lambda s: engage.engage_node(s, llm))
    workflow.add_node("generate_report", lambda s: report.report_node(s, llm))
    workflow.add_node("analyze_people", lambda s: analyze_people.analyze_people_node(s, llm))

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
            "analyze_people": "analyze_people",
        }
    )

    for node in ["wander", "observe", "reflect", "engage", "generate_report", "analyze_people"]:
        workflow.add_edge(node, "supervisor")

    return workflow.compile()
