#!/usr/bin/env python3
"""
Apply each criterion's target to what run_eval.py got back.

    python eval_verdicts.py --label before

`run_eval.py` sends the scenarios in scenarios.py three times and records the
real responses; it does not decide whether a trial passed. The targets are in
criteria.md and are applied here, in one place, committed before the first run.
They are not changed after a score has been seen, and a missed target is
diagnosed, not lowered.

Per trial (every criterion must hold in ALL three trials to be MET):

  1  My own writing        at most 1 of the 10 pieces gets guess "ai".
  2  Score spread          mean combined_score of the 5 clearly-AI texts is at
                           least 0.30 above the mean of the 5 clearly-human
                           texts. The combined score is recomputed from the two
                           signal scores with scoring.combine_signals, the same
                           function the route uses.
  3  Labels reachable      all three labels appear across the 9 inputs, and at
                           least 2 of the 3 borderline inputs get "unsure".
  4  Appeals               all 5 appeals return 200 with status "under_review"
                           and add exactly one new log entry (an appeal for that
                           content_id with status under_review); an id that was
                           never issued returns 404 and writes no under_review
                           entry.
  5  Bad input             all 8 bad bodies get the status criteria.md lists, no
                           500, and each adds exactly one rejection entry.

A trial where a request failed outright (no status) cannot meet a criterion.
"""

import argparse
import json
import re
import statistics
import sys
from pathlib import Path

import config
import scenarios
import scoring

TARGETS = {
    1: "at most 1 of 10 labelled AI",
    2: "mean combined gap of AI over human at least 0.30",
    3: "all 3 labels appear; at least 2 of 3 borderline are unsure",
    4: "5 of 5 appeals: 200, under_review, one new entry; unknown id 404, no under_review entry",
    5: "8 of 8 get the listed code, no 500, one rejection entry each",
}
NAMES = {
    1: "My own writing flagged as AI",
    2: "Clearly-AI and clearly-human texts score far apart",
    3: "All three labels are reachable",
    4: "An appeal always changes status and is recorded",
    5: "Bad input never crashes the service",
}


# ── reading the report ───────────────────────────────────────────────────────

TOKEN = re.compile(
    r"^### (?P<name>[^\n]+)$|^\*\*Trial (?P<n>\d+)\*\*\n\n```json\n(?P<json>.*?)\n```",
    re.M | re.S,
)


def parse_report(text: str) -> dict[str, dict[int, list]]:
    """scenario name -> trial number -> the list of results run_eval recorded."""
    out: dict[str, dict[int, list]] = {}
    name = None
    for m in TOKEN.finditer(text):
        if m.group("name"):
            name = m.group("name")
        elif name is not None:
            out.setdefault(name, {})[int(m.group("n"))] = json.loads(m.group("json"))
    return out


def latest_report(label: str) -> Path:
    found = sorted(config.RESULTS_DIR.glob(f"run_*_{label}.md"))
    if not found:
        sys.exit(f"No results/run_*_{label}.md. Run run_eval.py --label {label} first.")
    return found[-1]


# ── the five criteria, for one trial ─────────────────────────────────────────
# Each takes {scenario name: [results]} for ONE trial and returns (met, value).

def _all_scored(results) -> bool:
    return bool(results) and all(r.get("status") == 200 for r in results)


def criterion_1(trial: dict) -> tuple[bool, str]:
    results = trial["my own writing"]
    flagged = sum(1 for r in results if r.get("guess") == "ai")
    ok = _all_scored(results) and flagged <= 1
    return ok, f"{flagged}/{len(results)}" + ("" if _all_scored(results) else " (a request failed)")


def combined(result: dict) -> float:
    return scoring.combine_signals(result["model_score"], result["style_score"])


def criterion_2(trial: dict) -> tuple[bool, str]:
    ai, human = trial["clear AI"], trial["clear human"]
    if not (_all_scored(ai) and _all_scored(human)):
        return False, "n/a (a request failed)"
    gap = statistics.mean(combined(r) for r in ai) - statistics.mean(combined(r) for r in human)
    return gap >= 0.30, f"{gap:.3f}"


def criterion_3(trial: dict) -> tuple[bool, str]:
    groups = [trial["labels: AI"], trial["labels: human"], trial["labels: borderline"]]
    if not all(_all_scored(g) for g in groups):
        return False, "n/a (a request failed)"
    seen = {r["guess"] for g in groups for r in g}
    unsure = sum(1 for r in trial["labels: borderline"] if r["guess"] == "unsure")
    return len(seen) == 3 and unsure >= 2, f"{len(seen)}/3 labels, {unsure}/3 unsure"


def _appeal_ok(r: dict) -> bool:
    entries = r.get("appeal_new_entries")
    return (
        r.get("status") == 200
        and r.get("appeal_status") == 200
        and r.get("appeal_state") == "under_review"
        and entries is not None
        and len(entries) == 1
        and entries[0].get("event") == "appeal"
        and entries[0].get("status") == "under_review"
        and entries[0].get("content_id") == r.get("content_id")
    )


def _unknown_ok(r: dict) -> bool:
    entries = r.get("appeal_new_entries")
    return (
        r.get("appeal_status") == 404
        and entries is not None
        and all(e.get("status") != "under_review" for e in entries)
    )


def criterion_4(trial: dict) -> tuple[bool, str]:
    results = trial["appeals"]
    appeals = [r for r in results if "unknown_id" not in r]
    unknown = [r for r in results if "unknown_id" in r]
    good = sum(1 for r in appeals if _appeal_ok(r))
    unknown_ok = bool(unknown) and all(_unknown_ok(r) for r in unknown)
    ok = len(appeals) == 5 and good == 5 and unknown_ok
    return ok, f"{good}/{len(appeals)}, unknown id {'404' if unknown_ok else 'wrong'}"


def _bad_input_ok(r: dict, expected: int) -> bool:
    entries = r.get("new_entries")
    return (
        r.get("status") == expected
        and (r.get("status") or 0) < 500
        and entries is not None
        and len(entries) == 1
        and entries[0].get("event") == "rejected"
        and entries[0].get("http_status") == expected
    )


def criterion_5(trial: dict) -> tuple[bool, str]:
    expected = next(s["expect"] for s in scenarios.SCENARIOS if s["name"] == "bad input")
    results = trial["bad input"]
    if len(results) != len(expected):
        return False, f"n/a ({len(results)} results for {len(expected)} bodies)"
    good = sum(1 for r, e in zip(results, expected) if _bad_input_ok(r, e))
    return good == len(expected), f"{good}/{len(expected)}"


CRITERIA = {1: criterion_1, 2: criterion_2, 3: criterion_3, 4: criterion_4, 5: criterion_5}


# ── running them across trials ───────────────────────────────────────────────

def evaluate(report: dict[str, dict[int, list]]) -> dict[int, list[tuple[bool, str]]]:
    """criterion number -> one (met, value) per trial."""
    trials = sorted({n for runs in report.values() for n in runs})
    out = {}
    for number, rule in CRITERIA.items():
        out[number] = [rule({name: runs[t] for name, runs in report.items()}) for t in trials]
    return out


def verdict(per_trial: list[tuple[bool, str]]) -> str:
    return "MET" if per_trial and all(ok for ok, _ in per_trial) else "MISSED"


def write(results: dict, label: str, source: Path) -> Path:
    path = config.RESULTS_DIR / f"eval_verdicts_{label}.md"
    n = len(next(iter(results.values())))
    head = " | ".join(f"Run {i}" for i in range(1, n + 1))
    lines = [
        f"# Criteria verdicts — {label}", "",
        f"- Report read: `{source.name}`; rules: `eval_verdicts.py` (committed before the run)", "",
        f"| Criterion | Target | {head} | Verdict |",
        f"|---|---|{'|'.join(['---'] * n)}|---|",
    ]
    for number, per_trial in results.items():
        cells = " | ".join(value for _, value in per_trial)
        lines.append(f"| {number}. {NAMES[number]} | {TARGETS[number]} | {cells} | {verdict(per_trial)} |")
    identical = all(len({value for _, value in per_trial}) == 1 for per_trial in results.values())
    lines += ["", f"- Trials identical on every criterion: **{'yes' if identical else 'NO'}**"]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--label", required=True)
    args = parser.parse_args()
    source = latest_report(args.label)
    report = parse_report(source.read_text(encoding="utf-8"))
    missing = [s["name"] for s in scenarios.SCENARIOS if s["name"] not in report]
    if missing:
        sys.exit(f"The report has no results for: {missing}")
    results = evaluate(report)
    path = write(results, args.label, source)
    for number, per_trial in results.items():
        print(f"{number}. {verdict(per_trial):7} " + "  ".join(v for _, v in per_trial))
    print(f"wrote {path.relative_to(config.ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
