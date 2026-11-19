"""Write the monthly people report as an Excel workbook.

The workbook uses real Excel formulas for the calculated columns (attrition rate,
funnel conversion), so a reader can click a cell and see how the number is made.
"""

from __future__ import annotations

from pathlib import Path

from openpyxl import Workbook
from openpyxl.chart import BarChart, LineChart, Reference
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter

from .privacy import MIN_GROUP, SUPPRESSED

HEAD = PatternFill("solid", fgColor="1F3A5F")
HEAD_FONT = Font(bold=True, color="FFFFFF")
BLUE = "2A78D6"


def _table(ws, top: int, headers: list[str], rows: list[list]) -> None:
    for c, h in enumerate(headers, start=1):
        cell = ws.cell(row=top, column=c, value=h)
        cell.fill, cell.font = HEAD, HEAD_FONT
        cell.alignment = Alignment(wrap_text=True, vertical="center")
    for r, row in enumerate(rows, start=top + 1):
        for c, v in enumerate(row, start=1):
            ws.cell(row=r, column=c, value=v)
    for c in range(1, len(headers) + 1):
        ws.column_dimensions[get_column_letter(c)].width = max(14, len(headers[c - 1]) + 4)


def write(result: dict, path: Path) -> None:
    wb = Workbook()

    # Summary
    ws = wb.active
    ws.title = "Summary"
    ws["A1"] = f"People report – {result['month']}"
    ws["A1"].font = Font(bold=True, size=16)
    ws["A3"] = result["summary"]
    ws["A3"].alignment = Alignment(wrap_text=True, vertical="top")
    ws.merge_cells("A3:F8")
    ws["A9"] = f"({result['summary_source']})"
    ws["A9"].font = Font(italic=True, color="666666")
    k = result["kpis"]
    _table(ws, 11, ["Measure", "Value"], [
        ["Headcount", k["headcount"]], ["Hires (12 months)", k["hires_12m"]], ["Voluntary leavers (12 months)", k["leavers_12m"]],
        ["Voluntary attrition (12 months, %)", k["attrition_rate"]], ["Open roles", k["open_roles"]],
        ["Median days to hire", k["median_days_to_hire"]], ["Offer acceptance (%)", k["offer_acceptance_pct"]],
    ])
    ws.column_dimensions["A"].width = 36

    # Headcount trend with a line chart
    ws = wb.create_sheet("Headcount")
    m = result["monthly"]
    _table(ws, 1, ["Month", "Headcount", "Hires", "Voluntary exits", "Involuntary exits"],
           [[r["month"], r["headcount"], r["hires"], r["exits_voluntary"], r["exits_involuntary"]] for r in m])
    chart = LineChart()
    chart.title, chart.y_axis.title, chart.height, chart.width = "Headcount, end of month", "Employees", 8, 18
    chart.add_data(Reference(ws, min_col=2, min_row=1, max_row=len(m) + 1), titles_from_data=True)
    chart.set_categories(Reference(ws, min_col=1, min_row=2, max_row=len(m) + 1))
    chart.series[0].graphicalProperties.line.solidFill = BLUE
    chart.series[0].graphicalProperties.line.width = 22000
    chart.legend = None
    ws.add_chart(chart, "G2")

    # Departments, attrition rate as a formula
    ws = wb.create_sheet("Departments")
    deps = result["departments"]
    _table(ws, 1, ["Department", "Headcount", "Voluntary leavers (12m)", "Attrition rate (12m, %)", "Open roles", "Engagement (1–5)"],
           [[d["department"], d["headcount"], d["voluntary_leavers_12m"], None, d["open_roles"], d["engagement"]] for d in deps])
    for i, d in enumerate(deps, start=2):
        # leavers / average headcount (12 months ago and today); the average comes from the tool
        ws.cell(row=i, column=4, value=d["attrition_rate_12m"] if d["attrition_rate_12m"] == SUPPRESSED
                else f"=ROUND(C{i}/{d['avg_headcount_12m']}*100,1)")
    ws.cell(row=len(deps) + 3, column=1, value=f"Groups with fewer than {MIN_GROUP} people are shown as {SUPPRESSED} to protect privacy.").font = Font(italic=True)
    bar = BarChart()
    bar.type, bar.title, bar.height, bar.width = "bar", "Voluntary leavers in the last 12 months", 8, 18
    bar.add_data(Reference(ws, min_col=3, min_row=1, max_row=len(deps) + 1), titles_from_data=True)
    bar.set_categories(Reference(ws, min_col=1, min_row=2, max_row=len(deps) + 1))
    bar.series[0].graphicalProperties.solidFill = BLUE
    bar.legend = None
    ws.add_chart(bar, "H2")

    # Recruiting funnel with conversion formulas
    ws = wb.create_sheet("Recruiting")
    f = result["recruiting"]["funnel"]
    _table(ws, 1, ["Stage", "Count", "Share of previous stage (%)"], [[s["stage"], s["count"], None] for s in f])
    for i in range(3, len(f) + 2):
        ws.cell(row=i, column=3, value=f"=ROUND(B{i}/B{i - 1}*100,1)")

    # Method
    ws = wb.create_sheet("Notes & method")
    notes = [
        "How the numbers are made",
        "Headcount: employees with a hire date on or before the last day of the month and no exit before it.",
        "Voluntary attrition (12 months): voluntary leavers in the last 12 months divided by the average of headcount 12 months ago and today.",
        "Time to hire: days from opening a role to the accepted offer, median of filled roles.",
        f"Privacy: pseudonymous IDs only; any group under {MIN_GROUP} people is hidden; only aggregated numbers are exported.",
        "Data: fictional sample data generated for a portfolio project.",
    ]
    for r, t in enumerate(notes, start=1):
        ws.cell(row=r, column=1, value=t).font = Font(bold=(r == 1))
    ws.column_dimensions["A"].width = 120

    wb.save(path)
