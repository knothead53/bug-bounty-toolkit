# src/bbt/recon/http_checker.py
import concurrent.futures
import logging
from typing import Dict, List

import requests

logger = logging.getLogger(__name__)

DEFAULT_TIMEOUT = 8  # seconds
USER_AGENT = "bbt-livecheck/0.1 (ethical; authorized testing only)"

def probe_url(host: str, prefer_http: bool = False) -> Dict:
    """
    Try HTTPS first, then HTTP (or reverse if prefer_http=True).
    Returns dict: { host, tried, status_code, server, final_url, error }.
    """
    session = requests.Session()
    session.headers.update({"User-Agent": USER_AGENT})

    candidates = [f"https://{host}", f"http://{host}"]
    if prefer_http:
        candidates.reverse()

    result = {
        "host": host,
        "tried": [],
        "status_code": None,
        "server": None,
        "final_url": None,
        "error": None,
    }

    for url in candidates:
        result["tried"].append(url)
        try:
            # HEAD is polite and fast; allow redirects
            resp = session.head(url, allow_redirects=True, timeout=DEFAULT_TIMEOUT)
            result["status_code"] = resp.status_code
            result["server"] = resp.headers.get("Server")
            result["final_url"] = resp.url
            return result
        except requests.exceptions.RequestException as e:
            result["error"] = str(e)
            continue

    return result

def check_hosts(hosts: List[str], max_workers: int = 6) -> List[Dict]:
    """
    Low-concurrency probe of many hosts. Returns list of probe results.
    """
    results: List[Dict] = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as pool:
        futs = {pool.submit(probe_url, h): h for h in hosts}
        for fut in concurrent.futures.as_completed(futs):
            host = futs[fut]
            try:
                results.append(fut.result())
            except Exception as exc:
                logger.exception("Probe failed for %s: %s", host, exc)
                results.append({"host": host, "error": str(exc)})
    return results