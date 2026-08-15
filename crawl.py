from urllib.parse import urlsplit

from bs4 import BeautifulSoup, Tag

DEFAULT_PORTS = {
    "http": 80,
    "https": 443,
}


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


def tag_text(tag) -> str:
    if not isinstance(tag, Tag):
        return ""
    
    return " ".join(tag.get_text().split()) # split()/join() collapses newlines and indentation
