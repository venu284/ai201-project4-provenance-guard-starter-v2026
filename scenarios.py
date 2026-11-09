"""
What your test runs.  <- UNIT 8, MILESTONE 3

Each of the five criteria in criteria.md has something run against it here.
`run_eval.py` runs everything in SCENARIOS three times; `eval_verdicts.py` then
applies each criterion's target to what came back.

FROZEN: this file and eval_verdicts.py are committed before the first run, and
they do not change after any score has been seen. Every text was chosen by what
it is (its author and its place in a numbered series), never by the score it
gets. Anything that looks convenient is said so next to it.

Scenario keys beyond the starter's:

    "role"         what the texts are, for eval_verdicts.py: ai, human, borderline
    "appeal"       True: after each submission, appeal it (criterion 4)
    "unknown_ids"  appeal ids that were never issued (criterion 4)
    "expect"       the status code each body should get (criterion 5)

Where the texts come from:

    samples/own_writing/    ten pieces drafted by an AI agent that could not see
                            the repo or any score, reviewed and accepted by the
                            student as written, not rewritten. They are stand-ins
                            for the student's own writing; the README says so.
    samples/calibration/    the 30 calibration texts. AI texts there were written
                            by an AI; the "human" ones are AI-written imitations
                            of human writing. Neither is a real person's writing.
"""

from pathlib import Path

ROOT = Path(__file__).parent


def _own(n: int) -> str:
    return (ROOT / "samples" / "own_writing" / f"own_{n:02d}.txt").read_text(encoding="utf-8")


def _cal(name: str) -> str:
    return (ROOT / "samples" / "calibration" / "texts" / f"{name}.txt").read_text(encoding="utf-8")


# A valid submission, used where a criterion needs a body that should succeed.
_GOOD = ("I walked to the shop on Tuesday because we had run out of milk. The queue "
         "was long, so I read the notices by the door. Nobody smiled, but the cashier "
         "waved when I left, which was nice.")

# Criterion 5: exactly 19 words, one under the 20-word minimum.
_NINETEEN = "one two three four five six seven eight nine ten eleven twelve thirteen fourteen fifteen sixteen seventeen eighteen nineteen"
assert len(_NINETEEN.split()) == 19

SCENARIOS = [
    # ── Criterion 1: false positives on my own writing ──────────────────────
    {
        "name": "my own writing",
        "criterion": 1,
        "role": "human",
        # All ten pieces, own_01 to own_10. Chosen: all of them, in order, with
        # no selection. own_08, own_09 and own_10 are the three plain ones the
        # criterion requires (mean sentence length under 12 words, common
        # words); own_04 (a lab note) and own_06 (a numbered list) are also
        # short-sentenced but are not the plain ones.
        "texts": [_own(n) for n in range(1, 11)],
    },
    # ── Criterion 2: clearly-AI and clearly-human text score far apart ──────
    {
        "name": "clear AI",
        "criterion": 2,
        "role": "ai",
        # The first five ordinary AI texts in the calibration set (ai_01 to
        # ai_05): essays, an email and similar, written by an AI. Taken by id
        # order. Not chosen by score; the plain-AI texts are left out because
        # they are a different group (ai_plain_*), not because of how they score.
        "texts": [_cal(f"ai_0{n}") for n in range(1, 6)],
    },
    {
        "name": "clear human",
        "criterion": 2,
        "role": "human",
        # The first five varied pieces, own_01 to own_05, by id order. They are
        # AI-drafted stand-ins for a person's writing (see the header), so this
        # side of the criterion is weaker than "texts a person wrote".
        "texts": [_own(n) for n in range(1, 6)],
    },
    # ── Criterion 3: all three labels are reachable ─────────────────────────
    {
        "name": "labels: AI",
        "criterion": 3,
        "role": "ai",
        # ai_06, ai_07, ai_08: the next three ordinary AI texts by id. Ordinary
        # AI is what "clearly AI" means here. Plain AI texts are not swapped in
        # to make the "ai" label appear: if ordinary AI never reaches it, that
        # is the result.
        "texts": [_cal(f"ai_0{n}") for n in (6, 7, 8)],
    },
    {
        "name": "labels: human",
        "criterion": 3,
        "role": "human",
        # human_01, human_02, human_03: the first three human texts by id. They
        # happen to be the casual, messy group in the calibration set. They are
        # AI-written imitations of human writing.
        "texts": [_cal(f"human_0{n}") for n in (1, 2, 3)],
    },
    {
        "name": "labels: borderline",
        "criterion": 3,
        "role": "borderline",
        # ai_edited_01 to ai_03: AI text with light human edits, the kind of
        # text neither a person nor a detector can place. Taken by id order.
        "texts": [_cal(f"ai_edited_0{n}") for n in (1, 2, 3)],
    },
    # ── Criterion 4: an appeal always changes status and is recorded ────────
    {
        "name": "appeals",
        "criterion": 4,
        "appeal": True,
        # Five submissions, each then appealed: own_06 to own_10 (the last five
        # pieces by id). Plus one id that was never issued, which must be a 404
        # and must not write an under_review entry.
        "texts": [_own(n) for n in range(6, 11)],
        "unknown_ids": ["00000000-0000-0000-0000-000000000000"],
    },
    # ── Criterion 5: bad input never crashes the service ────────────────────
    {
        "name": "bad input",
        "criterion": 5,
        # The eight bodies named in criteria.md, in that order.
        "bodies": [
            {"creator_id": "eval_bad_1"},                                    # text missing
            {"text": "", "creator_id": "eval_bad_2"},                        # text empty
            {"text": "   \n\t  ", "creator_id": "eval_bad_3"},              # whitespace only
            {"text": None, "creator_id": "eval_bad_4"},                      # text null
            {"text": 12345, "creator_id": "eval_bad_5"},                     # text a number
            {"text": _NINETEEN, "creator_id": "eval_bad_6"},                 # 19 words
            {"text": "word " * 50_000, "creator_id": "eval_bad_7"},          # 50,000 words
            {"text": _GOOD},                                                 # creator_id missing
        ],
        "expect": [400, 400, 400, 400, 400, 400, 413, 400],
    },
]


def validate() -> list[str]:
    """
    Complain about anything malformed, before a long run rather than during.

    A "bodies" scenario is deliberately exempt from the empty check — an empty
    string is the whole point of a bad-input case, and refusing to run one
    would make that criterion untestable.
    """
    problems = []
    for i, scenario in enumerate(SCENARIOS, 1):
        if not scenario.get("name"):
            problems.append(f"scenario {i} has no name")

        texts = scenario.get("texts")
        bodies = scenario.get("bodies")

        if texts and bodies:
            problems.append(
                f"scenario {i} ('{scenario.get('name')}') has both texts and "
                f"bodies — pick one"
            )
            continue

        if bodies:
            for j, body in enumerate(bodies, 1):
                if not isinstance(body, dict):
                    problems.append(
                        f"scenario {i}, body {j} is not a dict — bodies are whole "
                        f"request bodies, like {{'text': '', 'creator_id': 'x'}}"
                    )
            continue

        if not texts:
            problems.append(f"scenario {i} has no texts and no bodies")
            continue

        for j, text in enumerate(texts, 1):
            if not str(text).strip():
                problems.append(
                    f"scenario {i}, text {j} is empty — if an empty submission is what "
                    f"you're testing, use 'bodies' instead of 'texts'"
                )
            elif str(text).startswith("REPLACE ME"):
                problems.append(
                    f"scenario {i} ('{scenario.get('name')}'), text {j} is still "
                    f"the placeholder"
                )
    return problems
