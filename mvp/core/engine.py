"""SIP maths. Every number the user sees is computed here; the AI only words these facts."""
import bisect
from datetime import date

from . import data as D

MIN_STARTS = 24  # a history needs at least this many past SIP starts to say "X in 10"


def inr(x):
    """Indian digit grouping, whole rupees: 123456 -> '₹1,23,456'."""
    neg, n = x < 0, int(round(abs(x)))
    s = str(n)
    if len(s) > 3:
        head, tail = s[:-3], s[-3:]
        parts = []
        while len(head) > 2:
            parts.insert(0, head[-2:]); head = head[:-2]
        if head:
            parts.insert(0, head)
        s = ",".join(parts + [tail])
    return ("-" if neg else "") + "₹" + s


def in10(share):
    """0.27 -> 3 (as in '3 in 10'). Never 0 or 10 unless truly none/all."""
    if share <= 0:
        return 0
    if share >= 1:
        return 10
    return min(9, max(1, int(round(share * 10))))


class Series:
    def __init__(self, pts):
        self.pts = pts
        self.dates = [d for d, _ in pts]

    def first_on_or_after(self, d):
        i = bisect.bisect_left(self.dates, d)
        return self.pts[i] if i < len(self.pts) else None

    def last_on_or_before(self, d):
        i = bisect.bisect_right(self.dates, d) - 1
        return self.pts[i] if i >= 0 else None

    def cut(self, as_of):
        return Series([p for p in self.pts if p[0] <= as_of])


def add_months(y, m, k):
    t = y * 12 + (m - 1) + k
    return t // 12, t % 12 + 1


def inst_date(y, m, day):
    import calendar
    return date(y, m, min(day, calendar.monthrange(y, m)[1]))


def run_sip(s, y, m, day, amount, n, measure):
    """n monthly instalments starting (y, m) on `day`; value on `measure` (last NAV on or before)."""
    units, invested = 0.0, 0.0
    for k in range(n):
        yy, mm = add_months(y, m, k)
        p = s.first_on_or_after(inst_date(yy, mm, day))
        if p is None or p[0] > measure:
            return None
        units += amount / p[1]
        invested += amount
    last = s.last_on_or_before(measure)
    if last is None:
        return None
    return invested, units * last[1]


def count_instalments(s, y, m, day, as_of):
    n = 0
    while True:
        yy, mm = add_months(y, m, n)
        d = inst_date(yy, mm, day)
        p = s.first_on_or_after(d)
        if d > as_of or p is None or p[0] > as_of:
            return n
        n += 1


def replay(s, n, horizons, day=5, loss_ratio=None):
    """Every past monthly SIP start in `s`: share red after n instalments (measured on the day the next
    instalment would be due), and of those red, share above invested at each horizon."""
    if not s.pts:
        return None
    y0, m0 = s.dates[0].year, s.dates[0].month
    y0, m0 = add_months(y0, m0, 1)  # first full month
    last = s.dates[-1]
    starts, red_starts, deep = 0, [], 0
    k = 0
    while True:
        y, m = add_months(y0, m0, k)
        k += 1
        my, mm = add_months(y, m, n)
        measure = inst_date(my, mm, day)
        if measure > last:
            break
        r = run_sip(s, y, m, day, 1000, n, measure)
        if r is None:
            continue
        starts += 1
        if r[1] < r[0]:
            red_starts.append((y, m))
        if loss_ratio is not None and r[1] / r[0] <= loss_ratio:
            deep += 1
    out = {"starts": starts, "red": len(red_starts), "red_share": (len(red_starts) / starts) if starts else None,
           "deep_share": (deep / starts) if (starts and loss_ratio is not None) else None, "horizons": []}
    for h in horizons:
        seen = above = 0
        for (y, m) in red_starts:
            hy, hm = add_months(y, m, h)
            measure = inst_date(hy, hm, day)
            if measure > last:
                continue
            r = run_sip(s, y, m, day, 1000, h, measure)
            if r is None:
                continue
            seen += 1
            above += r[1] > r[0]
        out["horizons"].append({"month": h, "red_starts_seen": seen, "above": above,
                                "above_share": (above / seen) if seen else None})
    return out


def horizons_for(n):
    return [24 if n < 24 else n + 12, 36 if n < 36 else n + 24]


def sip_paths(s, day=5, max_m=36, max_starts=160):
    """Time-machine data (shown, not given to the AI): for every past monthly start in `s`, the value as a % above
    or below money put in after 1..max_m instalments, measured when the next instalment is due (as in replay)."""
    if not s or not s.pts:
        return []
    y0, m0 = add_months(s.dates[0].year, s.dates[0].month, 1)
    last = s.dates[-1]
    out, k = [], 0
    while True:
        y, m = add_months(y0, m0, k)
        k += 1
        if inst_date(*add_months(y, m, 1), day) > last:
            break
        units, inv, path = 0.0, 0.0, []
        for t in range(max_m):
            yy, mm = add_months(y, m, t)
            p = s.first_on_or_after(inst_date(yy, mm, day))
            ny, nm = add_months(y, m, t + 1)
            measure = inst_date(ny, nm, day)
            if p is None or measure > last:
                break
            units += 1000 / p[1]
            inv += 1000
            q = s.last_on_or_before(measure)
            path.append(round(100 * (units * q[1] / inv - 1), 1))
        if path:
            out.append({"start": f"{y}-{m:02d}", "p": path})
    if len(out) > max_starts:
        step = len(out) / max_starts
        out = [out[int(i * step)] for i in range(max_starts)]
    return out


def own_path(s, y, m, day, n, as_of):
    units, inv, path = 0.0, 0.0, []
    for t in range(n):
        yy, mm = add_months(y, m, t)
        p = s.first_on_or_after(inst_date(yy, mm, day))
        if p is None:
            break
        units += 1000 / p[1]
        inv += 1000
        ny, nm = add_months(y, m, t + 1)
        q = s.last_on_or_before(min(inst_date(ny, nm, day), as_of))
        path.append(round(100 * (units * q[1] / inv - 1), 1))
    return path


def months_of(s):
    return (s.dates[-1].year - s.dates[0].year) * 12 + s.dates[-1].month - s.dates[0].month if s.pts else 0


def pick_history(n, own=None, proxy=None, market=None):
    """Own fund history if it has enough past starts, else the category index, else the market."""
    need = horizons_for(n)[1] + MIN_STARTS
    for cand in (own, proxy, market):
        if cand and months_of(cand[1]) >= need:
            return cand
    for cand in (market, proxy, own):  # fall back to whatever is long enough for "red at month n"
        if cand and months_of(cand[1]) >= n + MIN_STARTS:
            return cand
    return None, None


def attribution(invested, fund_v, cat_v=None, mkt_v=None):
    """Plain label for 'is it the market or my fund?' (2% of invested is the 'about the same' band)."""
    band = 0.02 * invested
    if fund_v >= invested:
        return "not_red"
    ref = cat_v if cat_v is not None else mkt_v
    if ref is None:
        return "unknown"
    ref_red = ref < invested
    lag = fund_v < ref - band
    if ref_red and not lag:
        return "market"
    if lag and not ref_red:
        return "fund"
    if lag and ref_red:
        return "both"
    return "close"  # index not red and fund within the band: both sit near what was put in


def facts_from_fund(code, start_y, start_m, day, amount, as_of=None, live=True):
    meta, pts, src = D.load_fund(code, live=live)
    own = Series(pts)
    as_of = as_of or own.dates[-1]
    own = own.cut(as_of)
    n = count_instalments(own, start_y, start_m, day, as_of)
    if n < 1:
        raise D.DataError("no instalment has happened yet for that start month")
    inv, val = run_sip(own, start_y, start_m, day, amount, n, as_of)
    pkey = D.proxy_for(meta.get("scheme_category"))
    series = {}
    for key in ("market", pkey):
        if key and key not in series:
            try:
                series[key] = Series(D.load_fund(D.PROXIES[key]["code"], live=live)[1]).cut(as_of)
            except D.DataError:
                pass
    cmp_ = {}
    for key, s in series.items():
        r = run_sip(s, start_y, start_m, day, amount, n, as_of)
        if r:
            cmp_[key] = r[1]
    is_index = "index" in (meta.get("scheme_category") or "").lower() or "etf" in (meta.get("scheme_category") or "").lower()
    cat_v = cmp_.get(pkey) if pkey else None
    lbl, hist = pick_history(n, ("this fund", own), (D.PROXIES[pkey]["label"], series[pkey]) if pkey in series else None,
                             (D.PROXIES["market"]["label"], series["market"]) if "market" in series else None)
    f = base_facts(inv, val, n, amount, as_of)
    f.update({"path": "fund", "fund_name": meta.get("scheme_name", ""), "category": meta.get("scheme_category", ""),
              "category_name": D.CATEGORY_NAMES.get(pkey, ""), "price_source": src, "is_index_fund": is_index})
    equity = "equity" in (meta.get("scheme_category") or "").lower()
    f["compare"] = compare_block(inv, val, cmp_.get("market"), cat_v, pkey) if equity else \
        {"available": False, "reason": "not an equity fund, so a share-market index is not a fair comparison"}
    f["history"] = history_block(n, lbl, hist, loss_ratio=(val / inv) if val < inv else None)
    if f["history"].get("available"):
        f["_paths"] = {"series": lbl, "max_m": horizons_for(n)[1], "paths": sip_paths(hist, 5, horizons_for(n)[1]),
                       "you": own_path(own, start_y, start_m, day, n, as_of)}
    return finish(f)


def facts_from_manual(invested, value, months, as_of=None, live=True):
    market = Series(D.load_fund(D.PROXIES["market"]["code"], live=live)[1])
    if as_of:
        market = market.cut(as_of)
    amount = invested / months if months else invested
    f = base_facts(invested, value, months, amount, as_of or market.dates[-1])
    f.update({"path": "manual", "fund_name": "", "category": "", "category_name": "", "price_source": "manual",
              "is_index_fund": False})
    f["compare"] = {"available": False, "reason": "no fund chosen"}
    lbl, hist = pick_history(months, None, None, (D.PROXIES["market"]["label"], market))
    f["history"] = history_block(months, lbl, hist, loss_ratio=(value / invested) if value < invested else None)
    if f["history"].get("available"):
        f["_paths"] = {"series": lbl, "max_m": horizons_for(months)[1],
                       "paths": sip_paths(hist, 5, horizons_for(months)[1]),
                       "you": [None] * (months - 1) + [round(100 * (value / invested - 1), 1)]}
    return finish(f)


def base_facts(inv, val, n, amount, as_of):
    inv, val = round(inv), round(val)
    gain = val - inv
    return {"months": n, "monthly_amount": inr(amount), "invested": inr(inv), "value": inr(val),
            "gain": inr(gain), "gain_abs": inr(abs(gain)), "direction": "down" if gain < -0.5 else ("up" if gain > 0.5 else "flat"),
            "gain_pct": round(100 * gain / inv, 1) if inv else 0.0, "as_of": as_of.strftime("%d %b %Y"),
            "_inv": inv, "_val": val}


def compare_block(inv, val, mkt_v, cat_v, pkey):
    inv, val = round(inv), round(val)
    mkt_v = round(mkt_v) if mkt_v is not None else None
    cat_v = round(cat_v) if cat_v is not None else None
    if mkt_v is None and cat_v is None:
        return {"available": False, "reason": "no index prices"}
    c = {"available": True, "attribution": attribution(inv, val, cat_v, mkt_v)}
    if mkt_v is not None:
        c.update({"market_label": D.PROXIES["market"]["label"], "market_value": inr(mkt_v),
                  "market_gain": inr(mkt_v - inv), "market_gain_abs": inr(abs(mkt_v - inv)),
                  "market_direction": "down" if mkt_v < inv else "up", "_mkt": mkt_v,
                  "fund_vs_market_abs": inr(abs(val - mkt_v)), "fund_above_market": val >= mkt_v})
    if cat_v is not None and pkey != "market":
        c.update({"category_label": D.PROXIES[pkey]["label"], "category_value": inr(cat_v),
                  "category_gain": inr(cat_v - inv), "category_gain_abs": inr(abs(cat_v - inv)),
                  "category_direction": "down" if cat_v < inv else "up", "_cat": cat_v,
                  "fund_vs_category": inr(val - cat_v), "fund_vs_category_abs": inr(abs(val - cat_v)),
                  "fund_above_category": val >= cat_v})
    return c


def history_block(n, label, s, loss_ratio=None):
    if s is None:
        return {"available": False, "reason": "price history too short"}
    hz = horizons_for(n)
    r = replay(s, n, hz, loss_ratio=loss_ratio)
    if not r or r["starts"] < MIN_STARTS:
        return {"available": False, "reason": "price history too short"}
    h = {"available": True, "series": label, "since_year": s.dates[0].year, "past_starts": r["starts"],
         "red_in_10": in10(r["red_share"]), "red_pct": round(100 * r["red_share"]), "horizons": []}
    if r.get("deep_share") is not None:
        h["deep_share_pct"] = round(100 * r["deep_share"])
        h["deep_in_10"] = in10(r["deep_share"])
        h["deep_rare"] = r["deep_share"] < 0.05
    for x in r["horizons"]:
        if x["red_starts_seen"] >= 5:
            h["horizons"].append({"month": x["month"], "red_starts_seen": x["red_starts_seen"],
                                  "above_in_10": in10(x["above_share"]), "not_above_in_10": 10 - in10(x["above_share"]),
                                  "above_pct": round(100 * x["above_share"])})
    return h


def finish(f):
    """Attach plain-language phrases (so the AI rewords instead of interpreting raw fields) and the list of
    numbers the AI is allowed to use (the gate checks against it)."""
    from . import template
    f["say"] = {"your_numbers": template.your_numbers(f), "history": template.history_line(f), "meaning": template.meaning(f),
                "market_or_fund": template.market_or_fund(f), "patience": template.patience_lines(f),
                "uncertainty": template.UNCERTAIN}
    f["allowed_numbers"] = sorted(numbers_in(f))
    return f


def numbers_in(obj):
    import re
    out = set()
    def walk(o, key=""):
        if isinstance(o, dict):
            for k, v in o.items():
                if not k.startswith("_") and k != "allowed_numbers":
                    walk(v, k)
        elif isinstance(o, list):
            for v in o:
                walk(v, key)
        elif isinstance(o, bool):
            return
        elif isinstance(o, (int, float)):
            out.add(norm_num(str(o)))
        elif isinstance(o, str):
            for t in re.findall(r"\d[\d,]*(?:\.\d+)?", o):
                out.add(norm_num(t))
    walk(obj)
    out.update({"10"})  # "X in 10"
    return out


def norm_num(t):
    t = t.replace(",", "")
    if "." in t:
        t = t.rstrip("0").rstrip(".")
    return t
