from urllib.error import HTTPError
import requests
import logging
from bs4 import BeautifulSoup


def do_request(url, payload):

    logging.info("hitting service brace!!!")
    try:
        res = requests.post(
            url,
            data=payload,
        )
    except HTTPError as ex:
        logging.exception(f"failed to get data from server {url} {payload}")
    else:
        return res.text


def fetch_sale_details(fpsid, month, year, dist_code):
    payload = {
        "dist_code": dist_code,
        "fps_id": fpsid,
        "month": month,
        "year": year,
    }
    return do_request("http://epos.bihar.gov.in/FPS_Trans_Details.jsp", payload)


def fetch_rc_details(rc_number, month, year):
    payload = {
        "src_no": rc_number,
        "month": month,
        "year": year,
    }
    return do_request("http://epos.bihar.gov.in/SRC_Trans_Details.jsp", payload)


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
        ths = ths[:6] + trs.pop(0).find_all("th") + ths[7:]
        return [th.get_text().strip() for th in ths]


class RCDetailParser:
    def parse(self, content):
        root_bs = BeautifulSoup(content, features="html.parser")
        tables = root_bs.find_all("table")
        members = self._parse_members(tables[0])
        transactons = self._parse_transactions(tables[-1])
        return members, transactons

    def _parse_members(self, table):
        try:
            trs = table.find_all("tr")
            trs = trs[2:]
            headers = [th.get_text().strip() for th in trs.pop(0).find_all("th")]
            rows = [[td.get_text().strip() for td in tr.find_all("td")] for tr in trs]
        except Exception:
            return []
        else:
            return [dict(zip(headers, row)) for row in rows]

    def _parse_transactions(self, table):
        try:
            trs = table.find_all("tr")
            trs = trs[1:]
            tds = trs.pop(0).find_all("td")
            tds = tds[:-1] + trs.pop(0).find_all("td")
            headers = [td.get_text().strip() for td in tds]
            rows = [[td.get_text().strip() for td in tr.find_all("td")] for tr in trs]
        except Exception:
            return []
        else:
            return [dict(zip(headers, row)) for row in rows]


def get_sales_details(fpsid=123300100909, month=3, year=2022, dist_code=233):
    table = fetch_sale_details(fpsid=fpsid, month=month, year=year, dist_code=dist_code)
    _, items = SalesDetailsParser().parse(table)
    return items


def get_rc_details(rc_number=10310060087015900034, month=3, year=2022):
    content = fetch_rc_details(rc_number=rc_number, month=month, year=year)
    members, transactions = RCDetailParser().parse(content)
    return members, transactions
