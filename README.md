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
2. **The route validates.** `text` must be a string of at least 20 words and at most 20,000 characters, and `creator_id` must be non-blank. Bad input gets a 400 or 413 and a logged rejection. This step adds a clean input.
3. **Signal one (`detector.py`).** A local gpt2 model reads up to 400 tokens and measures how predictable the text is. If the model can't load, the route answers 503 and logs a rejection. This step adds `model_score`.
4. **Signal two (`stylometry.py`).** Measures the shape of the text: sentence-length spread, vocabulary repetition, punctuation density. This step adds `style_score`.
5. **Combine (`scoring.py::combine_signals`).** One rule, leaning toward whichever signal reads more human, turns the two scores into a single `combined_score` from 0 (human) to 1 (AI).
6. **Label (`scoring.py::score_to_label`).** Below 0.30 is "human", 0.85 and above is "AI", and everything between is "unsure". Each maps to a short plain-language message. `score_to_label` adds `guess` and `label`, and `scoring.py::confidence_for` adds `confidence`.
7. **Log and answer.** The submission gets a new `content_id`, `audit.log_decision` writes all nine fields with status `decided`, and the response goes back to the caller. If the writer asks for a review, `POST /appeal` checks the `content_id` exists and appends an `under_review` entry beside the original decision, filed under the original writer.

---

## Signals and Scoring

<!-- For each signal: what property it measures, why that might differ between
     human and AI writing, and WHAT IT CAN'T SEE.

     The blind spot is not optional. If you can't name it you don't understand
     the signal yet — and unit 8's attack set is built out of blind spots. -->

### Signal one — the model signal

**What it measures:** how predictable the text is to a small language model (gpt2) running on my own machine, as perplexity, squashed to a 0–1 score where higher means more likely AI. The squash is the starter's, unchanged: perplexity 45 scores 0.5, lower perplexity scores higher, and a steepness of 1.6 sets how fast it moves either side of 45.

**Why that might differ between human and AI writing:** a language model writes by choosing likely next words, so its output is easy for a model to predict. Human writing wanders more: odd word choices, specific details, abrupt turns.

**What it can't see:** who wrote it. Predictability is not authorship. It rewards common words in short, ordinary sentences, so a second-language writer, a younger writer, or anyone writing plainly scores about as machine-like as a machine does. Dense, rare-word prose scores as human, so AI text padded with rare words can slip through. It also reads only the first 400 tokens.

### Signal two — the style signal

**What it measures:** the shape of the text without reading it: how much sentence length varies, how much of the vocabulary repeats, and how much punctuation there is.

**Why that might differ between human and AI writing:** generated prose tends toward even, mid-length sentences and a narrower vocabulary. Human prose is lumpier, with a three-word sentence next to a forty-word one.

**What it can't see:** what the text says. Typos, broken-up sentences, or a pasted quotation change the shape without changing who wrote it, and that is cheap to do on purpose. Longer text repeats more of its words, so the share of new words falls with length; I measure it over 50-word windows to soften that, but short and long texts still aren't perfectly comparable. Most of all, a plain human writer with even sentences looks AI-shaped here too. In testing, this signal turned out to measure how even and simple the writing is, not who wrote it (see the numbers below).

### The combining rule

<!-- Write the rule in words, then give the numbers. What happens when the two
     signals disagree? -->

**The rule:** lean human. The combined score is three quarters of the lower of the two scores plus one quarter of the higher. Both signals have to read AI for the result to read AI. If either one reads human, the result is pulled toward human. When the two agree, the result is that same value.

I chose this because a false accusation costs a writer more than a missed AI text costs me, and because signal one scores plain human writing as AI-like, so a plain average over-trusts it.

**The numbers:**

- `config.LOWER_SIGNAL_WEIGHT = 0.75`, so `combined = 0.75 * lower + 0.25 * higher`.
- Inside the style signal (`stylometry.py`), three measures are flipped so higher means AI, rescaled to 0–1 between two anchor values, then weighted: sentence-length spread 0.60, type-token ratio 0.25 (over 50-word windows), punctuation density 0.15 (commas, semicolons, colons, round brackets, double quotes, en and em dashes; full stops, hyphens and apostrophes excluded).
- The anchors (the raw value that counts as fully human and fully AI) are rough. The first version came from six short calibration paragraphs (the table below). A separate agent then wrote 24 texts (16 genuine AI, 8 imitation human). I re-fit the sentence-length anchors (human end 0.60, AI end 0.25) on half of them and checked the other half. The type-token anchors (0.90 human, 0.70 AI) and punctuation anchors (0.15 human, 0.03 AI, in marks per word) were not re-fit.

Six paragraphs written for calibration (not real writers' work), scored with the current constants. Combined is computed from the unrounded signal scores, so redoing the formula on the rounded numbers can be off in the last digit.

| Text | Signal one | Signal two | Combined |
|---|---|---|---|
| Clearly AI | 0.809 | 0.688 | 0.719 |
| Clearly human (narrative) | 0.303 | 0.103 | 0.153 |
| Plain human (short, even sentences) | 0.819 | 0.765 | 0.778 |
| Lightly edited AI | 0.601 | 0.631 | 0.609 |
| Plain human, uneven sentence lengths | 0.797 | 0.315 | 0.435 |
| AI padded with rare words | 0.143 | 0.750 | 0.295 |

Clearly AI and clearly human land 0.566 apart on these. On the agent's 24 texts the held-out half (12 texts, not used to set the anchors) moved only a little after the re-fit: ordinary AI went from a mean style score of 0.501 to 0.528, messy human stayed low (0.123), and no group changed label. A wider anchor setting I tried first (human end 0.45) pushed some AI text into the human label on both halves, so I dropped it.

What the 24 texts show that I did not want:

- **Plain, even writing scores AI on both signals.** All three plain human imitations scored 0.79–0.80 combined, about as high as plain AI (0.77–0.91) and well above ordinary AI (mean 0.61). The combining rule cannot help when both signals agree, so that writer would be accused. The label thresholds are the only protection left; see Label Variants.
- **Signal two measures evenness and simplicity, not authorship.** Ordinary AI and formal human writing both score near the middle on it. It cleanly separates only messy, lumpy writing from the rest.
- **Type-token ratio and punctuation density do not separate AI from human at 100–250 words.** They only pick out plain, simple text. Sentence-length spread does most of the work.
- **Ordinary AI text lands in the middle.** All eight ordinary AI texts scored 0.49–0.73 combined, so with the final thresholds (Label Variants) every one of them is "unsure".

The human texts in that set were written by an AI imitating human writing, and each group has only two to four texts, so treat these as a stress test, not a measurement.

**Reproducing these numbers.** The 24 texts and the six calibration paragraphs are committed in `samples/calibration/`, with their groups and the train/holdout split in `manifest.json`. `python calibrate.py` prints the per-text and per-group tables from the current code and `config.py` (add `--live` to re-score signal one with the model, `--split holdout` for the held-out half). `python calibrate.py --check` fails if any style score, combined score or label has moved from `results/calibration_baseline.json`, and `python -m pytest` runs the same check, so a change to `stylometry.py` cannot silently shift every score.

**Where it lives:** `scoring.py::combine_signals`

<!-- ⚠️ The grader checks your code against that line. If your rule lives
     somewhere else, say where. -->

**A case where my two signals split, and what my rule does with it:**

A short paragraph of AI-style text padded with rare words ("Contemporary epistemological frameworks increasingly emphasize multifaceted heuristics…"). Signal one reads it as human (0.143), because rare words are hard for gpt2 to predict. Signal two reads it as AI-shaped (0.750), because the sentences are all about the same length. The rule gives 0.75 × 0.143 + 0.25 × 0.750 = 0.295, which is on the human side. That is the price of leaning human: padded AI text gets through.

The reverse split is a plain human paragraph with very uneven sentence lengths: signal one 0.797, signal two 0.315, combined 0.435. A plain average would give 0.556. The rule moves it toward human, but it is still in the middle, not clearly human.



---

## Label Variants

<!-- The exact text of all three labels, as a reader would see them, and the
     score range each covers.

     Write them for someone who has never heard the word "threshold". -->

| Label | Score range | The exact text a reader sees |
|---|---|---|
| high-confidence human | 0.00 – 0.30 (below 0.30) | We think this was probably written by a person. |
| unsure | 0.30 – 0.85 (from 0.30 up to, not including, 0.85) | We can't tell whether this was written by a person or by an AI tool. This is not a finding against you: our check often can't tell, and many people's own writing gets this result. If you'd like a person to read it, you can ask for a review. |
| high-confidence AI | 0.85 – 1.00 (0.85 and above) | Our check thinks this may have been mostly written by an AI tool, though spell-check and grammar tools don't count. It is often wrong, especially on plain writing by people, and this is not a final decision. Anyone can ask for a review, and a person will read it. |

The score is the combined score from the rule above.

All three labels are reachable. The three request bodies are committed in `samples/`: a messy personal paragraph, an ordinary AI paragraph and a plain AI paragraph, all written by an AI for testing. These were run on the live service; the responses are cut to the scoring fields (the full shape is in Sample Run). I restored the audit log afterwards so it holds only the Sample Run below.

```
$ curl -s -X POST http://127.0.0.1:5000/submit -H "Content-Type: application/json" -d @samples/human_messy.json
{"guess": "human", "confidence": 0.8492, "model_score": 0.3976, "style_score": 0.0685, "combined_score": 0.1508}
$ curl -s -X POST http://127.0.0.1:5000/submit -H "Content-Type: application/json" -d @samples/ai_ordinary.json
{"guess": "unsure", "confidence": 0.5117, "model_score": 0.6961, "style_score": 0.419, "combined_score": 0.4883}
$ curl -s -X POST http://127.0.0.1:5000/submit -H "Content-Type: application/json" -d @samples/ai_plain.json
{"guess": "ai", "confidence": 0.9045, "model_score": 0.8858, "style_score": 0.9605, "combined_score": 0.9045}
```

`confidence` is how sure the service is of its own guess. For "human" it is 1 minus the combined score, for "AI" it is the combined score, and for "unsure" it is whichever side the score leans to. So "unsure" with confidence 0.80 means it leans AI but not far enough to say so.

The AI label is rare by design. Most AI text, and all the plain human text I tested, lands in "unsure". The 0.85 line is only 0.05 above the highest plain human text I tried (0.80), and those texts were imitations written by an AI, so a real plain writer could cross it.

**Why I worded the "unsure" one this way:**

The person reading it may have written every word themselves. So it says first that we don't know, and then says outright that this is "not a finding against you." I had a fresh reader go through my first draft as the writer. They said my line about plain, simple writing sounded like a mild insult, and "nothing has been decided about you" sounded like a decision was coming, so both went. It says "AI tool" rather than "AI", and "ask for a review" rather than "appeal", which sounded like a court. It still tells the reader what they can do next.

The AI label got the same treatment. My first draft said "If you wrote it yourself", which the same reader heard as doubt and as putting the burden of proof on them. It now says anyone can ask for a review, that spell-check and grammar tools don't count, and that the check is often wrong on plain writing by people.

---

## Sample Run

<!-- One submission and one appeal, pasted as text: the request, the response,
     and the log entries. -->

**A submission**

<!-- The response needs content_id, guess, confidence, label, AND both
     signal scores - model_score and style_score. Unit 8's tools read those
     two off the response, so leaving them out costs you next unit's
     diagnostics. -->

The text is a plain, simple paragraph of the kind a younger or second-language writer might write. An AI wrote it as a test imitation, so it is not a real writer's work. It scores high on both signals and lands in "unsure".

```bash
$ curl -X POST http://127.0.0.1:5000/submit \
  -H "Content-Type: application/json" \
  -d '{"text": "Our school has a garden. It is behind the main building. Every spring the students plant vegetables there. This year our class planted carrots, beans and tomatoes. We worked in groups of four. My group planted the beans.\n\nFirst we dug the soil. It was hard work and our hands got dirty. Then we put the seeds in small holes. We gave them water every day. After two weeks the beans were growing. I was very happy to see them.\n\nThe teacher said that plants need sun and water to grow. She also said that gardens help the bees. I did not know this before. Now I want to have a garden at my house too. My grandmother has a small yard, so I will ask her. I think it is a good idea. Plants make the world beautiful and we can eat them too.", "creator_id": "demo_writer"}'
```

```json
{
    "combined_score": 0.7957,
    "confidence": 0.7957,
    "content_id": "3f583ab5-c278-4e77-a7ee-fe49cc6af854",
    "guess": "unsure",
    "label": "We can't tell whether this was written by a person or by an AI tool. This is not a finding against you: our check often can't tell, and many people's own writing gets this result. If you'd like a person to read it, you can ask for a review.",
    "model_score": 0.7975,
    "status": "decided",
    "style_score": 0.7951
}
```

**An appeal**

The reasoning is written as the imagined writer of that paragraph might put it.

```bash
$ curl -X POST http://127.0.0.1:5000/appeal \
  -H "Content-Type: application/json" \
  -d '{"content_id": "3f583ab5-c278-4e77-a7ee-fe49cc6af854", "reasoning": "I wrote this myself. English is my second language, and I write short, simple sentences."}'
```

```json
{
    "content_id": "3f583ab5-c278-4e77-a7ee-fe49cc6af854",
    "message": "Your review request is recorded. A person will read it.",
    "status": "under_review"
}
```

**What the log shows afterwards**

```bash
$ curl "http://127.0.0.1:5000/log?limit=2"
```

*The first entry is the original decision, unchanged. The second is the appeal, filed under the same writer and `content_id`, with status `under_review`.*

```json
{
    "count": 2,
    "entries": [
        {
            "combined_score": 0.7957,
            "content_id": "3f583ab5-c278-4e77-a7ee-fe49cc6af854",
            "creator_id": "demo_writer",
            "guess": "unsure",
            "label": "We can't tell whether this was written by a person or by an AI tool. This is not a finding against you: our check often can't tell, and many people's own writing gets this result. If you'd like a person to read it, you can ask for a review.",
            "model_score": 0.7975,
            "status": "decided",
            "style_score": 0.7951,
            "timestamp": "2026-11-01T04:49:27+00:00"
        },
        {
            "content_id": "3f583ab5-c278-4e77-a7ee-fe49cc6af854",
            "creator_id": "demo_writer",
            "event": "appeal",
            "reasoning": "I wrote this myself. English is my second language, and I write short, simple sentences.",
            "status": "under_review",
            "timestamp": "2026-11-01T04:49:27+00:00"
        }
    ]
}
```

---

## How I Used AI

**Moment 1 — testing the style signal**

- *What I asked for:* My first calibration used only six short paragraphs, which I didn't trust. I asked a separate Claude agent to write 24 test texts and score them with my two signals. There were 16 AI texts in different genres and 8 imitations of human writing (messy, plain and formal). I also asked it to tell me what was wrong with my style signal.
- *What came back:* A table of scores and a critique. My style signal gave ordinary AI text a middling score, because my anchors came from my own six paragraphs. It suggested re-anchoring sentence-length spread to 0.45 (human) and 0.25 (AI), and cutting the weight on type-token ratio and punctuation.
- *What I changed:* I didn't take the numbers as given. I split the 24 texts in half, tried the suggestion on one half and checked it on the other. The 0.45 anchor pushed ordinary and lightly edited AI text into the "human" label, so I rejected it. I used 0.60 / 0.25 instead, which kept every group's label and raised ordinary AI's style score a little. I kept the weight cut. In this README I also say that the agent's "human" texts are imitations, not real writers.

**Moment 2 — reading the labels as a writer**

- *What I asked for:* I gave a fresh Claude agent only my three label texts, with no explanation of the system. I asked it, as the writer, what each one says about them and what they would do next. It answered twice: once as someone who wrote every word, and once as someone who used AI. I told it not to rewrite them.
- *What came back:* The human label was fine. The unsure label was mostly reassuring, but "plain, simple writing" read as a mild insult, and "nothing has been decided about you" sounded like a decision was coming. The AI label read as an accusation with a hedge. "If you wrote it yourself" sounded like doubt and put the burden of proof on the writer. It also asked whether spell-check counts as "help of AI".
- *What I changed:* I reworded both labels myself. The unsure label now says plainly that it is "not a finding against you". The AI label drops "If you wrote it yourself", says spell-check and grammar tools don't count, and says anyone can ask for a review. Both say "ask for a review" instead of "appeal", which sounded like a court. I changed the `/appeal` confirmation to "Your review request is recorded" so the reply matches the label.

<!-- ═══════════════════════ UNIT 8 — THE TEST ═══════════════════════ -->

---

## Rate Limiting

**My limits:** 12 per minute, 30 per day

**Why those numbers and not others:**

Two people use `/submit`. A real writer sends their own work a few times in a day, and when they revise a piece they might send two or three versions inside a minute. A script sends a thousand variations of one text to find where the thresholds sit.

- **12 a minute** never gets in a writer's way, and it stops a burst: a flood of 15 gets twelve `200`s and three `429`s. On its own it would be a weak limit, because a script held to 12 a minute could still send over 17,000 a day.
- **30 a day** is the limit that does the real work. A long day of revisions fits inside it, and a script gets 30 probes per `creator_id`, which is too few to find where 0.30 and 0.85 sit. I did not go lower because a writer who hits a limit is the person the label wording is trying to protect. I did not go higher because every extra probe is one more point on the map.
- The two limits are different checks. At 12 a minute it takes three minutes of steady use to reach 30: two full minutes make 24, and the 31st submission is refused with `30 per 1 day`. The `429` says which limit it hit, so the two are easy to tell apart.

The numbers are `RATE_LIMIT_PER_MINUTE` and `RATE_LIMIT_PER_DAY` in `config.py`, with the reasoning beside them. The limiter is on by default; `AI201_RATE_LIMITS=0` switches it off.

**What a caller counts as:** the `creator_id` in the request body. When a request has no usable `creator_id` (missing, not a string, or not a JSON object) it counts against the caller's address instead, so all of those requests from one machine share one allowance.

This was a choice, and it costs something. A script that makes up a new `creator_id` for every request is never limited by the per-creator rule, so the limit stops one noisy creator and does not stop a determined caller who rotates names. A per-address limit would stop that, but it would count one household or one office as a single caller, and it would limit the whole attack set, which sends every attack under its own `creator_id`, from one address. The address fallback only covers requests that give no name at all. The counts live in memory, so a restart forgets them. Requests that are refused with a `400` still count, so a flood of bad input is limited too.

**The run of status codes when I pushed past it:**

`python run_attacks.py --flood 15` (15 submissions from one `creator_id`, written to `results/flood_2026-11-04_2132.md`):

```
200 200 200 200 200 200 200 200 200 200 200 200 429 429 429
```

The same service, one `creator_id`, three bursts of 12 submissions with a minute between them, to reach the daily limit (the third burst ran for about a second, so every request counted):

```
burst 1 (requests 1-12):  200 200 200 200 200 200 200 200 200 200 200 200
burst 2 (requests 13-24): 200 200 200 200 200 200 200 200 200 200 200 200
burst 3 (requests 25-36): 200 200 200 200 200 200 429 429 429 429 429 429   limit: 30 per 1 day
```

Request 31 is the first one refused. The log records every refusal, with the limit that caused it (one of the `429` entries from that run):

```json
{"timestamp": "2026-11-05T02:34:19+00:00", "content_id": null, "creator_id": "daycap_tester", "guess": null, "model_score": null, "style_score": null, "combined_score": null, "label": null, "status": "rejected", "event": "rejected", "reason": "rate_limited", "http_status": 429, "limit": "30 per 1 day"}
```

**The audit log.** Every entry in `logs/audit.jsonl` starts with the same nine fields in the same order: `timestamp`, `content_id`, `creator_id`, `guess`, `model_score`, `style_score`, `combined_score`, `label`, `status`. A decision fills all nine. A rejection leaves `content_id`, `guess`, the scores and `label` null, because nothing was decided, and adds `event`, `reason` and `http_status`. An appeal copies `guess`, the scores and `label` from the decision it is about, so the line says what was decided and that it is now `under_review`, without going to find the original. The Sample Run above was recorded in unit 7, before the log gained these fields, so its appeal line has the old, shorter shape.

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

       [x] criteria.md has five numbered criteria, each naming a target
       [x] Each has a reason underneath
       [x] POST /submit returns content_id, guess, confidence, label,
           model_score and style_score
       [x] Two signals that measure DIFFERENT things, each with a named blind spot
       [x] Three label variants, all reachable, written out in full
       [x] POST /appeal changes status and writes to the log
       [x] Signals and Scoring names scoring.py::combine_signals
       [x] Sample Run: a submission AND an appeal, as pasted text
       [x] At least four new commits
       [ ] Repository URL submitted — WRITE IT DOWN

     SUBMISSION CHECKLIST — unit 8

       [x] Rate limiting on /submit, with your numbers justified
       [x] The pasted run of status codes showing 429
       [x] Audit log with all nine fields, recording rejections too
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
