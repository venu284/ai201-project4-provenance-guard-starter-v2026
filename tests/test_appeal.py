"""POST /appeal: it must always change status, and always leave a record."""

import pytest

import audit

from test_submit import post


def submit_one(client, model_score, creator="writer_1"):
    model_score(0.5)
    from conftest import GOOD_TEXT
    return post(client, {"text": GOOD_TEXT, "creator_id": creator}).get_json()["content_id"]


def appeal(client, content_id, reasoning="I wrote this myself."):
    return client.post("/appeal", json={"content_id": content_id, "reasoning": reasoning})


def test_appeal_returns_under_review_and_adds_exactly_one_entry(client, model_score):
    cid = submit_one(client, model_score)
    before = len(audit.read_entries())
    r = appeal(client, cid)
    assert r.status_code == 200
    assert r.get_json()["status"] == "under_review"
    assert r.get_json()["content_id"] == cid
    after = audit.read_entries()
    assert len(after) == before + 1
    assert after[-1]["content_id"] == cid
    assert after[-1]["status"] == "under_review"
    assert after[-1]["event"] == "appeal"


def test_the_original_decision_is_left_untouched(client, model_score):
    """The log is append-only: the decision stays as it was, with its own status."""
    cid = submit_one(client, model_score)
    original = audit.entries_for(cid)[0]
    appeal(client, cid)
    assert audit.entries_for(cid)[0] == original
    assert original["status"] == "decided"


def test_five_submissions_five_appeals_criterion_4(client, model_score):
    for i in range(5):
        cid = submit_one(client, model_score, creator=f"w{i}")
        before = len(audit.read_entries())
        r = appeal(client, cid)
        assert r.status_code == 200 and r.get_json()["status"] == "under_review"
        assert len(audit.read_entries()) == before + 1


def test_appeal_is_filed_under_the_original_writer(client, model_score):
    cid = submit_one(client, model_score, creator="the_real_writer")
    appeal(client, cid)
    assert audit.read_entries()[-1]["creator_id"] == "the_real_writer"


def test_appeal_stores_the_reasoning(client, model_score):
    cid = submit_one(client, model_score)
    appeal(client, cid, reasoning="  I wrote it on the train.  ")
    assert audit.read_entries()[-1]["reasoning"] == "I wrote it on the train."


def test_unknown_content_id_is_404_and_no_under_review_entry(client):
    r = appeal(client, "00000000-0000-0000-0000-000000000000")
    assert r.status_code == 404
    assert r.get_json()["error"] == "unknown_content_id"
    entries = audit.read_entries()
    assert all(e["status"] != "under_review" for e in entries)
    assert entries[-1]["event"] == "rejected"


def test_a_typo_in_the_id_is_404_not_a_silent_success(client, model_score):
    cid = submit_one(client, model_score)
    assert appeal(client, cid[:-1] + ("0" if cid[-1] != "0" else "1")).status_code == 404


def test_an_appeal_cannot_be_filed_against_a_rejection(client):
    """Rejections have no content_id, so they can never be appealed."""
    post(client, {"text": "", "creator_id": "c"})
    assert appeal(client, "unknown").status_code == 404


def test_second_appeal_on_the_same_id_is_accepted_and_recorded_again(client, model_score):
    cid = submit_one(client, model_score)
    appeal(client, cid)
    before = len(audit.read_entries())
    assert appeal(client, cid).status_code == 200
    assert len(audit.read_entries()) == before + 1


@pytest.mark.parametrize("body", [
    {},
    {"content_id": "x"},
    {"reasoning": "r"},
    {"content_id": "", "reasoning": "r"},
    {"content_id": "x", "reasoning": "   "},
    {"content_id": 5, "reasoning": "r"},
    {"content_id": "x", "reasoning": None},
    {"content_id": "x", "reasoning": "r" * 2_001},
])
def test_malformed_appeals_are_400_and_write_no_under_review_entry(client, body):
    r = client.post("/appeal", json=body)
    assert r.status_code == 400
    assert all(e["status"] != "under_review" for e in audit.read_entries())


@pytest.mark.parametrize("raw", ["nope", "[1]", "7"])
def test_appeal_body_that_is_not_an_object_is_400(client, raw):
    assert client.post("/appeal", data=raw, content_type="application/json").status_code == 400


def test_appeal_entry_carries_the_original_scores_and_label(client, model_score):
    cid = submit_one(client, model_score)
    original = audit.entries_for(cid)[0]
    appeal(client, cid)
    entry = audit.read_entries()[-1]
    assert tuple(list(entry)[:9]) == audit.NINE_FIELDS
    for field in ("guess", "model_score", "style_score", "combined_score", "label"):
        assert entry[field] == original[field]


def test_appeal_rejections_carry_the_http_status(client):
    appeal(client, "nope")
    entry = audit.read_entries()[-1]
    assert (entry["event"], entry["http_status"]) == ("rejected", 404)
