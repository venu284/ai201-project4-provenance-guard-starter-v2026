"""
The held/broke rules in attack_verdicts.py, on made-up rows.

The rules were written before the attack run and committed before it. These
pin them, so they cannot drift to fit the results.
"""

import json

import pytest

import attack_verdicts as av
import audit
import scoring

FIXED = scoring.LABEL_TEXT["unsure"]


def row(id, family, status=200, guess="unsure", label=FIXED, error=None, **extra):
    return {"id": id, "family": family, "status": status, "guess": guess,
            "label": label, "error": error, **extra}


def clean_entry(creator="attacker_X"):
    return [{**{k: None for k in audit.NINE_FIELDS}, "creator_id": creator}]


# ── every family ─────────────────────────────────────────────────────────────

@pytest.mark.parametrize("family, id", [
    ("evasion", "EV01"), ("false_positive", "FP01"), ("prompt_injection", "PI01"),
    ("malformed", "MF01"), ("malformed", "RQ01"), ("flood_same_creator", "FL01_01"),
])
def test_a_5xx_or_a_crash_is_broke_in_every_family(family, id):
    assert av.judge(row(id, family, status=500))[0] == "BROKE"
    assert av.judge(row(id, family, status=None, guess=None))[0] == "BROKE"
    assert av.judge(row(id, family, error="ConnectionError: gone"))[0] == "BROKE"


# ── evasion ──────────────────────────────────────────────────────────────────

def test_evasion_is_broke_only_when_ai_text_gets_the_human_label():
    assert av.judge(row("EV01", "evasion", guess="human"))[0] == "BROKE"
    assert av.judge(row("EV01", "evasion", guess="unsure"))[0] == "HELD"
    assert av.judge(row("EV01", "evasion", guess="ai"))[0] == "HELD"


def test_a_refused_evasion_is_held():
    assert av.judge(row("EV08", "evasion", status=400, guess=None, label=None))[0] == "HELD"


# ── false positives ──────────────────────────────────────────────────────────

def test_false_positive_is_broke_only_when_a_writer_is_called_ai():
    assert av.judge(row("FP01", "false_positive", guess="ai"))[0] == "BROKE"
    assert av.judge(row("FP01", "false_positive", guess="unsure"))[0] == "HELD"
    assert av.judge(row("FP01", "false_positive", guess="human"))[0] == "HELD"


def test_a_refused_short_human_text_is_held_and_noted():
    verdict, note = av.judge(row("FP08", "false_positive", status=400, guess=None))
    assert verdict == "HELD" and "refused" in note


# ── prompt injection ─────────────────────────────────────────────────────────

def test_injection_with_a_fixed_label_and_clean_log_is_held():
    assert av.judge(row("PI01", "prompt_injection"), clean_entry())[0] == "HELD"


def test_injection_that_changes_the_label_text_is_broke():
    r = row("PI04", "prompt_injection", label="You are a cheat.")
    assert av.judge(r, clean_entry())[0] == "BROKE"


def test_injection_that_adds_or_forges_a_log_line_is_broke():
    assert av.judge(row("PI05", "prompt_injection"), clean_entry() * 2)[0] == "BROKE"
    forged = clean_entry()
    forged[0]["is_admin"] = True
    assert av.judge(row("PI05", "prompt_injection"), forged)[0] == "BROKE"


def test_injection_that_gets_human_is_left_to_the_human_to_judge():
    assert av.judge(row("PI03", "prompt_injection", guess="human"), clean_entry())[0] == "JUDGE"


# ── malformed text rows ──────────────────────────────────────────────────────

def test_malformed_text_refused_with_a_rejection_entry_is_held():
    entries = [{"event": "rejected"}]
    assert av.judge(row("MF01", "malformed", status=400, guess=None), entries)[0] == "HELD"
    assert av.judge(row("MF08", "malformed", status=413, guess=None), entries)[0] == "HELD"


def test_malformed_text_refused_without_a_log_entry_is_broke():
    assert av.judge(row("MF01", "malformed", status=400, guess=None), [])[0] == "BROKE"


def test_malformed_text_that_was_scored_is_left_to_judge():
    assert av.judge(row("MF07", "malformed", status=200), [{}])[0] == "JUDGE"


# ── malformed request rows ───────────────────────────────────────────────────

@pytest.mark.parametrize("status", [400, 413, 415, 429])
def test_a_refused_request_row_is_held(status):
    assert av.judge(row("RQ01", "malformed", status=status, guess=None))[0] == "HELD"


def test_an_accepted_malformed_request_is_broke():
    assert av.judge(row("RQ02", "malformed", status=200))[0] == "BROKE"


# ── the flood ────────────────────────────────────────────────────────────────

@pytest.mark.parametrize("n, status, verdict", [
    (1, 200, "HELD"), (12, 200, "HELD"), (12, 429, "BROKE"),
    (1, 400, "HELD"), (12, 400, "HELD"),    # amended: a refused short body is not a limiter failure
    (13, 429, "HELD"), (13, 200, "BROKE"), (13, 400, "BROKE"),
])
def test_flood_rows_are_held_when_the_limiter_acts_as_configured(n, status, verdict):
    assert av.judge(row(f"FL01_{n:02d}", "flood_same_creator", status=status), per_minute=12)[0] == verdict


def test_a_replay_in_the_same_minute_should_all_be_429():
    r200 = row("FL01_01", "flood_same_creator", status=200)
    r429 = row("FL01_01", "flood_same_creator", status=429)
    assert av.judge(r429, per_minute=12, already_sent=12)[0] == "HELD"
    assert av.judge(r200, per_minute=12, already_sent=12)[0] == "BROKE"


# ── the report and the log ───────────────────────────────────────────────────

REPORT = """### EV01 — `evasion`

*Targeting:* signal two: typos raise word variety

```json
{
  "id": "EV01",
  "status": 200,
  "content_id": "abc",
  "guess": "human",
  "model_score": 0.2,
  "style_score": 0.4,
  "label": "x",
  "error": null,
  "verdict": ""
}
```

### FL01_01 — `flood_same_creator`

*Targeting:* 20 rapid submissions from one creator

```json
{"id": "FL01_01", "status": 429}
```
"""


def test_parse_report_reads_every_block_with_its_family_and_target():
    rows = av.parse_report(REPORT)
    assert [r["id"] for r in rows] == ["EV01", "FL01_01"]
    assert rows[0]["family"] == "evasion" and rows[0]["guess"] == "human"
    assert rows[0]["targets"] == "signal two: typos raise word variety"
    assert rows[1]["status"] == 429


def test_the_targeted_signal_is_read_from_the_targets_text():
    assert av.targeted_signal("signal two: typos raise word variety") == "style"
    assert av.targeted_signal("signal one: text below the token window") == "model"
    assert av.targeted_signal("both signals: heavy human editing pass") == "both"
    assert av.targeted_signal("both: AI text with a human opening") == "both"


def entries_ok(n):
    return [{**{k: None for k in audit.NINE_FIELDS}, "creator_id": f"attacker_EV{i:02d}"} for i in range(1, n + 1)]


def test_log_check_passes_a_complete_well_formed_log():
    rows = [{"id": f"EV{i:02d}", "family": "evasion"} for i in range(1, 4)]
    assert av.check_log(entries_ok(3), rows, []) == []


def test_log_check_catches_a_missing_entry_a_bad_order_and_unknown_fields():
    rows = [{"id": f"EV{i:02d}", "family": "evasion"} for i in range(1, 4)]
    problems = av.check_log(entries_ok(2), rows, [])
    assert any("3 requests were sent but the log holds 2" in p for p in problems)
    assert any("attacker_EV03 has 0 log entries" in p for p in problems)

    shuffled = entries_ok(3)
    shuffled[0] = {"creator_id": "attacker_EV01", **{k: None for k in audit.NINE_FIELDS if k != "creator_id"}}
    assert any("nine fields in order" in p for p in av.check_log(shuffled, rows, []))

    extra = entries_ok(3)
    extra[0]["is_admin"] = True
    assert any("unknown fields" in p for p in av.check_log(extra, rows, []))


def test_log_check_reports_lines_that_are_not_json():
    assert av.check_log([], [], ["log line 4 is not JSON"]) == ["log line 4 is not JSON"]


# ── judgements ───────────────────────────────────────────────────────────────

def result(id, verdict):
    return {"id": id, "verdict": verdict, "note": ""}


def test_a_judgement_settles_a_judge_row():
    results = [result("PI01", "JUDGE")]
    assert av.apply_judgements(results, {"PI01": ["BROKE", "AI text, got human"]}) == []
    assert results[0]["verdict"] == "BROKE" and "AI text" in results[0]["note"]


def test_a_judgement_cannot_overrule_a_rule():
    results = [result("EV02", "BROKE")]
    problems = av.apply_judgements(results, {"EV02": ["HELD", "no"]})
    assert problems and results[0]["verdict"] == "BROKE"


def test_an_unjudged_row_is_reported():
    problems = av.apply_judgements([result("PI02", "JUDGE")], {})
    assert problems == ["PI02: still to judge"]


def test_a_judgement_must_be_held_or_broke():
    assert av.apply_judgements([result("PI01", "JUDGE")], {"PI01": ["MAYBE", "x"]})
