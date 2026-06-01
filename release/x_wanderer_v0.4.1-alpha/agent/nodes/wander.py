from agent.state import WandererState
from platforms.x.tools import search_x
from agent.memory.memory_manager import MemoryManager


def wander_node(state: WandererState, llm=None) -> dict:
    """
    漫游节点（支持主动回访重要画像）
    """
    current_goal = state.get("current_goal", "")
    short_term = state.get("short_term_memory", [])
    active_revisits = state.get("active_revisit_targets", [])
    memory_manager = MemoryManager()

    # 优先处理主动回访目标
    revisit_target = None
    if active_revisits:
        revisit_target = active_revisits[0]
        query = f"from:{revisit_target} -is:retweet" if " " not in revisit_target else revisit_target
        print(f"[Wander] 执行主动回访：{revisit_target}")
    else:
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
        "decision_reason": f"进行了漫游{'（主动回访模式）' if revisit_target else ''}，发现 {len(results)} 条内容。",
        "short_term_memory": short_term[-18:],
        "x_current_focus": {
            "last_search_query": query,
            "results_count": len(results),
            "revisit_mode": bool(revisit_target)
        }
    }

    # 如果完成了回访，从 active_revisit_targets 中移除
    if revisit_target and active_revisits:
        new_targets = [t for t in active_revisits if t != revisit_target]
        update["active_revisit_targets"] = new_targets
        memory_manager.record_profile_revisit("person" if "@" not in revisit_target else "person", revisit_target)

    return update
