"""fb-leme-shadow: simulações shadow LONG/SHORT para recovery do Guardian."""
import asyncio
import logging
import os

from shadow_simulator import LongShadowScanner, ShortShadowScanner

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("fb-leme-shadow")

DATABASE_URL = os.getenv("DATABASE_URL", "")


async def main():
    logger.info("fb-leme-shadow iniciando (LONG + SHORT scanners)...")
    long_shadow = LongShadowScanner(DATABASE_URL)
    short_shadow = ShortShadowScanner(DATABASE_URL)
    asyncio.create_task(long_shadow.run_loop())
    asyncio.create_task(short_shadow.run_loop())
    while True:
        await asyncio.sleep(3600)


if __name__ == "__main__":
    asyncio.run(main())
