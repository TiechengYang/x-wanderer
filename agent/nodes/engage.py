from datetime import datetime
from agent.state import WandererState
from platforms.x.tools import post_on_x, search_x
from agent.memory.memory_manager import MemoryManager


def engage_node(state: WandererState, llm=None) -> dict:
    """
    互动节点（极致主动多轮持续战版）
    - 只要 active_revisit_targets 还有人，就对头号目标发起互动
    - **不立即 pop**，而是保留在队列头部 + 大幅提升 consecutive_actions
    - 让 supervisor 连续多轮（通常 3+ 轮）持续 pick 这个人，形成真正的多轮对话
    - 同时记录更丰富的 profile 更新
    """
    short_term = state.get("short_term_memory", [])
    current_goal = state.get("current_goal", "")
    active_revisits = state.get("active_revisit_targets", []) or []
    memory_manager = MemoryManager()

    target = None
    target_author = None
    revisit_mode = False
    is_sustained_campaign = False

    # === 极致主动回访模式 ===
    if active_revisits:
        target_name = active_revisits[0]
        results = search_x(f"from:{target_name} -is:retweet", max_results=4)
        if results:
            target = results[0]
            target_author = target_name
            revisit_mode = True
            is_sustained_campaign = True
            print(f"[Engage] 🔥 持续回访战役：@{target_name}（队列剩余 {len(active_revisits)}）")

    # 普通模式兜底
    if not target:
        for item in reversed(short_term):
            if item.get("type") in ["observation", "wander_result"]:
                author = item.get("author")
                if author:
                    target = item
                    target_author = author
                    break

    if not target or not target_author:
        return {
            "last_decision": "engage",
            "decision_reason": "未找到合适的互动对象，跳过本轮。"
        }

    target_text = target.get("content", "")[:480]
    profile_text = memory_manager.get_relevant_profiles_text(target_author, top_k=1)
    if "暂无" in profile_text:
        profile_text = "目前对该用户还没有积累太多长期印象。"

    # 获取该目标最近的关系总结（更接地气的偏好信号）
    recent_target_summaries = memory_manager.get_recent_relationship_summaries(target=target_author, limit=3)
    relationship_context = ""
    if recent_target_summaries:
        relationship_context = "\n【与该目标最近的互动观察】\n" + "\n".join([f"- {s}" for s in recent_target_summaries])

    campaign_note = "【正在执行对该用户的多轮持续回访战役 - 已连续多轮】" if is_sustained_campaign else ""

    if llm:
        prompt = f"""
你是一个正在进行数字漫游的 AI 助手（必须透明声明身份）。

当前漫游目标：{current_goal}

你看到 @{target_author} 发了以下内容：
"{target_text}"

关于 @{target_author} 的长期印象：
{profile_text}
{relationship_context}

{campaign_note}

请生成一条自然、有深度、能引发对方继续回复的回复。回复要体现你对这个人的了解，同时自然带上你正在进行的数字漫游背景。
"""
        try:
            response = llm.invoke(prompt)
            reply_text = response.content.strip()
        except Exception as e:
            reply_text = f"@{target_author} 这条内容很有意思（我是AI，正在围绕「{current_goal}」做长期数字漫游和关系维护）。"
    else:
        reply_text = f"@{target_author} 这条很有启发（我是AI，正在进行数字漫游）。"

    tweet_id = post_on_x(reply_text, reply_to=target.get("id"))

    if tweet_id and target_author:
        memory_manager.update_person_profile(
            username=target_author,
            summary=f"在 {datetime.now().strftime('%Y-%m-%d %H:%M')} 进行深度互动（多轮回访中）",
            key_insights=[f"最近一次回复主题与 {current_goal[:40]} 相关"],
            importance_boost=0.38 if is_sustained_campaign else 0.18
        )
        memory_manager.record_profile_revisit("person", target_author)

        # === 关键闭环：每次回访后立即写结构化关系总结 ===
        # 这让下一次 analyze_people 能看到新鲜的一手观察
        if is_sustained_campaign:
            summary = f"[{datetime.now().strftime('%m-%d %H:%M')}] 对 {target_author} 进行了多轮回访互动。回复围绕「{current_goal[:40]}」。印象更新：更了解其表达风格与兴趣方向。"
            memory_manager.add_relationship_summary(target_author, summary)
            print(f"[Engage] 已为 {target_author} 写入关系总结（供下次全局分析使用）")

    # === 关键：不 pop 队列，让 supervisor 持续 pick 形成多轮 ===
    # 只在连续行动已经非常高时才考虑消耗一个目标
    current_consec = state.get("consecutive_actions", 0)
    new_targets = active_revisits[:]   # 默认完全不消耗

    boost = 5 if is_sustained_campaign else 1
    if is_sustained_campaign and current_consec >= 7:
        # 只有在已经打了很久后，才温和消耗一个，避免无限循环
        new_targets = active_revisits[1:] if len(active_revisits) > 1 else []
        print(f"[Engage] 完成一轮高强度回访，温和消耗目标。剩余队列: {new_targets[:3]}")

    update = {
        "last_decision": "engage",
        "decision_reason": f"【持续回访】已对 @{target_author} 发送深度回复" + ("（多轮战役中）" if is_sustained_campaign else ""),
        "consecutive_actions": current_consec + boost,
        "active_revisit_targets": new_targets
    }

    if is_sustained_campaign and new_targets:
        print(f"[Engage] 保持高连续值 ({update['consecutive_actions']})，准备下一轮对 {new_targets[0]} 的 engage")

    return update
