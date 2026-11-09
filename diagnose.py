#!/usr/bin/env python3
"""
Show WHY each broken attack and the missed criterion came out as they did.

    python diagnose.py            # offline: uses committed run reports + a cache
    python diagnose.py --live     # also re-score the counterfactual texts with gpt2

A diagnosis names a stage and a mechanism. This prints the numbers behind them,
so the README's claims can be re-derived in one command instead of taken on
trust (the unit 7 review asked for exactly that).

What it prints (and writes to results/diagnosis_before.md):

  1. For every broken attack: the sentence lengths, the three raw style
     measures, each measure scaled to 0..1 by its anchor, the weighted style
     score, signal one, and the combined score. These are the numbers the
     service computed (signal scores from the attack run report, the rest
     recomputed here with stylometry.py).
  2. A counterfactual for each: the same text with the one edit that makes it
     an attack taken out (the one-word "Really." sentences, the 51-word
     sentence, the injected prefix). If taking the edit out flips the result,
     that edit is the mechanism. EV05 has no counterfactual: it is a genuine
     rewrite, not an edit on top of a stock text.
  3. For criterion 3: the combined score of the nine inputs against the two
     thresholds, and how far the best ordinary-AI score is from the AI label.
  4. The plain pieces' distance below the AI label (criterion 1's margin).
  5. After the Milestone 5 change (sentences under SPREAD_MIN_SENTENCE_WORDS
     words no longer count in the spread): the same five attacks and the plain
     pieces, with the same signal-one scores, so only signal two moves.

Sections 1 to 4 describe the service as it was before that change, so they are
computed with min_words=1 (every sentence counts), whatever stylometry.py does
now.

Signal-one scores of the counterfactual texts need the model, so they are cached
in results/diagnosis_model_cache.json (keyed by a hash of the text); --live
recomputes them.
"""

import argparse
import csv
import hashlib
import json
import re
import statistics
import sys
from pathlib import Path

import attack_verdicts
import calibrate
import config
import eval_verdicts
import scoring
import stylometry as S

CACHE = config.RESULTS_DIR / "diagnosis_model_cache.json"
OUT = config.RESULTS_DIR / "diagnosis.md"
BROKEN = ["EV02", "EV05", "EV06", "PI01", "PI02"]

STOCK_START = "The importance of effective communication in the workplace cannot be overstated."


# ── the measures ─────────────────────────────────────────────────────────────

def measures(text: str, min_words: int = 1) -> dict:
    """
    Raw measures, their scaled parts and the weighted style score for one text.

    `min_words` is the shortest sentence counted in the spread: 1 is the service
    before Milestone 5, S.SPREAD_MIN_SENTENCE_WORDS is the service now. The style
    score is rebuilt here the way stylometry.style_signal builds it, so either
    view can be reproduced whatever the module's default is.
    """
    sents = S.sentences(text)
    lengths = [len(S.words(s)) for s in sents]
    kept = S.spread_lengths(text, min_words)
    raw = {
        "spread": S.sentence_length_spread(text, min_words),
        "ttr": S.type_token_ratio(text),
        "punct": S.punctuation_density(text),
    }
    scaled = {
        "spread": (S.NEUTRAL if len(kept) < 2
                   else S._flip_and_scale(raw["spread"], S.SPREAD_HUMAN, S.SPREAD_AI)),
        "ttr": S._flip_and_scale(raw["ttr"], S.TTR_HUMAN, S.TTR_AI),
        "punct": S._flip_and_scale(raw["punct"], S.PUNCT_HUMAN, S.PUNCT_AI),
    }
    contribution = {
        "spread": S.WEIGHT_SPREAD * scaled["spread"],
        "ttr": S.WEIGHT_TTR * scaled["ttr"],
        "punct": S.WEIGHT_PUNCT * scaled["punct"],
    }
    style = S.NEUTRAL if not S.words(text) else round(min(1.0, max(0.0, sum(contribution.values()))), 4)
    return {
        "words": len(S.words(text)),
        "sentences": len(sents),
        "lengths": lengths,
        "kept": kept,
        "raw": raw,
        "scaled": scaled,
        "contribution": contribution,
        "style": style,
    }


def strip_lever(attack_id: str, text: str) -> str | None:
    """
    The same text with the edit that makes it an attack taken out, or None when
    there is no such edit (EV05 is a genuine rewrite).
    """
    if attack_id == "EV02":
        return re.sub(r" Really\.", "", text)
    if attack_id in ("EV06", "PI01", "PI02"):
        i = text.find(STOCK_START)
        return text[i:] if i != -1 else None
    return None


def lever_description(attack_id: str) -> str:
    return {
        "EV02": 'without the one-word "Really." sentences',
        "EV06": "without the 51-word sentence and the one-word sentence",
        "PI01": "without the injected prefix",
        "PI02": "without the injected prefix",
    }.get(attack_id, "no counterfactual (a genuine rewrite)")


# ── signal one, cached ───────────────────────────────────────────────────────

def _load_cache() -> dict:
    return json.loads(CACHE.read_text(encoding="utf-8")) if CACHE.exists() else {}


def model_score(text: str, cache: dict, live: bool) -> float | None:
    key = hashlib.sha256(text.encode()).hexdigest()
    if live or key not in cache:
        if not live:
            return None
        import detector
        cache[key] = detector.model_signal(text)
    return cache[key]


# ── building the report ──────────────────────────────────────────────────────

def fmt(v, digits=3) -> str:
    return "n/a" if v is None else f"{v:.{digits}f}"


def attack_rows() -> dict[str, dict]:
    texts = {r["id"]: r["text"] for r in csv.DictReader(
        (config.ROOT / "attack_set" / "attacks.csv").open(encoding="utf-8"))}
    report = attack_verdicts.parse_report(attack_verdicts.latest_report("before").read_text(encoding="utf-8"))
    by_id = {r["id"]: r for r in report}
    return {i: {"text": texts[i], "run": by_id[i]} for i in BROKEN}


def build(live: bool) -> tuple[str, dict]:
    cache = _load_cache()
    rows = attack_rows()
    lines = ["# Diagnosis evidence — before", "",
             "Produced by `diagnose.py`. Signal scores for the actual attacks are from the attack run report; "
             "everything else is recomputed from `stylometry.py` and `scoring.py`.", "",
             "## 1. The broken attacks as the service scored them", "",
             "| Attack | Words | Sentence lengths | Spread raw | Spread scaled | Style | Model | Combined |",
             "|---|---|---|---|---|---|---|---|"]
    detail = {}
    for i in BROKEN:
        t, run = rows[i]["text"], rows[i]["run"]
        m = measures(t)
        combined = scoring.combine_signals(run["model_score"], run["style_score"])
        detail[i] = {"measures": m, "model": run["model_score"], "combined": combined}
        lens = ", ".join(map(str, m["lengths"]))
        lines.append(f"| {i} | {m['words']} | {lens} | {m['raw']['spread']:.2f} | {m['scaled']['spread']:.2f} | "
                     f"{run['style_score']:.3f} | {run['model_score']:.3f} | {combined:.3f} |")
    lines += ["", f"Spread anchors: human end {S.SPREAD_HUMAN}, AI end {S.SPREAD_AI}; the spread part carries "
              f"{S.WEIGHT_SPREAD:.2f} of the style score. A raw spread at or above {S.SPREAD_HUMAN} scales to 0.00.", "",
              "### What each part of the style score contributed", "",
              "| Attack | Spread part (x0.60) | Type-token part (x0.25) | Punctuation part (x0.15) | Style |",
              "|---|---|---|---|---|"]
    for i in BROKEN:
        c = detail[i]["measures"]["contribution"]
        lines.append(f"| {i} | {c['spread']:.3f} | {c['ttr']:.3f} | {c['punct']:.3f} | "
                     f"{detail[i]['measures']['style']:.3f} |")

    lines += ["", "## 2. The same text with the attacking edit taken out", "",
              "| Attack | Counterfactual | Sentence lengths | Spread raw | Spread scaled | Style | Model | Combined | Label |",
              "|---|---|---|---|---|---|---|---|---|"]
    for i in BROKEN:
        cf = strip_lever(i, rows[i]["text"])
        if cf is None:
            lines.append(f"| {i} | {lever_description(i)} | | | | | | | |")
            continue
        m = measures(cf)
        model = model_score(cf, cache, live)
        combined = scoring.combine_signals(model, m["style"]) if model is not None else None
        label = scoring.score_to_label(combined)[0] if combined is not None else "n/a"
        detail[i]["counterfactual"] = {"measures": m, "model": model, "combined": combined, "label": label}
        lines.append(f"| {i} | {lever_description(i)} | {', '.join(map(str, m['lengths']))} | "
                     f"{m['raw']['spread']:.2f} | {m['scaled']['spread']:.2f} | {m['style']:.3f} | "
                     f"{fmt(model)} | {fmt(combined)} | {label} |")
    lines += ["", f"Thresholds from `config.py`: human below {config.HUMAN_THRESHOLD}, ai at or above "
              f"{config.AI_THRESHOLD}, lower-signal weight {config.LOWER_SIGNAL_WEIGHT}."]

    # criterion 3 and the plain pieces, from the criteria run
    report = eval_verdicts.parse_report(eval_verdicts.latest_report("before").read_text(encoding="utf-8"))
    lines += ["", "## 3. Criterion 3: why the \"ai\" label never appeared", "",
              "Trial 1 of the criteria run, combined score recomputed with `scoring.combine_signals`.", "",
              "| Group | Combined scores | Highest | Below the AI label by |", "|---|---|---|---|"]
    best_ai = None
    for name in ("labels: AI", "labels: human", "labels: borderline"):
        scores = [eval_verdicts.combined(r) for r in report[name][1]]
        top = max(scores)
        if name == "labels: AI":
            best_ai = top
        lines.append(f"| {name} | {', '.join(f'{s:.3f}' for s in scores)} | {top:.3f} | "
                     f"{config.AI_THRESHOLD - top:.3f} |")
    cal = calibrate.score_all()
    ordinary = [r["combined"] for r in cal if r["group"] == "AI"]
    plain_ai = [r["combined"] for r in cal if r["group"] == "AI-plain"]
    plain_human = [r["combined"] for r in cal if r["group"] == "human-plain"]
    lines += ["", f"Calibration set (30 texts): ordinary AI combined {min(ordinary):.3f} to {max(ordinary):.3f}; "
              f"plain AI {min(plain_ai):.3f} to {max(plain_ai):.3f}; plain human {min(plain_human):.3f} to "
              f"{max(plain_human):.3f}. The \"ai\" label starts at {config.AI_THRESHOLD}: only the plain texts "
              f"get near it, and plain human and plain AI overlap."]
    mean_style = statistics.mean(r["style"] for r in cal if r["group"] == "AI")
    mean_model = statistics.mean(r["model"] for r in cal if r["group"] == "AI")
    lines += [f"Ordinary AI texts average model {mean_model:.3f} and style {mean_style:.3f}. With the weight of "
              f"{config.LOWER_SIGNAL_WEIGHT} on the lower signal, that averages to about "
              f"{scoring.combine_signals(mean_model, mean_style):.3f}, below {config.AI_THRESHOLD}."]

    lines += ["", "## 4. Criterion 1's margin: the plain pieces", "",
              "| Piece | Combined | Below the AI label by |", "|---|---|---|"]
    own = report["my own writing"][1]
    margins = {}
    for n, r in enumerate(own, 1):
        if n >= 8:
            c = eval_verdicts.combined(r)
            margins[f"own_{n:02d}"] = config.AI_THRESHOLD - c
            lines.append(f"| own_{n:02d} (plain) | {c:.3f} | {config.AI_THRESHOLD - c:.3f} |")
    detail["criterion3_best_ai"] = best_ai
    detail["plain_margins"] = margins

    # Section 5: the same texts and the same signal-one scores, after the change
    n = S.SPREAD_MIN_SENTENCE_WORDS
    lines += ["", f"## 5. After the Milestone 5 change (sentences under {n} words no longer count in the spread)", "",
              "Signal-one scores are the ones the service returned before; only signal two changes. "
              "Sentence lengths are the ones that still count.", "",
              "| Text | Counted sentence lengths | Spread raw | Spread scaled | Style (before > after) | Model | "
              "Combined (before > after) | Label (before > after) |",
              "|---|---|---|---|---|---|---|---|"]
    detail["after"] = {}

    def after_row(name, text, model, before_style):
        m = measures(text, n)
        c_before = scoring.combine_signals(model, before_style)
        c_after = scoring.combine_signals(model, m["style"])
        lab_before, lab_after = scoring.score_to_label(c_before)[0], scoring.score_to_label(c_after)[0]
        detail["after"][name] = {"style": m["style"], "combined": c_after, "label": lab_after,
                                 "combined_before": c_before}
        lines.append(f"| {name} | {', '.join(map(str, m['kept']))} | {m['raw']['spread']:.2f} | "
                     f"{m['scaled']['spread']:.2f} | {before_style:.3f} > {m['style']:.3f} | {model:.3f} | "
                     f"{c_before:.3f} > {c_after:.3f} | {lab_before} > {lab_after} |")

    for i in BROKEN:
        run = rows[i]["run"]
        after_row(i, rows[i]["text"], run["model_score"], run["style_score"])
    scen = {s_["name"]: s_ for s_ in eval_verdicts.scenarios.SCENARIOS}
    for k, (text, result) in enumerate(zip(scen["my own writing"]["texts"], report["my own writing"][1]), 1):
        if k >= 8:
            after_row(f"own_{k:02d} (plain)", text, result["model_score"], result["style_score"])

    if live:
        CACHE.write_text(json.dumps(cache, indent=1) + "\n", encoding="utf-8")
    return "\n".join(lines) + "\n", detail


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--live", action="store_true", help="re-score the counterfactual texts with gpt2")
    args = parser.parse_args()
    text, _ = build(args.live)
    config.RESULTS_DIR.mkdir(exist_ok=True)
    OUT.write_text(text, encoding="utf-8")
    print(text)
    print(f"wrote {OUT.relative_to(config.ROOT)}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
