import asyncio
import signal
from datetime import datetime

from langchain_openai import ChatOpenAI

from agent.graph import build_wanderer_graph
from agent.state import WandererState
from commands.file_command import check_file_command
from commands.cli import start_cli_listener
from config.settings import get_settings
from utils.scheduler import start_memory_maintenance_scheduler

settings = get_settings()


async def main():
    print("=== X Wanderer Agent 启动 ===")
    print(f"模型: {settings.llm_model}")
    print("模式: 完全自主决策 + 强化画像 + 主动回访 + 目标进度管理")
    print("人类干预已启用（文件 + 命令行）\n")

    llm = ChatOpenAI(
        model=settings.llm_model,
        api_key=settings.llm_api_key,
        base_url=settings.llm_base_url,
        temperature=0.6,
    )

    graph = build_wanderer_graph(llm)

    start_memory_maintenance_scheduler(llm, interval_minutes=48)

    state: WandererState = {
        "current_goal": "在 X 上进行有深度的数字漫游，观察有趣的人、话题和文化现象，并适度参与有价值的讨论。",
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
        "whitelist": settings.whitelist,
        "policies": settings.policies,
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
        print("\n正在安全关闭...")
        state["should_continue"] = False

    signal.signal(signal.SIGINT, handle_exit)
    signal.signal(signal.SIGTERM, handle_exit)

    try:
        while state["should_continue"]:
            file_cmd = check_file_command()
            if file_cmd:
                state["pending_human_command"] = file_cmd
                state["last_human_intervention_time"] = datetime.now()
                print(f"[文件指令] {file_cmd}")

            try:
                result = await graph.ainvoke(state)
                state.update(result)
            except Exception as e:
                print(f"[循环异常] {e}")
                await asyncio.sleep(10)

            await asyncio.sleep(5)

    finally:
        cli_task.cancel()
        print("Agent 已停止。")


if __name__ == "__main__":
    asyncio.run(main())
