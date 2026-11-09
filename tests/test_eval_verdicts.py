"""The five criteria's rules (eval_verdicts.py), on made-up trial data."""

import json

import pytest

import eval_verdicts as ev


def res(guess="unsure", model=0.5, style=0.5, status=200, **extra):
    return {"status": status, "guess": guess, "model_score": model, "style_score": style, **extra}


def trial(**over):
    base = {
        "my own writing": [res("unsure") for _ in range(10)],
        "clear AI": [res(model=0.9, style=0.9) for _ in range(5)],
        "clear human": [res("human", model=0.1, style=0.1) for _ in range(5)],
        "labels: AI": [res("ai") for _ in range(3)],
        "labels: human": [res("human") for _ in range(3)],
        "labels: borderline": [res("unsure") for _ in range(3)],
        "appeals": [appeal_ok(f"c{i}") for i in range(5)] + [unknown_ok()],
        "bad input": [bad(s) for s in (400, 400, 400, 400, 400, 400, 413, 400)],
    }
    base.update(over)
    return base


def appeal_ok(cid):
    return {"status": 200, "content_id": cid, "appeal_status": 200, "appeal_state": "under_review",
            "appeal_new_entries": [{"event": "appeal", "status": "under_review", "content_id": cid}]}


def unknown_ok():
    return {"unknown_id": "x", "appeal_status": 404,
            "appeal_new_entries": [{"event": "rejected", "status": "rejected", "content_id": None}]}


def bad(status):
    return {"status": status, "new_entries": [{"event": "rejected", "status": "rejected", "http_status": status}]}


# ── criterion 1 ──────────────────────────────────────────────────────────────

def test_c1_allows_one_ai_and_not_two():
    one = trial(**{"my own writing": [res("ai")] + [res("unsure") for _ in range(9)]})
    two = trial(**{"my own writing": [res("ai"), res("ai")] + [res("unsure") for _ in range(8)]})
    assert ev.criterion_1(one) == (True, "1/10")
    assert ev.criterion_1(two) == (False, "2/10")


def test_c1_a_failed_request_cannot_meet_it():
    t = trial(**{"my own writing": [res(status=500, guess=None)] + [res() for _ in range(9)]})
    assert ev.criterion_1(t)[0] is False


# ── criterion 2 ──────────────────────────────────────────────────────────────

def test_c2_gap_is_computed_with_the_combining_rule():
    ok, value = ev.criterion_2(trial())
    assert ok and value == "0.800"          # 0.9 vs 0.1, equal signals combine to themselves


def test_c2_misses_below_the_target_and_meets_at_it():
    close = trial(**{"clear human": [res(model=0.7, style=0.7) for _ in range(5)]})
    assert ev.criterion_2(close)[0] is False
    edge = trial(**{"clear human": [res(model=0.6, style=0.6) for _ in range(5)]})
    assert ev.criterion_2(edge)[0] is True   # 0.9 - 0.6 = 0.30


# ── criterion 3 ──────────────────────────────────────────────────────────────

def test_c3_needs_all_three_labels_and_two_unsure_borderline():
    assert ev.criterion_3(trial()) == (True, "3/3 labels, 3/3 unsure")


def test_c3_misses_when_ai_label_never_appears():
    t = trial(**{"labels: AI": [res("unsure") for _ in range(3)]})
    assert ev.criterion_3(t) == (False, "2/3 labels, 3/3 unsure")


def test_c3_misses_when_borderline_is_not_unsure():
    t = trial(**{"labels: borderline": [res("unsure"), res("ai"), res("human")]})
    assert ev.criterion_3(t)[0] is False


# ── criterion 4 ──────────────────────────────────────────────────────────────

def test_c4_met_when_every_appeal_adds_one_entry_and_unknown_is_404():
    assert ev.criterion_4(trial()) == (True, "5/5, unknown id 404")


def test_c4_misses_if_an_appeal_adds_two_entries():
    bad_one = appeal_ok("c0")
    bad_one["appeal_new_entries"] = bad_one["appeal_new_entries"] * 2
    t = trial(appeals=[bad_one] + [appeal_ok(f"c{i}") for i in range(1, 5)] + [unknown_ok()])
    assert ev.criterion_4(t) == (False, "4/5, unknown id 404")


def test_c4_misses_if_the_unknown_id_writes_an_under_review_entry():
    u = unknown_ok()
    u["appeal_new_entries"] = [{"event": "appeal", "status": "under_review", "content_id": None}]
    t = trial(appeals=[appeal_ok(f"c{i}") for i in range(5)] + [u])
    assert ev.criterion_4(t)[0] is False


def test_c4_misses_if_the_appeal_entry_belongs_to_another_content_id():
    wrong = appeal_ok("c0")
    wrong["appeal_new_entries"][0]["content_id"] = "someone-else"
    t = trial(appeals=[wrong] + [appeal_ok(f"c{i}") for i in range(1, 5)] + [unknown_ok()])
    assert ev.criterion_4(t)[0] is False


# ── criterion 5 ──────────────────────────────────────────────────────────────

def test_c5_met_when_all_eight_get_the_listed_code_and_one_entry():
    assert ev.criterion_5(trial()) == (True, "8/8")


def test_c5_misses_on_a_500():
    results = [bad(s) for s in (400, 400, 400, 400, 400, 400, 413, 400)]
    results[3] = {"status": 500, "new_entries": []}
    assert ev.criterion_5(trial(**{"bad input": results})) == (False, "7/8")


def test_c5_misses_when_a_rejection_leaves_no_log_entry():
    results = [bad(s) for s in (400, 400, 400, 400, 400, 400, 413, 400)]
    results[0]["new_entries"] = []
    assert ev.criterion_5(trial(**{"bad input": results}))[0] is False


def test_c5_misses_on_a_429_instead_of_the_expected_400():
    results = [bad(s) for s in (400, 400, 400, 400, 400, 400, 413, 400)]
    results[7] = bad(429)
    assert ev.criterion_5(trial(**{"bad input": results}))[0] is False


# ── across trials and the report ─────────────────────────────────────────────

def test_a_criterion_is_met_only_if_every_trial_meets_it():
    assert ev.verdict([(True, "a"), (True, "a"), (True, "a")]) == "MET"
    assert ev.verdict([(True, "a"), (False, "b"), (True, "a")]) == "MISSED"


def test_parse_report_groups_results_by_scenario_and_trial():
    text = ("### my own writing\n\n**Trial 1**\n\n```json\n" + json.dumps([{"status": 200}]) +
            "\n```\n\n**Trial 2**\n\n```json\n" + json.dumps([{"status": 400}]) +
            "\n```\n\n### bad input\n\n**Trial 1**\n\n```json\n[]\n```\n")
    out = ev.parse_report(text)
    assert out["my own writing"][1] == [{"status": 200}] and out["my own writing"][2] == [{"status": 400}]
    assert out["bad input"] == {1: []}


def test_evaluate_runs_all_five_over_all_trials():
    report = {name: {1: rows, 2: rows, 3: rows} for name, rows in trial().items()}
    results = ev.evaluate(report)
    assert set(results) == {1, 2, 3, 4, 5}
    assert all(len(v) == 3 for v in results.values())
    assert all(ev.verdict(v) == "MET" for v in results.values())
