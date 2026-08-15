import asyncio
import logging
from typing import TypedDict
from urllib.parse import urljoin, urlsplit

import aiohttp
from bs4 import BeautifulSoup, Tag

CRAWLABLE_SCHEMES = ("http", "https")

USER_AGENT = "BootCrawler/1.0"

TIMEOUT_SECONDS = 10

MAX_CONCURRENCY = 5

MAX_PAGES = 100

MAX_PAGE_BYTES = 5 * 1024 * 1024

MAX_REDIRECTS = 10

RETRY_ATTEMPTS = 3

RETRY_BASE_DELAY = 1.0

MAX_RETRY_DELAY = 30.0

RETRYABLE_STATUSES = (408, 425, 429, 500, 502, 503, 504)

# extensions worth skipping before we spend a request finding out they are not html
SKIP_EXTENSIONS = (
    ".7z", ".avi", ".bmp", ".bz2", ".css", ".csv", ".doc", ".docx", ".exe",
    ".gif", ".gz", ".ico", ".jpeg", ".jpg", ".js", ".json", ".mov", ".mp3",
    ".mp4", ".pdf", ".png", ".ppt", ".pptx", ".rar", ".rss", ".svg", ".tar",
    ".txt", ".wav", ".webm", ".webp", ".woff", ".woff2", ".xls", ".xlsx",
    ".xml", ".zip",
)

DEFAULT_PORTS = {
    "http": 80,
    "https": 443,
}

logger = logging.getLogger(__name__)


class PageData(TypedDict):
    url: str
    heading: str
    first_paragraph: str
    outgoing_links: list[str]
    internal_links: list[str]
    external_links: list[str]
    internal_link_count: int
    external_link_count: int
    image_urls: list[str]


class CrawlError(Exception):
    pass


class SkipPage(CrawlError):
    pass


class RetryableError(CrawlError):
    def __init__(self, message, retry_after=None):
        super().__init__(message)
        self.retry_after = retry_after


class AsyncCrawler:
    def __init__(self, base_url, max_concurrency=MAX_CONCURRENCY, max_pages=MAX_PAGES):
        self.base_url = base_url
        self.base_domain = get_host(base_url)
        self.page_data = {}
        self.lock = asyncio.Lock()
        self.max_concurrency = max_concurrency
        self.semaphore = asyncio.Semaphore(max_concurrency)
        self.session = None
        self.max_pages = max_pages
        self.should_stop = False
        self.all_tasks = set()
        self.errors = {}

    async def __aenter__(self):
        connector = aiohttp.TCPConnector(
            limit=self.max_concurrency,
            limit_per_host=self.max_concurrency,
            ttl_dns_cache=300,
        )
        self.session = aiohttp.ClientSession(
            headers={"User-Agent": USER_AGENT},
            timeout=aiohttp.ClientTimeout(total=TIMEOUT_SECONDS),
            connector=connector,
        )
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.session.close()

    async def crawl(self):
        if not self.base_domain:
            raise ValueError(f"no host found in base_url: {self.base_url}")

        await self.crawl_page(self.base_url)

        crawled = {url: data for url, data in self.page_data.items() if data is not None}
        logger.info("crawled %d pages, %d failed", len(crawled), len(self.errors))

        return crawled

    async def crawl_page(self, current_url=None):
        if self.should_stop:
            return

        if current_url is None:
            current_url = self.base_url

        if get_host(current_url) != self.base_domain:
            return # off-site, we only crawl the one domain
        if looks_like_binary(current_url):
            return # .pdf, .zip and friends are never worth fetching

        # the semaphore caps requests in flight, and claiming inside it keeps
        # queued tasks from reserving every max_pages slot before a fetch lands
        async with self.semaphore:
            if self.should_stop:
                return

            normalized_url = normalize_url(current_url)
            if not await self.add_page_visit(normalized_url):
                return # another task got here first, or we hit max_pages

            logger.info("crawling: %s", current_url)
            try:
                html = await self.get_html(current_url)
            except Exception as err:
                self.record_error(current_url, err)
                return

        try:
            data = extract_page_data(html, current_url, self.base_domain)
        except Exception as err: # malformed markup can still blow up the parser
            self.record_error(current_url, err)
            return

        async with self.lock:
            self.page_data[normalized_url] = data

        await self.crawl_links(data["internal_links"])

    async def crawl_links(self, links):
        tasks = set()
        for url in dict.fromkeys(links): # de-duplicated, original order kept
            if self.should_stop:
                break
            if normalize_url(url) in self.page_data:
                continue # dirty read to avoid queueing a task, add_page_visit re-checks

            task = asyncio.create_task(self.crawl_page(url))
            tasks.add(task)
            self.all_tasks.add(task)

        if not tasks:
            return

        try:
            # return_exceptions keeps a cancelled child from tearing down its parent
            await asyncio.gather(*tasks, return_exceptions=True)
        finally:
            self.all_tasks -= tasks

    async def add_page_visit(self, normalized_url):
        async with self.lock:
            if self.should_stop:
                return False

            if len(self.page_data) >= self.max_pages:
                self.should_stop = True
                logger.info("Reached maximum number of pages to crawl.")
                for task in list(self.all_tasks):
                    task.cancel()
                return False

            if normalized_url in self.page_data:
                return False

            self.page_data[normalized_url] = None # claims the url before we await anything
            return True

    async def get_html(self, url):
        for attempt in range(1, RETRY_ATTEMPTS + 1):
            try:
                return await self.fetch_html(url)
            except RetryableError as err:
                if attempt == RETRY_ATTEMPTS:
                    raise

                delay = retry_delay(attempt, err.retry_after)
                logger.warning("  retrying %s in %.1fs (%s)", url, delay, err)
                await asyncio.sleep(delay)

    async def fetch_html(self, url):
        try:
            async with self.session.get(
                url,
                allow_redirects=True,
                max_redirects=MAX_REDIRECTS,
            ) as response:
                if response.status in RETRYABLE_STATUSES:
                    raise RetryableError(
                        f"HTTP {response.status}",
                        retry_after=parse_retry_after(response.headers.get("Retry-After")),
                    )
                if response.status >= 400:
                    raise SkipPage(f"HTTP {response.status}")

                content_type = response.headers.get("Content-Type", "")
                if not content_type.strip().lower().startswith("text/html"):
                    raise SkipPage(f"expected text/html, got '{content_type}'")

                declared_bytes = parse_int(response.headers.get("Content-Length"))
                if declared_bytes is not None and declared_bytes > MAX_PAGE_BYTES:
                    raise SkipPage(f"page declares {declared_bytes} bytes, over the limit")

                body = await response.content.read(MAX_PAGE_BYTES + 1)
                if len(body) > MAX_PAGE_BYTES:
                    raise SkipPage(f"page is over the {MAX_PAGE_BYTES} byte limit")

                return decode_body(body, response.charset)
        except aiohttp.TooManyRedirects as err:
            raise SkipPage(f"too many redirects: {err}") from err
        except (aiohttp.ClientError, asyncio.TimeoutError, OSError) as err:
            raise RetryableError(f"{type(err).__name__}: {err}") from err

    def record_error(self, url, err):
        message = f"{type(err).__name__}: {err}"
        self.errors[url] = message
        logger.warning("  skipping %s (%s)", url, message)


async def crawl_site_async(base_url, max_concurrency=MAX_CONCURRENCY, max_pages=MAX_PAGES):
    async with AsyncCrawler(base_url, max_concurrency, max_pages) as crawler:
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


def extract_page_data(html: str, page_url: str, base_domain=None) -> PageData:
    if base_domain is None:
        base_domain = get_host(page_url)

    outgoing_links = get_urls_from_html(html, page_url)
    internal_links, external_links = classify_links(outgoing_links, base_domain)

    return {
        "url": page_url,
        "heading": get_heading_from_html(html),
        "first_paragraph": get_first_paragraph_from_html(html),
        "outgoing_links": outgoing_links,
        "internal_links": internal_links,
        "external_links": external_links,
        "internal_link_count": len(internal_links),
        "external_link_count": len(external_links),
        "image_urls": get_images_from_html(html, page_url),
    }


def classify_links(urls, base_domain):
    internal = []
    external = []
    for url in urls:
        if get_host(url) == base_domain:
            internal.append(url)
        else:
            external.append(url)

    return internal, external


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


def looks_like_binary(url):
    return split_url(url).path.lower().endswith(SKIP_EXTENSIONS)


def decode_body(body, charset):
    for encoding in (charset, "utf-8"):
        if not encoding:
            continue

        try:
            return body.decode(encoding)
        except (LookupError, UnicodeDecodeError):
            continue

    return body.decode("utf-8", errors="replace")


def parse_int(value):
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def parse_retry_after(value):
    seconds = parse_int(value) # http-date form is ignored, we fall back to backoff
    if seconds is None or seconds < 0:
        return None

    return float(seconds)


def retry_delay(attempt, retry_after=None):
    if retry_after is not None:
        return min(retry_after, MAX_RETRY_DELAY)

    return min(RETRY_BASE_DELAY * 2 ** (attempt - 1), MAX_RETRY_DELAY)


def tag_text(tag) -> str:
    if not isinstance(tag, Tag):
        return ""

    return " ".join(tag.get_text().split()) # split()/join() collapses newlines and indentation
