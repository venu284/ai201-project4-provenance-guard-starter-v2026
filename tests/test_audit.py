"""The audit log (audit.py): shape, append-only, and surviving bad lines."""

import audit

NINE = {"timestamp", "content_id", "creator_id", "guess", "model_score",
        "style_score", "combined_score", "label", "status"}


def test_log_decision_has_all_nine_fields_even_when_unfilled():
    entry = audit.log_decision(content_id="c1", creator_id="w")
    assert NINE <= set(entry)
    assert entry["guess"] is None and entry["status"] == "decided"


def test_entries_are_appended_in_order_and_read_back():
    audit.log_decision(content_id="c1", creator_id="w")
    audit.log_appeal(content_id="c1", creator_id="w", reasoning="mine")
    audit.log_rejection(creator_id="w", reason="bad_input")
    kinds = [e.get("event", "decision") for e in audit.read_entries()]
    assert kinds == ["decision", "appeal", "rejected"]


def test_entries_for_returns_only_that_id():
    audit.log_decision(content_id="a", creator_id="w")
    audit.log_decision(content_id="b", creator_id="w")
    audit.log_appeal(content_id="a", creator_id="w", reasoning="r")
    assert [e["content_id"] for e in audit.entries_for("a")] == ["a", "a"]


def test_read_entries_limit_keeps_the_most_recent():
    for i in range(5):
        audit.log_decision(content_id=f"c{i}", creator_id="w")
    assert [e["content_id"] for e in audit.read_entries(limit=2)] == ["c3", "c4"]


def test_a_malformed_line_is_skipped_not_fatal():
    import config
    audit.log_decision(content_id="c1", creator_id="w")
    with config.AUDIT_LOG.open("a", encoding="utf-8") as f:
        f.write("{not json\n\n")
    audit.log_decision(content_id="c2", creator_id="w")
    assert [e["content_id"] for e in audit.read_entries()] == ["c1", "c2"]


def test_read_on_a_missing_log_is_empty():
    assert audit.read_entries() == []


def test_clear_reports_how_many_went():
    audit.log_decision(content_id="c1", creator_id="w")
    audit.log_decision(content_id="c2", creator_id="w")
    assert audit.clear() == 2
    assert audit.read_entries() == []


def test_extra_fields_are_written():
    entry = audit.log_rejection(creator_id="w", reason="rate_limited", limit="10/minute")
    assert entry["limit"] == "10/minute"
    assert audit.read_entries()[0]["limit"] == "10/minute"
