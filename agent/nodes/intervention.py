from agent.state import WandererState
from commands.file_command import check_file_command


def check_intervention_node(state: WandererState) -> dict:
    """
    检查人类干预（文件 + CLI）
    支持特殊指令如 /analyze_people
    """
    updates = {}

    file_cmd = check_file_command()
    if file_cmd:
        cmd = file_cmd.strip().lower()

        if cmd.startswith("/analyze_people"):
            # 触发人物分析
            updates["pending_human_command"] = None
            updates["last_decision"] = "analyze_people"
            updates["decision_reason"] = "用户主动要求进行所有相关人物的深度分析。"
            print("[Intervention] 用户触发人物全局分析")
            return updates

        updates["pending_human_command"] = file_cmd
        updates["last_human_intervention_time"] = __import__("datetime").datetime.now()

    return updates
