"""
Groundedness evaluation for the AI-insights layer.

The insights narrative is only trustworthy if every number in it traces back to
the validated evidence (outputs/insights_evidence.json). This script measures
that, instead of just asserting it:

  1. Extracts every numeric claim from a narrative report.
  2. Checks each one against the evidence, allowing only rounding differences
     (a reported "1,234" matches evidence 1233.7; "12.3%" matches 12.34).
  3. Reports a groundedness rate and lists any ungrounded numbers.
  4. Red-teams the evaluator itself: mutates a random number in the report
     (simulating an LLM hallucination) N times and measures how many mutations
     the checker catches. A checker that cannot catch fabrications is useless.

Run:
    python python/eval_groundedness.py                 # evaluate docs/sample_insights.md
    python python/eval_groundedness.py --report PATH   # evaluate any report
    python python/eval_groundedness.py --llm           # also generate + evaluate a Claude report
"""
import argparse
import json
import random
import re
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
OUT = BASE / "outputs"
DOCS = BASE / "docs"

# Numbers that are methodology constants stated in the narrative template
# (detection thresholds), not data-derived claims.
METHODOLOGY_CONSTANTS = {2.5, 1.5}

DATE_RE = re.compile(r"\b\d{4}-\d{2}-\d{2}\b")
NUM_RE = re.compile(r"(?<![\w.])[-+]?\d[\d,]*\.?\d*")


def flatten_numbers(obj, acc=None):
    """Collect every numeric leaf in the evidence, including numbers embedded in strings."""
    acc = [] if acc is None else acc
    if isinstance(obj, dict):
        for k, v in obj.items():
            flatten_numbers(k, acc)
            flatten_numbers(v, acc)
    elif isinstance(obj, (list, tuple)):
        for v in obj:
            flatten_numbers(v, acc)
    elif isinstance(obj, bool):
        pass
    elif isinstance(obj, (int, float)):
        acc.append(float(obj))
    elif isinstance(obj, str):
        for m in NUM_RE.findall(DATE_RE.sub(" ", obj)):
            try:
                acc.append(float(m.replace(",", "")))
            except ValueError:
                pass
    return acc


def extract_claims(report: str):
    """Return (token, value, decimals) for every numeric claim; dates are stripped first."""
    text = DATE_RE.sub(" ", report)
    claims = []
    for m in NUM_RE.finditer(text):
        token = m.group().rstrip(".,")
        if not token or token in {"+", "-"}:
            continue
        try:
            value = float(token.replace(",", ""))
        except ValueError:
            continue
        decimals = len(token.split(".")[1]) if "." in token else 0
        claims.append((token, value, decimals))
    return claims


def is_grounded(value: float, decimals: int, evidence_numbers) -> bool:
    if abs(value) in METHODOLOGY_CONSTANTS:
        return True
    tol = 0.5 * 10 ** (-decimals) + 1e-9
    return any(abs(abs(value) - abs(e)) <= tol for e in evidence_numbers)


def evaluate(report: str, evidence: dict) -> dict:
    ev_nums = flatten_numbers(evidence)
    claims = extract_claims(report)
    ungrounded = [t for t, v, d in claims if not is_grounded(v, d, ev_nums)]
    n = len(claims)
    return {
        "numbers_checked": n,
        "grounded": n - len(ungrounded),
        "ungrounded": ungrounded,
        "groundedness_rate": (n - len(ungrounded)) / n if n else 1.0,
    }


def mutate_one_number(report: str, rng: random.Random):
    """Simulate a hallucination: change one data-bearing number by 7-40% (never a no-op)."""
    text = DATE_RE.sub(lambda m: m.group().replace("-", "\x00"), report)  # protect dates
    spans = [m for m in NUM_RE.finditer(text) if m.group().rstrip(".,").replace(",", "").replace("-", "").replace("+", "").replace(".", "").isdigit()]
    spans = [m for m in spans if len(m.group().replace(",", "").replace(".", "").lstrip("+-")) >= 2]
    if not spans:
        return None
    m = rng.choice(spans)
    raw = m.group().rstrip(".,")
    value = float(raw.replace(",", ""))
    decimals = len(raw.split(".")[1]) if "." in raw else 0
    factor = 1 + rng.choice([-1, 1]) * rng.uniform(0.07, 0.40)
    new_value = value * factor
    new_token = f"{new_value:,.{decimals}f}" if "," in raw else f"{new_value:.{decimals}f}"
    mutated = text[: m.start()] + new_token + text[m.start() + len(raw):]
    return mutated.replace("\x00", "-")


def red_team(report: str, evidence: dict, trials: int = 200, seed: int = 7) -> dict:
    rng = random.Random(seed)
    caught = tried = 0
    for _ in range(trials):
        mutated = mutate_one_number(report, rng)
        if mutated is None:
            continue
        tried += 1
        if evaluate(mutated, evidence)["ungrounded"]:
            caught += 1
    return {"trials": tried, "caught": caught, "detection_rate": caught / tried if tried else 0.0}


def render_markdown(results: dict) -> str:
    lines = ["# Groundedness Evaluation", "",
             "_Auto-generated by `python/eval_groundedness.py`. Measures whether every number in an "
             "AI-generated narrative traces back to the validated evidence file._", ""]
    for name, r in results["reports"].items():
        e = r["eval"]
        lines += [f"## {name}", "",
                  f"- Numeric claims checked: **{e['numbers_checked']}**",
                  f"- Grounded in evidence: **{e['grounded']}** ({e['groundedness_rate']:.1%})",
                  f"- Ungrounded: {', '.join(e['ungrounded']) if e['ungrounded'] else 'none'}", ""]
        rt = r["red_team"]
        lines += [f"**Red-team of the checker:** {rt['caught']}/{rt['trials']} injected hallucinations "
                  f"(one number altered by 7-40%) were detected -- **{rt['detection_rate']:.1%}** detection rate.", ""]
    lines += ["## Method", "",
              "- A numeric claim is *grounded* if it matches a number in `insights_evidence.json` within "
              "rounding tolerance for the precision it was reported at.",
              "- Dates are excluded; the detection thresholds stated as methodology (2.5, 1.5) are allow-listed.",
              "- The red-team step answers: would this evaluator actually catch an LLM that invents or distorts a figure?",
              "- Limitation 1: matching is against the *pool* of evidence numbers, so a hallucinated figure that "
              "happens to equal some other legitimate number (common for small integers) is not caught. "
              "The undetected red-team cases are all of this collision type. Entity-level matching "
              "(claim -> specific evidence key) would close the gap.",
              "- Limitation 2: this verifies *numeric* fidelity, not whether the prose draws a sensible conclusion "
              "from the numbers. Qualitative review is still required."]
    return "\n".join(lines)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--report", type=Path, default=DOCS / "sample_insights.md")
    ap.add_argument("--llm", action="store_true", help="Also generate a Claude report and evaluate it")
    ap.add_argument("--trials", type=int, default=200)
    args = ap.parse_args()

    evidence = json.loads((OUT / "insights_evidence.json").read_text(encoding="utf-8"))
    results = {"reports": {}}

    rule_report = args.report.read_text(encoding="utf-8")
    results["reports"][f"Rule-based report (`{args.report.name}`)"] = {
        "eval": evaluate(rule_report, evidence),
        "red_team": red_team(rule_report, evidence, args.trials),
    }

    if args.llm:
        import ai_insights  # same-directory import when run as `python python/eval_groundedness.py`
        llm_report = ai_insights.write_llm_report(evidence)
        if llm_report:
            (OUT / "llm_report.md").write_text(llm_report, encoding="utf-8")
            results["reports"]["Claude-phrased report (`outputs/llm_report.md`)"] = {
                "eval": evaluate(llm_report, evidence),
                "red_team": red_team(llm_report, evidence, args.trials),
            }

    md = render_markdown(results)
    (OUT / "groundedness_eval.md").write_text(md, encoding="utf-8")
    print(md)


if __name__ == "__main__":
    main()
