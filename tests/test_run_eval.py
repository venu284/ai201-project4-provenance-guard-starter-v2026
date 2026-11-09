"""
run_eval.py's helpers against the real app (model stubbed), through an adapter
that looks like the `requests` module. They record the log entries each request
added and send appeals, which is what criteria 4 and 5 are judged on.
"""

import pytest

import run_eval

from conftest import GOOD_TEXT


class Http:
    """Just enough of `requests` for run_eval, backed by Flask's test client."""

    def __init__(self, client):
        self.client = client

    @staticmethod
    def _path(url):
        return "/" + url.split("/", 3)[3]

    def _wrap(self, response):
        class R:
            status_code = response.status_code
            content = response.data

            @staticmethod
            def json():
                return response.get_json()
        return R

    def get(self, url, timeout=None):
        return self._wrap(self.client.get(self._path(url)))

    def post(self, url, json=None, timeout=None):
        return self._wrap(self.client.post(self._path(url), json=json))


@pytest.fixture
def http(client, model_score):
    model_score(0.5)
    return Http(client)


URL = "http://127.0.0.1:5000"


def test_a_good_submission_records_its_scores_and_one_new_log_entry(http):
    r = run_eval.send_body(http, URL, {"text": GOOD_TEXT, "creator_id": "w"}, 5)
    assert r["status"] == 200 and r["guess"] in {"human", "unsure", "ai"}
    assert r["combined_score"] is not None and r["content_id"]
    assert len(r["new_entries"]) == 1
    assert r["new_entries"][0]["status"] == "decided"


def test_a_refused_submission_records_its_rejection_entry(http):
    r = run_eval.send_body(http, URL, {"text": "", "creator_id": "w"}, 5)
    assert r["status"] == 400
    assert [(e["event"], e["http_status"]) for e in r["new_entries"]] == [("rejected", 400)]


def test_an_appeal_records_status_and_the_one_entry_it_added(http):
    sub = run_eval.send_body(http, URL, {"text": GOOD_TEXT, "creator_id": "w"}, 5)
    r = run_eval.send_appeal(http, URL, sub["content_id"], 5)
    assert (r["appeal_status"], r["appeal_state"]) == (200, "under_review")
    assert len(r["appeal_new_entries"]) == 1
    assert r["appeal_new_entries"][0]["content_id"] == sub["content_id"]


def test_an_unknown_id_is_a_404_with_no_under_review_entry(http):
    r = run_eval.send_appeal(http, URL, "00000000-0000-0000-0000-000000000000", 5)
    assert r["appeal_status"] == 404
    assert all(e["status"] != "under_review" for e in r["appeal_new_entries"])


def test_run_scenario_once_appeals_every_submission_and_tries_the_unknown_ids(http):
    scenario = {"name": "appeals", "texts": [GOOD_TEXT, GOOD_TEXT], "appeal": True,
                "unknown_ids": ["nope"]}
    results = run_eval.run_scenario_once(http, URL, scenario, 5)
    assert len(results) == 3
    assert [r.get("appeal_status") for r in results] == [200, 200, 404]
    assert results[2]["unknown_id"] == "nope"


def test_a_scenario_without_appeal_does_not_appeal(http):
    results = run_eval.run_scenario_once(http, URL, {"name": "x", "texts": [GOOD_TEXT]}, 5)
    assert "appeal_status" not in results[0]


def test_an_unreadable_log_gives_none_not_a_crash():
    class Dead:
        def get(self, *a, **k):
            raise ConnectionError("down")

        def post(self, *a, **k):
            raise ConnectionError("down")

    r = run_eval.send_body(Dead(), URL, {"text": GOOD_TEXT, "creator_id": "w"}, 1)
    assert r["status"] is None and "ConnectionError" in r["error"]
    assert r["new_entries"] is None
