import asyncio
import sys

from config import Settings, configure_logging
from pipeline import run_report


async def main():
    configure_logging()

    try:
        settings = Settings.from_env()
    except ValueError as err:
        print(err)
        sys.exit(1)

    apply_args(settings, sys.argv)

    await run_report(settings)


def apply_args(settings, argv):
    if len(argv) < 2:
        print("no website provided")
        sys.exit(1)
    if len(argv) > 4:
        print("too many arguments provided")
        sys.exit(1)

    settings.base_url = argv[1]
    settings.max_concurrency = parse_positive_int(
        argv, 2, "max_concurrency", settings.max_concurrency
    )
    settings.max_pages = parse_positive_int(argv, 3, "max_pages", settings.max_pages)

    return settings


def parse_positive_int(argv, index, name, default):
    if len(argv) <= index:
        return default

    try:
        value = int(argv[index])
    except ValueError:
        print(f"{name} must be a whole number, got '{argv[index]}'")
        sys.exit(1)

    if value < 1:
        print(f"{name} must be at least 1, got {value}")
        sys.exit(1)

    return value


if __name__ == "__main__":
    asyncio.run(main())
