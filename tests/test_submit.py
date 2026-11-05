"""
POST /submit: every branch the route has.

The language model is stubbed (see conftest.model_score), so these check the
route, the combining rule, the label and the log, not gpt2. The five rejection
paths, the 503, the 413 and the success case are all here.
"""

import json
import uuid

import pytest

import app as app_module
import audit
import detector

from conftest import GOOD_TEXT

NINE_FIELDS = {"timestamp", "content_id", "creator_id", "guess", "model_score",
               "style_score", "combined_score", "label", "status"}


def post(client, body):
    return client.post("/submit", json=body)


# ── success ──────────────────────────────────────────────────────────────────

def test_success_returns_every_documented_field(client, model_score, good_body):
    model_score(0.9)
    r = post(client, good_body)
    assert r.status_code == 200
    data = r.get_json()
    assert set(data) == {"content_id", "guess", "confidence", "label", "model_score",
                         "style_score", "combined_score", "status"}
    assert data["model_score"] == 0.9
    assert data["status"] == "decided"
    assert data["guess"] in {"human", "unsure", "ai"}
    uuid.UUID(data["content_id"])  # raises if it is not a uuid


def test_success_writes_one_entry_with_all_nine_fields(client, model_score, good_body):
    model_score(0.9)
    data = post(client, good_body).get_json()
    entries = audit.read_entries()
    assert len(entries) == 1
    entry = entries[0]
    assert NINE_FIELDS <= set(entry)
    assert entry["content_id"] == data["content_id"]
    assert entry["creator_id"] == "tester"
    assert entry["model_score"] == data["model_score"]
    assert entry["style_score"] == data["style_score"]
    assert entry["combined_score"] == data["combined_score"]
    assert entry["guess"] == data["guess"]
    assert entry["status"] == "decided"
    assert "event" not in entry


def test_response_and_log_agree_on_the_label_text(client, model_score, good_body):
    model_score(0.1)
    data = post(client, good_body).get_json()
    assert audit.read_entries()[0]["label"] == data["label"]


@pytest.mark.parametrize("model, expected", [(0.0, "human"), (1.0, "ai")])
def test_extreme_model_scores_can_reach_human_and_ai(client, model_score, model, expected):
    """With the style signal real, a very low or very high model score still
    needs the style signal to agree; pick a text where it does not matter much."""
    model_score(model)
    # Plain, even, short sentences: style reads AI. Messy: style reads human.
    plain = " ".join(["The cat sat on the mat today."] * 5)
    messy = ("Honestly? I never expected it. We drove for hours, past the quarry, the "
             "old rail bridge, the bakery that burned down in '09 -- and then nothing. "
             "Nothing! Just a field. Odd, really; lovely too.")
    text = plain if expected == "ai" else messy
    data = post(client, {"text": text, "creator_id": "x"}).get_json()
    assert data["guess"] == expected


def test_same_text_twice_gets_two_different_content_ids(client, model_score, good_body):
    model_score(0.5)
    a = post(client, good_body).get_json()["content_id"]
    b = post(client, good_body).get_json()["content_id"]
    assert a != b


# ── the five rejection paths + the 413 ───────────────────────────────────────

REJECTIONS = [
    ("missing text", {"creator_id": "c"}, 400),
    ("empty text", {"text": "", "creator_id": "c"}, 400),
    ("whitespace text", {"text": "   \n\t ", "creator_id": "c"}, 400),
    ("null text", {"text": None, "creator_id": "c"}, 400),
    ("number text", {"text": 12345, "creator_id": "c"}, 400),
    ("list text", {"text": ["a", "b"], "creator_id": "c"}, 400),
    ("19 words", {"text": " ".join(["word"] * 19), "creator_id": "c"}, 400),
    ("50,000 words", {"text": "word " * 50_000, "creator_id": "c"}, 413),
    ("missing creator_id", {"text": GOOD_TEXT}, 400),
    ("blank creator_id", {"text": GOOD_TEXT, "creator_id": "  "}, 400),
    ("number creator_id", {"text": GOOD_TEXT, "creator_id": 7}, 400),
]


@pytest.mark.parametrize("name, body, status", REJECTIONS, ids=[r[0] for r in REJECTIONS])
def test_bad_input_is_refused_and_logged(client, model_score, name, body, status):
    model_score(0.5)
    r = post(client, body)
    assert r.status_code == status
    assert "error" in r.get_json()
    entries = audit.read_entries()
    assert len(entries) == 1, "a rejection must leave exactly one log entry"
    assert entries[0]["event"] == "rejected"
    assert entries[0]["status"] == "rejected"
    assert entries[0]["reason"] == r.get_json()["error"]


@pytest.mark.parametrize("raw", ["not json at all", "[1, 2, 3]", '"just a string"', "42", "null", ""])
def test_a_body_that_is_not_a_json_object_is_a_400_not_a_crash(client, raw):
    r = client.post("/submit", data=raw, content_type="application/json")
    assert r.status_code == 400
    assert audit.read_entries()[0]["event"] == "rejected"


def test_wrong_content_type_is_a_400_not_a_crash(client):
    r = client.post("/submit", data=json.dumps({"text": GOOD_TEXT, "creator_id": "c"}),
                    content_type="text/plain")
    assert r.status_code == 400


def test_word_limit_boundary(client, model_score):
    model_score(0.5)
    assert post(client, {"text": " ".join(["word"] * (app_module.MIN_WORDS - 1)),
                         "creator_id": "c"}).status_code == 400
    assert post(client, {"text": " ".join(["word"] * app_module.MIN_WORDS),
                         "creator_id": "c"}).status_code == 200


def test_character_limit_boundary(client, model_score):
    model_score(0.5)
    at_limit = ("word " * app_module.MAX_CHARS)[: app_module.MAX_CHARS]
    assert post(client, {"text": at_limit, "creator_id": "c"}).status_code == 200
    assert post(client, {"text": at_limit + "x", "creator_id": "c"}).status_code == 413


def test_oversize_text_is_refused_before_the_model_runs(client, model_score):
    model_score(AssertionError("the model must not be called for oversize text"))
    r = post(client, {"text": "word " * 50_000, "creator_id": "c"})
    assert r.status_code == 413


def test_rejection_keeps_the_creator_id_when_it_is_known(client):
    post(client, {"text": "", "creator_id": "writer_9"})
    assert audit.read_entries()[0]["creator_id"] == "writer_9"


# ── the model fails ──────────────────────────────────────────────────────────

def test_model_unavailable_is_a_503_and_is_logged(client, model_score, good_body):
    model_score(detector.DetectorUnavailable("no model"))
    r = post(client, good_body)
    assert r.status_code == 503
    assert r.get_json()["error"] == "detector_unavailable"
    entry = audit.read_entries()[0]
    assert (entry["event"], entry["reason"]) == ("rejected", "detector_unavailable")


def test_model_value_error_is_a_400(client, model_score, good_body):
    model_score(ValueError("too short"))
    assert post(client, good_body).status_code == 400


# ── the other routes are untouched ───────────────────────────────────────────

def test_ping_still_works(client):
    r = client.post("/ping", json={"message": "hello"})
    assert r.status_code == 200
    assert r.get_json() == {"ok": True, "you_sent": "hello", "service": "provenance-guard"}


def test_log_route_returns_what_was_written(client, model_score, good_body):
    model_score(0.5)
    post(client, good_body)
    data = client.get("/log?limit=10").get_json()
    assert data["count"] == 1
    assert data["entries"][0]["creator_id"] == "tester"
