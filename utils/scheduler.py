from apscheduler.schedulers.background import BackgroundScheduler
from agent.memory.memory_manager import MemoryManager
import logging

logger = logging.getLogger("Scheduler")

scheduler = BackgroundScheduler()


def start_memory_maintenance_scheduler(llm, interval_minutes: int = 48):
    """
    智能记忆维护 + 主动画像回访建议定时任务（强化版）
    """
    memory_manager = MemoryManager()

    def memory_maintenance_job():
        logger.info("执行定时记忆维护任务（含主动画像建议）...")
        try:
            memory_manager.compress_old_memories(llm, max_keep=32)

            # 主动建议需要回访的画像
            suggested = memory_manager.suggest_profiles_to_revisit(limit=6)
            if suggested:
                logger.info("【主动回访建议】以下画像值得优先关注：")
                for p in suggested:
                    logger.info(f"  → [{p['type']}] {p['name']} (重要性: {p['importance_score']:.2f})")

                # 这里可以进一步把建议写入某个共享状态或触发 Supervisor 决策
                # 当前版本通过日志 + Supervisor 决策实现

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
    logger.info(f"智能记忆维护定时任务已启动（每 {interval_minutes} 分钟），支持主动画像回访建议")
