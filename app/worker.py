"""Worker 进程入口"""
import asyncio
import logging

from app.workers.processor import task_processor

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)


async def main():
    try:
        await task_processor.start()
    finally:
        task_processor.stop()


if __name__ == "__main__":
    asyncio.run(main())
