"""API 依赖注入"""
import os
import uuid
from typing import AsyncGenerator

from fastapi import Depends, HTTPException, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import SessionLocal
from app.core.security import verify_token


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """获取数据库会话"""
    async with SessionLocal() as session:
        yield session


async def get_current_user(token: str = Depends(verify_token)) -> str:
    """获取当前用户（Token 认证）"""
    return token


# 支持的音频格式
ALLOWED_EXTENSIONS = {".mp3", ".wav", ".m4a", ".webm", ".ogg", ".flac", ".aac"}


def validate_audio_file(file: UploadFile) -> None:
    """验证音频文件"""
    file_ext = os.path.splitext(file.filename or "")[1].lower()

    if file_ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported file format. Allowed: {', '.join(ALLOWED_EXTENSIONS)}",
        )


async def save_upload_file(file: UploadFile) -> tuple[str, int]:
    """
    保存上传的文件（使用流式写入防止内存耗尽）

    Returns:
        (文件路径, 文件大小)
    """
    upload_dir = settings.UPLOAD_DIR
    os.makedirs(upload_dir, exist_ok=True)

    file_ext = os.path.splitext(file.filename or "")[1]
    unique_filename = f"{uuid.uuid4()}{file_ext}"
    file_path = os.path.join(upload_dir, unique_filename)

    file_size = 0
    chunk_size = 1024 * 1024  # 1MB chunks

    try:
        with open(file_path, "wb") as f:
            while True:
                chunk = await file.read(chunk_size)
                if not chunk:
                    break
                file_size += len(chunk)
                if file_size > settings.MAX_FILE_SIZE:
                    # 文件过大，删除已写入的部分
                    f.close()
                    os.remove(file_path)
                    raise HTTPException(
                        status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                        detail=f"File too large. Max size: {settings.MAX_FILE_SIZE // (1024 * 1024)}MB",
                    )
                f.write(chunk)
    except HTTPException:
        raise
    except Exception as e:
        if os.path.exists(file_path):
            os.remove(file_path)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to save file: {str(e)}",
        )

    return file_path, file_size


# Stage descriptions
STAGE_DESCRIPTIONS = {
    "preprocessing": "正在预处理音频...",
    "transcribing": "正在转录音频...",
    "diarizing": "正在识别说话人...",
    "generating": "正在生成会议纪要...",
}