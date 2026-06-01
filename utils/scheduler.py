from apscheduler.schedulers.background import BackgroundScheduler
from agent.memory.memory_manager import MemoryManager
from datetime import datetime
import logging

logger = logging.getLogger("Scheduler")

scheduler = BackgroundScheduler()


def start_memory_maintenance_scheduler(llm, interval_minutes: int = 38):
    """
    智能记忆维护 + 条件触发人物分析（主动注入版）
    """
    memory_manager = MemoryManager()

    def memory_maintenance_job():
        logger.info("执行定时记忆维护任务（智能触发版）...")
        try:
            memory_manager.compress_old_memories(llm, max_keep=26)

            important_profiles = memory_manager.get_important_profiles(limit=18)
            suggested_revisits = memory_manager.suggest_profiles_to_revisit(limit=5, days_since_last=5)

            # === 智能触发条件 ===
            should_trigger_analysis = False
            trigger_reason = ""

            if len(important_profiles) >= 9:
                # 条件1：画像数量多 + 很久没分析
                last_analysis_time = None
                recent = memory_manager.long_term.get_recent_memories(limit=20)
                for m in recent:
                    if m.metadata.get("type") == "people_analysis":
                        last_analysis_time = m.timestamp
                        break

                if last_analysis_time:
                    days = (datetime.now() - last_analysis_time).days
                    if days >= 4:
                        should_trigger_analysis = True
                        trigger_reason = f"已积累 {len(important_profiles)} 位重要人物，{days} 天未做全局分析"
                else:
                    should_trigger_analysis = True
                    trigger_reason = f"已积累 {len(important_profiles)} 位重要人物，但从未进行过人物分析"

            # 条件2：有很多需要回访但未处理的画像
            if not should_trigger_analysis and len(suggested_revisits) >= 3:
                should_trigger_analysis = True
                trigger_reason = f"存在 {len(suggested_revisits)} 位高价值画像需要回访，建议先做全局分析以优化优先级"

            if should_trigger_analysis:
                logger.info(f"【智能主动触发】{trigger_reason}")
                memory_manager.add_reflection(
                    content=f"【系统建议】{trigger_reason}，建议尽快执行 analyze_people。",
                    metadata={"type": "system_suggestion", "action": "analyze_people"}
                )
            else:
                if suggested_revisits:
                    # === 更激进的直接注入 ===
                    top_names = [p["name"] for p in suggested_revisits[:4]]
                    memory_manager.seed_forced_revisit_targets(top_names, reason="scheduler_stale_high_value")
                    logger.info(f"【主动回访种子注入】已直接推荐高价值目标进入下一轮决策：{top_names}")

        except Exception as e:
            logger.error(f"定时记忆维护失败: {e}")

    scheduler.add_job(
        memory_maintenance_job,
        'interval',
        minutes=interval_minutes,
        id='memory_maintenance',
        replace_existing=True
    )
    scheduler.start()
    logger.info(f"智能记忆维护定时任务已启动（每 {interval_minutes} 分钟），支持条件主动触发人物分析")
