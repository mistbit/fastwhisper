"""FastAPI 应用入口"""
import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.router import api_router
from app.core.config import settings
from app.workers.processor import task_processor

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    # 启动时
    logger.info("Starting FastWhisper service...")

    # 启动后台任务处理器
    processor_task = asyncio.create_task(task_processor.start())

    yield

    # 关闭时
    logger.info("Shutting down FastWhisper service...")
    task_processor.stop()
    processor_task.cancel()


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