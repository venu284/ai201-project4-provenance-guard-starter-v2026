# Provenance Guard

> ### 👋 Start here
>
> **New to this repo? Read [RUNNING.md](RUNNING.md) first.**
>
> Once `python test.py` passes, in one terminal:
>
> ```bash
> python app.py
> ```
>
> and in another:
>
> ```bash
> curl -X POST http://127.0.0.1:5000/ping \
>   -H "Content-Type: application/json" \
>   -d '{"message": "hello"}'
> ```
>
> That's a web service. Something sent it text and it sent something back.
> Everything this unit is filling in the middle.
>
> **The rest of this file is your submission.** Fill it in as you go.

---

<!-- ─────────────────────────────────────────────────────────────────────────
     Unit 7 asks for the first five sections. Unit 8 adds the five below.

     Everything is pasted as TEXT. A pasted curl response gets full credit;
     a picture of your terminal gets none.
     ───────────────────────────────────────────────────────────────────────── -->

<!-- ═══════════════════════ UNIT 7 — THE BUILD ═══════════════════════ -->

## What This Does

<!-- The path a submission takes, from arriving to the label a reader sees.
     Six or seven steps — this is the trace you wrote in Milestone 1. -->

1. **Request arrives.** A writer or script sends `text` and `creator_id` to `POST /submit`. In unit 8 a rate limiter checks the caller first and logs a rejection if it refuses.
2. **The route validates.** `text` must be a string of at least 20 words and at most 20,000 characters, and `creator_id` must be non-blank. Bad input gets a 400 or 413 and a logged rejection. This step adds a clean input and a new `content_id`.
3. **Signal one (`detector.py`).** A local gpt2 model reads up to 400 tokens and measures how predictable the text is. This step adds `model_score`.
4. **Signal two (`stylometry.py`).** Measures the shape of the text: sentence-length spread, vocabulary repetition, punctuation density. This step adds `style_score`.
5. **Combine (`scoring.py::combine_signals`).** One rule turns the two scores into a single `combined_score` from 0 (human) to 1 (AI).
6. **Label (`scoring.py::score_to_label`).** The score is compared to two thresholds and mapped to one of three sentences. This step adds `guess`, `label` and `confidence`.
7. **Log and answer.** `audit.log_decision` writes all nine fields with status `decided`, and the response goes back to the caller. If the writer disagrees, `POST /appeal` appends an `under_review` entry for the same `content_id`.

---

## Signals and Scoring

<!-- For each signal: what property it measures, why that might differ between
     human and AI writing, and WHAT IT CAN'T SEE.

     The blind spot is not optional. If you can't name it you don't understand
     the signal yet — and unit 8's attack set is built out of blind spots. -->

### Signal one — the model signal

**What it measures:** how predictable the text is to a small language model (gpt2) running on my own machine, as perplexity, squashed to a 0–1 score where higher means more likely AI.

**Why that might differ between human and AI writing:** a language model writes by choosing likely next words, so its output is easy for a model to predict. Human writing wanders more: odd word choices, specific details, abrupt turns.

**What it can't see:** who wrote it. Predictability is not authorship. It rewards common words in short, ordinary sentences, so a second-language writer, a younger writer, or anyone writing plainly scores about as machine-like as a machine does. Dense, rare-word prose scores as human, so AI text padded with rare words can slip through. It also reads only the first 400 tokens.

### Signal two — the style signal

**What it measures:** the shape of the text without reading it: how much sentence length varies, how much of the vocabulary repeats, and how much punctuation there is.

**Why that might differ between human and AI writing:** generated prose tends toward even, mid-length sentences and a narrower vocabulary. Human prose is lumpier, with a three-word sentence next to a forty-word one.

**What it can't see:** what the text says. Typos, broken-up sentences, or a pasted quotation change the shape without changing who wrote it, and that is cheap to do on purpose. Vocabulary repetition also falls as text gets longer, so short and long texts are not directly comparable, and a plain human writer with even sentences looks AI-shaped here too.

### The combining rule

<!-- Write the rule in words, then give the numbers. What happens when the two
     signals disagree? -->

**The rule:** lean human. The combined score is three quarters of the lower of the two scores plus one quarter of the higher. Both signals have to read AI for the result to read AI. If either one reads human, the result is pulled toward human. When the two agree, the result is that same value.

I chose this because a false accusation costs a writer more than a missed AI text costs me, and because signal one scores plain human writing as AI-like, so a plain average over-trusts it.

**The numbers:**

- `config.LOWER_SIGNAL_WEIGHT = 0.75`, so `combined = 0.75 * lower + 0.25 * higher`.
- Inside the style signal (`stylometry.py`), three measures are flipped so higher means AI, rescaled to 0–1 between two anchor values, then weighted: sentence-length spread 0.40, type-token ratio 0.35 (over 50-word windows), punctuation density 0.25 (commas, semicolons, colons, dashes, brackets, quotes; full stops excluded).
- The anchors (the raw value that counts as fully human and fully AI) are rough. I set them from a handful of my own paragraphs, so they are not tested yet.

Six paragraphs I wrote or generated for calibration (not real writers' work):

| Text | Signal one | Signal two | Combined |
|---|---|---|---|
| Clearly AI | 0.809 | 0.547 | 0.613 |
| Clearly human (narrative) | 0.303 | 0.189 | 0.218 |
| Plain human (short, even sentences) | 0.819 | 0.752 | 0.768 |
| Lightly edited AI | 0.601 | 0.480 | 0.510 |
| Plain human, uneven sentence lengths | 0.797 | 0.471 | 0.553 |
| AI padded with rare words | 0.143 | 0.627 | 0.264 |

Clearly AI and clearly human land 0.395 apart. Two things this table shows that I did not want:

- **Plain, even writing scores AI on both signals** (0.768). The combining rule cannot help when both signals agree, so that writer would be accused. The label thresholds in Milestone 5 are the only protection left.
- **Type-token ratio does not separate AI from human at 50–90 words.** Both sample texts sit at about 0.9, so that measure only moves for repetitive text. Punctuation density also barely separates them. Sentence-length spread does most of the work.

**Where it lives:** `scoring.py::combine_signals`

<!-- ⚠️ The grader checks your code against that line. If your rule lives
     somewhere else, say where. -->

**A case where my two signals split, and what my rule does with it:**

A short paragraph of AI-style text padded with rare words ("Contemporary epistemological frameworks increasingly emphasize multifaceted heuristics…"). Signal one reads it as human (0.143), because rare words are hard for gpt2 to predict. Signal two reads it as AI-shaped (0.627), because the sentences are all about the same length. The rule gives 0.75 × 0.143 + 0.25 × 0.627 = 0.264, which is on the human side. That is the price of leaning human: padded AI text gets through.

The reverse split is a plain human paragraph with very uneven sentence lengths: signal one 0.797, signal two 0.471, combined 0.553. A plain average would give 0.634, close to an accusation. The rule puts it in the middle instead.



---

## Label Variants

<!-- The exact text of all three labels, as a reader would see them, and the
     score range each covers.

     Write them for someone who has never heard the word "threshold". -->

| Label | Score range | The exact text a reader sees |
|---|---|---|
| high-confidence human |  |  |
| unsure |  |  |
| high-confidence AI |  |  |

**Why I worded the "unsure" one this way:**
<!-- It's the hardest of the three. It has to admit uncertainty without
     sounding like an accusation, because the person reading it may well have
     written every word themselves. -->



---

## Sample Run

<!-- One submission and one appeal, pasted as text: the request, the response,
     and the log entries. -->

**A submission**

<!-- The response needs content_id, guess, confidence, label, AND both
     signal scores - model_score and style_score. Unit 8's tools read those
     two off the response, so leaving them out costs you next unit's
     diagnostics. -->

```bash
$ curl -X POST http://127.0.0.1:5000/submit \
  -H "Content-Type: application/json" \
  -d '{"text": "My grandmother kept a jar of buttons she never used, and every time I visited she tipped it onto the kitchen table so I could sort them by colour. Half were from coats long gone. One, a brass thing with an anchor, she swore came off my grandfather'"'"'s navy jacket, though Dad says he never served.", "creator_id": "demo_writer"}'
```

*Milestone 3 state: only signal one is wired in, so `guess`, `confidence` and `style_score` are `null` and `label` is a placeholder. These are filled in at Milestones 4 and 5.*

```json
{
    "confidence": null,
    "content_id": "2316d85d-47fa-4709-a49b-a03a1571c2a6",
    "guess": null,
    "label": "PLACEHOLDER — the real label comes in Milestone 5",
    "model_score": 0.2276,
    "status": "decided",
    "style_score": null
}
```

**An appeal**

```bash
$ curl -X POST http://127.0.0.1:5000/appeal \
  -H "Content-Type: application/json" \
  -d '{"content_id": "...", "reasoning": "..."}'
```

```json

```

**What the log shows afterwards**

```bash
$ curl "http://127.0.0.1:5000/log?limit=3"
```

*The middle entry is a submission of three words that the route refused.*

```json
{
    "count": 3,
    "entries": [
        {
            "combined_score": null,
            "content_id": "2316d85d-47fa-4709-a49b-a03a1571c2a6",
            "creator_id": "demo_writer",
            "guess": null,
            "label": null,
            "model_score": 0.2276,
            "status": "decided",
            "style_score": null,
            "timestamp": "2026-10-31T19:30:49+00:00"
        },
        {
            "creator_id": "demo_writer",
            "event": "rejected",
            "reason": "bad_input",
            "status": "rejected",
            "timestamp": "2026-10-31T19:30:49+00:00"
        },
        {
            "combined_score": null,
            "content_id": "b83e6edd-e35f-4856-8dd7-1950978e47cc",
            "creator_id": "demo_writer",
            "guess": null,
            "label": null,
            "model_score": 0.8504,
            "status": "decided",
            "style_score": null,
            "timestamp": "2026-10-31T19:30:49+00:00"
        }
    ]
}
```

---

## How I Used AI

**Moment 1**

- *What I asked for:*
- *What came back:*
- *What I changed:*

**Moment 2**

- *What I asked for:*
- *What came back:*
- *What I changed:*

<!-- ═══════════════════════ UNIT 8 — THE TEST ═══════════════════════ -->

---

## Rate Limiting

**My limits:** ___ per minute, ___ per day

**Why those numbers and not others:**
<!-- Think about two people: a real writer submitting their own work a few
     times an hour, and a script sending a thousand variations to map your
     thresholds. Your numbers have to be liveable for the first and hostile to
     the second. -->

**What a caller counts as:** <!-- per address, or per creator_id? They fail
differently — one script can look like a thousand callers, and one household
can look like one. -->

**The run of status codes when I pushed past it:**

<!-- python run_attacks.py --flood 15 -->

```

```

---

## Attack Run — Before

<!-- Every attack with its outcome and a held-or-broke mark.
     `run_attacks.py --label before` produces the table. -->



**Ten audit log entries from the run**

<!-- Choose entries that show the interesting failures, not the ten easiest. -->

```json

```

**The single worst outcome** — the one I'd least want to explain to a writer
whose work got caught by it:



---

## Run Log and Verdicts

<!-- Your five criteria across three trials. `run_eval.py --label before`. -->

| Criterion | Target | Run 1 | Run 2 | Run 3 | Verdict |
|---|---|---|---|---|---|
| 1.  |  |  |  |  |  |
| 2.  |  |  |  |  |  |
| 3.  |  |  |  |  |  |
| 4.  |  |  |  |  |  |
| 5.  |  |  |  |  |  |

**Real output from one trial**, pasted as text, naming the file and function
that produced it:

```json

```

**Diagnoses**

<!-- For each miss AND each broken attack: the stage and the mechanism.

     Your service has five stages: the route, signal one, signal two, the
     combining rule, and the label mapping.

     Not a diagnosis:  "The evasion attacks got through."
     A diagnosis:      "Four evasion inputs got through. All four had typos
                        added to AI-generated text. My second signal measures
                        word variety, and typos raise word variety — so it read
                        them as more human. My combining rule weights that
                        signal at 0.6, so it dragged the whole score down."

     Look for a pattern. Five failures on one signal is one problem, not five. -->



---

## The Improvement

**What I changed:**

**Which diagnosis pointed at it:**

### Attack Run — After

<!-- Same format. `run_attacks.py --label after` -->



**Did it help, and how do I know:**

<!-- Widening the unsure band usually fixes one problem and creates another.
     Reporting that trade honestly is worth full credit. -->



---

## What's Still Broken

<!-- For each attack still getting through and each criterion still missed:
     what you'd do, and why you stopped. -->



**The trade I'd make if this ran for real:**

<!-- Two sentences. Fewer wrong accusations means more AI text getting through.
     Say which way you'd go and WHO PAYS FOR IT. -->



<!-- ═════════════════════════════════════════════════════════════════════

     SUBMISSION CHECKLIST — unit 7

       [ ] criteria.md has five numbered criteria, each naming a target
       [ ] Each has a reason underneath
       [ ] POST /submit returns content_id, guess, confidence, label,
           model_score and style_score
       [ ] Two signals that measure DIFFERENT things, each with a named blind spot
       [ ] Three label variants, all reachable, written out in full
       [ ] POST /appeal changes status and writes to the log
       [ ] Signals and Scoring names scoring.py::combine_signals
       [ ] Sample Run: a submission AND an appeal, as pasted text
       [ ] At least four new commits
       [ ] Repository URL submitted — WRITE IT DOWN

     SUBMISSION CHECKLIST — unit 8

       [ ] Rate limiting on /submit, with your numbers justified
       [ ] The pasted run of status codes showing 429
       [ ] Audit log with all nine fields, recording rejections too
       [ ] The attack set run IN FULL, every input with an outcome
       [ ] Ten audit log entries pasted as text
       [ ] Five criteria across three trials
       [ ] A diagnosis for every miss and every broken attack — stage AND mechanism
       [ ] One improvement, with Attack Run — After
       [ ] What's Still Broken, including the production trade
       [ ] At least four new commits
       [ ] The SAME repository URL as last unit

     Do not delete and recreate this repository.
     ═════════════════════════════════════════════════════════════════════ -->

---

📖 **How to run this project: [RUNNING.md](RUNNING.md)**
