"""
diagnose.py: the numbers behind the diagnoses, pinned, with no model needed.

The signal-one scores of the counterfactual texts are cached in
results/diagnosis_model_cache.json, so the whole report regenerates offline and
must equal the committed results/diagnosis_before.md.
"""

import csv
import re

import pytest

import diagnose as d
import stylometry as S
from conftest import ROOT

TEXTS = {r["id"]: r["text"] for r in csv.DictReader((ROOT / "attack_set/attacks.csv").open(encoding="utf-8"))}


def test_measures_report_lengths_scaled_parts_and_the_weighted_style():
    m = d.measures("One two three. Four five six. Seven eight nine.")
    assert m["lengths"] == [3, 3, 3] and m["sentences"] == 3
    assert m["raw"]["spread"] == pytest.approx(0.0)
    assert m["scaled"]["spread"] == 1.0
    total = sum(m["contribution"].values())
    assert total == pytest.approx(m["style"], abs=1e-3)


@pytest.mark.parametrize("attack_id", ["EV02", "EV05", "EV06", "PI01", "PI02"])
def test_the_spread_part_is_zero_in_every_broken_attack(attack_id):
    """The pattern the README diagnoses: sentence-length spread saturates."""
    m = d.measures(TEXTS[attack_id])
    assert m["raw"]["spread"] >= S.SPREAD_HUMAN
    assert m["scaled"]["spread"] == 0.0
    assert m["contribution"]["spread"] == 0.0


@pytest.mark.parametrize("attack_id, expected_style", [
    ("EV02", 0.146), ("EV05", 0.178), ("EV06", 0.147), ("PI01", 0.150), ("PI02", 0.132),
])
def test_style_scores_match_what_the_service_returned(attack_id, expected_style):
    assert d.measures(TEXTS[attack_id])["style"] == pytest.approx(expected_style, abs=1e-3)


def test_removing_the_one_word_sentences_flips_ev02s_style_from_human_to_ai_side():
    cf = d.strip_lever("EV02", TEXTS["EV02"])
    assert "Really" not in cf
    assert d.measures(TEXTS["EV02"])["style"] < 0.2
    assert d.measures(cf)["style"] == pytest.approx(0.743, abs=5e-4)


def test_removing_the_long_sentence_brings_ev06_spread_inside_the_anchors():
    cf = d.strip_lever("EV06", TEXTS["EV06"])
    assert cf.startswith(d.STOCK_START)
    assert S.SPREAD_AI < d.measures(cf)["raw"]["spread"] < S.SPREAD_HUMAN


def test_removing_the_injected_prefix_leaves_the_stock_text():
    for attack_id in ("PI01", "PI02"):
        cf = d.strip_lever(attack_id, TEXTS[attack_id])
        assert cf.startswith(d.STOCK_START)
        assert "instruction" not in cf.lower() and "SYSTEM" not in cf


def test_ev05_has_no_counterfactual_because_it_is_a_genuine_rewrite():
    assert d.strip_lever("EV05", TEXTS["EV05"]) is None


def test_every_counterfactual_text_has_a_cached_model_score():
    cache = d._load_cache()
    import hashlib
    for attack_id in ("EV02", "EV06", "PI01", "PI02"):
        cf = d.strip_lever(attack_id, TEXTS[attack_id])
        assert hashlib.sha256(cf.encode()).hexdigest() in cache


def test_the_committed_report_regenerates_offline_exactly():
    text, detail = d.build(live=False)
    assert text == d.OUT.read_text(encoding="utf-8")
    assert "n/a" not in re.sub(r"no counterfactual[^|]*", "", text).split("## 3.")[0].split("## 2.")[1]


def test_the_report_numbers_that_the_readme_quotes():
    _, detail = d.build(live=False)
    assert detail["EV02"]["counterfactual"]["label"] == "unsure"
    assert detail["EV02"]["combined"] < 0.30 < detail["EV02"]["counterfactual"]["combined"]
    assert detail["criterion3_best_ai"] == pytest.approx(0.706, abs=5e-4)
    assert detail["plain_margins"]["own_08"] == pytest.approx(0.041, abs=1e-3)
