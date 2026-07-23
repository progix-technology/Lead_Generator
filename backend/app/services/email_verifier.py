import smtplib
import socket
import dns.resolver
import logging
import asyncio
import re
from typing import Tuple

logger = logging.getLogger(__name__)

# ─── Blocklist: Known no-reply, platform, CMS, and undeliverable domains ────
BLOCKED_DOMAINS = {
    # Readymag, website builders (no real inbox)
    "readymag.com", "wix.com", "squarespace.com", "weebly.com", "jimdo.com",
    "godaddysites.com", "webflow.io", "webflow.com", "carrd.co", "sites.google.com",
    "wordpress.com", "blogspot.com", "tumblr.com", "medium.com",
    # No-reply / system addresses
    "noreply.com", "no-reply.com", "donotreply.com",
    # Placeholder / temp mail / disposable
    "mailinator.com", "guerrillamail.com", "throwam.com", "yopmail.com",
    "tempmail.com", "sharklasers.com", "guerrillamailblock.com",
    "grr.la", "guerrillamail.info", "guerrillamail.biz", "guerrillamail.de",
    "trashmail.com", "dispostable.com", "fakeinbox.com", "spamgourmet.com",
    "maildrop.cc", "mailnull.com", "spamex.com", "mailexpire.com",
    # Platform / social media (not company emails)
    "facebook.com", "instagram.com", "twitter.com", "x.com",
    "linkedin.com", "tiktok.com", "youtube.com", "pinterest.com",
    # Booking / directory platforms (not owned by business)
    "opentable.com", "bookatable.co.uk", "fresha.com", "treatwell.co.uk",
    "vagaro.com", "styleseat.com", "mindbodyonline.com", "timely.cc",
    "glofox.com", "mariana-tek.com", "tripadvisor.com", "yelp.com",
    "zomato.com", "justeat.co.uk", "deliveroo.co.uk", "ubereats.com",
    "doordash.com", "grubhub.com", "seamless.com",
    # Support / ticketing platforms
    "zendesk.com", "freshdesk.com", "intercom.io",
}

# ─── No-reply / generic prefixes that should not be emailed ─────────────────
BLOCKED_PREFIXES = {
    "noreply", "no-reply", "donotreply", "do-not-reply", "mailer-daemon",
    "postmaster", "bounce", "bounces", "notifications", "notify",
    "automated", "system", "robot", "bot",
}

def is_email_sendable(email: str) -> Tuple[bool, str]:
    """
    Pre-flight check BEFORE any SMTP attempt.
    Returns (can_send: bool, reason: str).
    Catches:
      - Invalid format
      - Blocked domain (platforms, disposable, builders, booking sites)
      - No-reply/automated prefixes
    """
    if not email or "@" not in email:
        return False, "Invalid email format"

    email = email.strip().lower()
    
    # Basic format validation
    if not re.match(r'^[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}$', email):
        return False, f"Malformed email address: {email}"

    prefix, domain = email.split("@", 1)

    # Check blocked domains
    if domain in BLOCKED_DOMAINS:
        return False, f"Domain '{domain}' is a platform/builder/disposable — not a real business inbox"

    # Check partial domain matches (subdomains of blocked platforms)
    for blocked in BLOCKED_DOMAINS:
        if domain.endswith("." + blocked):
            return False, f"Domain '{domain}' is a subdomain of blocked platform '{blocked}'"

    # Check no-reply prefixes
    if prefix in BLOCKED_PREFIXES:
        return False, f"Email prefix '{prefix}' indicates automated/no-reply address"

    return True, "Email passed pre-flight checks"


def verify_email_existence_sync(email: str, from_email: str = "info@progixtechnology.com") -> Tuple[bool, str]:
    """
    Performs an SMTP handshake check to verify if the email mailbox exists.
    Does NOT send an actual email.
    Returns (is_valid, explanation_message).
    """
    # ── Step 0: Pre-flight blocklist check ──────────────────────────────────
    can_send, preflight_reason = is_email_sendable(email)
    if not can_send:
        logger.info(f"Email pre-flight blocked: {email} — {preflight_reason}")
        return False, preflight_reason

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
    # ── Pre-flight check first ───────────────────────────────────────────────
    can_send, preflight_reason = is_email_sendable(email)
    if not can_send:
        return False, preflight_reason

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
