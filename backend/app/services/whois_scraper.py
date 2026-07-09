import socket
import re
import logging
from typing import Optional, Tuple

logger = logging.getLogger(__name__)

def query_whois_raw(domain: str) -> str:
    """
    Directly queries raw WHOIS directory data on port 43 using standard TCP sockets.
    Requires zero external python packages or WHOIS binaries.
    """
    # Clean domain string
    domain = domain.replace("https://", "").replace("http://", "").replace("www.", "").split("/")[0].strip()
    if not domain or "." not in domain:
        return ""
        
    # Choose registry server based on top-level domain
    whois_server = "whois.iana.org"
    if domain.endswith(".com") or domain.endswith(".net"):
        whois_server = "whois.verisign-grs.com"
    elif domain.endswith(".org"):
        whois_server = "whois.pir.org"
    elif domain.endswith(".info"):
        whois_server = "whois.afilias-grs.info"
    elif domain.endswith(".biz"):
        whois_server = "whois.neulevel.biz"
    elif domain.endswith(".us"):
        whois_server = "whois.nic.us"
    elif domain.endswith(".co.uk") or domain.endswith(".uk"):
        whois_server = "whois.nic.uk"
        
    try:
        logger.info(f"Querying WHOIS for domain '{domain}' via server '{whois_server}'")
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(6.0)
        s.connect((whois_server, 43))
        
        # Format query for Nominet (UK registry) or generic registry servers
        query = domain + "\r\n"
        s.send(query.encode("utf-8"))
        
        response = b""
        while True:
            data = s.recv(4096)
            if not data:
                break
            response += data
        s.close()
        return response.decode("utf-8", errors="ignore")
    except Exception as e:
        logger.warning(f"WHOIS socket query error for {domain}: {e}")
        return ""

def extract_email_from_whois(domain: str) -> Optional[Tuple[str, str]]:
    """
    Crawls WHOIS database and extracts domain registrant contact email if available.
    Returns: Tuple[email, email_source] (e.g. ("owner@example.com", "WHOIS")) or None.
    """
    if not domain:
        return None
        
    raw_data = query_whois_raw(domain)
    if not raw_data:
        return None
        
    # Regex matching email format
    emails = re.findall(r'[\w\.-]+@[\w\.-]+\.\w+', raw_data)
    if not emails:
        return None
        
    # Standard exclusions to filter out domain registrars (abuse, technical contact, privacy blockers)
    registrar_keywords = ["abuse", "domain", "registry", "registrar", "support", "hostmaster", "postmaster", "dns", "tech", "billing", "admin", "privacy", "proxy"]
    
    for email in emails:
        email_lower = email.lower()
        if not any(kw in email_lower for kw in registrar_keywords):
            # Verify basic structure
            if len(email_lower) > 5 and "." in email_lower.split("@")[1]:
                logger.info(f"Successfully extracted registrant email from WHOIS database: {email_lower}")
                return email_lower, "WHOIS Registry"
                
    return None
