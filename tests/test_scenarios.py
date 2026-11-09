"""The frozen scenarios: right shape, right counts, texts unchanged."""

import hashlib
import json
import statistics

import pytest

import scenarios
import stylometry
from conftest import ROOT

BY_NAME = {s["name"]: s for s in scenarios.SCENARIOS}


def test_scenarios_validate_with_no_placeholders():
    assert scenarios.validate() == []


def test_every_criterion_is_covered():
    assert {s["criterion"] for s in scenarios.SCENARIOS} == {1, 2, 3, 4, 5}


def test_scenario_names_are_distinct_in_their_first_twelve_characters():
    """run_eval builds creator ids from name[:12]; a clash would share a rate-limit bucket."""
    prefixes = [s["name"][:12] for s in scenarios.SCENARIOS]
    assert len(prefixes) == len(set(prefixes))


def test_counts_match_criteria_md():
    assert len(BY_NAME["my own writing"]["texts"]) == 10
    assert len(BY_NAME["clear AI"]["texts"]) == len(BY_NAME["clear human"]["texts"]) == 5
    nine = [len(BY_NAME[n]["texts"]) for n in ("labels: AI", "labels: human", "labels: borderline")]
    assert nine == [3, 3, 3]
    assert len(BY_NAME["appeals"]["texts"]) == 5 and BY_NAME["appeals"]["unknown_ids"]
    assert len(BY_NAME["bad input"]["bodies"]) == len(BY_NAME["bad input"]["expect"]) == 8


def test_no_text_is_reused_inside_criterion_2_or_3():
    c2 = BY_NAME["clear AI"]["texts"] + BY_NAME["clear human"]["texts"]
    c3 = sum((BY_NAME[n]["texts"] for n in ("labels: AI", "labels: human", "labels: borderline")), [])
    assert len(set(c2)) == 10 and len(set(c3)) == 9
    assert not set(c2) & set(c3)


def test_bad_input_bodies_are_the_eight_in_criteria_md():
    bodies = BY_NAME["bad input"]["bodies"]
    assert "text" not in bodies[0]
    assert bodies[1]["text"] == "" and not bodies[2]["text"].strip()
    assert bodies[3]["text"] is None and isinstance(bodies[4]["text"], int)
    assert len(bodies[5]["text"].split()) == 19
    assert len(bodies[6]["text"]) > 20_000 and len(bodies[6]["text"].split()) == 50_000
    assert "creator_id" not in bodies[7]
    assert BY_NAME["bad input"]["expect"] == [400, 400, 400, 400, 400, 400, 413, 400]


def test_own_pieces_are_unchanged_since_the_freeze():
    manifest = json.loads((ROOT / "samples/own_writing/manifest.json").read_text(encoding="utf-8"))
    for piece in manifest["pieces"]:
        text = (ROOT / "samples/own_writing" / piece["file"]).read_text(encoding="utf-8")
        assert hashlib.sha256(text.encode()).hexdigest() == piece["sha256"], piece["file"]


def test_the_three_plain_pieces_have_short_sentences_and_the_rest_are_not_claimed_plain():
    manifest = json.loads((ROOT / "samples/own_writing/manifest.json").read_text(encoding="utf-8"))
    plain = [p for p in manifest["pieces"] if p["kind"] == "plain"]
    assert len(plain) == 3
    for piece in plain:
        text = (ROOT / "samples/own_writing" / piece["file"]).read_text(encoding="utf-8")
        mean = statistics.mean(len(stylometry.words(s)) for s in stylometry.sentences(text))
        assert mean < 12, (piece["file"], mean)


def test_every_own_piece_is_long_enough_to_submit():
    for text in BY_NAME["my own writing"]["texts"]:
        assert len(text.split()) >= 20
