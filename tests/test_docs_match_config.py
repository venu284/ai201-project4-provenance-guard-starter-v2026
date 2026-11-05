"""
Prose must not lie about the code.

A number that is both configured and quoted in a document will eventually
drift. This caught one in unit 8: criteria.md justified a target with an unsure
band of "0.35 to 0.65" while config.py shipped 0.30 and 0.85. These tests read
the documents and compare every quoted constant against its source.

When one fails, fix the document (or cite the config name instead of the
number). Do not edit the test to match a stale document.
"""

import re

import app
import config
import scoring
import stylometry

from conftest import ROOT

README = (ROOT / "README.md").read_text(encoding="utf-8")
CRITERIA = (ROOT / "criteria.md").read_text(encoding="utf-8")


def _num(value: float) -> str:
    return f"{value:.2f}"


def test_readme_label_step_quotes_the_thresholds():
    assert f"Below {_num(config.HUMAN_THRESHOLD)}" in README
    assert f"{_num(config.AI_THRESHOLD)} and above" in README


def test_readme_label_table_matches_label_ranges():
    for name, span in scoring.label_ranges():
        row = next((l for l in README.splitlines() if l.startswith(f"| {name} |")), None)
        assert row is not None, f"README has no label table row for {name!r}"
        assert span in row, f"README row for {name!r} does not contain {span!r}: {row}"


def test_readme_lower_signal_weight_matches():
    w = config.LOWER_SIGNAL_WEIGHT
    assert f"config.LOWER_SIGNAL_WEIGHT = {w}" in README
    assert f"combined = {w} * lower + {round(1 - w, 2)} * higher" in README


def test_readme_style_weights_and_anchors_match():
    ws = stylometry
    assert (
        f"sentence-length spread {ws.WEIGHT_SPREAD:.2f}, type-token ratio "
        f"{ws.WEIGHT_TTR:.2f}"
    ) in README
    assert f"punctuation density {ws.WEIGHT_PUNCT:.2f}" in README
    assert f"human end {ws.SPREAD_HUMAN:.2f}, AI end {ws.SPREAD_AI:.2f}" in README
    assert f"({ws.TTR_HUMAN:.2f} human, {ws.TTR_AI:.2f} AI)" in README
    assert f"({ws.PUNCT_HUMAN:.2f} human, {ws.PUNCT_AI:.2f} AI" in README


def test_criteria_never_quote_a_band_that_differs_from_config():
    """
    Any 'unsure band (a to b)' in criteria.md must be the shipped one.

    Blockquote lines are skipped: a "Correction" or "Revised" note has to be
    able to quote the old, wrong number in order to say it was wrong.
    """
    shipped = (_num(config.HUMAN_THRESHOLD), _num(config.AI_THRESHOLD))
    prose = "\n".join(l for l in CRITERIA.splitlines() if not l.startswith(">"))
    for match in re.finditer(r"unsure band[^.\n]*?\((\d\.\d+) to (\d\.\d+)\)", prose):
        assert match.groups() == shipped, (
            f"criteria.md quotes an unsure band of {match.groups()}, "
            f"config.py ships {shipped}"
        )


def test_criteria_input_limits_match_the_route():
    assert f"at least {app.MIN_WORDS} words" in CRITERIA
    assert f"at most {app.MAX_CHARS:,} characters" in CRITERIA


def test_readme_rate_limit_numbers_match_config():
    assert (
        f"**My limits:** {config.RATE_LIMIT_PER_MINUTE} per minute, "
        f"{config.RATE_LIMIT_PER_DAY} per day"
    ) in README
    assert f"**{config.RATE_LIMIT_PER_MINUTE} a minute**" in README
    assert f"**{config.RATE_LIMIT_PER_DAY} a day**" in README
    assert f"`{config.RATE_LIMIT_PER_DAY} per 1 day`" in README
