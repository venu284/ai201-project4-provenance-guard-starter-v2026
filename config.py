"""
Settings for Provenance Guard.

Everything you're likely to change lives here, at the top, on purpose.

You'll edit the thresholds in Milestone 5; the rate limits were set in unit 8.
"""

import os
from pathlib import Path

ROOT = Path(__file__).parent


# ─── The service ─────────────────────────────────────────────────────────────

# `127.0.0.1` is loopback — only your own machine can reach it, which is what
# you want all through units 7 and 8. A host somewhere else has to accept
# traffic from outside the box, and that means `0.0.0.0`. Setting the env var
# is how you get it; the default keeps your local `curl` commands unchanged.
HOST = os.getenv("HOST", "127.0.0.1")
PORT = int(os.getenv("PORT", "5000"))

# Flask's debug mode gives anyone who can reach the service an interactive
# Python prompt inside your process. Fine on loopback, a gift to strangers
# anywhere else — so it turns itself off the moment HOST isn't loopback.
DEBUG = os.getenv("AI201_DEBUG", "1") == "1" and HOST in ("127.0.0.1", "localhost")


# ─── The local model ─────────────────────────────────────────────────────────
# Your first signal runs a language model ON YOUR OWN MACHINE. No account, no
# key, no card. It downloads about 550 MB the first time — do that before
# class, not during it.
#
# What it measures: how *predictable* your text is to a language model. Text a
# model finds easy to predict tends to be text a model wrote.
#
# The first call is the slow one — ten to twenty seconds while the model loads,
# longer on an older laptop. After that it stays in memory and a submission
# takes a second or two. That cost is part of what you're learning: this is
# what running a model inline in a request actually looks like.

DETECTOR_MODEL = os.getenv("AI201_DETECTOR_MODEL", "gpt2")

# Longer text gives a steadier reading but takes longer. 400 tokens is roughly
# 300 words, which is enough for the signal to mean something.
DETECTOR_MAX_TOKENS = 400


# ─── Scoring (Milestone 4) ───────────────────────────────────────────────────
# How much each signal counts toward the combined score.
#
# The rule is "lean human": the combined score is
#   LOWER_SIGNAL_WEIGHT * (the lower signal) + (1 - LOWER_SIGNAL_WEIGHT) * (the higher)
# so both signals have to read AI for the result to read AI. 0.5 would be a
# plain average; 1.0 would ignore the higher signal completely. The rule itself
# is in scoring.py::combine_signals.

LOWER_SIGNAL_WEIGHT = 0.75


# ─── Thresholds (Milestone 5) ────────────────────────────────────────────────
# Where one label becomes another. Scores run 0.0 (confidently human) to 1.0
# (confidently AI).
#
#   score < HUMAN_THRESHOLD          -> high-confidence human
#   between the two                  -> unsure
#   score >= AI_THRESHOLD            -> high-confidence AI
#
# ⚠️ This is where your false-positive decision from Milestone 1 actually gets
# made. Widening the unsure band means fewer wrong accusations and more AI text
# getting through. There is no setting that avoids the trade — only settings
# that decide who pays for it.

# Chosen from 24 test texts scored with both signals (combined score):
#   messy human .15-.21 | edited AI .35-.62 | formal human .44-.63
#   ordinary AI .49-.73 | plain human .79-.80 | plain AI .77-.91
# Plain human and plain AI overlap, so no threshold separates them. 0.85 keeps
# the plain human texts in "unsure", at the price that most AI text is "unsure"
# too. The margin over .80 is thin and rests on three imitation human texts.
# A score exactly at HUMAN_THRESHOLD is "unsure"; at AI_THRESHOLD it is "ai".
HUMAN_THRESHOLD = 0.30
AI_THRESHOLD = 0.85

# ⚠️ One thing that catches people out in Milestone 5. A weighted average can
# only land between its two inputs — so while `style_signal` is still the stub
# returning 0.5, the combined score can never leave 0.25–0.75 no matter what
# the model signal says, and the human label needs a model score below 0.20 to
# be reachable at all.
#
# If a label you can't reach is the problem, the fix is upstream of the
# thresholds: a style signal that actually varies. `scoring.label_ranges()`
# prints the bands; the reachable range is a different question.


# ─── Rate limiting (UNIT 8) ──────────────────────────────────────────────────
# On by default now. Set AI201_RATE_LIMITS=0 to switch it off (the test suite
# does, because most tests send more than 12 requests from one creator_id).
#
# Two people to think about: a real writer submitting their own work, and a
# script sending a thousand variations to map the thresholds above.
#
#   12 a minute  A writer revising a piece sends two or three in a minute at
#                most, so this never blocks them. It does stop a burst: a flood
#                of 15 gets twelve 200s and three 429s.
#   30 a day     This is the cap that does the real work. At 12 a minute a
#                script could send over 17,000 a day; 30 leaves a writer room
#                for a long day of revisions and gives a script 30 probes per
#                creator_id, too few to find where the thresholds sit. It takes
#                three minutes of steady use to reach it: two full minutes make
#                24, and the 31st submission is refused with "30 per 1 day".
#
# Both count per creator_id (falling back to the caller's address when a request
# has no usable creator_id). The README says what that does and does not stop.

RATE_LIMITING_ENABLED = os.getenv("AI201_RATE_LIMITS", "1") == "1"

RATE_LIMIT_PER_MINUTE = 12
RATE_LIMIT_PER_DAY = 30

# Flask-Limiter warns loudly without this. In-memory is right for one laptop
# and wrong for anything real — a restart forgets every count, and two copies
# of the service wouldn't share limits.
RATE_LIMIT_STORAGE = "memory://"


# ─── Paths ───────────────────────────────────────────────────────────────────

LOG_DIR = ROOT / "logs"
AUDIT_LOG = LOG_DIR / "audit.jsonl"
RESULTS_DIR = ROOT / "results"
