from agent.state import WandererState
from commands.file_command import check_file_command


def check_intervention_node(state: WandererState) -> dict:
    """
    每次循环检查人类干预
    """
    updates = {}

    # 检查文件指令
    file_cmd = check_file_command()
    if file_cmd:
        updates["pending_human_command"] = file_cmd
        updates["last_human_intervention_time"] = __import__("datetime").datetime.now()

    # 这里可以扩展更多干预处理逻辑
    return updates
