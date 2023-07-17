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

from celery import shared_task


def _fetch_sale_details(fpsid, month, year, dist_code):
    payload = {
        "dist_code": dist_code,
        "fps_id": fpsid,
        "month": month,
        "year": year,
    }
    return do_request("https://epos.bihar.gov.in/FPS_Trans_Details.jsp", payload).text


def _fetch_rc_details(rc_number, month, year):
    payload = {
        "src_no": rc_number,
        "month": month,
        "year": year,
    }
    return do_request("https://epos.bihar.gov.in/SRC_Trans_Details.jsp", payload).text


def _fetch_stock_details(fpsid, month, year, dist_code):
    payload = {
        "dist_code": dist_code,
        "fps_id": fpsid,
        "month": month,
        "year": year,
    }
    return do_request(
        "https://epos.bihar.gov.in/fps_stock_register.action", payload
    ).text

def _get_epds_hidden_fields(url):
    # do a get call fetch the __VIEWSTATE __EVENTVALIDATION and __VIEWSTATEGENERATOR values then do a post call
    # fetching fresh values is not required as per testing but keeping it here for reference
    # valid for "https://epds.bihar.gov.in/SearchByRCID.aspx"
    import requests
    import re
    try:
        res = requests.get(url)
    except Exception:
        logging.exception(f"failed to get data from server {url}")
    else:
        content = res.text
        viewstate_patter = re.compile(r'<input type="hidden" name="__VIEWSTATE" id="__VIEWSTATE" value="(.*)" />')
        viewstategenerator_pattern = re.compile(r'<input type="hidden" name="__VIEWSTATEGENERATOR" id="__VIEWSTATEGENERATOR" value="(.*)" />')
        eventvalidation_pattern = re.compile(r'<input type="hidden" name="__EVENTVALIDATION" id="__EVENTVALIDATION" value="(.*)" />')
        viewstate = viewstate_patter.search(content).group(1)
        viewstategenerator = viewstategenerator_pattern.search(content).group(1)
        eventvalidation = eventvalidation_pattern.search(content).group(1)
        return viewstate, viewstategenerator, eventvalidation


def _fetch_rc_detailsepds(rc_number="10310060087015900096", dist_code="233"):
    """fetches RC details from epds.bihar.gov.in"""
    url = "https://epds.bihar.gov.in/SearchByRCID.aspx"     
    # viewstate,viewstategenerator,eventvalidation =  _get_epds_hidden_fields(url)
    payload = {
        "__EVENTTARGET": "",
        "__EVENTARGUMENT": "",
        "__VIEWSTATE": "/wEPDwUKMTAyMTY4OTIyNQ9kFgJmD2QWAgIDD2QWAgIJD2QWCgIHDxAPFgYeDURhdGFUZXh0RmllbGQFEERpc3RyaWN0X05hbWVfRW4eDkRhdGFWYWx1ZUZpZWxkBQhEaXN0cmljdB4LXyFEYXRhQm91bmRnZBAVJxEtU2VsZWN0IERpc3RyaWN0LRZQYXNoY2hpbSBDaGFtcGFyYW4oMDEpE1B1cmJhIENoYW1wYXJhbigwMikLU2hlb2hhcigwMykNU2l0YW1hcmhpKDA0KQ1NYWRodWJhbmkoMDUpClN1cGF1bCgwNikKQXJhcmlhKDA3KQ5LaXNoYW5nYW5qKDA4KQpQdXJuaWEoMDkpC0thdGloYXIoMTApDU1hZGhlcHVyYSgxMSkLU2FoYXJzYSgxMikNRGFyYmhhbmdhKDEzKQ9NdXphZmZhcnB1cigxNCkNR29wYWxnYW5qKDE1KQlTaXdhbigxNikJU2FyYW4oMTcpDFZhaXNoYWxpKDE4KQ5TYW1hc3RpcHVyKDE5KQ1CZWd1c2FyYWkoMjApDEtoYWdhcmlhKDIxKQ1CaGFnYWxwdXIoMjIpCUJhbmthKDIzKQpNdW5nZXIoMjQpDkxha2hpc2FyYWkoMjUpDlNoZWlraHB1cmEoMjYpC05hbGFuZGEoMjcpCVBhdG5hKDI4KQtCaG9qcHVyKDI5KQlCdXhhcigzMCkTS2FpbXVyIChCaGFidWEpKDMxKQpSb2h0YXMoMzIpDUplaGFuYWJhZCgzNykJQXJ3YWwoMzgpDkF1cmFuZ2FiYWQoMzMpCEdheWEoMzQpCk5hd2FkYSgzNSkJSmFtdWkoMzYpFScBMAMyMDMDMjA0AzIwNQMyMDYDMjA3AzIwOAMyMDkDMjEwAzIxMQMyMTIDMjEzAzIxNAMyMTUDMjE2AzIxNwMyMTgDMjE5AzIyMAMyMjEDMjIyAzIyMwMyMjQDMjI1AzIyNgMyMjcDMjI4AzIyOQMyMzADMjMxAzIzMgMyMzMDMjM0AzIzNQMyMzYDMjM3AzIzOAMyMzkDMjQwFCsDJ2dnZ2dnZ2dnZ2dnZ2dnZ2dnZ2dnZ2dnZ2dnZ2dnZ2dnZ2dnZ2dnZ2RkAgsPDxYCHgdWaXNpYmxlaGRkAhEPZBYCAgMPDxYCHgRUZXh0BRQxMDMxMDA2MDA4NzAxNTkwMDAzNGRkAhMPZBYKAgMPDxYCHwQFE0thaW11ciAoQmhhYnVhKSgzMSlkZAIHDw8WAh8EBQVDaGFuZGRkAgoPDxYCHwQFDDEyMzMwMDEwMDkwOWRkAg4PDxYCHwQFA1BISGRkAhEPDxYCHwQFATZkZAIVD2QWBAIBDzwrABEDAA8WBh8CZx4LXyFJdGVtQ291bnQCBh8DZ2QBEBYAFgAWAAwUKwAAFgJmD2QWEmYPDxYGHgtCb3JkZXJXaWR0aBsAAAAAAADwPwEAAAAeC0JvcmRlckNvbG9yCqQBHgRfIVNCAjBkZAICDw8WBh8GGwAAAAAAAPA/AQAAAB8HCqQBHwgCMGQWEGYPD2QWAh4Fc3R5bGUFFWJvcmRlci1jb2xvcjogI0ZGRkZGRmQCAQ8PZBYCHwkFFWJvcmRlci1jb2xvcjogI0ZGRkZGRmQCAg8PZBYCHwkFFWJvcmRlci1jb2xvcjogI0ZGRkZGRmQCAw8PZBYCHwkFFWJvcmRlci1jb2xvcjogI0ZGRkZGRmQCBA8PZBYCHwkFFWJvcmRlci1jb2xvcjogI0ZGRkZGRmQCBQ8PZBYCHwkFFWJvcmRlci1jb2xvcjogI0ZGRkZGRmQCBg8PZBYCHwkFFWJvcmRlci1jb2xvcjogI0ZGRkZGRmQCBw8PZBYCHwkFFWJvcmRlci1jb2xvcjogI0ZGRkZGRmQCAw9kFhBmDw9kFgIfCQUVYm9yZGVyLWNvbG9yOiAjRkZGRkZGFgICAQ8PFgIfBAUBMWRkAgEPDxYCHwQFFjEwMzEwMDYwMDg3MDE1OTAwMDM0MDEWAh8JBRVib3JkZXItY29sb3I6ICNGRkZGRkZkAgIPDxYCHwQFDERldmFudGkgRGV2aRYCHwkFFWJvcmRlci1jb2xvcjogI0ZGRkZGRmQCAw8PFgIfBAUOUkFNIEtSSVQgU0lOR0gWAh8JBRVib3JkZXItY29sb3I6ICNGRkZGRkZkAgQPDxYCHwQFAUYWAh8JBRVib3JkZXItY29sb3I6ICNGRkZGRkZkAgUPDxYCHwQFAjU2FgIfCQUVYm9yZGVyLWNvbG9yOiAjRkZGRkZGZAIGDw8WAh8EBQxYWFhYWFhYWDg4NDMWAh8JBRVib3JkZXItY29sb3I6ICNGRkZGRkZkAgcPDxYCHwQFBkFjdGl2ZRYCHwkFFWJvcmRlci1jb2xvcjogI0ZGRkZGRmQCBA9kFhBmDw9kFgIfCQUVYm9yZGVyLWNvbG9yOiAjRkZGRkZGFgICAQ8PFgIfBAUBMmRkAgEPDxYCHwQFFjEwMzEwMDYwMDg3MDE1OTAwMDM0MDIWAh8JBRVib3JkZXItY29sb3I6ICNGRkZGRkZkAgIPDxYCHwQFDFJhbWt1dCBTaW5naBYCHwkFFWJvcmRlci1jb2xvcjogI0ZGRkZGRmQCAw8PFgIfBAURTUFOR0kgU0lOR0ggWUFEQVYWAh8JBRVib3JkZXItY29sb3I6ICNGRkZGRkZkAgQPDxYCHwQFAU0WAh8JBRVib3JkZXItY29sb3I6ICNGRkZGRkZkAgUPDxYCHwQFAjU5FgIfCQUVYm9yZGVyLWNvbG9yOiAjRkZGRkZGZAIGDw8WAh8EBQxYWFhYWFhYWDU2ODAWAh8JBRVib3JkZXItY29sb3I6ICNGRkZGRkZkAgcPDxYCHwQFBkFjdGl2ZRYCHwkFFWJvcmRlci1jb2xvcjogI0ZGRkZGRmQCBQ9kFhBmDw9kFgIfCQUVYm9yZGVyLWNvbG9yOiAjRkZGRkZGFgICAQ8PFgIfBAUBM2RkAgEPDxYCHwQFFjEwMzEwMDYwMDg3MDE1OTAwMDM0MDMWAh8JBRVib3JkZXItY29sb3I6ICNGRkZGRkZkAgIPDxYCHwQFD0FtYXIgTmF0aCBZYWRhdhYCHwkFFWJvcmRlci1jb2xvcjogI0ZGRkZGRmQCAw8PFgIfBAUNUkFNS1JJVCBTSU5HSBYCHwkFFWJvcmRlci1jb2xvcjogI0ZGRkZGRmQCBA8PFgIfBAUBTRYCHwkFFWJvcmRlci1jb2xvcjogI0ZGRkZGRmQCBQ8PFgIfBAUCMjMWAh8JBRVib3JkZXItY29sb3I6ICNGRkZGRkZkAgYPDxYCHwQFDFhYWFhYWFhYODE1MxYCHwkFFWJvcmRlci1jb2xvcjogI0ZGRkZGRmQCBw8PFgIfBAUGQWN0aXZlFgIfCQUVYm9yZGVyLWNvbG9yOiAjRkZGRkZGZAIGD2QWEGYPD2QWAh8JBRVib3JkZXItY29sb3I6ICNGRkZGRkYWAgIBDw8WAh8EBQE0ZGQCAQ8PFgIfBAUWMTAzMTAwNjAwODcwMTU5MDAwMzQwNBYCHwkFFWJvcmRlci1jb2xvcjogI0ZGRkZGRmQCAg8PFgIfBAUPU3VkYXJzaGFuIFlhZGF2FgIfCQUVYm9yZGVyLWNvbG9yOiAjRkZGRkZGZAIDDw8WAh8EBQ1SQU1LUklUIFNJTkdIFgIfCQUVYm9yZGVyLWNvbG9yOiAjRkZGRkZGZAIEDw8WAh8EBQFNFgIfCQUVYm9yZGVyLWNvbG9yOiAjRkZGRkZGZAIFDw8WAh8EBQIyMBYCHwkFFWJvcmRlci1jb2xvcjogI0ZGRkZGRmQCBg8PFgIfBAUMWFhYWFhYWFg4OTI2FgIfCQUVYm9yZGVyLWNvbG9yOiAjRkZGRkZGZAIHDw8WAh8EBQZBY3RpdmUWAh8JBRVib3JkZXItY29sb3I6ICNGRkZGRkZkAgcPZBYQZg8PZBYCHwkFFWJvcmRlci1jb2xvcjogI0ZGRkZGRhYCAgEPDxYCHwQFATVkZAIBDw8WAh8EBRYxMDMxMDA2MDA4NzAxNTkwMDAzNDA1FgIfCQUVYm9yZGVyLWNvbG9yOiAjRkZGRkZGZAICDw8WAh8EBQxTVU1BTiBLVU1BUkkWAh8JBRVib3JkZXItY29sb3I6ICNGRkZGRkZkAgMPDxYCHwQFDVJBTUtSSVQgU0lOR0gWAh8JBRVib3JkZXItY29sb3I6ICNGRkZGRkZkAgQPDxYCHwQFAUYWAh8JBRVib3JkZXItY29sb3I6ICNGRkZGRkZkAgUPDxYCHwQFAjE3FgIfCQUVYm9yZGVyLWNvbG9yOiAjRkZGRkZGZAIGDw8WAh8EBQYmbmJzcDsWAh8JBRVib3JkZXItY29sb3I6ICNGRkZGRkZkAgcPDxYCHwQFBkFjdGl2ZRYCHwkFFWJvcmRlci1jb2xvcjogI0ZGRkZGRmQCCA9kFhBmDw9kFgIfCQUVYm9yZGVyLWNvbG9yOiAjRkZGRkZGFgICAQ8PFgIfBAUBNmRkAgEPDxYCHwQFFjEwMzEwMDYwMDg3MDE1OTAwMDM0MDYWAh8JBRVib3JkZXItY29sb3I6ICNGRkZGRkZkAgIPDxYCHwQFEFJBTSBCSEFST1MgS1VNQVIWAh8JBRVib3JkZXItY29sb3I6ICNGRkZGRkZkAgMPDxYCHwQFDVJBTUtSSVQgU0lOR0gWAh8JBRVib3JkZXItY29sb3I6ICNGRkZGRkZkAgQPDxYCHwQFAU0WAh8JBRVib3JkZXItY29sb3I6ICNGRkZGRkZkAgUPDxYCHwQFAjE1FgIfCQUVYm9yZGVyLWNvbG9yOiAjRkZGRkZGZAIGDw8WAh8EBQxYWFhYWFhYWDQ4NDMWAh8JBRVib3JkZXItY29sb3I6ICNGRkZGRkZkAgcPDxYCHwQFBkFjdGl2ZRYCHwkFFWJvcmRlci1jb2xvcjogI0ZGRkZGRmQCCQ8PFgIfA2hkFhBmDw9kFgIfCQUVYm9yZGVyLWNvbG9yOiAjRkZGRkZGZAIBDw9kFgIfCQUVYm9yZGVyLWNvbG9yOiAjRkZGRkZGZAICDw9kFgIfCQUVYm9yZGVyLWNvbG9yOiAjRkZGRkZGZAIDDw9kFgIfCQUVYm9yZGVyLWNvbG9yOiAjRkZGRkZGZAIEDw9kFgIfCQUVYm9yZGVyLWNvbG9yOiAjRkZGRkZGZAIFDw9kFgIfCQUVYm9yZGVyLWNvbG9yOiAjRkZGRkZGZAIGDw9kFgIfCQUVYm9yZGVyLWNvbG9yOiAjRkZGRkZGZAIHDw9kFgIfCQUVYm9yZGVyLWNvbG9yOiAjRkZGRkZGZAIDDw8WBh4JRm9yZUNvbG9yCiMfBAUXKiBSYXRpb24gQ2FyZCBGb3VuZC4uLiEfCAIEZGQYAgUeX19Db250cm9sc1JlcXVpcmVQb3N0QmFja0tleV9fFgMFIWN0bDAwJENvbnRlbnRQbGFjZUhvbGRlcjIkcmJSdXJhbAUhY3RsMDAkQ29udGVudFBsYWNlSG9sZGVyMiRyYlVyYmFuBSFjdGwwMCRDb250ZW50UGxhY2VIb2xkZXIyJHJiVXJiYW4FKWN0bDAwJENvbnRlbnRQbGFjZUhvbGRlcjIkZ3JpZHZpZXdfbWVtYmVyDzwrAAwBCAIBZIX3i07UP4Sqoz1NyjTgc8BWho6fq4edML39V2gXsR3M",
        "__VIEWSTATEGENERATOR": "9285028E",
        "__EVENTVALIDATION": "/wEdACw6sA8jYuhQo9AjFO52MgP31vlEgi4kHeVeEoXQmrrWnBmiRIP2V2EtD4Ms2ktNVkNKVkVlCeIHWGrF8NkYkEc7wU3yJLO9ZdNpWsZTbbCFCKQP4d37oKRoLPPdBrpGG6XtAwGvXIByLAqjOWUyvFY3QtjW4gO3uQybgRdAsabY9mr9cqj2S97o9bTBMJVpCje2P0toPFfCu1NIpdq52b+08a6u5v16CC5Ba7PAbu6hA+9nukHauIBGTzouuXsIjkT0S4w/pAdoprRv8CYWY7trKWjuWOKrh/byKaHml4+xFcgAVie4GMR0B8e7TWL4lTHkMMrQbi84aDRJWsadT09JG8dlN3kkojzZT6Uqbr4Jsu7xEPsSJvWMy4OsQdjSMk429G0cbelQaHKFx51EwFAzTN8w8gKKV6JFIUtPyYEqrvYnHVwtsDzLxOtqKa8tAcwkAABUqihbAdlFNHGq9nB33i/391Pw2bCC+olFmko6DEp+Y+ZsaQAmA7ANw4fswYDxJsoFXMnxVjkf/cefEyfGKB7KMDuNe2ODEBIPbAKBKFjAX2RP9/uUwhKddCcl+Z2DEe7GRhgdI15hWnJgsw3hkZXoq8UUeGLrUv5HeA5GJrsEwDk4X15x3znehlQzZ6E37ji1tUQmpJgk2BywyFpGSwz/4RPEw03GFn2DzrrsQw5ZarIOVdKmd2ccQJm54aS6mGo2eoNdZWXXqKd7NyV3vWiKP3/ZJ0mZNrvUhfX+OiTPR++bxo9pXNJlIDHuGPAsEGddU+L8nOnIr7gRmfKwXja04fASfPsOtKo2s6uiRUUc7QRc4+DZEMk6sRh70q2OsG2Curwz4gxt8UEn0+QB8O7ueotkKYlY+bxFP4AA7uzBz+BGyL/EeBGYNaKUtv/sqrRfhfAbvZpiOZg1B2eJmvCz0yYvmGeF/eCaxUpTCJKUY5RXZsSVKzLYgSqVJW7vjclWIJbJhokltHoaZR72",
        "ctl00$ContentPlaceHolder2$A": "rbRural",
        "ctl00$ContentPlaceHolder2$ddldistrict": dist_code,
        "ctl00$ContentPlaceHolder2$txtrcnumber": rc_number,
        "ctl00$ContentPlaceHolder2$btnsearch": "Search",
    }
    return do_request(
        url,
        payload,
    ).text


@shared_task(name="get_sales_details")
def get_sales_details(fpsid=123300100909, month=3, year=2022, dist_code=233):
    table = _fetch_sale_details(
        fpsid=fpsid, month=month, year=year, dist_code=dist_code
    )
    _, items = SalesDetailsParser().parse(table)
    for item in items:
        try:
            rc_details = get_rc_details(
                rc_number=item["RC No"], 
                month=month,
                year=year,
            )
            members = rc_details["members"]
            transactions = rc_details["transactions"]
            name = transactions[0]["Member"] if transactions else None
            total = len(members)
            seeded = len([m for m in members if m["UID Status"] == "Seeded"])
        except Exception as ex:
            logging.exception(ex)
        else:
            item["extra"] = {"name": name, "total":total, "seeded":seeded}
    return items


@shared_task(name="get_rc_details_from_epds")
def get_rc_details_from_epds(
    rc_number=10310060087015900034, dist_code=233, use_cache=True
):
    cache = utils.get_cache()
    cache_key = f"rc_details_epds:{rc_number}:{dist_code}"
    data = cache.get(cache_key) if use_cache else None
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


@shared_task(name="get_rc_details")
def get_rc_details(rc_number=10310060087015900034, month=3, year=2022, use_cache=True):
    cache = utils.get_cache()
    cache_key = f"rc_details:{rc_number}:{month}:{year}"
    data = cache.get(cache_key) if use_cache else None
    logging.debug(data)
    if not data:
        content = _fetch_rc_details(rc_number=rc_number, month=month, year=year)
        members, transactions = RCDetailParser().parse(content)
        cache.set(cache_key, {"members": members, "transactions": transactions})
    else:
        members, transactions = data["members"], data["transactions"]
    return {"members": members, "transactions": transactions}


@shared_task(name="get_stock_details")
def get_stock_details(fpsid=123300100909, month=3, year=2022, dist_code=233):
    content = _fetch_stock_details(
        fpsid=fpsid, month=month, year=year, dist_code=dist_code
    )
    entries = StockDetailParser().parse(content)
    return entries
