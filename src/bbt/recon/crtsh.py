import requests
import time
import logging
from typing import Set
from urllib.parse import quote_plus

from bbt.config import CRTSH_URL

logger = logging.getLogger(__name__)

def fetch_crtsh_subdomains(domain: str, sleep: float = 0.5) -> Set[str]:
    """
    Query crt.sh JSON output for certificate names and extract subdomains.
    Returns a set of unique subdomains (string).
    NOTE: This is passive reconnaissance only (public records).
    """
    url = CRTSH_URL.format(domain=quote_plus(domain))
    logger.info("Querying crt.sh for domain: %s", domain)
    try:
        resp = requests.get(url, timeout=20)
        if resp.status_code != 200:
            logger.warning("crt.sh returned status %s", resp.status_code)
            return set()
        entries = resp.json()
        results = set()
        for e in entries:
            name = e.get("name_value")
            if not name:
                continue
            # name_value may contain multiple names separated by \n
            for n in str(name).splitlines():
                n = n.strip()
                if n.endswith(domain) and "*" not in n:
                    results.add(n.lower())
        # polite pause
        time.sleep(sleep)
        return results
    except Exception as exc:
        logger.exception("Error querying crt.sh: %s", exc)
        return set()