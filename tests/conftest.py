"""
Shared test setup.

Every test that touches the service gets a throwaway audit log, so running the
tests never writes to the committed `logs/audit.jsonl`. The language model is
replaced by a stub unless a test asks for the real one: tests need to run in
seconds and give the same answer every time.
"""

import os
import sys
from pathlib import Path

import pytest

# The shipped config turns rate limiting on. Most tests send far more than 12
# requests from one creator_id, so switch it off for them; test_rate_limit.py
# reloads app.py with it on. This must happen before config is imported.
os.environ["AI201_RATE_LIMITS"] = "0"

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import config  # noqa: E402


@pytest.fixture(autouse=True)
def isolated_log(tmp_path, monkeypatch):
    """Point the audit log at a temp directory for the length of one test."""
    monkeypatch.setattr(config, "LOG_DIR", tmp_path)
    monkeypatch.setattr(config, "AUDIT_LOG", tmp_path / "audit.jsonl")
    return tmp_path / "audit.jsonl"


@pytest.fixture
def model_score(monkeypatch):
    """
    Replace the language model with a settable number.

        model_score(0.9)   # every submission now gets signal one = 0.9

    Pass an exception class or instance to make the detector raise it.
    """
    import detector

    state = {"value": 0.5}

    def fake(_text):
        value = state["value"]
        if isinstance(value, BaseException) or (
            isinstance(value, type) and issubclass(value, BaseException)
        ):
            raise value
        return value

    monkeypatch.setattr(detector, "model_signal", fake)

    def set_value(value):
        state["value"] = value

    return set_value


@pytest.fixture
def client():
    from app import app

    app.config["TESTING"] = True
    return app.test_client()


# A valid body: 25 words, more than one sentence.
GOOD_TEXT = (
    "I walked to the shop on Tuesday because we had run out of milk. "
    "The queue was long, so I read the notices by the door. "
    "Nobody smiled, but the cashier waved when I left, which was nice."
)


@pytest.fixture
def good_body():
    return {"text": GOOD_TEXT, "creator_id": "tester"}
