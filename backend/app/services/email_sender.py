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
    Supports TLS & SSL encryption, auto-port failover (587 -> 465), and dynamic DB overrides.
    """
    import socket
    # 1. Resolve credentials from custom config or fallback to .env settings
    host = (smtp_config or {}).get("smtp_host") or settings.SMTP_HOST or "smtp.gmail.com"
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
    
    def _try_connect(target_port: int):
        if target_port == 465:
            logger.info(f"SMTP: Connecting via Secure SSL to {host}:{target_port}...")
            return smtplib.SMTP_SSL(host, target_port, timeout=15)
        else:
            logger.info(f"SMTP: Connecting via TLS to {host}:{target_port}...")
            srv = smtplib.SMTP(host, target_port, timeout=15)
            srv.starttls()
            return srv

    server = None
    try:
        server = _try_connect(port)
    except Exception as primary_err:
        logger.warning(f"Primary SMTP connection to {host}:{port} failed: {primary_err}. Retrying via fallback port...")
        fallback_port = 465 if port != 465 else 587
        try:
            server = _try_connect(fallback_port)
        except Exception as fallback_err:
            logger.error(f"Fallback SMTP connection to {host}:{fallback_port} failed: {fallback_err}")
            raise primary_err

    try:
        server.login(username, password)
        server.sendmail(from_email, to_email, msg.as_string())
        server.quit()
        logger.info(f"Email successfully sent to {to_email} using SMTP username: {username}")
        return True
    except Exception as e:
        logger.error(f"Failed to send SMTP email to {to_email} using host {host}: {str(e)}")
        raise e

async def send_smtp_email(to_email: str, subject: str, html_content: str, smtp_config: Optional[dict] = None) -> bool:
    """
    Unified entry point for sending emails.
    Supports SMTP, Resend API (HTTP), and SendGrid API (HTTP).
    """
    config = smtp_config or {}
    provider = config.get("email_service_provider") or "SMTP"
    
    if provider == "Resend":
        return await send_resend_email(to_email, subject, html_content, config)
    elif provider == "SendGrid":
        return await send_sendgrid_email(to_email, subject, html_content, config)
    else:
        # Standard SMTP Fallback
        return await asyncio.to_thread(send_smtp_email_sync, to_email, subject, html_content, smtp_config)

async def send_resend_email(to_email: str, subject: str, html_content: str, config: dict) -> bool:
    import httpx
    api_key = config.get("resend_api_key")
    from_email = config.get("smtp_email") or "onboarding@resend.dev"
    
    if not api_key:
        logger.error("Resend API Key is missing in settings.")
        raise Exception("Resend API Key is missing")
        
    url = "https://api.resend.com/emails"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    payload = {
        "from": from_email,
        "to": [to_email],
        "subject": subject,
        "html": html_content
    }
    
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            r = await client.post(url, json=payload, headers=headers)
            if r.status_code in [200, 201, 202]:
                logger.info(f"Resend: Email successfully sent to {to_email}")
                return True
            else:
                logger.error(f"Resend API failed: Status {r.status_code} - {r.text}")
                raise Exception(f"Resend API failed (HTTP {r.status_code}): {r.text}")
    except Exception as e:
        logger.error(f"Resend exception when sending to {to_email}: {e}")
        raise e

async def send_sendgrid_email(to_email: str, subject: str, html_content: str, config: dict) -> bool:
    import httpx
    api_key = config.get("sendgrid_api_key")
    sender_email = config.get("sendgrid_sender") or config.get("smtp_email")
    
    if not api_key:
        logger.error("SendGrid API Key is missing in settings.")
        raise Exception("SendGrid API Key is missing")
    if not sender_email:
        logger.error("SendGrid verified sender email is missing in settings.")
        raise Exception("SendGrid verified sender email is missing")
        
    url = "https://api.sendgrid.com/v3/mail/send"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    payload = {
        "personalizations": [
            {
                "to": [
                    {
                        "email": to_email
                    }
                ]
            }
        ],
        "from": {
            "email": sender_email
        },
        "subject": subject,
        "content": [
            {
                "type": "text/html",
                "value": html_content
            }
        ]
    }
    
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            r = await client.post(url, json=payload, headers=headers)
            if r.status_code in [200, 201, 202]:
                logger.info(f"SendGrid: Email successfully sent to {to_email}")
                return True
            else:
                logger.error(f"SendGrid API failed: Status {r.status_code} - {r.text}")
                raise Exception(f"SendGrid API failed (HTTP {r.status_code}): {r.text}")
    except Exception as e:
        logger.error(f"SendGrid exception when sending to {to_email}: {e}")
        raise e

