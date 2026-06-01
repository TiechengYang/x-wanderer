from datetime import datetime
from agent.state import WandererState
from platforms.x.tools import post_on_x, search_x
from agent.memory.memory_manager import MemoryManager


def engage_node(state: WandererState, llm=None) -> dict:
    """
    互动节点（主动回访 + 主动发起增强版）
    不仅被动回复，也会主动寻找重要画像进行互动
    """
    short_term = state.get("short_term_memory", [])
    current_goal = state.get("current_goal", "")
    memory_manager = MemoryManager()

    target = None
    revisit_mode = False
    proactive_mode = False

    # 1. 优先处理 Supervisor 建议的回访对象
    for item in reversed(short_term):
        if item.get("type") == "suggested_revisit":
            content = item.get("content", "")
            if "回访" in content:
                name = content.split("：")[-1].strip() if "：" in content else None
                if name:
                    results = search_x(f"from:{name} -is:retweet", max_results=3)
                    if results:
                        target = results[0]
                        revisit_mode = True
                        break

    # 2. 如果没有明确建议，主动寻找高重要性画像进行互动（新增主动能力）
    if not target:
        important_profiles = memory_manager.get_important_profiles(limit=5)
        for profile in important_profiles:
            if profile["type"] == "person" and profile["importance_score"] > 0.65:
                # 搜索该重要人物的近期内容
                results = search_x(f"from:{profile['name']} -is:retweet", max_results=2)
                if results:
                    target = results[0]
                    proactive_mode = True
                    break

    # 3. 最后才退回到普通短期记忆中的内容
    if not target:
        for item in reversed(short_term):
            if item.get("type") in ["observation", "wander_result"]:
                author = item.get("author")
                if author:
                    target = item
                    break

    if not target:
        return {
            "last_decision": "engage",
            "decision_reason": "未找到合适的互动对象（包括重要画像）。"
        }

    target_text = target.get("content", "")[:450]
    target_author = target.get("author", "某用户")

    # 获取长期画像
    profile_text = memory_manager.get_relevant_profiles_text(target_author, top_k=1)
    if "暂无" in profile_text:
        profile_text = "目前对该用户还没有积累太多长期印象。"

    # 使用 LLM 生成高质量回复
    if llm:
        prompt = f"""
你是一个正在进行数字漫游的 AI 助手。

当前漫游目标：{current_goal}

你看到 @{target_author} 发了以下内容：
"{target_text}"

关于 @{target_author} 的长期印象：
{profile_text}

{'【当前处于主动回访/关系维护模式】' if (revisit_mode or proactive_mode) else ''}

请生成一条自然、有深度、且与你当前漫游目标相关的回复。
要求：
- 如果有长期印象，可以自然引用
- 必须明确表明自己是 AI
- 语气友好且有思考性
- 长度控制在 70-160 字
"""
        try:
            response = llm.invoke(prompt)
            reply_text = response.content.strip()
        except Exception as e:
            reply_text = f"看到 @{target_author} 的内容很有意思（我是AI，正在围绕「{current_goal}」进行数字漫游）。"
    else:
        reply_text = f"看到 @{target_author} 的这条内容很有启发（我是AI，正在进行数字漫游）。"

    tweet_id = post_on_x(reply_text, reply_to=target.get("id"))

    # 更新画像
    if tweet_id and target_author:
        memory_manager.update_person_profile(
            username=target_author,
            summary=f"曾在 {datetime.now().strftime('%Y-%m-%d')} 进行过互动。",
            key_insights=[],
            importance_boost=0.18 if (revisit_mode or proactive_mode) else 0.1
        )

    mode_tag = ""
    if revisit_mode:
        mode_tag = "（主动回访）"
    elif proactive_mode:
        mode_tag = "（主动关系维护）"

    reason = f"已使用画像生成回复并发送给 @{target_author}{mode_tag}"

    return {
        "last_decision": "engage",
        "decision_reason": reason,
        "consecutive_actions": state.get("consecutive_actions", 0) + 1
    }
