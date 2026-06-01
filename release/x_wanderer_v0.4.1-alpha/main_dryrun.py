"""
干运行模式（Dry Run） - 增强可视化版
用于测试和观察 Agent 内部状态，而不调用真实 API。
"""
import asyncio
import signal
from datetime import datetime
from typing import Any, Dict

from agent.graph import build_wanderer_graph
from agent.state import WandererState
from commands.file_command import check_file_command
from commands.cli import start_cli_listener
from agent.memory.memory_manager import MemoryManager


class FakeLLM:
    """模拟 LLM（激进 ABC 版）- 能正确返回结构化 SupervisorDecision + 支持 analyze_people 路径"""
    def __init__(self):
        self.call_count = 0
        self._last_action = "observe"

    def invoke(self, prompt: str):
        self.call_count += 1
        prompt_lower = prompt.lower()

        # === Supervisor 决策模拟（激进 ABC 结构化铁律版）===
        if "supervisor" in prompt_lower or "下一步行动" in prompt or "铁律" in prompt or "结构化激进铁律" in prompt:
            # 结构化铁律现在在 supervisor 内部直接 short-circuit，这里只是兜底
            if "active_revisit_targets" in prompt and "[]" not in str(prompt).split("active_revisit_targets")[-1][:80]:
                action = "engage"
                reason = "干运行模拟：结构化铁律已启动回访战役，连续多轮 engage"
            else:
                actions = ["engage", "analyze_people", "reflect", "observe", "wander"]
                action = actions[self.call_count % len(actions)]
                reason = f"干运行模拟 #{self.call_count}（ABC 强化版）"

            updated_goal = "围绕 testbridge 等高价值节点进行多轮关系维护" if self.call_count % 5 == 0 else None

            fake_json = {
                "action": action,
                "reason": reason,
                "updated_goal": updated_goal,
                "suggested_revisit": None,
                "goal_status": "needs_revision" if action == "analyze_people" else "active",
                "goal_progress_score": 0.18 if action == "analyze_people" else 0.35
            }
            return type('obj', (object,), {'content': str(fake_json).replace("'", '"')})()

        # === analyze_people 模拟（返回结构化分析结果）===
        if "全局人物分析" in prompt or "analyze_all_people" in prompt_lower or "高优先级主动回访名单" in prompt:
            fake_analysis = """
REPORT:
干运行模拟分析：目前积累了 6 位重要人物，形成 2 个明显聚类。@corebridge 是关键桥梁人物，@deepthinker 和 @explorer 有高潜力但互动不足。

HIGH_PRIORITY:
corebridge, deepthinker, explorer, patternseeker

SUB_GOALS:
- 对 corebridge 发起连续 3 轮对话，探索其对长期 AI 关系维护的看法
- 与 deepthinker 进行至少 2 次深度互动并记录 4 条新洞见

GOAL_ADJUST:
当前主目标与实际积累的 4 位高价值人物脱节，建议立即把主目标调整为“围绕 corebridge 等核心节点进行多轮关系维护与知识萃取”。
"""
            return type('obj', (object,), {'content': fake_analysis})()

        # Reflect 模拟
        if "反思" in prompt or "reflect" in prompt_lower:
            return type('obj', (object,), {
                'content': f"【干运行反思 #{self.call_count}】检测到高价值关系集群。建议 supervisor 在 analyze 后进入 4+ 轮连续 engage。已更新 2 个画像的重要性。"
            })()

        # Report 模拟
        if "报告" in prompt or "report" in prompt_lower:
            return type('obj', (object,), {
                'content': "【干运行阶段报告 - ABC 激进版】analyze_people → 目标重定向 → 连续 engage 战役 已成功打通。关系图谱洞见正在驱动决策。"
            })()

        # 针对偏好定制互动的模拟回复（当 prompt 包含偏好/画像关键词时）
        if "偏好" in prompt or "画像" in prompt or "relationship_position" in prompt_lower or "engagement_suggestions" in prompt_lower:
            return type('obj', (object,), {
                'content': "（干运行偏好定制回复）看到你这条内容，我想起你之前分享过对跨界思考的兴趣。这让我想到一个最近观察到的模式……（AI身份声明）你怎么看？"
            })

        return type('obj', (object,), {
            'content': "（干运行模拟）AI 正在围绕目标进行数字漫游（透明身份声明）。"
        })


def print_dashboard(state: WandererState):
    """打印当前 Agent 状态仪表盘（ABC 激进版 - 突出关系维护与目标联动）"""
    print("\n" + "="*75)
    print(f"【干运行仪表盘 - 激进 ABC 模式】 {datetime.now().strftime('%H:%M:%S')}")
    print(f"目标状态: {state.get('goal_status', 'unknown')} | 进度分: {state.get('goal_progress_score', 0):.2f}")
    print(f"当前目标: {state.get('current_goal', '')[:72]}...")
    
    sub_goals = state.get("sub_goals", [])
    if sub_goals:
        print(f"子目标 ({len(sub_goals)}): {sub_goals[0][:55]}...")

    print(f"连续行动: {state.get('consecutive_actions', 0)}")
    print(f"最新决策: {state.get('last_decision')} | {state.get('decision_reason', '')[:58]}")

    # === 核心：主动回访队列 + 显式战役状态（ABC 激进多轮的核心可视化）===
    active = state.get("active_revisit_targets", []) or []
    campaign = state.get("current_revisit_campaign") or {}
    if campaign:
        print(f"\n🔥🔥 当前回访战役: {campaign.get('target')} | 已连续 {campaign.get('streak',0)} 轮 | 队列剩余 {len(active)}")
    elif active:
        print(f"\n🔥 主动回访队列 (长度 {len(active)}): {active[:5]}  （等待启动战役）")
    else:
        print("\n回访队列: 空")

    # 显示最近一次互动是否使用了偏好定制（新功能）
    if state.get("last_decision") == "engage" and "偏好定制" in str(state.get("decision_reason", "")):
        print("   ↳ 最近回复已根据目标画像+关系网+偏好个性化生成")



    # 重要画像
    try:
        mm = MemoryManager()
        profiles = mm.get_important_profiles(limit=4)
        if profiles:
            print("\nTop 长期画像:")
            for p in profiles:
                print(f"  • {p['name']} | 重要性 {p.get('importance_score',0):.2f} | 互动 {p.get('interaction_count',0)}")
    except Exception as e:
        pass

    # 最近分析结果（判断是否刚触发过 analyze_people）
    short_term = state.get("short_term_memory", [])
    for item in reversed(short_term[-3:]):
        if item.get("type") == "people_analysis":
            hp = item.get("high_priority_people", [])
            print(f"\n📊 最近人物分析: 高优先级={hp[:4]} | 子目标建议数={len(item.get('suggested_sub_goals', []))}")

            break

    # 最近反思
    reflections = state.get("reflections", [])
    if reflections:
        print(f"\n最新反思: {reflections[-1][:72]}...")

    print("="*75 + "\n")


async def main():
    print("=== X Wanderer Agent（增强干运行模式） ===")
    print("此模式完全模拟运行，无真实 API 调用。\n")

    llm = FakeLLM()
    graph = build_wanderer_graph(llm)

    state: WandererState = {
        "current_goal": "在测试环境中验证数字漫游者系统的完整逻辑流程与长期记忆能力。",
        "agent_generated_goals": [],
        "human_directives": [],
        "goal_last_updated": datetime.now(),
        "goal_progress_notes": [],
        "sub_goals": [],
        "goal_status": "active",
        "goal_milestones": [],
        "goal_progress_score": 0.35,
        "last_decision": None,
        "decision_reason": None,
        "consecutive_actions": 0,
        "last_action_time": datetime.now(),
        "total_actions": 0,
        "x_last_checked_id": None,
        "x_current_focus": {},
        "active_revisit_targets": [],
        "whitelist": ["testuser1", "testuser2"],
        "policies": {"max_engage_per_hour": 99},
        "short_term_memory": [],
        "episodic_memory_ids": [],
        "semantic_memory_summary": None,
        "reflections": [],
        "pending_human_command": None,
        "intervention_mode": "normal",
        "last_human_intervention_time": None,
        "should_continue": True,
        "last_cycle_time": datetime.now(),
    }

    cli_task = asyncio.create_task(start_cli_listener(state))

    def handle_exit(signum, frame):
        print("\n正在退出干运行模式...")
        state["should_continue"] = False

    signal.signal(signal.SIGINT, handle_exit)
    signal.signal(signal.SIGTERM, handle_exit)

    print("开始干运行... 每轮会打印状态仪表盘。\n")

    cycle = 0
    try:
        while state["should_continue"]:
            cycle += 1

            file_cmd = check_file_command()
            if file_cmd:
                state["pending_human_command"] = file_cmd
                print(f"[文件指令] {file_cmd}")

            try:
                result = await graph.ainvoke(state)
                state.update(result)
            except Exception as e:
                print(f"[异常] {e}")

            # 每 2 轮打印一次仪表盘
            if cycle % 2 == 0:
                print_dashboard(state)

            await asyncio.sleep(2.5)

    finally:
        cli_task.cancel()
        print("\n干运行模式已结束。")
        print(f"共运行 {cycle} 轮。")


if __name__ == "__main__":
    asyncio.run(main())
