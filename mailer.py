import logging
import mimetypes
import os
import smtplib
import ssl
from email.message import EmailMessage

MAX_ATTACHMENT_BYTES = 10 * 1024 * 1024

logger = logging.getLogger(__name__)


def send_report_email(settings, page_data, attachments):
    settings.validate()

    message = EmailMessage()
    message["Subject"] = f"Crawl report for {settings.base_url}"
    message["From"] = settings.email_from
    message["To"] = ", ".join(settings.email_to)
    message.set_content(build_summary(settings, page_data))

    for path in attachments:
        attach_file(message, path)

    send_message(settings, message)
    logger.info("emailed report to %s", ", ".join(settings.email_to))


def build_summary(settings, page_data):
    pages = list(page_data.values())
    internal_links = sum(page["internal_link_count"] for page in pages)
    external_links = sum(page["external_link_count"] for page in pages)
    images = sum(len(page["image_urls"]) for page in pages)

    lines = [
        f"Crawl of {settings.base_url}",
        "",
        f"pages crawled:  {len(pages)}",
        f"internal links: {internal_links}",
        f"external links: {external_links}",
        f"images:         {images}",
        "",
        "Most linked-out pages:",
    ]

    busiest = sorted(pages, key=lambda page: page["external_link_count"], reverse=True)
    for page in busiest[:10]:
        lines.append(
            f"  {page['external_link_count']:>4} external  {page['url']}"
        )

    lines.append("")
    lines.append("The full report is attached.")

    return "\n".join(lines)


def attach_file(message, path):
    if not path or not os.path.exists(path):
        logger.warning("attachment %s does not exist, skipping it", path)
        return

    size = os.path.getsize(path)
    if size > MAX_ATTACHMENT_BYTES:
        logger.warning("attachment %s is %d bytes, too big to send", path, size)
        return

    mime_type, _ = mimetypes.guess_type(path)
    maintype, _, subtype = (mime_type or "application/octet-stream").partition("/")

    with open(path, "rb") as attachment:
        message.add_attachment(
            attachment.read(),
            maintype=maintype,
            subtype=subtype,
            filename=os.path.basename(path),
        )


def send_message(settings, message):
    if settings.smtp_security == "ssl":
        client = smtplib.SMTP_SSL(
            settings.smtp_host,
            settings.smtp_port,
            context=ssl.create_default_context(),
            timeout=30,
        )
    else:
        client = smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=30)

    with client:
        if settings.smtp_security == "starttls":
            client.starttls(context=ssl.create_default_context())
        if settings.smtp_username:
            client.login(settings.smtp_username, settings.smtp_password)

        client.send_message(message)
