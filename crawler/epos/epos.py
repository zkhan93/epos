from functools import lru_cache
from ..core import do_request
from .parsers import RCDetailParser, SalesDetailsParser, StockDetailParser


def _fetch_sale_details(fpsid, month, year, dist_code):
    payload = {
        "dist_code": dist_code,
        "fps_id": fpsid,
        "month": month,
        "year": year,
    }
    return do_request("http://epos.bihar.gov.in/FPS_Trans_Details.jsp", payload).text


def _fetch_rc_details(rc_number, month, year):
    payload = {
        "src_no": rc_number,
        "month": month,
        "year": year,
    }
    return do_request("http://epos.bihar.gov.in/SRC_Trans_Details.jsp", payload).text


def _fetch_stock_details(fpsid, month, year, dist_code):
    payload = {
        "dist_code": dist_code,
        "fps_id": fpsid,
        "month": month,
        "year": year,
    }
    return do_request(
        "http://epos.bihar.gov.in/fps_stock_register.action", payload
    ).text


# @lru_cache
def get_sales_details(fpsid=123300100909, month=3, year=2022, dist_code=233):
    table = _fetch_sale_details(
        fpsid=fpsid, month=month, year=year, dist_code=dist_code
    )
    _, items = SalesDetailsParser().parse(table)
    return items


# @lru_cache
def get_rc_details(rc_number=10310060087015900034, month=3, year=2022):
    content = _fetch_rc_details(rc_number=rc_number, month=month, year=year)
    members, transactions = RCDetailParser().parse(content)
    return members, transactions


# @lru_cache
def get_stock_details(fpsid=123300100909, month=3, year=2022, dist_code=233):
    content = _fetch_stock_details(
        fpsid=fpsid, month=month, year=year, dist_code=dist_code
    )
    entries = StockDetailParser().parse(content)
    return entries
