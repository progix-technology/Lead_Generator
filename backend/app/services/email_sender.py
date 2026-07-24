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
    from app.services.email_verifier import is_email_sendable

    # 0. Pre-flight check — block platform/disposable/no-reply emails before SMTP
    can_send, preflight_reason = is_email_sendable(to_email)
    if not can_send:
        logger.warning(f"SMTP send blocked (pre-flight): {to_email} — {preflight_reason}")
        return False

    # 1. Resolve credentials from custom config or fallback to .env settings
    smtp_config = smtp_config or {}
    host = smtp_config.get("smtp_host") or settings.SMTP_HOST
    port = smtp_config.get("smtp_port") or settings.SMTP_PORT
    # In the DB schema, smtp_email acts as the username/sender. 
    username = smtp_config.get("smtp_username") or smtp_config.get("smtp_email") or settings.SMTP_USERNAME
    password = smtp_config.get("smtp_password") or settings.SMTP_PASSWORD
    from_email = smtp_config.get("smtp_email") or settings.SMTP_FROM_EMAIL or username or settings.SMTP_USERNAME

    # Convert port safely
    try:
        port = int(port)
    except (ValueError, TypeError):
        port = 587

    if not host or not username or not password:
        logger.warning("SMTP configurations are missing (neither in DB settings nor in .env). Skipping email delivery.")
        return False

    if password:
        password = str(password).strip()
        if "gmail" in str(host).lower():
            password = password.replace(" ", "")
        
    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = from_email
    msg["To"] = to_email
    
    # Attach HTML body
    part = MIMEText(html_content, "html")
    msg.attach(part)
    
    def _try_connect(target_port: int):
        # Force IPv4 socket resolution to prevent Linux/cloud IPv6 '[Errno 101] Network is unreachable' errors
        ipv4_target = host
        try:
            addrs = socket.getaddrinfo(host, target_port, family=socket.AF_INET, type=socket.SOCK_STREAM)
            if addrs:
                ipv4_target = addrs[0][4][0]
        except Exception:
            pass

        if target_port == 465:
            logger.info(f"SMTP: Connecting via Secure SSL to {host} ({ipv4_target}):{target_port}...")
            return smtplib.SMTP_SSL(ipv4_target, target_port, timeout=120)
        else:
            logger.info(f"SMTP: Connecting via TLS to {host} ({ipv4_target}):{target_port}...")
            srv = smtplib.SMTP(ipv4_target, target_port, timeout=120)
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
    Includes automatic fallback to Resend if SMTP fails.
    """
    import logging
    logger = logging.getLogger(__name__)
    
    config = smtp_config or {}
    provider = config.get("email_service_provider") or "SMTP"
    
    try:
        if provider == "Resend":
            return await send_resend_email(to_email, subject, html_content, config)
        elif provider == "SendGrid":
            return await send_sendgrid_email(to_email, subject, html_content, config)
        else:
            # Standard SMTP Fallback
            return await asyncio.to_thread(send_smtp_email_sync, to_email, subject, html_content, config)
    except Exception as e:
        # AUTOMATIC FALLBACK: If primary provider (SMTP) fails and Resend key is available, try Resend
        if provider != "Resend" and config.get("resend_api_key"):
            logger.warning(f"Primary provider '{provider}' failed ({e}). Auto-falling back to Resend API...")
            try:
                return await send_resend_email(to_email, subject, html_content, config)
            except Exception as resend_err:
                logger.error(f"Fallback Resend API also failed: {resend_err}")
                raise Exception(f"{provider} failed ({str(e)}) AND Fallback Resend failed ({str(resend_err)})")
        
        # If no fallback available or it's already Resend, re-raise original error
        raise e

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

