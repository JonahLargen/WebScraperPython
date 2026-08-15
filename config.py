import logging
import os
import sys
from dataclasses import dataclass, field

from crawl import MAX_CONCURRENCY, MAX_PAGES

DEFAULT_INTERVAL_MINUTES = 60

DEFAULT_RUN_TIMEOUT_MINUTES = 30


@dataclass
class Settings:
    base_url: str = ""
    max_concurrency: int = MAX_CONCURRENCY
    max_pages: int = MAX_PAGES
    output_dir: str = "."
    json_filename: str = "report.json"
    graph_filename: str = "report.png"
    graph_enabled: bool = True
    interval_minutes: int = DEFAULT_INTERVAL_MINUTES
    run_timeout_minutes: int = DEFAULT_RUN_TIMEOUT_MINUTES
    run_on_start: bool = True
    email_enabled: bool = False
    email_from: str = ""
    email_to: list[str] = field(default_factory=list)
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_username: str = ""
    smtp_password: str = ""
    smtp_security: str = "starttls" # starttls, ssl or none

    @classmethod
    def from_env(cls):
        return cls(
            base_url=env_str("CRAWL_URL"),
            max_concurrency=env_int("MAX_CONCURRENCY", MAX_CONCURRENCY),
            max_pages=env_int("MAX_PAGES", MAX_PAGES),
            output_dir=env_str("OUTPUT_DIR", "."),
            json_filename=env_str("JSON_FILENAME", "report.json"),
            graph_filename=env_str("GRAPH_FILENAME", "report.png"),
            graph_enabled=env_bool("GRAPH_ENABLED", True),
            interval_minutes=env_int("CRAWL_INTERVAL_MINUTES", DEFAULT_INTERVAL_MINUTES),
            run_timeout_minutes=env_int("RUN_TIMEOUT_MINUTES", DEFAULT_RUN_TIMEOUT_MINUTES),
            run_on_start=env_bool("RUN_ON_START", True),
            email_enabled=env_bool("EMAIL_ENABLED", False),
            email_from=env_str("EMAIL_FROM"),
            email_to=env_list("EMAIL_TO"),
            smtp_host=env_str("SMTP_HOST"),
            smtp_port=env_int("SMTP_PORT", 587),
            smtp_username=env_str("SMTP_USERNAME"),
            smtp_password=env_str("SMTP_PASSWORD", strip=False),
            smtp_security=env_str("SMTP_SECURITY", "starttls").lower(),
        )

    def json_path(self):
        return self.build_path(self.json_filename)

    def graph_path(self):
        return self.build_path(self.graph_filename)

    def build_path(self, filename):
        if not self.output_dir or self.output_dir == ".":
            return filename

        return os.path.join(self.output_dir, filename)

    def validate(self):
        problems = []

        if self.max_concurrency < 1:
            problems.append("MAX_CONCURRENCY must be at least 1")
        if self.max_pages < 1:
            problems.append("MAX_PAGES must be at least 1")
        if self.interval_minutes < 1:
            problems.append("CRAWL_INTERVAL_MINUTES must be at least 1")
        if self.run_timeout_minutes < 1:
            problems.append("RUN_TIMEOUT_MINUTES must be at least 1")

        if self.email_enabled:
            if not self.smtp_host:
                problems.append("SMTP_HOST is required when EMAIL_ENABLED is true")
            if not self.email_from:
                problems.append("EMAIL_FROM is required when EMAIL_ENABLED is true")
            if not self.email_to:
                problems.append("EMAIL_TO is required when EMAIL_ENABLED is true")
            if self.smtp_security not in ("starttls", "ssl", "none"):
                problems.append("SMTP_SECURITY must be one of: starttls, ssl, none")

        if problems:
            raise ValueError("invalid configuration:\n  " + "\n  ".join(problems))

        return self


def configure_logging(with_timestamps=False):
    # stdout, not the default stderr, so the crawl log stays in one stream
    logging.basicConfig(
        level=logging.INFO,
        stream=sys.stdout,
        format="%(asctime)s %(levelname)s %(message)s" if with_timestamps else "%(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    for name in ("aiohttp", "asyncio", "matplotlib", "PIL"):
        logging.getLogger(name).setLevel(logging.WARNING)


def env_str(name, default="", strip=True):
    value = os.environ.get(name)
    if value is None:
        return default

    return value.strip() if strip else value


def env_int(name, default):
    raw = os.environ.get(name, "").strip()
    if not raw:
        return default

    try:
        return int(raw)
    except ValueError as err:
        raise ValueError(f"{name} must be a whole number, got '{raw}'") from err


def env_bool(name, default=False):
    raw = os.environ.get(name, "").strip().lower()
    if not raw:
        return default

    return raw in ("1", "true", "yes", "on")


def env_list(name):
    return [item.strip() for item in os.environ.get(name, "").split(",") if item.strip()]
