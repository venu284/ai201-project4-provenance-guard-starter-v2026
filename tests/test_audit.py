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


# ── every entry type carries the nine keys (unit 8, M1) ──────────────────────

DECISION_FIELDS = ("guess", "model_score", "style_score", "combined_score", "label")


def test_nine_keys_come_first_and_in_the_same_order_on_every_entry_type():
    audit.log_decision(content_id="c1", creator_id="w", guess="human", model_score=0.1,
                       style_score=0.2, combined_score=0.15, label="L")
    audit.log_appeal(content_id="c1", creator_id="w", reasoning="r")
    audit.log_rejection(creator_id="w", reason="bad_input", http_status=400)
    order = list(audit.NINE_FIELDS)
    for entry in audit.read_entries():
        assert list(entry)[:9] == order


def test_rejection_has_all_nine_keys_with_nulls_for_what_never_happened():
    entry = audit.log_rejection(creator_id="w", reason="bad_input", http_status=400)
    assert audit.NINE_FIELDS == tuple(list(entry)[:9])
    assert entry["status"] == "rejected"
    assert entry["content_id"] is None
    assert all(entry[f] is None for f in DECISION_FIELDS)
    assert (entry["event"], entry["reason"], entry["http_status"]) == ("rejected", "bad_input", 400)


def test_appeal_copies_the_decision_so_the_line_stands_alone():
    original = audit.log_decision(content_id="c1", creator_id="w", guess="unsure",
                                  model_score=0.7, style_score=0.4, combined_score=0.475,
                                  label="L")
    entry = audit.log_appeal(content_id="c1", creator_id="w", reasoning="mine", original=original)
    for field in DECISION_FIELDS:
        assert entry[field] == original[field]
    assert (entry["status"], entry["event"], entry["reasoning"]) == ("under_review", "appeal", "mine")


def test_appeal_without_an_original_still_has_all_nine_keys():
    entry = audit.log_appeal(content_id="c1", creator_id="w", reasoning="r")
    assert tuple(list(entry)[:9]) == audit.NINE_FIELDS
    assert all(entry[f] is None for f in DECISION_FIELDS)
