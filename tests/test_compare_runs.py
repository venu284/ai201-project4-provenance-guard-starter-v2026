"""compare_runs.py: parsing the verdict files and the pre-registered success test."""

import compare_runs as cr

ATTACKS = """| ID | Family | Status | Guess | Model | Style | Combined | Verdict | Why |
|---|---|---|---|---|---|---|---|---|
| EV01 | evasion | 200 | human | 0.2 | 0.2 | 0.200 | BROKE | x |
| FP01 | false_positive | 200 | unsure | 0.5 | 0.5 | 0.500 | HELD | x |

## By family
"""

CRITERIA = """| Criterion | Target | Run 1 | Run 2 | Run 3 | Verdict |
|---|---|---|---|---|---|
| 1. My own writing flagged as AI | at most 1 | 0/10 | 0/10 | 0/10 | MET |
| 3. All three labels are reachable | all 3 | 2/3 labels, 3/3 unsure | 2/3 labels, 3/3 unsure | 2/3 labels, 3/3 unsure | MISSED |
"""


def test_parse_attack_table_reads_every_row():
    rows = cr.parse_attack_table(ATTACKS)
    assert rows["EV01"] == {"family": "evasion", "status": "200", "guess": "human",
                            "combined": "0.200", "verdict": "BROKE"}
    assert set(rows) == {"EV01", "FP01"}


def test_parse_criteria_table_reads_runs_and_verdict():
    rows = cr.parse_criteria_table(CRITERIA)
    assert rows[1]["runs"] == ["0/10", "0/10", "0/10"] and rows[1]["verdict"] == "MET"
    assert rows[3]["verdict"] == "MISSED" and rows[3]["runs"][0] == "2/3 labels, 3/3 unsure"


def test_counts_by_family():
    c = cr.counts(cr.parse_attack_table(ATTACKS))
    assert c["evasion"] == {"HELD": 0, "BROKE": 1, "JUDGE": 0}


def attacks(**v):
    return {i: {"family": "false_positive" if i.startswith("FP") else "evasion", "guess": g, "verdict": vd}
            for i, (g, vd) in v.items()}


def own(*guesses):
    return [{"guess": g} for g in guesses]


def test_success_test_passes_when_broken_falls_and_nobody_is_newly_accused():
    b = attacks(EV01=("human", "BROKE"), FP01=("unsure", "HELD"))
    a = attacks(EV01=("unsure", "HELD"), FP01=("unsure", "HELD"))
    t = cr.success_test(b, a, own("unsure"), own("unsure"), {1: {"verdict": "MET"}}, {1: {"verdict": "MET"}})
    assert [ok for _, ok, _ in t] == [True, True, True]


def test_success_test_fails_if_a_writer_is_newly_accused():
    b = attacks(EV01=("human", "BROKE"), FP01=("unsure", "HELD"))
    a = attacks(EV01=("unsure", "HELD"), FP01=("ai", "BROKE"))
    t = cr.success_test(b, a, own("unsure"), own("unsure"), {}, {})
    assert t[1][1] is False and "FP01" in t[1][2]


def test_success_test_fails_if_an_own_piece_is_newly_ai():
    b = attacks(EV01=("human", "BROKE"))
    a = attacks(EV01=("unsure", "HELD"))
    t = cr.success_test(b, a, own("unsure", "unsure"), own("unsure", "ai"), {}, {})
    assert t[1][1] is False and "own_02" in t[1][2]


def test_success_test_fails_if_a_met_criterion_is_missed_or_nothing_improved():
    b = attacks(EV01=("human", "BROKE"))
    t = cr.success_test(b, b, own(), own(), {2: {"verdict": "MET"}}, {2: {"verdict": "MISSED"}})
    assert t[0][1] is False and t[2][1] is False and "2" in t[2][2]
