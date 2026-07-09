import smtplib
import socket
import dns.resolver
import logging
import asyncio
from typing import Tuple

logger = logging.getLogger(__name__)

def verify_email_existence_sync(email: str, from_email: str = "progixtechnology@gmail.com") -> Tuple[bool, str]:
    """
    Performs an SMTP handshake check to verify if the email mailbox exists.
    Does NOT send an actual email.
    Returns (is_valid, explanation_message).
    """
    if not email or "@" not in email:
        return False, "Invalid email address format"
        
    domain = email.split("@")[1]
    
    # 1. Fetch MX Records
    try:
        records = dns.resolver.resolve(domain, 'MX')
        # Sort by preference
        mx_record = sorted(records, key=lambda r: r.preference)[0].exchange.to_text()
    except Exception as e:
        logger.warning(f"Could not resolve MX records for domain '{domain}': {e}")
        return False, f"Domain has no valid mail servers (MX records missing)"
        
    # 2. Connect to MX Server
    try:
        host = socket.gethostname()
        server = smtplib.SMTP(timeout=5)
        server.connect(mx_record, 25)
        server.helo(host)
        server.mail(from_email)
        code, message = server.rcpt(email)
        server.quit()
        
        # 250 is the success code meaning the inbox exists and is open to receive mails
        if code == 250:
            return True, "Email mailbox is active and valid"
        else:
            reason = message.decode('utf-8', errors='ignore')
            logger.info(f"SMTP Handshake check failed for {email} (Code {code}): {reason}")
            return False, f"Server returned {code}: {reason}"
            
    except smtplib.SMTPServerDisconnected:
        return False, "Mail server closed connection abruptly"
    except Exception as e:
        logger.warning(f"SMTP Connection/Handshake error for {email}: {e}")
        # SAFETY FALLBACK:
        # Many local ISPs, firewalls, and cloud providers block outgoing port 25 connections completely.
        # If we cannot establish a connection, we must return True (and assume valid) so we don't
        # delete valid scrapings due to our own network/firewall blocking!
        return True, "Server connection blocked. Assuming valid as fallback."

async def verify_email_existence(email: str) -> Tuple[bool, str]:
    """
    Asynchronous SMTP verifier wrapper.
    Delegates to thread executor to prevent event loop blocks.
    """
    return await asyncio.to_thread(verify_email_existence_sync, email)
