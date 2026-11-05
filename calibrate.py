#!/usr/bin/env python3
"""
Re-derive the calibration table from the committed texts, in one command.

    python calibrate.py                 # print the table (no model needed)
    python calibrate.py --live          # re-score signal one with gpt2 too
    python calibrate.py --split holdout # only the held-out half
    python calibrate.py --check         # fail if any style score moved
    python calibrate.py --update-baseline   # accept the current scores

The texts and their groups are in samples/calibration/manifest.json. Signal one
(the language model) is slow and needs a 550 MB download, so each text's
model_score is cached in the manifest next to a hash of the text; the cache is
used unless --live is given or the text has changed. Signal two, the combining
rule and the labels are computed fresh every time from the current code and
config.py.

--check compares those fresh numbers with results/calibration_baseline.json.
That is the alarm for "a tweak to stylometry.py silently moved every score":
it fails, names the texts, and tells you to run --update-baseline if the move
was intended. tests/test_calibration.py runs the same check.

The human-kind texts are AI-written imitations of human writing, not real
writers. Read the table as a stress test, not a measurement.
"""

import argparse
import hashlib
import json
import statistics
import sys
from pathlib import Path

import config
import scoring
import stylometry

CAL_DIR = config.ROOT / "samples" / "calibration"
MANIFEST = CAL_DIR / "manifest.json"
BASELINE = config.RESULTS_DIR / "calibration_baseline.json"
TOLERANCE = 0.0005  # scores are rounded to 4 places; allow float noise only

GROUP_ORDER = ["AI", "AI-plain", "AI-edited", "human-messy", "human-plain",
               "human-formal", "seed"]


def load_manifest() -> dict:
    return json.loads(MANIFEST.read_text(encoding="utf-8"))


def score_all(live: bool = False, split: str | None = None) -> list[dict]:
    """Score every text in the manifest and return one row per text."""
    rows = []
    detector = None
    for entry in load_manifest()["texts"]:
        if split and entry["split"] != split:
            continue
        text = (CAL_DIR / entry["file"]).read_text(encoding="utf-8")
        digest = hashlib.sha256(text.encode()).hexdigest()
        if live or digest != entry["sha256"]:
            if detector is None:
                import detector as detector  # loads gpt2 on first use
            model = detector.model_signal(text)
        else:
            model = entry["model_score"]
        style = stylometry.style_signal(text)
        combined = scoring.combine_signals(model, style)
        rows.append({
            "name": Path(entry["file"]).stem,
            "group": entry["group"],
            "kind": entry["kind"],
            "split": entry["split"],
            "note": entry.get("note", ""),
            "words": len(stylometry.words(text)),
            "spread": stylometry.sentence_length_spread(text),
            "ttr": stylometry.type_token_ratio(text),
            "punct": stylometry.punctuation_density(text),
            "model": model,
            "style": style,
            "combined": combined,
            "guess": scoring.score_to_label(combined)[0],
        })
    return rows


def _counts(rows, key) -> str:
    """human/unsure/ai counts when `key` is read against the shipped thresholds."""
    def label(v):
        if v >= config.AI_THRESHOLD:
            return "ai"
        return "human" if v < config.HUMAN_THRESHOLD else "unsure"
    got = [label(r[key]) for r in rows]
    return "/".join(str(got.count(k)) for k in ("human", "unsure", "ai"))


def print_table(rows: list[dict]) -> None:
    print("| text | group | split | words | spread | ttr | punct | model | style | combined | guess |")
    print("|---|---|---|---|---|---|---|---|---|---|---|")
    for r in rows:
        print(f"| {r['name']} | {r['group']} | {r['split']} | {r['words']} | "
              f"{r['spread']:.2f} | {r['ttr']:.2f} | {r['punct']:.3f} | "
              f"{r['model']:.3f} | {r['style']:.3f} | {r['combined']:.3f} | {r['guess']} |")

    print()
    print(f"Thresholds from config.py: human < {config.HUMAN_THRESHOLD}, "
          f"ai >= {config.AI_THRESHOLD}. Counts are human/unsure/ai.")
    print()
    print("| group | n | model | style | combined | min-max combined | combined h/u/a | model h/u/a | style h/u/a |")
    print("|---|---|---|---|---|---|---|---|---|")
    for g in GROUP_ORDER:
        grp = [r for r in rows if r["group"] == g]
        if not grp:
            continue
        mean = lambda k: statistics.mean(r[k] for r in grp)
        combos = [r["combined"] for r in grp]
        print(f"| {g} | {len(grp)} | {mean('model'):.3f} | {mean('style'):.3f} | "
              f"{mean('combined'):.3f} | {min(combos):.2f}-{max(combos):.2f} | "
              f"{_counts(grp, 'combined')} | {_counts(grp, 'model')} | {_counts(grp, 'style')} |")

    ai = [r["combined"] for r in rows if r["group"] in ("AI", "AI-plain", "AI-edited")]
    human = [r["combined"] for r in rows if r["group"].startswith("human")]
    if ai and human:
        print()
        print(f"Mean combined, AI texts {statistics.mean(ai):.3f} vs human texts "
              f"{statistics.mean(human):.3f}: gap {statistics.mean(ai) - statistics.mean(human):.3f}")


def baseline_snapshot(rows: list[dict]) -> dict:
    return {r["name"]: {"style": r["style"], "model": r["model"], "combined": r["combined"],
                       "guess": r["guess"]} for r in rows}


def check_against_baseline(rows: list[dict]) -> list[str]:
    """Return one complaint per text whose scores or label moved."""
    if not BASELINE.exists():
        return [f"no baseline at {BASELINE}; run python calibrate.py --update-baseline"]
    expected = json.loads(BASELINE.read_text(encoding="utf-8"))
    problems = []
    now = baseline_snapshot(rows)
    for name in sorted(set(expected) | set(now)):
        if name not in now or name not in expected:
            problems.append(f"{name}: in only one of baseline and manifest")
            continue
        for field in ("style", "model", "combined"):
            if abs(now[name][field] - expected[name][field]) > TOLERANCE:
                problems.append(f"{name}: {field} {expected[name][field]} -> {now[name][field]}")
        if now[name]["guess"] != expected[name]["guess"]:
            problems.append(f"{name}: label {expected[name]['guess']} -> {now[name]['guess']}")
    return problems


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--live", action="store_true", help="re-score signal one with the model")
    parser.add_argument("--split", choices=["train", "holdout", "seed"], help="only one split")
    parser.add_argument("--check", action="store_true", help="fail if scores moved from the baseline")
    parser.add_argument("--update-baseline", action="store_true", help="write the current scores as the baseline")
    args = parser.parse_args()

    if args.update_baseline and args.split:
        parser.error("--update-baseline needs the whole set; drop --split")

    rows = score_all(live=args.live, split=args.split if not args.check else None)

    if args.update_baseline:
        config.RESULTS_DIR.mkdir(exist_ok=True)
        BASELINE.write_text(json.dumps(baseline_snapshot(rows), indent=1) + "\n", encoding="utf-8")
        print(f"wrote {BASELINE.relative_to(config.ROOT)} ({len(rows)} texts)")
        return 0

    if args.check:
        problems = check_against_baseline(rows)
        if problems:
            print("Scores moved from the baseline:")
            for p in problems:
                print("  " + p)
            print("If that was intended, run: python calibrate.py --update-baseline")
            return 1
        print(f"ok: {len(rows)} texts match the baseline")
        return 0

    print_table(rows)
    return 0


if __name__ == "__main__":
    sys.exit(main())
