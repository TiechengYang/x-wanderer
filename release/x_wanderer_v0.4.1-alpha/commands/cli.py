from __future__ import annotations

import asyncio
from typing import Any, Dict


async def start_cli_listener(state: Dict[str, Any]):
    """
    简单的命令行干预监听（Stage 1 基础版）
    用户可以在运行时输入指令
    """
    print("[CLI] 人类干预已启用。输入指令后按回车即可发送给 Agent。")
    print("[CLI] 示例: /goal 去观察AI相关讨论 | /pause | /reflect")

    loop = asyncio.get_event_loop()

    while state.get("should_continue", True):
        try:
            cmd = await loop.run_in_executor(None, input, "> ")
            if cmd.strip():
                state["pending_human_command"] = cmd.strip()
                state["last_human_intervention_time"] = __import__("datetime").datetime.now()
                print(f"[CLI] 已接收指令: {cmd}")
        except EOFError:
            break
        except Exception as e:
            print(f"[CLI Error] {e}")
            await asyncio.sleep(2)
