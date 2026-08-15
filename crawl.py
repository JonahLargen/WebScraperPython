from typing import TypedDict
from urllib.parse import urljoin, urlsplit

from bs4 import BeautifulSoup, Tag

CRAWLABLE_SCHEMES = ("http", "https")

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


def normalize_url(url):
    if not isinstance(url, str):
        raise TypeError(f"url must be a string, got {type(url).__name__}")

    stripped = url.strip()
    if not stripped:
        raise ValueError("url must not be empty")

    parts = urlsplit(stripped)
    if not parts.scheme and not parts.netloc:
        parts = urlsplit("//" + stripped)

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


def tag_text(tag) -> str:
    if not isinstance(tag, Tag):
        return ""
    
    return " ".join(tag.get_text().split()) # split()/join() collapses newlines and indentation
