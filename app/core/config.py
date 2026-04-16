from typing import Literal, Optional

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_ignore_empty=True, extra="ignore"
    )

    # Database Configuration
    DATABASE_URL: str = "sqlite+aiosqlite:///./storage/fastwhisper.db"

    # PostgreSQL Configuration (optional; useful when switching back to PostgreSQL)
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

    # ASR Engine Selection
    ASR_ENGINE: Literal["whisper", "sensevoice"] = "whisper"

    # Whisper Configuration
    WHISPER_MODEL: str = "large-v3"  # tiny/base/small/medium/large-v3/large-v3-turbo
    WHISPER_DEVICE: str = "cuda"  # cuda/cpu
    WHISPER_COMPUTE_TYPE: str = "float16"  # float16/int8
    WHISPER_BEAM_SIZE: int = 5
    WHISPER_TEMPERATURE: float = 0.0

    # SenseVoice (FunASR) Configuration
    SENSEVOICE_MODEL: str = "iic/SenseVoiceSmall"

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
    MAX_FILE_SIZE: int = Field(default=500 * 1024 * 1024, gt=0)  # 500MB

    # Runtime mode
    TASK_RUNNER: Literal["inline", "worker"] = "inline"
    ENABLE_SPEAKER_DIARIZATION: bool = False
    ENABLE_LLM_MINUTES: bool = False

    # Worker
    MAX_CONCURRENT_TASKS: int = Field(default=3, gt=0)
    WORKER_LEASE_SECONDS: int = Field(default=300, gt=0)
    WORKER_HEARTBEAT_SECONDS: int = Field(default=30, gt=0)

    @property
    def IS_SQLITE(self) -> bool:
        return self.DATABASE_URL.startswith("sqlite")

    @property
    def USE_INLINE_TASKS(self) -> bool:
        return self.TASK_RUNNER == "inline"

    @model_validator(mode="after")
    def validate_worker_settings(self):
        if self.WORKER_HEARTBEAT_SECONDS >= self.WORKER_LEASE_SECONDS:
            raise ValueError("WORKER_HEARTBEAT_SECONDS must be smaller than WORKER_LEASE_SECONDS.")
        return self


settings = Settings()
