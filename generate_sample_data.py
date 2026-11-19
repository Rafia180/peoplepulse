"""Generate fictional HR sample data in data/.

Every person, department, number and survey answer is invented. Employees have
pseudonymous IDs only (no names, no contact details), as people data should
be handled in analytics.
"""

from __future__ import annotations

import random
from datetime import date, timedelta
from pathlib import Path

import pandas as pd

OUT = Path(__file__).parent / "data"
rng = random.Random(21)
START, END = date(2024, 10, 1), date(2026, 9, 30)

DEPARTMENTS = {  # department: (start headcount, monthly hires weight, monthly voluntary exit probability)
    "Investments": (70, 3.0, 0.009),
    "Asset Management": (60, 2.0, 0.010),
    "Technology & Solutions": (45, 2.0, 0.008),
    "Finance": (40, 1.0, 0.006),
    "Legal & Compliance": (25, 0.8, 0.005),
    "People & Culture": (15, 0.5, 0.006),
    "Group IT": (12, 0.4, 0.007),
}
LEVELS = ["Analyst", "Associate", "Manager", "Director"]
LOCATIONS = ["Copenhagen", "Copenhagen", "Copenhagen", "London", "Hamburg", "Singapore"]


def months():
    d = START
    while d <= END:
        yield d
        d = date(d.year + (d.month == 12), d.month % 12 + 1, 1)


def employees() -> pd.DataFrame:
    rows, n = [], 0

    def new(dept, hired):
        nonlocal n
        n += 1
        return {"emp_id": f"E{n:04d}", "department": dept, "location": rng.choice(LOCATIONS),
                "level": rng.choices(LEVELS, weights=[40, 30, 20, 10])[0],
                "gender": rng.choices(["Woman", "Man", "Not disclosed"], weights=[44, 53, 3])[0],
                "hire_date": hired.isoformat(), "exit_date": "", "exit_type": ""}

    for dept, (count, _, _) in DEPARTMENTS.items():
        for _ in range(count):
            rows.append(new(dept, START - timedelta(days=rng.randint(30, 3000))))
    for m in months():
        for dept, (_, hires, quit_p) in DEPARTMENTS.items():
            # Asset Management loses more people in the last 6 months: the story in the data
            if dept == "Asset Management" and m >= date(2026, 4, 1):
                quit_p *= 2.8
            for r in rows:
                if r["department"] == dept and not r["exit_date"] and r["hire_date"] < m.isoformat():
                    if rng.random() < quit_p:
                        r["exit_date"] = (m + timedelta(days=rng.randint(0, 27))).isoformat()
                        r["exit_type"] = "Voluntary"
                    elif rng.random() < 0.0015:
                        r["exit_date"] = (m + timedelta(days=rng.randint(0, 27))).isoformat()
                        r["exit_type"] = "Involuntary"
            for _ in range(int(hires) + (rng.random() < hires % 1)):
                rows.append(new(dept, m + timedelta(days=rng.randint(0, 27))))
    return pd.DataFrame(rows)


def requisitions() -> pd.DataFrame:
    rows = []
    for i in range(1, 61):
        dept = rng.choice(list(DEPARTMENTS))
        opened = END - timedelta(days=rng.randint(10, 330))
        applicants = rng.randint(25, 160)
        screened = int(applicants * rng.uniform(0.25, 0.4))
        interviewed = int(screened * rng.uniform(0.35, 0.55))
        offers = rng.choice([1, 1, 1, 2, 2, 3])          # a role is usually filled by the first or second offer
        accepted = 1
        days = rng.randint(28, 85) + (25 if dept == "Technology & Solutions" else 0)
        filled = opened + timedelta(days=days)
        is_open = filled > END or accepted == 0
        rows.append({"req_id": f"R{i:03d}", "department": dept, "level": rng.choice(LEVELS[:3]),
                     "opened": opened.isoformat(), "filled": "" if is_open else filled.isoformat(),
                     "applicants": applicants, "screened": screened, "interviewed": interviewed,
                     "offers": offers, "accepted": 0 if is_open else accepted})
    return pd.DataFrame(rows)


def engagement() -> pd.DataFrame:
    rows = []
    for dept, (count, _, _) in DEPARTMENTS.items():
        respondents = max(3, int(count * rng.uniform(0.6, 0.85)))
        if dept == "Group IT":
            respondents = 4                      # too few to report: must be suppressed
        base = 3.4 if dept == "Asset Management" else rng.uniform(3.7, 4.2)
        rows.append({"survey": "2026-09", "department": dept, "respondents": respondents,
                     "engagement": round(base, 2), "manager_support": round(base + rng.uniform(-0.2, 0.3), 2),
                     "growth": round(base - rng.uniform(0.0, 0.4), 2), "workload": round(base - rng.uniform(0.1, 0.5), 2)})
    return pd.DataFrame(rows)


if __name__ == "__main__":
    OUT.mkdir(exist_ok=True)
    employees().to_csv(OUT / "employees.csv", index=False)
    requisitions().to_csv(OUT / "requisitions.csv", index=False)
    engagement().to_csv(OUT / "engagement_survey.csv", index=False)
    print("Sample data written to", OUT)
