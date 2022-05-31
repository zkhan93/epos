import logging

from ..core import do_request
from .parsers import (
    EPDSRCDetailParser,
    RCDetailParser,
    SalesDetailsParser,
    StockDetailParser,
)
import utils

logging.basicConfig(level=logging.INFO)

from worker import celery


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


def _fetch_rc_detailsepds(rc_number="10310060087015900096", dist_code="233"):
    """fetches RC details from epds.bihar.gov.in"""
    payload = {
        "__EVENTTARGET": "",
        "__EVENTARGUMENT": "",
        "__VIEWSTATE": "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MzMwMTQ1MTI0OTYzNjAwMDAwMDUxMDIWAh8JBRVib3JkZXItY29sb3I6ICNGRkZGRkZkAgIPDxYCHwQFClNPTlUgS1VNQVIWAh8JBRVib3JkZXItY29sb3I6ICNGRkZGRkZkAgMPDxYCHwQFCkdJUkFKQSBSQU0WAh8JBRVib3JkZXItY29sb3I6ICNGRkZGRkZkAgQPDxYCHwQFAU0WAh8JBRVib3JkZXItY29sb3I6ICNGRkZGRkZkAgUPDxYCHwQFAjI0FgIfCQUVYm9yZGVyLWNvbG9yOiAjRkZGRkZGZAIGDw8WAh8EBQxYWFhYWFhYWDIzMzEWAh8JBRVib3JkZXItY29sb3I6ICNGRkZGRkZkAgUPZBYOZg8PZBYCHwkFFWJvcmRlci1jb2xvcjogI0ZGRkZGRhYCAgEPDxYCHwQFATNkZAIBDw8WAh8EBRoxMDIzMzAxNDUxMjQ5NjM2MDAwMDAwNTEwMxYCHwkFFWJvcmRlci1jb2xvcjogI0ZGRkZGRmQCAg8PFgIfBAUMU0FDSElOIEtVTUFSFgIfCQUVYm9yZGVyLWNvbG9yOiAjRkZGRkZGZAIDDw8WAh8EBQpTT05VIEtVTUFSFgIfCQUVYm9yZGVyLWNvbG9yOiAjRkZGRkZGZAIEDw8WAh8EBQFNFgIfCQUVYm9yZGVyLWNvbG9yOiAjRkZGRkZGZAIFDw8WAh8EBQE5FgIfCQUVYm9yZGVyLWNvbG9yOiAjRkZGRkZGZAIGDw8WAh8EBQxYWFhYWFhYWDQwMDUWAh8JBRVib3JkZXItY29sb3I6ICNGRkZGRkZkAgYPDxYCHwNoZBYOZg8PZBYCHwkFFWJvcmRlci1jb2xvcjogI0ZGRkZGRmQCAQ8PZBYCHwkFFWJvcmRlci1jb2xvcjogI0ZGRkZGRmQCAg8PZBYCHwkFFWJvcmRlci1jb2xvcjogI0ZGRkZGRmQCAw8PZBYCHwkFFWJvcmRlci1jb2xvcjogI0ZGRkZGRmQCBA8PZBYCHwkFFWJvcmRlci1jb2xvcjogI0ZGRkZGRmQCBQ8PZBYCHwkFFWJvcmRlci1jb2xvcjogI0ZGRkZGRmQCBg8PZBYCHwkFFWJvcmRlci1jb2xvcjogI0ZGRkZGRmQCAw8PFgYeCUZvcmVDb2xvcgojHwQFFyogUmF0aW9uIENhcmQgRm91bmQuLi4hHwgCBGRkGAIFHl9fQ29udHJvbHNSZXF1aXJlUG9zdEJhY2tLZXlfXxYDBSFjdGwwMCRDb250ZW50UGxhY2VIb2xkZXIyJHJiUnVyYWwFIWN0bDAwJENvbnRlbnRQbGFjZUhvbGRlcjIkcmJVcmJhbgUhY3RsMDAkQ29udGVudFBsYWNlSG9sZGVyMiRyYlVyYmFuBSljdGwwMCRDb250ZW50UGxhY2VIb2xkZXIyJGdyaWR2aWV3X21lbWJlcg88KwAMAQgCAWRUw8Y+yJjSYH59ahtiYIf20AI7bthMmT5j9Z0ZvdD1dw==",
        "__VIEWSTATEGENERATOR": "9285028E",
        "__EVENTVALIDATION": "/wEdACxOdNdAfri0oyc5tcgHY0/D1vlEgi4kHeVeEoXQmrrWnBmiRIP2V2EtD4Ms2ktNVkNKVkVlCeIHWGrF8NkYkEc7wU3yJLO9ZdNpWsZTbbCFCKQP4d37oKRoLPPdBrpGG6XtAwGvXIByLAqjOWUyvFY3QtjW4gO3uQybgRdAsabY9mr9cqj2S97o9bTBMJVpCje2P0toPFfCu1NIpdq52b+08a6u5v16CC5Ba7PAbu6hA+9nukHauIBGTzouuXsIjkT0S4w/pAdoprRv8CYWY7trKWjuWOKrh/byKaHml4+xFcgAVie4GMR0B8e7TWL4lTHkMMrQbi84aDRJWsadT09JG8dlN3kkojzZT6Uqbr4Jsu7xEPsSJvWMy4OsQdjSMk429G0cbelQaHKFx51EwFAzTN8w8gKKV6JFIUtPyYEqrvYnHVwtsDzLxOtqKa8tAcwkAABUqihbAdlFNHGq9nB33i/391Pw2bCC+olFmko6DEp+Y+ZsaQAmA7ANw4fswYDxJsoFXMnxVjkf/cefEyfGKB7KMDuNe2ODEBIPbAKBKFjAX2RP9/uUwhKddCcl+Z2DEe7GRhgdI15hWnJgsw3hkZXoq8UUeGLrUv5HeA5GJrsEwDk4X15x3znehlQzZ6E37ji1tUQmpJgk2BywyFpGSwz/4RPEw03GFn2DzrrsQw5ZarIOVdKmd2ccQJm54aS6mGo2eoNdZWXXqKd7NyV3vWiKP3/ZJ0mZNrvUhfX+OiTPR++bxo9pXNJlIDHuGPAsEGddU+L8nOnIr7gRmfKwXja04fASfPsOtKo2s6uiRUUc7QRc4+DZEMk6sRh70q2OsG2Curwz4gxt8UEn0+QB8O7ueotkKYlY+bxFP4AA7uzBz+BGyL/EeBGYNaKUtv/sqrRfhfAbvZpiOZg1B2eJmvCz0yYvmGeF/eCaxUpTCEM9yoK5DUT7P+rQM2WqlnvQT8qD0PsT0l3JDv87cD4R",
        "ctl00$ContentPlaceHolder2$A": "rbRural",
        "ctl00$ContentPlaceHolder2$ddldistrict": dist_code,
        "ctl00$ContentPlaceHolder2$txtrcnumber": rc_number,
        "ctl00$ContentPlaceHolder2$btnsearch": "Search",
    }
    return do_request(
        "http://epds.bihar.gov.in/SearchByRCID.aspx",
        payload,
    ).text


@celery.task(name="get_sales_details")
def get_sales_details(fpsid=123300100909, month=3, year=2022, dist_code=233):
    table = _fetch_sale_details(
        fpsid=fpsid, month=month, year=year, dist_code=dist_code
    )
    _, items = SalesDetailsParser().parse(table)
    return items


@celery.task(name="get_rc_details_from_epds")
def get_rc_details_from_epds(rc_number=10310060087015900034, dist_code=233):
    cache = utils.get_cache()
    cache_key = f"rc_details_epds:{rc_number}:{dist_code}"
    data = cache.get(cache_key)
    if not data:
        content = _fetch_rc_detailsepds(rc_number=rc_number, dist_code=dist_code)
        members, extra = EPDSRCDetailParser().parse(content)
        cache.set(
            cache_key,
            {"members": members, "extra": extra},
            expire=utils.WEEK_IN_SECONDS,
        )
    else:
        members, extra = data["members"], data["extra"]
        res = {"members": members}
        if extra:
            res.update(extra)
    return res


@celery.task(name="get_rc_details")
def get_rc_details(rc_number=10310060087015900034, month=3, year=2022):
    cache = utils.get_cache()
    cache_key = f"rc_details:{rc_number}:{month}:{year}"
    data = cache.get(cache_key)
    logging.info(data)
    if not data:
        content = _fetch_rc_details(rc_number=rc_number, month=month, year=year)
        members, transactions = RCDetailParser().parse(content)
        cache.set(cache_key, {"members": members, "transactions": transactions})
    else:
        members, transactions = data["members"], data["transactions"]
    return {"members": members, "transactions": transactions}


@celery.task(name="get_stock_details")
def get_stock_details(fpsid=123300100909, month=3, year=2022, dist_code=233):
    content = _fetch_stock_details(
        fpsid=fpsid, month=month, year=year, dist_code=dist_code
    )
    entries = StockDetailParser().parse(content)
    return entries
