"""API v1 路由"""
from fastapi import APIRouter

from app.api.v1 import tasks

api_router = APIRouter(prefix="/api/v1")

api_router.include_router(tasks.router)