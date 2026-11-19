"""Write the short summary at the top of the monthly report.

Default: a template filled with the month's numbers, so the text is always correct.
Optional: with PEOPLEPULSE_LLM=1 and ANTHROPIC_API_KEY set, a language model writes the
summary. It only receives aggregated numbers (never employee rows), and the result is
labelled "AI draft - review before sending".
"""

from __future__ import annotations

import json
import os
import urllib.request
from datetime import date

from .privacy import is_suppressed


def template_summary(r: dict) -> str:
    m = r["monthly"]
    last, first = m[-1], m[0]
    change = last["headcount"] - first["headcount"]
    depts = [d for d in r["departments"] if not is_suppressed(d["attrition_rate_12m"])]
    worst = max(depts, key=lambda d: d["attrition_rate_12m"])
    low_eng = [d for d in r["departments"] if d["engagement"] is not None and not is_suppressed(d["engagement"])]
    lowest = min(low_eng, key=lambda d: d["engagement"]) if low_eng else None
    rec = r["recruiting"]
    month = date.fromisoformat(last["month"] + "-01").strftime("%B %Y")
    parts = [
        f"Headcount is {last['headcount']} at the end of {month}, {'up' if change >= 0 else 'down'} {abs(change)} over 12 months.",
        f"Voluntary attrition over the last 12 months is {r['attrition']['rate']}% for the company and highest in {worst['department']} ({worst['attrition_rate_12m']}%).",
        f"{rec['open_roles']} roles are open; the median time to hire is {rec['median_days_to_hire']} days and {rec['offer_acceptance_pct']}% of offers made were accepted.",
    ]
    if lowest:
        parts.append(f"The lowest engagement score is in {lowest['department']} ({lowest['engagement']} of 5), worth discussing together with its attrition.")
    return " ".join(parts)


def llm_summary(r: dict) -> str | None:
    key = os.environ.get("ANTHROPIC_API_KEY")
    if os.environ.get("PEOPLEPULSE_LLM") != "1" or not key:
        return None
    aggregates = {k: r[k] for k in ("monthly", "attrition", "departments", "recruiting")}
    prompt = ("Write a 4-sentence summary of this month's people data for senior managers. Use only these aggregated "
              "numbers, mention the most important change and one suggested follow-up, and do not speculate about individuals.\n\n"
              + json.dumps(aggregates, default=str))
    body = json.dumps({"model": os.environ.get("PEOPLEPULSE_MODEL", "claude-sonnet-5-5"), "max_tokens": 300,
                       "messages": [{"role": "user", "content": prompt}]}).encode()
    req = urllib.request.Request("https://api.anthropic.com/v1/messages", data=body, headers={
        "x-api-key": key, "anthropic-version": "2023-06-01", "content-type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.load(resp)
        return "".join(b.get("text", "") for b in data.get("content", [])).strip() or None
    except Exception:
        return None


def summary(r: dict) -> tuple[str, str]:
    ai = llm_summary(r)
    return (ai, "AI draft - review before sending") if ai else (template_summary(r), "Generated from the numbers")
