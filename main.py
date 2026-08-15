import asyncio
import sys

from crawl import crawl_site_async


async def main():
    if len(sys.argv) < 2:
        print("no website provided")
        sys.exit(1)
    if len(sys.argv) > 2:
        print("too many arguments provided")
        sys.exit(1)

    base_url = sys.argv[1]
    print(f"starting crawl of: {base_url}")

    page_data = await crawl_site_async(base_url)
    print_report(page_data)


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
