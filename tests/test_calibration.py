"""
The calibration set as a regression alarm.

These read the committed texts in samples/calibration/ and the cached signal-one
scores, so they need no model and run in a fraction of a second. They fail the
moment a change to stylometry.py, scoring.py or the thresholds in config.py
moves a score or a label. If the move is intended, accept it with

    python calibrate.py --update-baseline

and say what moved and why in the commit message.
"""

import hashlib

import calibrate
import config
import scoring
from conftest import ROOT


def test_scores_match_the_committed_baseline():
    problems = calibrate.check_against_baseline(calibrate.score_all())
    assert not problems, "scores moved:\n  " + "\n  ".join(problems)


def test_cached_model_scores_belong_to_the_current_texts():
    """A changed text with a stale cached model score would hide a real change."""
    for entry in calibrate.load_manifest()["texts"]:
        text = (calibrate.CAL_DIR / entry["file"]).read_text(encoding="utf-8")
        assert hashlib.sha256(text.encode()).hexdigest() == entry["sha256"], (
            f"{entry['file']} changed since its model_score was cached; "
            f"run python calibrate.py --live and refresh the manifest"
        )


def test_no_human_kind_text_is_labelled_ai():
    """
    What the 0.85 in config.py is for: the plain-writing texts must stay out of
    the "ai" label. If this fails after a tuning change, the change made a
    false accusation more likely on the calibration set.
    """
    accused = [r["name"] for r in calibrate.score_all()
               if r["kind"] == "human" and r["guess"] == "ai"]
    assert accused == []


def test_the_three_labels_are_all_reached_by_the_set():
    guesses = {r["guess"] for r in calibrate.score_all()}
    assert guesses == {"human", "unsure", "ai"}


def test_every_text_in_the_folder_is_in_the_manifest():
    listed = {e["file"] for e in calibrate.load_manifest()["texts"]}
    on_disk = {f"texts/{p.name}" for p in (calibrate.CAL_DIR / "texts").glob("*.txt")}
    assert listed == on_disk
