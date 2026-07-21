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
        
        if code == 250:
            return True, "Email mailbox is active and valid"
        else:
            reason = message.decode('utf-8', errors='ignore')
            logger.info(f"SMTP Handshake check failed for {email} (Code {code}): {reason}")
            # If the block is an IP reputation block (like Proofpoint or Spamhaus), the email is likely valid, just our IP is banned.
            if code in (550, 554, 451, 421) and any(kw in reason.lower() for kw in ["blocked", "reputation", "spamhaus", "banned", "blacklisted", "client-ip", "rejected"]):
                return True, f"Unverified but assumed valid (IP reputation block during check): {reason}"
            return False, f"Server returned {code}: {reason}"
            
    except smtplib.SMTPServerDisconnected:
        return False, "Mail server closed connection abruptly"
    except Exception as e:
        logger.warning(f"SMTP Connection/Handshake error for {email}: {e}")
        # Do not auto-approve on connection failures; keep sender reputation safe.
        return False, "Unverified: SMTP connection blocked or server unreachable"


def verify_mx_only_sync(email: str) -> Tuple[bool, str]:
    """
    Lightweight verification: only checks if domain has valid MX records.
    Does NOT do SMTP handshake. Use this when SMTP port 25 is blocked (e.g. Render hosting).
    Returns (is_valid, explanation_message).
    """
    if not email or "@" not in email:
        return False, "Invalid email address format"
    domain = email.split("@")[1]
    try:
        records = dns.resolver.resolve(domain, 'MX')
        if records:
            return True, f"Domain '{domain}' has valid MX records (email server exists)"
        return False, f"No MX records found for domain '{domain}'"
    except Exception as e:
        logger.warning(f"Could not resolve MX records for domain '{domain}': {e}")
        return False, f"Domain has no valid mail servers (MX records missing)"


async def verify_mx_only(email: str) -> Tuple[bool, str]:
    """Async wrapper for MX-only email domain check (no SMTP handshake)."""
    return await asyncio.to_thread(verify_mx_only_sync, email)


async def verify_email_existence(email: str) -> Tuple[bool, str]:
    """
    Asynchronous SMTP verifier wrapper.
    Delegates to thread executor to prevent event loop blocks.
    """
    return await asyncio.to_thread(verify_email_existence_sync, email)
