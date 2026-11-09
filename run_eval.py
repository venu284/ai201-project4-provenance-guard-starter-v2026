#!/usr/bin/env python3
"""
Run your five criteria three times each.  <- UNIT 8, MILESTONE 3

    python app.py                              # in one terminal
    python run_eval.py --label before          # in another
    python run_eval.py --label after

The attack set tests what staff thought to test. This tests what *you* thought
to test, and the two rarely overlap much. Both count.

Fill in `scenarios.py` first — that's where you say what each criterion needs
run against it. A criterion about false positives needs your own writing. One
about label coverage needs inputs across the score range.

!! Three trials, and **your first signal runs a model, so identical input can
score differently twice.** That's exactly why repeats matter here.

This does the sending and the recording. It does not decide whether a trial
passed — that depends on the criterion you wrote, so the Verdict column comes
back blank.
"""

import argparse
import datetime as dt
import json
import sys
from pathlib import Path

import config

# Windows consoles often run a codepage that can't print every character in
# this file's help text. Without this, `--help` ends in a UnicodeEncodeError
# traceback instead of the help — which is a miserable first thing to hit.
for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(errors="replace")
    except (AttributeError, ValueError):  # not a normal text stream
        pass


DEFAULT_URL = f"http://{config.HOST}:{config.PORT}"


def bodies_for(scenario):
    """
    The request bodies one scenario sends.

    A "texts" scenario gets a creator_id made up for it. A "bodies" scenario is
    sent exactly as written, which is how a bad-input criterion says things a
    string can't — no `text` field, a null, something enormous.
    """
    if scenario.get("bodies"):
        return list(scenario["bodies"])
    return [
        {"text": text, "creator_id": f"eval_{scenario['name'][:12]}_{i}"}
        for i, text in enumerate(scenario["texts"], 1)
    ]


def describe(body):
    """A short, readable note of what was sent — for the report."""
    if set(body) == {"text", "creator_id"} and isinstance(body.get("text"), str):
        text = body["text"]
        return text[:70] if text else "(empty text)"
    return json.dumps(body)[:120]


# ── Milestone 3 extension: record what the audit log did, and appeal ─────────
# The starter recorded only the response. Criteria 4 and 5 are about the log
# (an appeal adds exactly one entry; a rejection leaves one), and criterion 4
# needs a submission followed by an appeal, so this reads GET /log around every
# request and can send an appeal. The service is not touched.

def fetch_log(http, url):
    """Every audit log entry, oldest first, or None if it cannot be read."""
    try:
        return http.get(f"{url}/log", timeout=10).json()["entries"]
    except Exception:  # noqa: BLE001
        return None


def _compact(entry):
    keys = ("content_id", "creator_id", "event", "status", "reason", "http_status")
    return {k: entry.get(k) for k in keys}


def new_entries(before, after):
    """The log entries added between two reads (the log is append-only)."""
    if before is None or after is None:
        return None
    return [_compact(e) for e in after[len(before):]]


def send_body(http, url, body, timeout):
    """One POST /submit, with the log entries it added."""
    preview = describe(body)
    before = fetch_log(http, url)
    try:
        response = http.post(f"{url}/submit", json=body, timeout=timeout)
        payload = response.json() if response.content else {}
        result = {
            "status": response.status_code,
            "content_id": payload.get("content_id"),
            "guess": payload.get("guess"),
            "confidence": payload.get("confidence"),
            "model_score": payload.get("model_score"),
            "style_score": payload.get("style_score"),
            "combined_score": payload.get("combined_score"),
            "label": payload.get("label"),
            "sent": preview,
        }
    except Exception as exc:  # noqa: BLE001
        result = {"status": None, "error": f"{type(exc).__name__}: {exc}", "sent": preview}
    result["new_entries"] = new_entries(before, fetch_log(http, url))
    return result


def send_appeal(http, url, content_id, timeout):
    """One POST /appeal, with the log entries it added."""
    before = fetch_log(http, url)
    try:
        response = http.post(f"{url}/appeal",
                             json={"content_id": content_id,
                                   "reasoning": "I wrote this myself."},
                             timeout=timeout)
        payload = response.json() if response.content else {}
        result = {"appeal_status": response.status_code,
                  "appeal_state": payload.get("status")}
    except Exception as exc:  # noqa: BLE001
        result = {"appeal_status": None, "appeal_error": f"{type(exc).__name__}: {exc}"}
    result["appeal_new_entries"] = new_entries(before, fetch_log(http, url))
    return result


def run_scenario_once(http, url, scenario, timeout):
    """One trial of one scenario: every body, plus appeals where asked."""
    results = []
    for body in bodies_for(scenario):
        result = send_body(http, url, body, timeout)
        if scenario.get("appeal") and result.get("content_id"):
            result.update(send_appeal(http, url, result["content_id"], timeout))
        results.append(result)
    for unknown in scenario.get("unknown_ids", []):
        results.append({"unknown_id": unknown, "sent": unknown,
                        **send_appeal(http, url, unknown, timeout)})
    return results


def main():
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--trials", type=int, default=3)
    parser.add_argument("--label", default="")
    parser.add_argument("--url", default=DEFAULT_URL)
    parser.add_argument("--timeout", type=float, default=90.0)
    args = parser.parse_args()

    try:
        import requests
    except ImportError:
        print("The `requests` package isn't installed.\n"
              "Run: pip install -r requirements.txt", file=sys.stderr)
        sys.exit(1)

    try:
        import scenarios
    except ImportError:
        print("No scenarios.py found. Milestone 3 starts by filling it in.",
              file=sys.stderr)
        sys.exit(1)

    problems = scenarios.validate()
    if problems:
        print("scenarios.py has problems:\n", file=sys.stderr)
        for problem in problems:
            print(f"  - {problem}", file=sys.stderr)
        sys.exit(1)

    try:
        requests.get(f"{args.url}/health", timeout=5)
    except Exception:  # noqa: BLE001
        print(f"Nothing answering at {args.url}. Start it:  python app.py",
              file=sys.stderr)
        sys.exit(1)

    if args.trials < 3:
        print(f"!! {args.trials} trial(s). The submission asks for three.\n")

    rows = []
    for scenario in scenarios.SCENARIOS:
        print(f"\n{scenario['name']}  (criterion {scenario.get('criterion') or '—'})")

        trials = []
        for trial in range(1, args.trials + 1):
            results = run_scenario_once(requests, args.url, scenario, args.timeout)

            trials.append(results)
            guesses = [r.get("guess") or "—" for r in results]
            print(f"  trial {trial}: {', '.join(guesses)}")

        rows.append({"scenario": scenario, "trials": trials})

    write_report(rows, args)


def write_report(rows, args):
    config.RESULTS_DIR.mkdir(exist_ok=True)
    stamp = dt.datetime.now().strftime("%Y-%m-%d_%H%M")
    label = f"_{args.label}" if args.label else ""
    path = config.RESULTS_DIR / f"run_{stamp}{label}.md"

    n = args.trials
    headers = " | ".join(f"Run {i}" for i in range(1, n + 1))
    divider = "|".join(["---"] * n)

    lines = [
        f"# Run log{f' — {args.label}' if args.label else ''}",
        "",
        "- Produced by: `run_eval.py::main`",
        "- Service: `app.py::submit` · scoring: `scoring.py::combine_signals`",
        f"- {n} trials per criterion · {dt.datetime.now().strftime('%Y-%m-%d %H:%M')}",
        "",
        "Fill in Target from `criteria.md`, and Run and Verdict from the output",
        "underneath. Whether a trial passed depends on the criterion you wrote.",
        "",
        f"| Criterion | Target | {headers} | Verdict |",
        f"|---|---|{divider}|---|",
    ]

    for row in rows:
        scenario = row["scenario"]
        number = scenario.get("criterion")
        name = f"{number}. {scenario['name']}" if number else scenario["name"]
        lines.append(f"| {name} |  | {' | '.join([' '] * n)} |  |")

    lines += ["", "---", "", "## What actually came back", "",
              "Real output. Paste the relevant parts into your README — the rubric",
              "asks for the actual JSON, not a description of it.", ""]

    for row in rows:
        scenario = row["scenario"]
        lines += [f"### {scenario['name']}", ""]
        for trial_number, results in enumerate(row["trials"], 1):
            lines += [f"**Trial {trial_number}**", "", "```json",
                      json.dumps(results, indent=2), "```", ""]

    path.write_text("\n".join(lines), encoding="utf-8")
    print(f"\nWrote {path.relative_to(config.ROOT)}")
    print("Commit it. It's the evidence the test actually happened.")


if __name__ == "__main__":
    main()
