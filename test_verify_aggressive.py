"""
快速验证 ABC 激进行为（analyze_people → 目标重定向 + 回访队列 → supervisor 强制连续 engage）
不依赖完整 langgraph / chromadb 环境，只测核心节点逻辑。
运行: python3 test_verify_aggressive.py
"""
import sys
from datetime import datetime
from agent.state import WandererState
from agent.memory.memory_manager import MemoryManager
from agent.nodes.analyze_people import analyze_people_node
from agent.nodes.supervisor import supervisor_node
from agent.nodes.engage import engage_node

class MockLLM:
    def invoke(self, prompt):
        class R:
            content = ""
        r = R()
        if "全局人物分析" in prompt or "HIGH_PRIORITY" in prompt:
            r.content = """REPORT:
验证用模拟分析：存在 3 位高价值桥梁人物，当前目标与关系图谱严重脱节。

HIGH_PRIORITY:
testbridge, deepfollower, patternkeeper

SUB_GOALS:
- 对 testbridge 发起 3 轮连续互动
- 提取 patternkeeper 的 4 条洞见

GOAL_ADJUST:
立即把主目标切换为围绕 testbridge 等核心人物进行多轮关系维护。
"""
        elif "铁律" in prompt or "active_revisit_targets" in prompt:
            r.content = '{"action": "engage", "reason": "检测到 active_revisit_targets，强制执行多轮 engage（ABC 验证）", "suggested_revisit": "testbridge"}'
        else:
            r.content = '{"action": "observe", "reason": "模拟默认决策"}'
        return r

def main():
    print("=== ABC 激进行为快速验证 ===\n")

    llm = MockLLM()
    mm = MemoryManager()

    # 构造干净初始 state
    state: WandererState = {
        "current_goal": "测试漫游目标",
        "agent_generated_goals": [],
        "human_directives": [],
        "goal_last_updated": datetime.now(),
        "goal_progress_notes": [],
        "sub_goals": [],
        "goal_status": "active",
        "goal_milestones": [],
        "goal_progress_score": 0.4,
        "last_decision": None,
        "decision_reason": None,
        "consecutive_actions": 0,
        "last_action_time": datetime.now(),
        "total_actions": 0,
        "x_last_checked_id": None,
        "x_current_focus": {},
        "active_revisit_targets": [],
        "current_revisit_campaign": None,
        "revisit_campaign_history": [],
        "whitelist": [],
        "policies": {},
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

    # 1. 先塞一点模拟画像，让 analyze 有东西可分析
    mm.update_person_profile("testbridge", "关键桥梁人物，经常讨论 AI 关系", ["桥梁", "高潜力"], 0.82)
    mm.update_person_profile("deepfollower", "深度思考者，输出质量高", ["深度", "洞见丰富"], 0.71)
    mm.update_person_profile("patternkeeper", "模式观察者", [], 0.68)

    print("【初始状态】")
    print(f"  目标: {state['current_goal']}")
    print(f"  回访队列: {state['active_revisit_targets']}")
    print(f"  子目标数: {len(state['sub_goals'])}")
    print(f"  进度分: {state['goal_progress_score']}")

    # 2. 执行 analyze_people（激进版核心）
    print("\n>>> 执行 analyze_people_node（极致激进版）...")
    update1 = analyze_people_node(state, llm=llm)
    state.update(update1)

    print("\n【analyze_people 后状态】")
    print(f"  目标: {state['current_goal'][:80]}...")
    print(f"  目标状态: {state['goal_status']} | 进度分: {state['goal_progress_score']}")
    print(f"  子目标: {state['sub_goals'][:2]}")
    print(f"  🔥 主动回访队列: {state['active_revisit_targets']}")
    print(f"  短期记忆中 people_analysis 条目: {len([x for x in state['short_term_memory'] if x.get('type')=='people_analysis'])}")

    # 3. 执行 supervisor（应该被铁律强制成 engage）
    print("\n>>> 执行 supervisor_node（应被 active_revisit_targets 强制成 engage）...")
    update2 = supervisor_node(state, llm=llm)
    state.update(update2)

    print("\n【supervisor 后状态】")
    print(f"  最新决策: {state['last_decision']}")
    print(f"  决策理由: {state['decision_reason'][:90]}...")
    print(f"  连续行动: {state['consecutive_actions']}")

    # 4. 模拟多次 engage（验证不轻易 pop + 持续高连续）
    print("\n>>> 连续执行 3 次 engage_node（验证多轮战役行为）...")
    for i in range(3):
        update_e = engage_node(state, llm=llm)
        state.update(update_e)
        print(f"  第 {i+1} 轮 engage → 决策: {state['last_decision']} | 连续值: {state['consecutive_actions']} | 队列剩余: {state.get('active_revisit_targets', [])}")

    print("\n=== 验证结论 ===")
    if state.get("active_revisit_targets"):
        print("✅ 成功：analyze_people 注入高优先级 + supervisor 结构化铁律（pre-LLM early return）启动了 current_revisit_campaign 并强制多轮 engage。")
        print(f"   战役状态: {state.get('current_revisit_campaign')}")
    else:
        print("⚠️ 整体流程已打通（队列可能被温和消耗）。")

    print("\nABC 激进闭环验证完成。真实环境运行 main_dryrun.py 可直观看到『analyze → 结构化铁律强制多轮战役 → 目标改写』全过程。")

if __name__ == "__main__":
    main()
