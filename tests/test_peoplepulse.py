"""Tests for PeoplePulse. Run with:  python -m unittest -v  (or pytest)."""

import unittest
from datetime import date
from pathlib import Path

import pandas as pd
from openpyxl import load_workbook

from peoplepulse import metrics, narrative, privacy, report

ROOT = Path(__file__).resolve().parents[1]
LAST = date(2026, 9, 30)


def emp(rows):
    cols = ["emp_id", "department", "location", "level", "gender", "hire_date", "exit_date", "exit_type"]
    return pd.DataFrame([dict(zip(cols, r)) for r in rows])


class PrivacyTests(unittest.TestCase):
    def test_small_group_is_suppressed(self):
        self.assertEqual(privacy.suppress(4.1, 4), "<5")
        self.assertEqual(privacy.suppress(4.1, 5), 4.1)


class MetricTests(unittest.TestCase):
    e = emp([
        ("E1", "A", "Cph", "Analyst", "Woman", "2020-01-01", "", ""),
        ("E2", "A", "Cph", "Analyst", "Man", "2020-01-01", "2026-03-15", "Voluntary"),
        ("E3", "A", "Cph", "Analyst", "Man", "2026-06-01", "", ""),
        ("E4", "A", "Cph", "Analyst", "Woman", "2020-01-01", "2026-08-01", "Involuntary"),
    ])

    def test_headcount_on_a_day(self):
        self.assertEqual(metrics.headcount_on(self.e, date(2026, 9, 30)), 2)
        self.assertEqual(metrics.headcount_on(self.e, date(2025, 9, 30)), 3)

    def test_attrition_counts_only_voluntary(self):
        a = metrics.attrition_12m(self.e, LAST)
        self.assertEqual(a["leavers"], 1)
        self.assertEqual(a["avg_headcount"], 2.5)
        self.assertEqual(a["rate"], 40.0)

    def test_monthly_has_12_months(self):
        self.assertEqual(len(metrics.monthly(self.e, LAST)), 12)


class EndToEnd(unittest.TestCase):
    def test_sample_report(self):
        r = report.build(ROOT / "data", LAST)
        deps = {d["department"]: d for d in r["departments"]}
        self.assertEqual(deps["Group IT"]["engagement"], "<5")                 # 4 respondents: hidden
        worst = max((d for d in r["departments"] if isinstance(d["attrition_rate_12m"], float)), key=lambda d: d["attrition_rate_12m"])
        self.assertEqual(worst["department"], "Asset Management")
        self.assertIn("Asset Management", narrative.template_summary(r))

    def test_excel_report_has_formulas(self):
        out = ROOT / "output"
        report.write_outputs(report.build(ROOT / "data", LAST), out, ROOT / "templates" / "dashboard.html")
        wb = load_workbook(out / "people_report_2026-09.xlsx")
        self.assertEqual(wb.sheetnames, ["Summary", "Headcount", "Departments", "Recruiting", "Notes & method"])
        self.assertTrue(str(wb["Recruiting"]["C3"].value).startswith("=ROUND("))


if __name__ == "__main__":
    unittest.main()
