import requests
import logging
from urllib.error import HTTPError

logging.basicConfig(level=logging.INFO)


def do_request(url, payload):

    logging.info("hitting service brace!!")
    try:
        res = requests.post(
            url,
            data=payload,
            verify=False,
        )
    except HTTPError as ex:
        logging.exception(f"failed to get data from server {url} {payload}")
    else:
        return res
