"""
The rate limit on POST /submit (unit 8, Milestone 1).

The limiter is built when app.py is imported, from config.py, so each test
reloads app.py with limiting switched on and then puts it back. The model is
stubbed: these test counting, not scoring.
"""

import importlib

import pytest

import audit
import config

from conftest import GOOD_TEXT


@pytest.fixture
def limited(monkeypatch, model_score):
    """
    A client for an app reloaded with the limiter on.

        client = limited()                          # shipped numbers
        client = limited(per_minute=3, per_day=50)  # for a test's own numbers
    """
    import app as app_module

    def make(per_minute=None, per_day=None):
        monkeypatch.setattr(config, "RATE_LIMITING_ENABLED", True)
        if per_minute is not None:
            monkeypatch.setattr(config, "RATE_LIMIT_PER_MINUTE", per_minute)
        if per_day is not None:
            monkeypatch.setattr(config, "RATE_LIMIT_PER_DAY", per_day)
        importlib.reload(app_module)
        app_module.app.config["TESTING"] = True
        return app_module.app.test_client()

    model_score(0.5)
    yield make
    monkeypatch.undo()
    importlib.reload(app_module)


def submit(client, creator="writer"):
    return client.post("/submit", json={"text": GOOD_TEXT, "creator_id": creator})


def codes(client, n, creator="writer"):
    return [submit(client, creator).status_code for _ in range(n)]


def test_the_shipped_numbers_are_the_ones_the_readme_defends():
    assert (config.RATE_LIMIT_PER_MINUTE, config.RATE_LIMIT_PER_DAY) == (12, 30)


def test_limiting_is_on_by_default(monkeypatch):
    """Off only when AI201_RATE_LIMITS=0, which conftest sets for the other tests."""
    monkeypatch.delenv("AI201_RATE_LIMITS", raising=False)
    import config as fresh
    importlib.reload(fresh)
    try:
        assert fresh.RATE_LIMITING_ENABLED is True
    finally:
        monkeypatch.setenv("AI201_RATE_LIMITS", "0")
        importlib.reload(fresh)


def test_twelve_pass_and_the_thirteenth_is_429(limited):
    client = limited(per_minute=config.RATE_LIMIT_PER_MINUTE, per_day=config.RATE_LIMIT_PER_DAY)
    run = codes(client, 15)
    assert run == [200] * 12 + [429] * 3


def test_the_429_says_which_limit_was_hit(limited):
    client = limited(per_minute=2, per_day=100)
    codes(client, 2)
    r = submit(client)
    assert r.status_code == 429
    body = r.get_json()
    assert body["error"] == "rate_limited"
    assert body["limit"] == "2 per 1 minute"


def test_the_day_cap_is_a_separate_429(limited):
    client = limited(per_minute=1000, per_day=3)
    run = codes(client, 5)
    assert run == [200, 200, 200, 429, 429]
    assert submit(client).get_json()["limit"] == "3 per 1 day"


def test_one_creator_hitting_the_limit_does_not_block_another(limited):
    client = limited(per_minute=2, per_day=100)
    codes(client, 3, creator="noisy")
    assert submit(client, creator="noisy").status_code == 429
    assert submit(client, creator="quiet").status_code == 200


def test_a_429_is_logged_with_nine_keys_and_the_limit(limited):
    client = limited(per_minute=1, per_day=100)
    codes(client, 2, creator="flooder")
    entry = audit.read_entries()[-1]
    assert tuple(list(entry)[:9]) == audit.NINE_FIELDS
    assert entry["event"] == "rejected" and entry["reason"] == "rate_limited"
    assert entry["http_status"] == 429
    assert entry["creator_id"] == "flooder"
    assert entry["status"] == "rejected"
    assert entry["limit"] == "1 per 1 minute"


def test_refused_requests_count_toward_the_limit(limited):
    """A flood of bad input is limited too: the 400s use up the allowance."""
    client = limited(per_minute=2, per_day=100)
    for _ in range(2):
        client.post("/submit", json={"text": "", "creator_id": "w"})
    assert submit(client, creator="w").status_code == 429


def test_requests_with_no_usable_creator_id_share_one_address_bucket(limited):
    client = limited(per_minute=2, per_day=100)
    for body in ({"text": GOOD_TEXT}, {"text": GOOD_TEXT, "creator_id": 7}):
        assert client.post("/submit", json=body).status_code == 400
    # a third creator-less request is from the same address: limited
    assert client.post("/submit", json={"text": GOOD_TEXT}).status_code == 429
    # a request with a real creator_id has its own bucket
    assert submit(client, creator="someone").status_code == 200


@pytest.mark.parametrize("raw", ["[1, 2]", '"text"', "null", "not json", "42"])
def test_a_body_that_is_not_an_object_never_crashes_the_key_function(limited, raw):
    client = limited(per_minute=100, per_day=100)
    r = client.post("/submit", data=raw, content_type="application/json")
    assert r.status_code == 400


def test_only_submit_is_limited(limited):
    client = limited(per_minute=1, per_day=100)
    codes(client, 3)
    assert client.post("/ping", json={"message": "x"}).status_code == 200
    assert client.get("/health").status_code == 200
    assert client.get("/log").status_code == 200


def test_health_reports_that_limiting_is_on(limited):
    client = limited()
    assert client.get("/health").get_json()["rate_limiting"] is True
