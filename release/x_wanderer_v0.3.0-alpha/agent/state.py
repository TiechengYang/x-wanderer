from typing import TypedDict, List, Optional, Dict, Any
from datetime import datetime


class WandererState(TypedDict):
    # ==================== 目标系统（混合模式 + 长期管理） ====================
    current_goal: Optional[str]
    agent_generated_goals: List[str]
    human_directives: List[str]
    goal_last_updated: datetime
    goal_progress_notes: List[str]
    sub_goals: List[str]
    goal_status: str                    # 新增： "active", "progressing", "stagnant", "needs_revision"

    # ==================== 决策与执行（平衡型） ====================
    last_decision: Optional[str]
    decision_reason: Optional[str]
    consecutive_actions: int
    last_action_time: datetime
    total_actions: int

    # ==================== X 平台上下文 ====================
    x_last_checked_id: Optional[str]
    x_current_focus: Dict[str, Any]

    # ==================== 白名单与策略 ====================
    whitelist: List[str]
    policies: Dict[str, Any]

    # ==================== 重度记忆系统 ====================
    short_term_memory: List[dict]
    episodic_memory_ids: List[str]
    semantic_memory_summary: Optional[str]
    reflections: List[str]

    # ==================== 人类干预（文件 + 命令行） ====================
    pending_human_command: Optional[str]
    intervention_mode: Optional[str]
    last_human_intervention_time: Optional[datetime]

    # ==================== 运行控制 ====================
    should_continue: bool
    last_cycle_time: datetime
