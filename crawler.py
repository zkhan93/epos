from functools import lru_cache
from urllib.error import HTTPError
import requests
import logging
from bs4 import BeautifulSoup


def fetch_sale_details(fpsid, month, year, dist_code):
    # raise Exception("bad exception!")
    logging.info("hitting service brace!!!")
    payload = {
        "dist_code": dist_code,
        "fps_id": fpsid,
        "month": month,
        "year": year,
    }
    try:
        res = requests.post(
            "http://epos.bihar.gov.in/FPS_Trans_Details.jsp",
            data=payload,
        )
    except HTTPError as ex:
        logging.exception(f"failed to get sales details for {payload}")
    else:
        return res.text


class SalesDetailsParser:
    def parse(self, content):
        root_bs = BeautifulSoup(content, features="html.parser")
        headers = self._parse_headers(root_bs)
        rows = self._parse_rows(root_bs)
        items = []
        for row in rows:
            items.append(dict(zip(headers, row)))
        return headers, items

    def _parse_rows(self, bs):
        """first 3 trs and last 1 tr are headers"""
        trs = bs.find_all("tr")
        trs = trs[3:-1]
        return [[td.get_text().strip() for td in tr.find_all("td")] for tr in trs]

    def _parse_headers(self, bs):
        # first tr is useles header
        # second tr have headers but at 8th position there is  a colspan which can be replaces with all items in 3rd tr
        trs = bs.find_all("tr")

        trs.pop(0)
        ths = trs.pop(0).find_all("th")
        ths = ths[:8] + trs.pop(0).find_all("th") + ths[9:]
        return [th.get_text().strip() for th in ths]


def get_sales_details(fpsid=123300100909, month=3, year=2022, dist_code=233):
    table = fetch_sale_details(fpsid=fpsid, month=month, year=year, dist_code=dist_code)
    _, items = SalesDetailsParser().parse(table)
    return items
