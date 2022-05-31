from collections import defaultdict
from datetime import datetime
from worker import celery
import utils
import logging
from .epos import get_sales_details, get_rc_details


unit_to_price_map = {
    1: 16,
    2: 35,
    3: 50,
    4: 65,
    5: 80,
    6: 100,
    7: 115,
    8: 130,
    9: 150,
    10: 160,
    11: 175,
    12: 195,
    13: 210,
    14: 225,
    15: 240,
    16: 255,
    17: 275,
    18: 290,
    19: 305,
    20: 320,
    21: 335,
    22: 355,
    23: 370,
    24: 385,
    25: 400,
    26: 420,
}


def _get_summary(date, sales, month, year):
    logging.info(f"{date}: {len(sales)}")
    cache = utils.get_cache()
    summary = {"date": date, "min": 0, "max": 0, "units": 0, "cards": len(sales)}
    total_units = 0
    total_actual_price = 0
    total_our_price = 0
    for sale in sales:
        rc_number = sale["RC No"]
        logging.info(f"for: {rc_number}")
        cache_key = f"rc_details:{rc_number}:{month}:{year}"
        data = cache.get(cache_key)
        if not data:
            data = get_rc_details.run(rc_number=rc_number, month=month, year=year)
            cache.set(cache_key, data)
        members = data["members"]
        is_seeded = lambda mem: mem["UID Status"].strip().lower() == "seeded"
        units = sum(is_seeded(member) for member in members)
        total_units += units
        actual_cost = units * 16
        total_our_price += unit_to_price_map.get(units, actual_cost)
        total_actual_price += actual_cost
    summary["units"] = total_units
    summary["max"] = total_our_price
    summary["min"] = total_actual_price
    return summary


@celery.task(name="get_summary")
def get_summary(fpsid=123300100909, month=3, year=2022, dist_code=233):
    cache = utils.get_cache()
    sales = get_sales_details.run(
        fpsid=fpsid, month=month, year=year, dist_code=dist_code
    )
    group_by_date = defaultdict(list)
    for sale in sales:
        group_by_date[sale["Date"]].append(sale)

    summary_list = []
    for (date, sales) in sorted(
        list(group_by_date.items()), key=lambda x: x[0], reverse=True
    ):
        cache_key = f"collection_summary:{date}:{month}:{year}"
        if date != datetime.today().strftime("%d-%m-%Y"):
            # cache summary if its not todays summary
            summary = cache.get(cache_key)
            if not summary:
                summary = _get_summary(date, sales, month, year)
                cache.set(cache_key, summary)
        else:
            summary = _get_summary(date, sales, month, year)
        summary_list.append(summary)
    return summary_list
