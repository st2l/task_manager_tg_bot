from aiogram import Router
from .start_handler import start_router
from .admin_handler import admin_router

router = Router()

router.include_router(start_router)
router.include_router(admin_router)