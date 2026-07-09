import smtplib
import logging
import asyncio
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Optional
from app.config.settings import settings

logger = logging.getLogger(__name__)

def send_smtp_email_sync(to_email: str, subject: str, html_content: str, smtp_config: Optional[dict] = None) -> bool:
    """
    Synchronous SMTP email sending.
    Supports TLS encryption. Supports dynamic DB overrides.
    """
    # 1. Resolve credentials from custom config or fallback to .env settings
    host = (smtp_config or {}).get("smtp_host") or settings.SMTP_HOST
    port = (smtp_config or {}).get("smtp_port") or settings.SMTP_PORT or 587
    username = (smtp_config or {}).get("smtp_email") or settings.SMTP_USERNAME
    password = (smtp_config or {}).get("smtp_password") or settings.SMTP_PASSWORD
    from_email = (smtp_config or {}).get("smtp_email") or settings.SMTP_FROM_EMAIL or settings.SMTP_USERNAME

    # Convert port safely
    try:
        port = int(port)
    except (ValueError, TypeError):
        port = 587

    if not host or not username or not password:
        logger.warning("SMTP configurations are missing (neither in DB settings nor in .env). Skipping email delivery.")
        return False
        
    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = from_email
    msg["To"] = to_email
    
    # Attach HTML body
    part = MIMEText(html_content, "html")
    msg.attach(part)
    
    try:
        # Connect using TLS
        server = smtplib.SMTP(host, port, timeout=10)
        server.starttls()
        server.login(username, password)
        server.sendmail(from_email, to_email, msg.as_string())
        server.quit()
        logger.info(f"Email successfully sent to {to_email} using SMTP username: {username}")
        return True
    except Exception as e:
        logger.error(f"Failed to send SMTP email to {to_email} using host {host}: {str(e)}")
        return False

async def send_smtp_email(to_email: str, subject: str, html_content: str, smtp_config: Optional[dict] = None) -> bool:
    """
    Asynchronous SMTP email sending (runs sync SMTP in a separate thread).
    """
    return await asyncio.to_thread(send_smtp_email_sync, to_email, subject, html_content, smtp_config)
