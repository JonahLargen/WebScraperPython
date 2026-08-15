import asyncio
import sys

from crawl import MAX_CONCURRENCY, MAX_PAGES, crawl_site_async


async def main():
    base_url, max_concurrency, max_pages = parse_args(sys.argv)

    print(f"starting crawl of: {base_url}")
    print(f"max_concurrency: {max_concurrency}, max_pages: {max_pages}")

    page_data = await crawl_site_async(base_url, max_concurrency, max_pages)
    print_report(page_data)


def parse_args(argv):
    if len(argv) < 2:
        print("no website provided")
        sys.exit(1)
    if len(argv) > 4:
        print("too many arguments provided")
        sys.exit(1)

    base_url = argv[1]
    max_concurrency = parse_positive_int(argv, 2, "max_concurrency", MAX_CONCURRENCY)
    max_pages = parse_positive_int(argv, 3, "max_pages", MAX_PAGES)

    return base_url, max_concurrency, max_pages


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


def print_report(page_data):
    print()
    print("=" * 60)
    print(f"crawl complete: {len(page_data)} pages found")
    print("=" * 60)

    for data in page_data.values():
        print()
        print(data["url"])
        print(f"  heading:         {truncate(data['heading'])}")
        print(f"  first paragraph: {truncate(data['first_paragraph'])}")
        print(f"  outgoing links:  {len(data['outgoing_links'])}")
        print(f"  images:          {len(data['image_urls'])}")


def truncate(text, limit=80):
    if len(text) <= limit:
        return text

    return text[: limit - 3] + "..."


if __name__ == "__main__":
    asyncio.run(main())
