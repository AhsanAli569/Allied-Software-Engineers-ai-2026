from fastapi import APIRouter

from app.api.v1 import account, auth, conversations, files, health, messages, models

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(health.router)
api_router.include_router(auth.router)
api_router.include_router(account.router)
api_router.include_router(conversations.router)
api_router.include_router(files.router)
api_router.include_router(messages.router)
api_router.include_router(models.router)
