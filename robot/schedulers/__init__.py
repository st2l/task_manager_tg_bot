from .base_scheduler import setup_scheduler
from .task_scheduler import setup_task_schedulers

async def setup_all_schedulers(bot):
    await setup_scheduler(bot)
    setup_task_schedulers(bot) 