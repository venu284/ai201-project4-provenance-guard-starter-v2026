#!/usr/bin/env python3
"""
Put the before and after runs side by side, and apply the success test that was
written before the change.

    python compare_runs.py                       # before = "before", after = "after"
    python compare_runs.py --before before --after after

Reads results/attack_verdicts_<label>.md, results/eval_verdicts_<label>.md and
the criteria run reports, prints the comparison and writes results/before_after.md.

The success test was fixed in the Milestone 5 plan before the change and the
re-run. The change helped if:

  (a) the number of broken attacks fell;
  (b) no real-writer text was newly labelled "ai" (the false_positive attacks and
      the ten own-writing pieces); and
  (c) no criterion that was MET became MISSED.

It says PASS or FAIL for each, and does not soften a FAIL.
"""

import argparse
import re
import sys
from pathlib import Path

import config
import eval_verdicts


def parse_attack_table(text: str) -> dict[str, dict]:
    """id -> {family, status, guess, combined, verdict} from an attack_verdicts file."""
    rows = {}
    main = text.split("## By family")[0]
    for line in main.splitlines():
        if line.startswith("| ") and not line.startswith(("| ID", "|---")):
            c = [x.strip() for x in line.strip().strip("|").split("|")]
            rows[c[0]] = {"family": c[1], "status": c[2], "guess": c[3],
                          "combined": c[6], "verdict": c[7]}
    return rows


def parse_criteria_table(text: str) -> dict[int, dict]:
    """criterion number -> {name, runs, verdict} from an eval_verdicts file."""
    rows = {}
    for line in text.splitlines():
        m = re.match(r"\| (\d)\. ([^|]+)\|([^|]*)\|(.*)\|\s*(MET|MISSED)\s*\|$", line)
        if m:
            runs = [x.strip() for x in m.group(4).split("|")]
            rows[int(m.group(1))] = {"name": m.group(2).strip(), "runs": runs, "verdict": m.group(5)}
    return rows


def counts(rows: dict[str, dict]) -> dict[str, dict[str, int]]:
    out: dict[str, dict[str, int]] = {}
    for r in rows.values():
        fam = out.setdefault(r["family"], {"HELD": 0, "BROKE": 0, "JUDGE": 0})
        fam[r["verdict"]] += 1
    return out


def success_test(before_attacks, after_attacks, before_own, after_own, before_c, after_c):
    """The three pre-registered checks. Each is (label, passed, detail)."""
    broke_b = sum(r["verdict"] == "BROKE" for r in before_attacks.values())
    broke_a = sum(r["verdict"] == "BROKE" for r in after_attacks.values())
    accused = [i for i, r in after_attacks.items()
               if r["family"] == "false_positive" and r["guess"] == "ai"
               and before_attacks[i]["guess"] != "ai"]
    own_new = [n for n, (b, a) in enumerate(zip(before_own, after_own), 1)
               if a["guess"] == "ai" and b["guess"] != "ai"]
    worse = [n for n, r in before_c.items() if r["verdict"] == "MET" and after_c[n]["verdict"] != "MET"]
    return [
        ("(a) fewer broken attacks", broke_a < broke_b, f"{broke_b} broke before, {broke_a} after"),
        ("(b) no real-writer text newly labelled ai", not accused and not own_new,
         "newly accused: " + (", ".join(accused + [f"own_{n:02d}" for n in own_new]) or "none")),
        ("(c) no MET criterion became MISSED", not worse,
         "became MISSED: " + (", ".join(map(str, worse)) or "none")),
    ]


def own_results(label: str) -> list[dict]:
    """Trial 1 of the own-writing scenario, each with its recomputed combined score."""
    rep = eval_verdicts.parse_report(eval_verdicts.latest_report(label).read_text(encoding="utf-8"))
    out = []
    for r in rep["my own writing"][1]:
        out.append({**r, "combined": eval_verdicts.combined(r)})
    return out


def build(before: str, after: str) -> tuple[str, list]:
    ba = parse_attack_table((config.RESULTS_DIR / f"attack_verdicts_{before}.md").read_text(encoding="utf-8"))
    aa = parse_attack_table((config.RESULTS_DIR / f"attack_verdicts_{after}.md").read_text(encoding="utf-8"))
    bc = parse_criteria_table((config.RESULTS_DIR / f"eval_verdicts_{before}.md").read_text(encoding="utf-8"))
    ac = parse_criteria_table((config.RESULTS_DIR / f"eval_verdicts_{after}.md").read_text(encoding="utf-8"))
    bo, ao = own_results(before), own_results(after)

    lines = [f"# Before and after ({before} vs {after})", "",
             "Produced by `compare_runs.py` from the verdict files and the criteria run reports.", "",
             "## Attack set, by family", "", "| Family | Attacks | Held before > after | Broke before > after |",
             "|---|---|---|---|"]
    cb, ca = counts(ba), counts(aa)
    for fam in cb:
        n = sum(cb[fam].values())
        lines.append(f"| {fam} | {n} | {cb[fam]['HELD']} > {ca[fam]['HELD']} | {cb[fam]['BROKE']} > {ca[fam]['BROKE']} |")
    tb = sum(r["verdict"] == "BROKE" for r in ba.values()); ta = sum(r["verdict"] == "BROKE" for r in aa.values())
    lines.append(f"| **all** | {len(ba)} | {len(ba) - tb} > {len(aa) - ta} | {tb} > {ta} |")

    changed = [i for i in ba if (ba[i]["guess"], ba[i]["verdict"], ba[i]["combined"]) !=
               (aa[i]["guess"], aa[i]["verdict"], aa[i]["combined"])]
    lines += ["", "## Attacks that moved", "",
              "| ID | Family | Guess before > after | Combined before > after | Verdict before > after |",
              "|---|---|---|---|---|"]
    for i in changed:
        lines.append(f"| {i} | {ba[i]['family']} | {ba[i]['guess']} > {aa[i]['guess']} | "
                     f"{ba[i]['combined']} > {aa[i]['combined']} | {ba[i]['verdict']} > {aa[i]['verdict']} |")
    lines.append(f"\n{len(ba) - len(changed)} of {len(ba)} attacks are unchanged in guess, combined score and verdict.")

    lines += ["", "## The five criteria", "", "| Criterion | Before (runs 1, 2, 3) | After (runs 1, 2, 3) | Verdict before > after |",
              "|---|---|---|---|"]
    for n in sorted(bc):
        lines.append(f"| {n}. {bc[n]['name']} | {' / '.join(bc[n]['runs'])} | {' / '.join(ac[n]['runs'])} | "
                     f"{bc[n]['verdict']} > {ac[n]['verdict']} |")

    lines += ["", "## What it cost: the ten own-writing pieces (trial 1)", "",
              "| Piece | Combined before > after | Label before > after | Below the AI label by (after) |",
              "|---|---|---|---|"]
    for n, (b, a) in enumerate(zip(bo, ao), 1):
        kind = " (plain)" if n >= 8 else ""
        lines.append(f"| own_{n:02d}{kind} | {b['combined']:.3f} > {a['combined']:.3f} | {b['guess']} > {a['guess']} | "
                     f"{config.AI_THRESHOLD - a['combined']:.3f} |")

    test = success_test(ba, aa, bo, ao, bc, ac)
    lines += ["", "## The success test written before the change", ""]
    lines += [f"- {label}: **{'PASS' if ok else 'FAIL'}** ({detail})" for label, ok, detail in test]
    return "\n".join(lines) + "\n", test


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--before", default="before")
    parser.add_argument("--after", default="after")
    args = parser.parse_args()
    text, _ = build(args.before, args.after)
    path = config.RESULTS_DIR / "before_after.md"
    path.write_text(text, encoding="utf-8")
    print(text)
    print(f"wrote {path.relative_to(config.ROOT)}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
