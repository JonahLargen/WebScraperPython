import asyncio
import logging
import signal
import sys
import time

from config import Settings, configure_logging
from pipeline import run_report

logger = logging.getLogger(__name__)


async def main():
    configure_logging(with_timestamps=True)

    try:
        settings = Settings.from_env().validate()
    except ValueError as err:
        logger.error("%s", err)
        return 1

    if not settings.base_url:
        logger.error("CRAWL_URL is not set, nothing to crawl")
        return 1

    stop = install_signal_handlers()

    logger.info(
        "scheduler started, crawling %s every %d minutes",
        settings.base_url,
        settings.interval_minutes,
    )

    if not settings.run_on_start:
        logger.info("RUN_ON_START is off, waiting for the first interval")
        if await wait_for_stop(stop, settings.interval_minutes * 60):
            return 0

    while True:
        started = time.monotonic()
        await run_cycle(settings)
        elapsed = time.monotonic() - started

        delay = max(0.0, settings.interval_minutes * 60 - elapsed)
        logger.info("next crawl in %d minutes", round(delay / 60))
        if await wait_for_stop(stop, delay):
            break

    logger.info("scheduler stopped")

    return 0


async def run_cycle(settings):
    timeout = settings.run_timeout_minutes * 60
    try:
        await asyncio.wait_for(run_report(settings), timeout=timeout)
    except asyncio.TimeoutError:
        logger.error("crawl ran longer than %d minutes, gave up on this cycle", settings.run_timeout_minutes)
    except Exception: # a failed cycle must not stop the loop
        logger.exception("crawl cycle failed")


async def wait_for_stop(stop, seconds):
    if stop.is_set():
        return True

    try:
        await asyncio.wait_for(stop.wait(), timeout=seconds)
        return True
    except asyncio.TimeoutError:
        return False


def install_signal_handlers():
    stop = asyncio.Event()
    loop = asyncio.get_running_loop()

    for name in ("SIGINT", "SIGTERM"):
        received = getattr(signal, name, None)
        if received is None:
            continue

        try:
            loop.add_signal_handler(received, stop.set)
        except NotImplementedError: # windows has no add_signal_handler
            signal.signal(received, lambda *_: stop.set())

    return stop


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
