import logging
from .core import do_request
from celery import shared_task
import utils

officer_types = {
    132: "District Level Officer",
    1163: "Police Officers",
    3975: "Revenue &amp; Land Reforms",
    4007: "Rural Development",
    3999: "Health",
    3971: "Public Grievance",
    3995: "Election",
    3985: "Food &amp; Consumer Protection",
    3991: "Treasury",
    4029: "Welfare",
    4069: "Planning Department",
    4083: "Registration Department",
    4017: "Agriculture &amp; Allied Services",
    4025: "Social Security",
    4003: "Education",
    4013: "Transport",
    4021: "Co-Operative",
    3983: "ICDS",
    4041: "Animal Husbandry",
    4033: "Industries",
    4045: "Labour Resources",
    1361: "Nodal Officer",
    1357: "Sub Divisional Officer",
    4059: "Line Department",
    4055: "Jail",
    4049: "Bank",
    4037: "Sports",
    1286: "Block Development Officer",
    1207: "Circle Officer",
}


def get_all_data(url, payload):
    """takes care of pagination"""
    items = []
    data = do_request(url, payload).json()
    items.extend(data["result"])
    page = data["paged"]
    while page < data["mp"]:
        payload["type"] = "next"
        payload["paged"] = page
        data = do_request(url, payload).json()
        items.extend(data["result"])
        page = data["paged"]
    return items


@shared_task(name="get_officers")
def get_officers():
    cache = utils.get_cache()
    all_items = []
    url = "https://kaimur.nic.in/wp-admin/admin-ajax.php"
    payload = dict(
        action="dir_filter",
        term_slug=None,
        filter="address,name,designation,email_address,mobile_number,landline_number,fax_number",
    )
    for officer_type, officer_type_name in officer_types.items():
        try:
            tmp_payload = payload.copy()
            tmp_payload["term_slug"] = officer_type
            key = f"get_officers:{officer_type}"
            officers = cache.get(key)
            if not officers:
                officers = get_all_data(url, tmp_payload)
                cache.set(key, officers)
            for officer in officers:
                officer["Type"] = officer_type_name
            all_items.extend(officers)
        except Exception as ex:
            logging.exception(f"failed to get all of {officer_type_name}")
    return all_items
