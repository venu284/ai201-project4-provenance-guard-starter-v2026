# Acceptance criteria — Provenance Guard

Five criteria that say what "working" means for this service, written in unit 7
**before** you built it.

**All five are yours.** None are given.

An acceptance criterion names a number or something plainly observable. *"The
detector is accurate"* is an opinion — and perfect AI detection isn't possible
anyway, so it's an opinion about something nobody can deliver. *"Of 10 pieces I
wrote myself, at most 1 is labelled high-confidence AI"* is a criterion.

Under each, write a sentence or two on **why that target**. *"I allow at most 1
false positive in 10 because on a writing site a wrong accusation costs more
than a missed detection"* is a real answer.

> Missing your own targets next unit costs you nothing. Setting a target so
> easy you can't miss it does.

---

## Pick numbers you can defend

**Cover at least three of these five areas.** They're prompts, not a form.

| Area | A question it could answer |
|---|---|
| False positives | How often may a human's writing get called AI? |
| Score spread | How far apart should clearly-AI and clearly-human text score? |
| Label coverage | Is every one of your three labels actually reachable? |
| The appeal path | Does an appeal always change status and always get recorded? |
| Bad input | What happens when `text` is missing, empty, or enormous? |

Two things worth knowing before you pick numbers:

- **The expensive mistake is one-sided.** Missing some AI text costs the site a
  little. Accusing a real writer costs that person a lot. A criterion that
  treats both errors as equally bad is describing a system nobody would ship.
- **Unit 8 tests across three trials, and the target has to hold across all
  three.** Your first signal runs a model, so identical input can score
  differently twice. A target of "at most 1 in 10" against trials of 2, 1, 2 is
  a **miss**.

---
**Definitions used below**

- **Trial:** one full `run_eval.py` run against a freshly started service, using the same frozen inputs every time.
- **Frozen:** written down and committed before the first run, and not changed after any score is seen.
- **Labels:** the `guess` field takes the values `"human"`, `"unsure"` and `"ai"`. "High-confidence AI" means `guess == "ai"`.
- **Plain writing:** mean sentence length under 12 words, using common words.
- **Rejection entry:** an audit log entry with `event: "rejected"` and a `reason`.
- **Input limits:** `text` must be at least 20 words and at most 20,000 characters.

---

## 1. False positives on my own writing

Of 10 pieces I wrote myself, at most 1 gets `guess == "ai"` in every one of the three trials. Three of the ten are plain writing as defined above. The ten are frozen before the first run.

**Why this target:**

On a writing site a wrong accusation costs the writer far more than a missed detection costs the site, so I allow 10% at most. The three plain pieces are there because signal one is known to score plain writing as machine-like; a set made only of my ornate prose would make this target easy to hit, and an easy target tells me nothing.

---

## 2. Clearly-AI and clearly-human text score far apart

The mean `combined_score` of 5 texts I am confident are AI-generated is at least 0.30 higher than the mean of 5 texts I am confident a person wrote, in every one of the three trials. The ten texts are frozen before the first run, and `scenarios.py` will list them with the reason I chose each.

**Why this target:**

0.30 is the smallest gap I would call "far apart". A gap under 0.30 means the two groups overlap so much that no pair of thresholds can separate them. The gap is a floor, not a guarantee: the labels themselves come from `HUMAN_THRESHOLD` and `AI_THRESHOLD` in `config.py`, and criterion 3 is the one that checks all three labels can be reached.

> **Correction, unit 8:** this paragraph first said 0.30 was "the width of the unsure band (0.35 to 0.65)". Those band numbers were a unit 7 draft and never matched the shipped thresholds. The target of 0.30 is unchanged. Only the reasoning under it was wrong. The thresholds are now cited from `config.py` instead of copied here, and `tests/test_docs_match_config.py` fails if a document quotes a threshold that differs from `config.py`.

---

## 3. All three labels are reachable

Across 9 inputs (3 clearly AI, 3 clearly human, 3 borderline), all three labels appear at least once, and at least 2 of the 3 borderline inputs get the unsure label, in every one of the three trials. The nine inputs are frozen before the first run, and `scenarios.py` will list which texts I judged borderline and why.

**Why this target:**

A label no score can produce is a design bug, not a setting. Requiring borderline text to land in "unsure" checks that the middle label means something and is not just a leftover gap between two thresholds.

---

## 4. An appeal always changes status and always gets recorded

For 5 submissions, each followed by an appeal on its `content_id`: all 5 appeals return 200 with a top-level `status` of `"under_review"` and add exactly one new entry to the audit log, carrying the same `content_id` and `status: "under_review"`. The entry written by the original submission does not count as new. An appeal with a `content_id` that was never issued returns 404 and writes no `under_review` entry. Unit 8 will say whether I extended `scenarios.py` for this or tested it by hand.

**Why this target:**

The appeal is the only thing between a wrong accusation and nothing at all, so it has to work every time, not usually. The 404 half guards the most common silent failure: a mistyped id that looks like a broken endpoint.

---

## 5. Bad input never crashes the service

Eight bad submissions each return the listed code, none returns a 500, and each adds one rejection entry to the audit log. The eight: `text` missing, `text` empty, `text` whitespace only, `text` null, and `text` a number instead of a string (all 400); a 19-word text, under the 20-word minimum (400); a 50,000-word text, over the 20,000-character cap (413); and `creator_id` missing (400).

**Why this target:**

A crash on malformed input is one of the most common real failures, and one 500 already means the route trusts its input. The log requirement is there because a rejected request that leaves no trace looks identical to a quiet afternoon, and an attack that shows up only as an absence can never be diagnosed.

---

<!-- ─────────────────────────────────────────────────────────────────────────
     UNIT 8 — read this before you change anything above.

     If a criterion turns out to be BROKEN rather than merely unmet, you can
     revise it, and that earns credit. But never delete or edit the original
     line. Add the revision underneath, like this:

         ## 2. Uncertain cases land in the unsure band

         The system handles uncertain cases well.

         **Why this target:** ...

         > **Revised in unit 8:** Text I judged borderline scores between
         > 0.4 and 0.6 in at least 4 of 5 cases.
         >
         > **Why revised:** "well" gave me nothing to check. I couldn't
         > reach a verdict from it at all.

     That's a revision because the criterion couldn't be MEASURED.

     Lowering a target because you missed it is not a revision, and it costs
     you the point:

         ✗ "At most 1 of 10 of my own pieces flagged as AI" → "at most 3
            of 10", because 1 of 10 turned out to be hard.

     A number you missed stays where it is, gets diagnosed, and gets a fix
     attempted. That's where the points are.
     ───────────────────────────────────────────────────────────────────────── -->
