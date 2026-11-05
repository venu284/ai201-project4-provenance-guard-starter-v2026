"""The combining rule and the label mapping (scoring.py)."""

import pytest

import config
import scoring


# ── combine_signals ──────────────────────────────────────────────────────────

@pytest.mark.parametrize("v", [0.0, 0.3, 0.5, 0.87, 1.0])
def test_when_the_signals_agree_the_result_is_that_value(v):
    assert scoring.combine_signals(v, v) == pytest.approx(v, abs=1e-4)


@pytest.mark.parametrize("a, b", [(0.1, 0.9), (0.2, 0.7), (0.0, 1.0), (0.55, 0.56)])
def test_order_of_the_two_signals_does_not_matter(a, b):
    assert scoring.combine_signals(a, b) == scoring.combine_signals(b, a)


def test_the_rule_leans_human():
    w = config.LOWER_SIGNAL_WEIGHT
    assert scoring.combine_signals(0.1, 0.9) == pytest.approx(w * 0.1 + (1 - w) * 0.9, abs=1e-4)
    assert scoring.combine_signals(0.1, 0.9) < 0.5, "a split must land below a plain average"


def test_the_readme_split_case_rare_word_ai():
    """README: signal one 0.143, signal two 0.750 -> 0.295."""
    assert scoring.combine_signals(0.143, 0.750) == pytest.approx(0.295, abs=1e-3)


@pytest.mark.parametrize("a, b", [(0.0, 0.0), (1.0, 1.0), (0.0, 1.0), (0.3, 0.6)])
def test_result_stays_between_zero_and_one(a, b):
    assert 0.0 <= scoring.combine_signals(a, b) <= 1.0


def test_result_is_between_its_two_inputs():
    for a, b in [(0.1, 0.9), (0.4, 0.5), (0.8, 0.2)]:
        assert min(a, b) <= scoring.combine_signals(a, b) <= max(a, b)


def test_a_higher_lower_weight_means_a_more_human_result(monkeypatch):
    monkeypatch.setattr(config, "LOWER_SIGNAL_WEIGHT", 0.5)
    plain_average = scoring.combine_signals(0.2, 0.8)
    monkeypatch.setattr(config, "LOWER_SIGNAL_WEIGHT", 0.9)
    assert scoring.combine_signals(0.2, 0.8) < plain_average
    assert plain_average == pytest.approx(0.5)


# ── score_to_label ───────────────────────────────────────────────────────────

H, A = config.HUMAN_THRESHOLD, config.AI_THRESHOLD


@pytest.mark.parametrize("score, guess", [
    (0.0, "human"),
    (H - 0.0001, "human"),
    (H, "unsure"),          # exactly at the human threshold is unsure
    ((H + A) / 2, "unsure"),
    (A - 0.0001, "unsure"),
    (A, "ai"),              # exactly at the AI threshold is ai
    (1.0, "ai"),
])
def test_label_boundaries(score, guess):
    assert scoring.score_to_label(score)[0] == guess


def test_every_label_is_reachable_and_has_text():
    seen = {}
    for score in (0.0, (H + A) / 2, 1.0):
        guess, text = scoring.score_to_label(score)
        seen[guess] = text
    assert set(seen) == {"human", "unsure", "ai"}
    assert all(t.strip() for t in seen.values())
    assert len(set(seen.values())) == 3


def test_there_is_no_gap_in_the_scale():
    """Every score on a fine grid gets a label: no hole between two thresholds."""
    for i in range(0, 1001):
        assert scoring.score_to_label(i / 1000)[0] in {"human", "unsure", "ai"}


def test_unsure_label_does_not_accuse():
    text = scoring.LABEL_TEXT["unsure"].lower()
    assert "not a finding against you" in text
    for banned in ("cheat", "fake", "plagiar", "copied"):
        assert banned not in text


def test_ai_label_is_hedged():
    text = scoring.LABEL_TEXT["ai"].lower()
    assert "may have been" in text and "not a final decision" in text and "review" in text


# ── confidence ───────────────────────────────────────────────────────────────

def test_confidence_for_each_guess():
    assert scoring.confidence_for("ai", 0.9) == 0.9
    assert scoring.confidence_for("human", 0.2) == 0.8
    assert scoring.confidence_for("unsure", 0.6) == 0.6
    assert scoring.confidence_for("unsure", 0.4) == 0.6


@pytest.mark.parametrize("score", [0.0, 0.1, 0.3, 0.5, 0.85, 0.99, 1.0])
def test_confidence_is_never_below_a_half(score):
    guess, _ = scoring.score_to_label(score)
    assert 0.5 <= scoring.confidence_for(guess, score) <= 1.0


# ── label_ranges ─────────────────────────────────────────────────────────────

def test_label_ranges_follow_config():
    ranges = dict(scoring.label_ranges())
    assert ranges["high-confidence human"] == f"0.00 – {H:.2f}"
    assert ranges["unsure"] == f"{H:.2f} – {A:.2f}"
    assert ranges["high-confidence AI"] == f"{A:.2f} – 1.00"


def test_thresholds_are_ordered():
    assert 0.0 < config.HUMAN_THRESHOLD < config.AI_THRESHOLD <= 1.0
