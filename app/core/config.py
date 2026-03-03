from typing import Optional

from pydantic import PostgresDsn, computed_field
from pydantic_core import MultiHostUrl
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_ignore_empty=True, extra="ignore"
    )

    # PostgreSQL Configuration
    POSTGRES_SERVER: str = "localhost"
    POSTGRES_PORT: int = 5432
    POSTGRES_USER: str = "postgres"
    POSTGRES_PASSWORD: str = ""
    POSTGRES_DB: str = "fastwhisper"

    # Redis Configuration
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_PASSWORD: Optional[str] = None

    # Auth - 固定 Token 认证
    API_TOKEN: str = ""

    # Whisper Configuration
    WHISPER_MODEL: str = "large-v3"  # tiny/base/small/medium/large-v3
    WHISPER_DEVICE: str = "cuda"  # cuda/cpu
    WHISPER_COMPUTE_TYPE: str = "float16"  # float16/int8

    # Diarization - pyannote 需要 HuggingFace Token
    HUGGINGFACE_TOKEN: str = ""

    # LLM Configuration
    LLM_PROVIDER: str = "qwen"  # qwen/wenxin/zhipu
    LLM_API_KEY: str = ""
    LLM_MODEL: str = "qwen-max"
    LLM_BASE_URL: Optional[str] = None

    # Storage
    UPLOAD_DIR: str = "./storage/uploads"
    RESULT_DIR: str = "./storage/results"
    MAX_FILE_SIZE: int = 500 * 1024 * 1024  # 500MB

    # Worker
    MAX_CONCURRENT_TASKS: int = 3

    @computed_field
    @property
    def DATABASE_URL(self) -> PostgresDsn:
        return MultiHostUrl.build(
            scheme="postgresql+asyncpg",
            username=self.POSTGRES_USER,
            password=self.POSTGRES_PASSWORD,
            host=self.POSTGRES_SERVER,
            port=self.POSTGRES_PORT,
            path=self.POSTGRES_DB,
        )


settings = Settings()