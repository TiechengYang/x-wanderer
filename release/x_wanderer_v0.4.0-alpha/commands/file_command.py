from __future__ import annotations

from pathlib import Path
from typing import Optional

COMMAND_FILE = "commands/human_input.txt"


def check_file_command() -> Optional[str]:
    """检查是否有新的文件指令"""
    path = Path(COMMAND_FILE)
    if not path.exists():
        return None

    content = path.read_text(encoding="utf-8").strip()
    if content:
        # 读取后清空文件，避免重复执行
        path.write_text("", encoding="utf-8")
        return content
    return None
