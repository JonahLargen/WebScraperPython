import asyncio
from typing import TypedDict
from urllib.parse import urljoin, urlsplit

import aiohttp
from bs4 import BeautifulSoup, Tag

CRAWLABLE_SCHEMES = ("http", "https")

USER_AGENT = "BootCrawler/1.0"

TIMEOUT_SECONDS = 10

MAX_CONCURRENCY = 5

DEFAULT_PORTS = {
    "http": 80,
    "https": 443,
}


class PageData(TypedDict):
    url: str
    heading: str
    first_paragraph: str
    outgoing_links: list[str]
    image_urls: list[str]


class AsyncCrawler:
    def __init__(self, base_url, max_concurrency=MAX_CONCURRENCY):
        self.base_url = base_url
        self.base_domain = get_host(base_url)
        self.page_data = {}
        self.lock = asyncio.Lock()
        self.max_concurrency = max_concurrency
        self.semaphore = asyncio.Semaphore(max_concurrency)
        self.session = None

    async def __aenter__(self):
        self.session = aiohttp.ClientSession(
            headers={"User-Agent": USER_AGENT},
            timeout=aiohttp.ClientTimeout(total=TIMEOUT_SECONDS),
        )
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.session.close()

    async def crawl(self):
        await self.crawl_page(self.base_url)
        return {url: data for url, data in self.page_data.items() if data is not None}

    async def crawl_page(self, current_url=None):
        if current_url is None:
            current_url = self.base_url

        if get_host(current_url) != self.base_domain:
            return # off-site, we only crawl the one domain

        normalized_url = normalize_url(current_url)
        if not await self.add_page_visit(normalized_url):
            return # another task got here first

        async with self.semaphore: # caps how many requests are in flight at once
            print(f"crawling: {current_url}")
            try:
                html = await self.get_html(current_url)
            except Exception as err:
                print(f"  skipping {current_url}: {err}")
                return

        data = extract_page_data(html, current_url)
        async with self.lock:
            self.page_data[normalized_url] = data

        tasks = [
            asyncio.create_task(self.crawl_page(url))
            for url in data["outgoing_links"]
        ]
        await asyncio.gather(*tasks)

    async def add_page_visit(self, normalized_url):
        async with self.lock:
            if normalized_url in self.page_data:
                return False

            self.page_data[normalized_url] = None # claims the url before we await anything
            return True

    async def get_html(self, url):
        async with self.session.get(url) as response:
            response.raise_for_status() # raises aiohttp.ClientResponseError on 400+

            content_type = response.headers.get("Content-Type", "")
            if not content_type.strip().lower().startswith("text/html"):
                raise ValueError(f"expected text/html, got '{content_type}' for {url}")

            return await response.text()


async def crawl_site_async(base_url, max_concurrency=MAX_CONCURRENCY):
    async with AsyncCrawler(base_url, max_concurrency) as crawler:
        return await crawler.crawl()


def normalize_url(url):
    if not isinstance(url, str):
        raise TypeError(f"url must be a string, got {type(url).__name__}")

    stripped = url.strip()
    if not stripped:
        raise ValueError("url must not be empty")

    parts = split_url(stripped)

    host = parts.hostname
    if not host:
        raise ValueError(f"no host found in url: {url}")
    if ":" in host: # IPv6 literal
        host = f"[{host}]"

    port = parts.port
    if port is not None and port != DEFAULT_PORTS.get(parts.scheme.lower()):
        host = f"{host}:{port}"

    path = parts.path.rstrip("/")

    return host + path


def extract_page_data(html: str, page_url: str) -> PageData:
    return {
        "url": page_url,
        "heading": get_heading_from_html(html),
        "first_paragraph": get_first_paragraph_from_html(html),
        "outgoing_links": get_urls_from_html(html, page_url),
        "image_urls": get_images_from_html(html, page_url),
    }


def get_heading_from_html(html: str) -> str:
    soup = BeautifulSoup(html, "html.parser")
    heading = soup.find("h1") or soup.find("h2")
    return tag_text(heading)


def get_first_paragraph_from_html(html: str) -> str:
    soup = BeautifulSoup(html, "html.parser")
    main = soup.find("main")

    paragraph = main.find("p") if isinstance(main, Tag) else None
    if paragraph is None: # no <main>, or a <main> with no <p> in it
        paragraph = soup.find("p")

    return tag_text(paragraph)


def get_urls_from_html(html, base_url):
    return get_links_from_html(html, base_url, "a", "href")


def get_images_from_html(html, base_url):
    return get_links_from_html(html, base_url, "img", "src")


def get_links_from_html(html, base_url, tag_name, attribute):
    soup = BeautifulSoup(html, "html.parser")

    urls = []
    for tag in soup.find_all(tag_name):
        value = tag.get(attribute)
        if not isinstance(value, str) or not value.strip():
            continue # the attribute is missing or empty

        url = urljoin(base_url, value.strip())
        if urlsplit(url).scheme in CRAWLABLE_SCHEMES: # skips mailto:, tel:, javascript:, data:
            urls.append(url)

    return urls


def split_url(url):
    parts = urlsplit(url.strip())
    if not parts.scheme and not parts.netloc: # ensures the host lands in netloc, adds the "//" urlsplit needs to see one
        parts = urlsplit("//" + url.strip())

    return parts


def get_host(url):
    return split_url(url).hostname or ""


def tag_text(tag) -> str:
    if not isinstance(tag, Tag):
        return ""
    
    return " ".join(tag.get_text().split()) # split()/join() collapses newlines and indentation
