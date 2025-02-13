from aiogram import Router
from .start_handler import start_router
from .admin_handler import admin_router
from .task_creation_handler import task_creation_router
from .navigation_handler import navigation_router

router = Router()

router.include_router(start_router)
router.include_router(admin_router)
router.include_router(task_creation_router)
router.include_router(navigation_router)