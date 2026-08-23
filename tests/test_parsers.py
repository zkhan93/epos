"""The parsers are the fragile part -- they depend on the exact table shape the
government site emits. These lock their output down so the container work
cannot have changed it."""

from conftest import fixture

from crawler.epos.parsers import (
    EPDSRCDetailParser,
    RCDetailParser,
    SalesDetailsParser,
    StockDetailParser,
)


def test_sales_details_flattens_the_colspan_header():
    headers, items = SalesDetailsParser().parse(fixture("sales_details.html"))
    # The 7th header is a colspan that has to be replaced by the sub-header row.
    assert headers == [
        "Sr No",
        "RC No",
        "Member Name",
        "Date",
        "Time",
        "Trans Type",
        "Wheat",
        "Rice",
        "Total Price",
    ]
    assert len(items) == 3, "leading header rows and the trailing total row drop out"
    assert items[0] == {
        "Sr No": "1",
        "RC No": "10310060087015900034",
        "Member Name": "Devanti Devi",
        "Date": "05-03-2022",
        "Time": "10:15:02",
        "Trans Type": "Sale",
        "Wheat": "5.000",
        "Rice": "10.000",
        "Total Price": "240",
    }


def test_rc_details_splits_members_and_transactions():
    members, transactions = RCDetailParser().parse(fixture("rc_details.html"))
    assert [m["Member Name"] for m in members] == [
        "Devanti Devi",
        "Ram Krit Singh",
        "Suman Kumari",
    ]
    # UID Status drives the unit count in collection.py.
    assert [m["UID Status"] for m in members] == ["Seeded", "Seeded", "Not Seeded"]
    # get_sales_details reads transactions[0]["Member"] for the display name.
    assert transactions[0]["Member"] == "Devanti Devi"
    assert transactions[0]["Wheat"] == "5.000"


def test_stock_details_suffixes_grouped_columns():
    entries = StockDetailParser().parse(fixture("stock_details.html"))
    assert list(entries[0]) == [
        "Sr No",
        "Commodity",
        "Opening Quantity",
        "Received Quantity",
        "Closing Quantity",
    ]
    assert entries[0]["Commodity"] == "Wheat"
    assert entries[1]["Closing Quantity"] == "60"


def test_stock_details_missing_table_is_empty_not_an_error():
    assert StockDetailParser().parse("<html><body>no table</body></html>") == []


def test_epds_parses_members_and_the_info_header():
    members, extra = EPDSRCDetailParser().parse(fixture("epds_rc_details.html"))
    assert len(members) == 2
    assert members[0]["Member Name"] == "Devanti Devi"
    assert members[0]["Aadhaar"] == "XXXXXXXX8843"
    assert extra == {
        "EPDS FPS Code": "123300100909",
        "Scheme": "PHH",
        "No. of Units": "6",
        "Message": "* Ration Card Found...!",
    }
