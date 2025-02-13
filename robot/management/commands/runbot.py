import os

from django.core.management.base import BaseCommand, CommandError

from aiogram import Dispatcher, Bot
from robot.handlers import router
import asyncio
import logging

class Command(BaseCommand):
    help = 'RUN COMMAND: python manage.py runbot'

    def handle(self, *args, **options):
        bot = Bot(token=os.getenv("TELEGRAM_TOKEN"))
        dp = Dispatcher()
        dp.include_router(router)

        logging.basicConfig(level=logging.INFO)

        asyncio.run(dp.start_polling(bot))