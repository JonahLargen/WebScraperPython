import logging
import os

from crawl import crawl_site_async
from json_report import write_json_report

logger = logging.getLogger(__name__)


async def run_report(settings):
    settings.validate()

    logger.info("starting crawl of: %s", settings.base_url)
    logger.info(
        "max_concurrency: %d, max_pages: %d",
        settings.max_concurrency,
        settings.max_pages,
    )

    page_data = await crawl_site_async(
        settings.base_url,
        settings.max_concurrency,
        settings.max_pages,
    )

    if settings.output_dir:
        os.makedirs(settings.output_dir, exist_ok=True)

    attachments = []

    json_path = write_json_report(page_data, settings.json_path())
    attachments.append(json_path)
    logger.info("crawl complete: %d pages written to %s", len(page_data), json_path)

    graph_path = write_graph(settings, page_data)
    if graph_path:
        attachments.append(graph_path)

    send_email(settings, page_data, attachments)

    return page_data


def write_graph(settings, page_data):
    if not settings.graph_enabled:
        return None

    try:
        # imported here so a missing matplotlib never costs us the json report
        from graph_report import write_graph_report

        graph_path = write_graph_report(page_data, settings.graph_path())
    except Exception:
        logger.exception("could not write the graph image")
        return None

    if graph_path:
        logger.info("graph written to %s", graph_path)

    return graph_path


def send_email(settings, page_data, attachments):
    if not settings.email_enabled:
        return

    try:
        from mailer import send_report_email

        send_report_email(settings, page_data, attachments)
    except Exception:
        logger.exception("could not email the report")
