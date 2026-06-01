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
    """模拟 LLM，返回可控的响应"""
    def __init__(self):
        self.call_count = 0

    def invoke(self, prompt: str):
        self.call_count += 1
        prompt_lower = prompt.lower()

        # Supervisor 决策模拟
        if "决策" in prompt or "supervisor" in prompt_lower or "下一步行动" in prompt:
            actions = ["wander", "observe", "reflect", "engage", "generate_report"]
            action = actions[self.call_count % len(actions)]
            return type('obj', (object,), {
                'content': f'{{"action": "{action}", "reason": "干运行模拟决策（第{self.call_count}次）", "updated_goal": null, "focus": "测试焦点", "suggested_revisit": null}}'
            })()

        # Reflect 模拟
        if "反思" in prompt or "reflect" in prompt_lower:
            return type('obj', (object,), {
                'content': f"【干运行反思 #{self.call_count}】观察到测试环境中的模式，建议继续探索画像与目标的联动关系。"
            })()

        # Report 模拟
        if "报告" in prompt or "report" in prompt_lower:
            return type('obj', (object,), {
                'content': "【干运行阶段报告】系统运行正常。记忆模块、画像系统、目标管理均处于活跃状态。"
            })()

        return type('obj', (object,), {
            'content': "（干运行模拟回复）这是一个用于测试流程的占位内容。"
        })


def print_dashboard(state: WandererState):
    """打印当前 Agent 状态仪表盘"""
    print("\n" + "="*70)
    print(f"【干运行仪表盘】 {datetime.now().strftime('%H:%M:%S')}")
    print(f"目标状态: {state.get('goal_status', 'unknown')}")
    print(f"当前目标: {state.get('current_goal', '')[:65]}...")
    print(f"连续行动: {state.get('consecutive_actions', 0)}")
    print(f"最新决策: {state.get('last_decision')} - {state.get('decision_reason', '')[:50]}")

    # 显示重要画像
    try:
        mm = MemoryManager()
        profiles = mm.get_important_profiles(limit=3)
        if profiles:
            print("\n重要画像:")
            for p in profiles:
                print(f"  - {p['name']} ({p['type']}) | 重要性: {p['importance_score']:.2f}")
    except:
        pass

    # 显示最近反思
    reflections = state.get("reflections", [])
    if reflections:
        print(f"\n最新反思: {reflections[-1][:80]}...")

    print("="*70 + "\n")


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
        "last_decision": None,
        "decision_reason": None,
        "consecutive_actions": 0,
        "last_action_time": datetime.now(),
        "total_actions": 0,
        "x_last_checked_id": None,
        "x_current_focus": {},
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
