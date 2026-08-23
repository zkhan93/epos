import logging
import os

import requests
import urllib3
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

log = logging.getLogger(__name__)

# The government endpoints have a broken certificate chain, so verify=False is
# deliberate; silence the per-request warning it would otherwise emit.
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

CONNECT_TIMEOUT = float(os.getenv("HTTP_CONNECT_TIMEOUT", "10"))
READ_TIMEOUT = float(os.getenv("HTTP_READ_TIMEOUT", "60"))
POOL_SIZE = int(os.getenv("HTTP_POOL_SIZE", "8"))


def _build_session():
    session = requests.Session()
    session.verify = False
    adapter = HTTPAdapter(
        pool_connections=2,
        pool_maxsize=POOL_SIZE,
        max_retries=Retry(
            total=2,
            backoff_factor=0.5,
            status_forcelist=(502, 503, 504),
            allowed_methods=("GET", "POST"),
        ),
    )
    session.mount("https://", adapter)
    session.mount("http://", adapter)
    return session


# One pooled session for the process. Every task hits the same two hosts, so
# reusing connections skips a TLS handshake per request -- the single largest
# CPU cost in a scrape.
session = _build_session()


def do_request(url, payload):
    log.info("POST %s", url)
    try:
        res = session.post(url, data=payload, timeout=(CONNECT_TIMEOUT, READ_TIMEOUT))
        res.raise_for_status()
    except requests.RequestException as ex:
        log.warning("request to %s failed: %s", url, ex)
        raise RuntimeError(f"upstream request to {url} failed: {ex}") from ex
    return res
