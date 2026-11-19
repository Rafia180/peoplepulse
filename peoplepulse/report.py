"""Build the monthly result and write all outputs."""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path

import pandas as pd

from . import excel, metrics, narrative


def build(data_dir: Path, last: date) -> dict:
    emp = pd.read_csv(data_dir / "employees.csv", dtype=str, keep_default_na=False)
    req = pd.read_csv(data_dir / "requisitions.csv", keep_default_na=False)
    survey = pd.read_csv(data_dir / "engagement_survey.csv")

    m = metrics.monthly(emp, last)
    att = metrics.attrition_12m(emp, last)
    deps = metrics.by_department(emp, req, survey, last)
    deps["avg_headcount_12m"] = [metrics.attrition_12m(emp, last, emp["department"] == d)["avg_headcount"] for d in deps["department"]]
    rec = metrics.recruiting(req)

    result = {
        "month": last.strftime("%Y-%m"), "as_of": last.isoformat(),
        "monthly": m.to_dict("records"), "attrition": att, "departments": deps.to_dict("records"),
        "recruiting": rec, "gender_by_level": metrics.gender_by_level(emp, last),
        "kpis": {"headcount": int(m.iloc[-1]["headcount"]), "hires_12m": int(m["hires"].sum()),
                 "leavers_12m": att["leavers"], "attrition_rate": att["rate"], "open_roles": rec["open_roles"],
                 "median_days_to_hire": rec["median_days_to_hire"], "offer_acceptance_pct": rec["offer_acceptance_pct"]},
    }
    result["summary"], result["summary_source"] = narrative.summary(result)
    return result


def write_outputs(result: dict, out: Path, template: Path) -> None:
    out.mkdir(parents=True, exist_ok=True)
    excel.write(result, out / f"people_report_{result['month']}.xlsx")
    pd.DataFrame(result["departments"]).to_csv(out / "departments.csv", index=False)
    (out / "summary.md").write_text(f"# People report – {result['month']}\n\n{result['summary']}\n\n*{result['summary_source']}*\n",
                                    encoding="utf-8")
    (out / "result.json").write_text(json.dumps(result, indent=2, default=str), encoding="utf-8")
    html = template.read_text(encoding="utf-8")
    payload = json.dumps(result, default=str, ensure_ascii=False).replace("</", "<\\/")
    (out / "dashboard.html").write_text(html.replace("/*__DATA__*/null", payload), encoding="utf-8")
