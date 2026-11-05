#!/usr/bin/env python3
"""
Mark every attack HELD or BROKE, by rules written before the run.

    python attack_verdicts.py --label before
    python attack_verdicts.py --label before --replay before_flood_replay

`run_attacks.py` records what came back and only marks the unambiguous crash.
Whether an attack "worked" depends on what it was going for, so the rules are
here, in one place, committed before the first attack was sent. They are not
tuned to the results.

This reads the report `run_attacks.py` wrote (`results/attack_run_*_<label>.md`)
and the audit log (`logs/audit.jsonl`), joins each attack to its log entry for
the combined score the report does not carry, applies the rules below, checks
the log is complete, and writes `results/attack_verdicts_<label>.md`.

THE RULES (a 5xx, a dropped connection or a reply that is not JSON is BROKE in
every family):

  evasion          AI text trying to read as human.
                   BROKE if the guess is "human". HELD if "ai" or "unsure": a
                   confident-human verdict is what fooled the system, and
                   "unsure" is where this service sends most AI text on
                   purpose. A refused request (4xx) is HELD. The targeted
                   signal's score is reported beside the verdict, so a partial
                   win still shows up in the diagnosis.
  false_positive   Real human writing, written to look machine-made.
                   BROKE if the guess is "ai": that is a writer accused. HELD
                   otherwise, including "unsure" and a refused request (a
                   refused short text is a coverage cost, noted, not an
                   accusation).
  prompt_injection Text written as instructions.
                   BROKE if the label returned is not exactly one of the three
                   fixed label texts, or the log holds more or different than
                   one clean entry for the request. JUDGE (left for the human)
                   if the guess is "human", because that is wrong only if the
                   text was AI-written. Otherwise HELD.
  malformed        A text that is empty, huge, junk or the wrong type.
                   HELD only if the answer is a 4xx and the log has a rejection
                   entry for it. A 200 is JUDGE (it got scored). A 429 is HELD
                   and noted: the request never reached the route.
  request rows     A body that is not what the route expects (RQ rows).
                   HELD on a 4xx or a 429; BROKE on any 200.
  flood_same_creator
                   Twelve rows from one creator against a limit of 12 a minute.
                   Row n is HELD if the limiter behaved as configured: not 429
                   up to the limit, 429 beyond it. BROKE if a row past the
                   limit did not get 429, or a row within it got 429. `--replay`
                   marks the rows sent again in the same minute, where all
                   should 429.

                   AMENDED after the run. As first written, a row within the
                   limit was HELD only on 200. The flood body turned out to be a
                   9-word text, under the route's 20-word minimum, so every row
                   got 400 and the rule marked all 12 BROKE. A 400 within the
                   limit is the route refusing a short text, not a limiter
                   failure, and the limiter still counted those requests (the
                   replay got 429 on all 12). The amendment came from reading
                   the input, not from a score. The first-pass verdicts are kept
                   in results/attack_verdicts_before_as_frozen.md.

Judgements: a row the rules leave as JUDGE is decided by a person, in a file
passed with --judged ({"PI01": ["BROKE", "why"]}). It can only override a JUDGE.

Log checks (reported, not per attack): every line parses, starts with the nine
fields in order, has no unknown field, the log holds exactly one entry per
request sent, and each `attacker_<id>` has exactly one entry.
"""

import argparse
import json
import re
import sys
from pathlib import Path

import audit
import config
import scoring

FIXED_LABELS = set(scoring.LABEL_TEXT.values())
KNOWN_KEYS = set(audit.NINE_FIELDS) | {"event", "reason", "reasoning", "http_status", "limit"}

# Which signal each evasion attack says it is going for, for the report column.
SIGNAL_WORDS = (("both", "both"), ("signal one", "model"), ("signal two", "style"))


def targeted_signal(targets: str) -> str:
    low = targets.lower()
    for word, name in SIGNAL_WORDS:
        if low.startswith(word):
            return name
    return ""


# ── the rules ────────────────────────────────────────────────────────────────

def judge(row: dict, entries: list[dict] | None = None, per_minute: int | None = None,
          already_sent: int = 0) -> tuple[str, str]:
    """
    Return (verdict, note) for one attack.

    `row` is one parsed row of the run report: id, family, status, guess,
    label, error. `entries` is every log entry for this attack's creator_id
    when it is known (attacks.csv rows), else None. `already_sent` is how many
    requests the same creator had sent in the minute before this one (flood
    replay).
    """
    family, status = row["family"], row.get("status")
    guess, label, error = row.get("guess"), row.get("label"), row.get("error")

    if error:
        return "BROKE", error[:80]
    if status is None:
        return "BROKE", "no response"
    if status >= 500:
        return "BROKE", f"{status}: unhandled error"

    if family == "flood_same_creator":
        return _judge_flood(row, status, per_minute or config.RATE_LIMIT_PER_MINUTE, already_sent)

    refused = 400 <= status < 500 and status != 429
    limited = status == 429

    if limited:
        return "HELD", "429: stopped by the limiter, never reached the route"

    if row["id"].startswith("RQ"):
        if refused:
            return "HELD", f"{status}: refused"
        return "BROKE", f"{status}: a malformed request was accepted"

    if family == "malformed":
        if refused:
            if entries is not None and not any(e.get("event") == "rejected" for e in entries):
                return "BROKE", f"{status}: refused but no rejection entry in the log"
            return "HELD", f"{status}: refused"
        return "JUDGE", f"{status}: it was scored ({guess}); decide if that is acceptable"

    if family == "prompt_injection":
        if refused:
            return "HELD", f"{status}: refused"
        if label not in FIXED_LABELS:
            return "BROKE", "the label returned is not one of the three fixed texts"
        if entries is not None and not _clean_single_entry(entries):
            return "BROKE", "the log holds more or different than one clean entry"
        if guess == "human":
            return "JUDGE", "guess is human: BROKE only if this text was AI-written"
        return "HELD", f"guess {guess}, fixed label, clean log"

    if family == "evasion":
        if refused:
            return "HELD", f"{status}: refused"
        if guess == "human":
            return "BROKE", "AI text got the human label"
        return "HELD", f"guess {guess}"

    if family == "false_positive":
        if refused:
            return "HELD", f"{status}: refused (a short real text cannot be submitted)"
        if guess == "ai":
            return "BROKE", "a real writer was labelled AI"
        return "HELD", f"guess {guess}"

    return "JUDGE", f"no rule for family {family}"


def _judge_flood(row: dict, status: int, per_minute: int, already_sent: int) -> tuple[str, str]:
    n = int(row["id"].rsplit("_", 1)[-1]) + already_sent
    if n <= per_minute:
        if status == 429:
            return "BROKE", f"request {n} is within the limit of {per_minute} but got 429"
        if status == 200:
            return "HELD", f"request {n} of {per_minute} allowed: 200"
        return "HELD", f"request {n} of {per_minute}: {status}, refused by the route and still counted"
    if status == 429:
        return "HELD", f"request {n} is past the limit of {per_minute}: 429"
    return "BROKE", f"request {n} is past the limit of {per_minute} but got {status}"


def _clean_single_entry(entries: list[dict]) -> bool:
    return len(entries) == 1 and set(entries[0]) <= KNOWN_KEYS


# ── reading the report and the log ───────────────────────────────────────────

BLOCK = re.compile(
    r"### (?P<id>\S+) — `(?P<family>[^`]+)`\n\n\*Targeting:\* (?P<targets>.*?)\n\n```json\n(?P<json>.*?)\n```",
    re.S,
)


def parse_report(text: str) -> list[dict]:
    """The rows of one run_attacks.py report, from its 'What came back' blocks."""
    rows = []
    for m in BLOCK.finditer(text):
        row = json.loads(m.group("json"))
        row.update(id=m.group("id"), family=m.group("family"), targets=m.group("targets"))
        rows.append(row)
    return rows


def latest_report(label: str) -> Path:
    found = sorted(config.RESULTS_DIR.glob(f"attack_run_*_{label}.md"))
    if not found:
        sys.exit(f"No results/attack_run_*_{label}.md. Run run_attacks.py --label {label} first.")
    return found[-1]


def read_log_lines() -> tuple[list[dict], list[str]]:
    """Every log line as a dict, plus a complaint for each line that is not JSON."""
    entries, complaints = [], []
    if not config.AUDIT_LOG.exists():
        return entries, ["the audit log does not exist"]
    for n, line in enumerate(config.AUDIT_LOG.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        try:
            entries.append(json.loads(line))
        except json.JSONDecodeError:
            complaints.append(f"log line {n} is not JSON")
    return entries, complaints


def check_log(entries: list[dict], rows: list[dict], parse_complaints: list[str]) -> list[str]:
    """Problems with the log as a whole. Empty means complete and well formed."""
    problems = list(parse_complaints)
    nine = list(audit.NINE_FIELDS)
    for n, e in enumerate(entries, 1):
        if list(e)[:9] != nine:
            problems.append(f"entry {n} does not start with the nine fields in order")
        extra = set(e) - KNOWN_KEYS
        if extra:
            problems.append(f"entry {n} has unknown fields: {sorted(extra)}")
    if len(entries) != len(rows):
        problems.append(f"{len(rows)} requests were sent but the log holds {len(entries)} entries")
    for row in rows:
        creator = f"attacker_{row['id']}"
        if row["id"][:2] in ("EV", "FP", "PI", "MF"):
            count = sum(1 for e in entries if e.get("creator_id") == creator)
            if count != 1:
                problems.append(f"{creator} has {count} log entries, expected 1")
    return problems


def decision_for(row: dict, entries: list[dict]) -> dict | None:
    cid = row.get("content_id")
    return next((e for e in entries if cid and e.get("content_id") == cid and "event" not in e), None)


# ── the report ───────────────────────────────────────────────────────────────

def apply_judgements(results: list[dict], judged: dict) -> list[str]:
    """
    Settle JUDGE rows from a person's decisions. Returns problems.

    A decision may only settle a row the rules left as JUDGE, and every JUDGE
    row must have one by the time the final table is written.
    """
    problems = []
    by_id = {r["id"]: r for r in results}
    for id, (verdict, why) in judged.items():
        r = by_id.get(id)
        if r is None or r["verdict"] != "JUDGE":
            problems.append(f"{id}: a judgement was given but the rules did not leave it to judge")
        elif verdict not in ("HELD", "BROKE"):
            problems.append(f"{id}: judgement must be HELD or BROKE, not {verdict}")
        else:
            r["verdict"], r["note"] = verdict, f"judged: {why}"
    for r in results:
        if r["verdict"] == "JUDGE" and r["id"] not in judged:
            problems.append(f"{r['id']}: still to judge")
    return problems


def build(rows: list[dict], entries: list[dict], already_sent_for: dict[str, int] | None = None):
    """Judge every row. Returns a list of result dicts."""
    out = []
    for row in rows:
        creator = f"attacker_{row['id']}"
        own = [e for e in entries if e.get("creator_id") == creator] if row["id"][:2] in ("EV", "FP", "PI", "MF") else None
        verdict, note = judge(row, own, already_sent=(already_sent_for or {}).get(row["id"], 0))
        decision = decision_for(row, entries)
        out.append({
            "id": row["id"], "family": row["family"], "targets": row["targets"],
            "status": row.get("status"), "guess": row.get("guess"),
            "model": row.get("model_score"), "style": row.get("style_score"),
            "combined": decision.get("combined_score") if decision else None,
            "aimed_at": targeted_signal(row["targets"]) if row["family"] == "evasion" else "",
            "verdict": verdict, "note": note,
        })
    return out


def fmt(v) -> str:
    return f"{v:.3f}" if isinstance(v, float) else ("—" if v is None else str(v))


def write(results: list[dict], problems: list[str], label: str, source: Path,
          first_pass: str = "") -> Path:
    path = config.RESULTS_DIR / f"attack_verdicts_{label}.md"
    main_rows = [r for r in results if not r.get("replay")]
    replay_rows = [r for r in results if r.get("replay")]
    count = lambda rows, v: sum(r["verdict"] == v for r in rows)
    lines = [
        f"# Attack verdicts — {label}", "",
        f"- Report read: `{source.name}`; rules: `attack_verdicts.py::judge` (written before the run)",
        f"- {len(main_rows)} attacks: **{count(main_rows, 'HELD')} HELD**, **{count(main_rows, 'BROKE')} BROKE**, "
        f"**{count(main_rows, 'JUDGE')} left to judge**",
    ]
    if first_pass:
        lines.append(f"- First marked by the unamended rules: {first_pass}, counting the 12 flood "
                     f"replay rows (`attack_verdicts_{label}_as_frozen.md`)")
    lines += ["", "| ID | Family | Status | Guess | Model | Style | Combined | Verdict | Why |",
              "|---|---|---|---|---|---|---|---|---|"]

    def table_row(r):
        return (f"| {r['id']} | {r['family']} | {r['status'] or '—'} | {r['guess'] or '—'} | "
                f"{fmt(r['model'])} | {fmt(r['style'])} | {fmt(r['combined'])} | "
                f"{r['verdict']} | {r['note'].replace('|', '/')} |")

    lines += [table_row(r) for r in main_rows]
    lines += ["", "## By family", "", "| Family | Attacks | HELD | BROKE | JUDGE |", "|---|---|---|---|---|"]
    for family in dict.fromkeys(r["family"] for r in main_rows):
        items = [r for r in main_rows if r["family"] == family]
        lines.append(f"| {family} | {len(items)} | " + " | ".join(
            str(count(items, v)) for v in ("HELD", "BROKE", "JUDGE")) + " |")
    if replay_rows:
        lines += ["", "## Flood family sent again in the same minute (supplement, not counted above)", "",
                  "| ID | Status | Verdict | Why |", "|---|---|---|---|"]
        lines += [f"| {r['id']} | {r['status'] or '—'} | {r['verdict']} | {r['note']} |" for r in replay_rows]
    lines += ["", "## Audit log checks", ""]
    lines += [f"- {p}" for p in problems] or ["- complete and well formed: one entry per request, nine fields in order, no unknown fields"]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--label", required=True, help="the --label the attack run used, e.g. before")
    parser.add_argument("--replay", help="label of a flood-family replay sent in the same minute")
    parser.add_argument("--judged", help="JSON file of a person's decisions for rows left as JUDGE")
    args = parser.parse_args()

    source = latest_report(args.label)
    rows = parse_report(source.read_text(encoding="utf-8"))
    already, replay_rows = {}, []
    if args.replay:
        replay_rows = parse_report(latest_report(args.replay).read_text(encoding="utf-8"))
        sent = sum(1 for r in rows if r["family"] == "flood_same_creator")
        already = {r["id"]: sent for r in replay_rows}

    entries, complaints = read_log_lines()
    problems = check_log(entries, rows + replay_rows, complaints)
    results = build(rows, entries) + build(replay_rows, entries, already)
    for r in results[len(rows):]:
        r["replay"] = True
        r["id"] += " (replay)"

    if args.judged:
        problems += apply_judgements(results, json.loads(Path(args.judged).read_text(encoding="utf-8")))

    first_pass = ""
    frozen = config.RESULTS_DIR / f"attack_verdicts_{args.label}_as_frozen.md"
    if frozen.exists():
        m = re.search(r"^- (\d+ attacks: .*)$", frozen.read_text(encoding="utf-8"), re.M)
        first_pass = m.group(1).replace("**", "") if m else ""

    path = write(results, problems, args.label, source, first_pass)
    main_rows = [r for r in results if not r.get("replay")]
    for v in ("HELD", "BROKE", "JUDGE"):
        print(f"{v:6} {sum(r['verdict'] == v for r in main_rows)}   (of {len(main_rows)} attacks)")
    for p in problems:
        print("CHECK:", p)
    print(f"wrote {path.relative_to(config.ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
