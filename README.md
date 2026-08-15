# Web Scraper - Python

Async crawler for a single domain. Extracts the heading, first paragraph, links and images from each page, writes them to JSON, and renders a graph of the links between pages.

## Usage

```bash
# uv run main.py URL [max_concurrency] [max_pages]
uv run main.py "https://learnwebscraping.dev/practice/ecommerce/" 3 25

uv run -m unittest
```

Writes `report.json` and `report.png` to the working directory.

## Output

`report.json` is a list, one object per page, sorted by url:

```json
{
  "url": "https://learnwebscraping.dev/practice/ecommerce/",
  "heading": "Practice Store",
  "first_paragraph": "Browse the catalog.",
  "outgoing_links": ["..."],
  "internal_links": ["..."],
  "external_links": ["..."],
  "internal_link_count": 12,
  "external_link_count": 3,
  "image_urls": ["..."]
}
```

`outgoing_links` is every link on the page. `internal_links` and `external_links` split that list by host, so the two add up to it. A different subdomain counts as external because the crawler won't follow it.

`report.png` is a node per crawled page and an edge per internal link between two of them. Node size is inbound links, colour is external link count. Labels are dropped past 60 nodes.

## Scheduling

`scheduler.py` runs the crawl on a timer and emails the reports. Config is environment variables, listed below and in `.env.example`.

```bash
cp .env.example .env
uv run scheduler.py
```

The interval is start to start, not end to start, so a slow crawl doesn't push the schedule later every cycle. A crawl still running after `RUN_TIMEOUT_MINUTES` is abandoned and retried on the next tick. A cycle that throws is logged and the loop continues.

## Docker

```bash
cp .env.example .env
mkdir -p output
docker compose up -d --build
docker compose logs -f
```

Reports land in `./output`. `docker compose stop` waits for the current crawl rather than killing it mid-request.

## Config

| Variable | Default | |
| --- | --- | --- |
| `CRAWL_URL` | | required by `scheduler.py`, `main.py` takes it as an argument |
| `MAX_CONCURRENCY` | `5` | requests in flight |
| `MAX_PAGES` | `100` | ceiling, not a target. in-flight requests are cancelled when it trips, so expect a couple fewer |
| `CRAWL_INTERVAL_MINUTES` | `60` | |
| `RUN_TIMEOUT_MINUTES` | `30` | kill a crawl that overruns |
| `RUN_ON_START` | `true` | `false` waits one interval first |
| `OUTPUT_DIR` | `.` | |
| `JSON_FILENAME` | `report.json` | |
| `GRAPH_FILENAME` | `report.png` | |
| `GRAPH_ENABLED` | `true` | |
| `EMAIL_ENABLED` | `false` | |
| `EMAIL_FROM` | | |
| `EMAIL_TO` | | comma separated |
| `SMTP_HOST` | | |
| `SMTP_PORT` | `587` | |
| `SMTP_USERNAME` | | leave empty to send unauthenticated |
| `SMTP_PASSWORD` | | app password, not your account password |
| `SMTP_SECURITY` | `starttls` | `starttls`, `ssl` or `none` |

## Caveats

Scope is the host, not the path. Start it at `/docs/` and site-wide nav will walk it across the whole domain.

No robots.txt handling, and no delay between requests beyond the concurrency cap. Don't leave it running against someone else's site on a five minute timer.

Known binary extensions are skipped without a request. 429s and 5xx are retried with backoff and honour `Retry-After`. Bodies are capped at 5MB. A page that fails is recorded so it isn't retried from every other page that links to it.
