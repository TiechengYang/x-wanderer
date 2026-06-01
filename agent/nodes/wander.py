from agent.state import WandererState
from platforms.x.tools import search_x
from agent.memory.memory_manager import MemoryManager


def wander_node(state: WandererState) -> dict:
    """
    漫游节点：支持主动回访重要画像
    """
    current_goal = state.get("current_goal", "")
    short_term = state.get("short_term_memory", [])
    memory_manager = MemoryManager()

    # 检查是否有来自 Supervisor 的回访建议
    revisit_suggestion = None
    for item in reversed(short_term):
        if item.get("type") == "suggested_revisit":
            revisit_suggestion = item.get("content", "")
            break

    if revisit_suggestion:
        # 主动回访模式：搜索该画像的近期内容
        query = f"{revisit_suggestion} -is:retweet"
        print(f"[Wander] 执行主动回访：{revisit_suggestion}")
    else:
        # 正常漫游
        query = f"{current_goal} lang:en OR lang:zh -is:retweet"

    results = search_x(query, max_results=7)

    for item in results[:4]:
        short_term.append({
            "type": "wander_result",
            "content": item.get("text", "")[:220],
            "author": item.get("author_username"),
            "id": item.get("id")
        })

    update = {
        "last_decision": "wander",
        "decision_reason": f"进行了漫游{'（主动回访模式）' if revisit_suggestion else ''}，发现 {len(results)} 条内容。",
        "short_term_memory": short_term[-18:],
        "x_current_focus": {
            "last_search_query": query,
            "results_count": len(results),
            "revisit_mode": bool(revisit_suggestion)
        }
    }

    return update
