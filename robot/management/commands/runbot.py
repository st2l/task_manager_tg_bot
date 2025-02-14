import os
from django.core.management.base import BaseCommand
from dotenv import load_dotenv
from aiogram import Dispatcher, Bot
from robot.handlers import router
from robot.schedulers import setup_all_schedulers
import asyncio
import logging

load_dotenv()

class Command(BaseCommand):
    help = 'RUN COMMAND: python manage.py runbot'

    def handle(self, *args, **options):
        bot = Bot(token=os.getenv("TELEGRAM_TOKEN"))
        dp = Dispatcher()
        dp.include_router(router)

        logging.basicConfig(level=logging.INFO)
        
        async def main():
            await setup_all_schedulers(bot)
            await dp.start_polling(bot)
            
        asyncio.run(main())