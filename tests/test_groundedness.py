import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "python"))

import eval_groundedness as g  # noqa: E402

EVIDENCE = {"total_revenue_eur": 1234567.89, "total_orders": 21500, "growth": -4.37,
            "top": [{"name": "Widget 12", "margin_pct": 41.2}]}


def test_exact_and_rounded_numbers_are_grounded():
    report = "Revenue EUR 1,234,568 from 21,500 orders; growth -4.4% ; Widget 12 margin 41.2%."
    result = g.evaluate(report, EVIDENCE)
    assert result["ungrounded"] == []


def test_fabricated_number_is_flagged():
    report = "Revenue EUR 1,234,568 from 23,900 orders."
    assert g.evaluate(report, EVIDENCE)["ungrounded"] == ["23,900"]


def test_dates_are_ignored():
    assert g.evaluate("As of 2025-12-01 orders were 21,500.", EVIDENCE)["ungrounded"] == []


def test_sample_report_is_fully_grounded():
    evidence = json.loads((ROOT / "outputs" / "insights_evidence.json").read_text(encoding="utf-8"))
    report = (ROOT / "docs" / "sample_insights.md").read_text(encoding="utf-8")
    assert g.evaluate(report, evidence)["groundedness_rate"] == 1.0
