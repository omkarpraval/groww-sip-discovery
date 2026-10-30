"""Hand-worked SIP checks (run: python -m pytest mvp/tests)."""
from datetime import date, timedelta

from mvp.core import engine as E


def daily(start, navs_by_month, day=5, end=None):
    """NAV equal to navs_by_month[i] from the `day` of month i until the next one."""
    pts, d = [], start
    y, m = start.year, start.month
    for i, v in enumerate(navs_by_month):
        y2, m2 = E.add_months(start.year, start.month, i + 1)
        stop = E.inst_date(y2, m2, day)
        while d < stop:
            pts.append((d, v)); d += timedelta(days=1)
    return E.Series(pts)


def test_three_instalments_by_hand():
    # NAV 10, 8, 12 on the 5th of Jan, Feb, Mar; NAV 11 on the day we measure.
    s = daily(date(2024, 1, 5), [10, 8, 12, 11])
    inv, val = E.run_sip(s, 2024, 1, 5, 1000, 3, date(2024, 4, 5))
    # units = 100 + 125 + 83.333 = 308.333 ; value = 308.333 * 11 = 3391.67
    assert inv == 3000
    assert abs(val - 3391.67) < 0.01


def test_flat_price_is_flat():
    s = daily(date(2024, 1, 5), [10] * 8)
    inv, val = E.run_sip(s, 2024, 1, 5, 2500, 6, date(2024, 7, 5))
    assert inv == 15000 and abs(val - 15000) < 1e-6


def test_falling_then_recovering():
    # 4,000 a month at 100, 80, 60; measured at 90: units 40+50+66.67=156.67 -> 14,100 vs 12,000
    s = daily(date(2023, 6, 5), [100, 80, 60, 90])
    inv, val = E.run_sip(s, 2023, 6, 5, 4000, 3, date(2023, 9, 5))
    assert inv == 12000 and abs(val - 14100) < 0.01


def test_count_and_weekend_shift():
    s = daily(date(2024, 1, 6), [10] * 5)  # data starts on the 6th: first instalment waits for the next price
    assert E.count_instalments(s, 2024, 1, 5, date(2024, 3, 31)) == 3


def test_inr_grouping():
    assert E.inr(123456) == "₹1,23,456" and E.inr(999) == "₹999" and E.inr(-12000.4) == "-₹12,000"


def test_in10():
    assert E.in10(0.27) == 3 and E.in10(0.01) == 1 and E.in10(0.99) == 9 and E.in10(0) == 0 and E.in10(1) == 10


def test_attribution():
    assert E.attribution(10000, 9500, 9600) == "market"
    assert E.attribution(10000, 9500, 10300) == "fund"
    assert E.attribution(10000, 9000, 9600) == "both"
    assert E.attribution(10000, 10100, 9000) == "not_red"
    assert E.attribution(10000, 9950, 10050) == "close"
