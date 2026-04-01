import pytest

from app.core.config import Settings


def test_worker_heartbeat_must_be_smaller_than_lease():
    with pytest.raises(ValueError, match="WORKER_HEARTBEAT_SECONDS"):
        Settings(
            _env_file=None,
            WORKER_LEASE_SECONDS=30,
            WORKER_HEARTBEAT_SECONDS=30,
        )


def test_worker_settings_accept_valid_values():
    settings = Settings(
        _env_file=None,
        WORKER_LEASE_SECONDS=60,
        WORKER_HEARTBEAT_SECONDS=15,
    )

    assert settings.WORKER_LEASE_SECONDS == 60
    assert settings.WORKER_HEARTBEAT_SECONDS == 15


def test_default_settings_use_local_sqlite_inline_mode():
    settings = Settings(_env_file=None)

    assert settings.DATABASE_URL.startswith("sqlite+aiosqlite:///")
    assert settings.USE_INLINE_TASKS is True
    assert settings.ENABLE_LLM_MINUTES is False
