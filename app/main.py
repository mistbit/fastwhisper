"""FastAPI 应用入口"""
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.router import api_router
from app.core.config import settings
from app.core.database import SessionLocal, init_database
from app.services.task_service import TaskService

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(_: FastAPI):
    await init_database()
    if settings.USE_INLINE_TASKS:
        async with SessionLocal() as db:
            requeued = await TaskService(db).requeue_inline_processing_tasks()
            if requeued:
                logger.info("Requeued %s interrupted inline tasks on startup", requeued)
    yield


app = FastAPI(
    title="FastWhisper - 录音转会议纪要服务",
    description="基于 Whisper 的录音转会议纪要服务，支持说话人识别和自动生成会议纪要",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS 配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册路由
app.include_router(api_router)


@app.get("/health", tags=["health"])
async def health_check():
    """健康检查"""
    return {"status": "ok", "service": "fastwhisper"}


@app.get("/", tags=["root"])
async def root():
    """根路径"""
    return {
        "service": "FastWhisper",
        "version": "1.0.0",
        "docs": "/docs",
    }
