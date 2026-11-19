"""Build the monthly people report.

Usage:
    python run.py --month-end 2026-09-30
    PEOPLEPULSE_LLM=1 ANTHROPIC_API_KEY=... python run.py --month-end 2026-09-30   # AI-written summary
"""

from __future__ import annotations

import argparse
from datetime import date
from pathlib import Path

from peoplepulse import report

ROOT = Path(__file__).parent

if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--month-end", type=date.fromisoformat, default=date(2026, 9, 30), help="last day of the report month")
    args = p.parse_args()
    result = report.build(ROOT / "data", args.month_end)
    report.write_outputs(result, ROOT / "output", ROOT / "templates" / "dashboard.html")
    print(result["summary"])
    print(f"\nWrote output/people_report_{result['month']}.xlsx, output/dashboard.html and output/summary.md")
