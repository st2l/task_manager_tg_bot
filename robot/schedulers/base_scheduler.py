from aiogram import Bot
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from datetime import datetime

scheduler = AsyncIOScheduler()


async def setup_scheduler(bot: Bot):
    if not scheduler.running:
        scheduler.start()
