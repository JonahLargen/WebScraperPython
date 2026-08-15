from urllib.parse import urlsplit

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
