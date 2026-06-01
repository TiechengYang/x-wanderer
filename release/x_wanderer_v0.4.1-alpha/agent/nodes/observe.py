from agent.state import WandererState
from platforms.x.tools import search_x


def observe_node(state: WandererState) -> dict:
    """
    观察节点：对特定话题或用户进行更深入的查看
    """
    focus = state.get("x_current_focus", {})
    query = focus.get("last_search_query", "AI OR LLM OR agent")

    results = search_x(query, max_results=5)

    short_term = state.get("short_term_memory", [])
    observations = []
    for item in results:
        obs = {
            "type": "observation",
            "content": item.get("text", "")[:300],
            "author": item.get("author_username"),
            "id": item.get("id")
        }
        short_term.append(obs)
        observations.append(obs)

    return {
        "last_decision": "observe",
        "decision_reason": f"对主题进行了深入观察，记录了 {len(observations)} 条内容。",
        "short_term_memory": short_term[-20:],
    }
