"""People metrics: headcount, hires, exits, attrition, recruiting and engagement."""

from __future__ import annotations

from datetime import date

import pandas as pd

from .privacy import suppress


def month_ends(last: date, n: int = 12) -> list[date]:
    """The last day of each of the n months up to and including `last`."""
    out, y, m = [], last.year, last.month
    for _ in range(n):
        nxt = date(y + (m == 12), m % 12 + 1, 1)
        out.append(date.fromordinal(nxt.toordinal() - 1))
        y, m = (y - 1, 12) if m == 1 else (y, m - 1)
    return sorted(out)


def headcount_on(emp: pd.DataFrame, day: date) -> int:
    d = day.isoformat()
    return int(((emp["hire_date"] <= d) & ((emp["exit_date"] == "") | (emp["exit_date"] > d))).sum())


def monthly(emp: pd.DataFrame, last: date) -> pd.DataFrame:
    rows = []
    for end in month_ends(last):
        start = date(end.year, end.month, 1).isoformat()
        e = end.isoformat()
        exits = emp[(emp["exit_date"] >= start) & (emp["exit_date"] <= e)]
        rows.append({"month": end.strftime("%Y-%m"), "headcount": headcount_on(emp, end),
                     "hires": int(((emp["hire_date"] >= start) & (emp["hire_date"] <= e)).sum()),
                     "exits_voluntary": int((exits["exit_type"] == "Voluntary").sum()),
                     "exits_involuntary": int((exits["exit_type"] == "Involuntary").sum())})
    return pd.DataFrame(rows)


def attrition_12m(emp: pd.DataFrame, last: date, group: pd.Series | None = None) -> dict:
    """Voluntary leavers in the last 12 months divided by average headcount (start and end)."""
    start = date(last.year - 1, last.month, last.day) if not (last.month == 2 and last.day == 29) else date(last.year - 1, 2, 28)
    e = emp if group is None else emp[group]
    leavers = int(((e["exit_type"] == "Voluntary") & (e["exit_date"] > start.isoformat()) & (e["exit_date"] <= last.isoformat())).sum())
    avg = (headcount_on(e, start) + headcount_on(e, last)) / 2
    return {"leavers": leavers, "avg_headcount": round(avg, 1), "rate": round(leavers / avg * 100, 1) if avg else 0.0}


def by_department(emp: pd.DataFrame, req: pd.DataFrame, survey: pd.DataFrame, last: date) -> pd.DataFrame:
    rows = []
    for dept in sorted(emp["department"].unique()):
        a = attrition_12m(emp, last, emp["department"] == dept)
        hc = headcount_on(emp[emp["department"] == dept], last)
        r = req[req["department"] == dept]
        s = survey[survey["department"] == dept]
        respondents = int(s["respondents"].iloc[0]) if len(s) else 0
        rows.append({
            "department": dept, "headcount": hc, "voluntary_leavers_12m": a["leavers"],
            "attrition_rate_12m": suppress(a["rate"], hc), "open_roles": int((r["filled"] == "").sum()),
            "engagement": suppress(float(s["engagement"].iloc[0]), respondents) if len(s) else None,
            "survey_respondents": respondents,
        })
    return pd.DataFrame(rows).sort_values("headcount", ascending=False, ignore_index=True)


def recruiting(req: pd.DataFrame) -> dict:
    filled = req[req["filled"] != ""].copy()
    filled["days"] = (pd.to_datetime(filled["filled"]) - pd.to_datetime(filled["opened"])).dt.days
    totals = {k: int(req[k].sum()) for k in ["applicants", "screened", "interviewed", "offers", "accepted"]}
    offers_decided = int(filled["offers"].sum())
    return {
        "funnel": [{"stage": k.capitalize(), "count": v} for k, v in totals.items()],
        "filled_roles": len(filled), "open_roles": int((req["filled"] == "").sum()),
        "median_days_to_hire": int(filled["days"].median()) if len(filled) else None,
        "offer_acceptance_pct": round(filled["accepted"].sum() / offers_decided * 100) if offers_decided else None,
        "days_by_department": filled.groupby("department")["days"].median().round().astype(int).to_dict(),
    }


def gender_by_level(emp: pd.DataFrame, last: date) -> list[dict]:
    d = last.isoformat()
    cur = emp[(emp["hire_date"] <= d) & ((emp["exit_date"] == "") | (emp["exit_date"] > d))]
    rows = []
    for level in ["Analyst", "Associate", "Manager", "Director"]:
        g = cur[cur["level"] == level]
        women = int((g["gender"] == "Woman").sum())
        rows.append({"level": level, "employees": len(g),
                     "women_pct": suppress(round(women / len(g) * 100) if len(g) else 0, len(g))})
    return rows
