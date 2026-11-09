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
- Inside the style signal (`stylometry.py`), three measures are flipped so higher means AI, rescaled to 0–1 between two anchor values, then weighted: sentence-length spread 0.60, type-token ratio 0.25 (over 50-word windows), punctuation density 0.15 (commas, semicolons, colons, round brackets, double quotes, en and em dashes; full stops, hyphens and apostrophes excluded). Since the unit 8 attack run, sentences under 3 words (fragments like "Really.") are left out of the sentence-length spread (`stylometry.py::SPREAD_MIN_SENTENCE_WORDS`); the calibration table below was measured before that change.
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

I ran the staff attack set once against the service exactly as it stood after Milestone 1 (rate limiting on, nine-field log, nothing else changed): `python run_attacks.py --set attack_set --label before`. It is 56 requests from two files: 32 texts in `attacks.csv` (10 evasion, 8 false positive, 6 prompt injection, 8 malformed) and 24 requests in `attacks_malformed_requests.csv` (12 malformed, 12 from one creator). The reports are `results/attack_run_2026-11-04_2156_before.md` and `results/attack_run_2026-11-04_2156_before_flood_replay.md`; the verdicts are `results/attack_verdicts_before.md`.

**How I decided held or broke.** The run script only marks a crash on its own, so I wrote one rule per family in `attack_verdicts.py` and committed it before sending anything (`0a47c2c`).

- **Evasion** (AI text trying to read as human): broke if the label is "human". "Unsure" counts as held, because a confident human verdict is what fooled the service, and this service sends most AI text to "unsure" on purpose.
- **False positive** (real writing made to look machine-made): broke if the label is "ai", which is a writer accused.
- **Prompt injection:** broke if the label text is not one of the three fixed texts, or the log holds more or different than one clean entry. A "human" label was left for me to judge, because it is wrong only if the text was AI-written.
- **Malformed:** held only if the answer is a 4xx and the log has a rejection entry for it. Any 500, crash or non-JSON answer is broke in every family.
- **Flood rows:** held if the limiter behaved as configured, not 429 within 12 a minute and 429 beyond it.

Two things were settled after I saw the results, and both are in the commit history. The first-pass verdicts, with the rules as first written, are kept in `results/attack_verdicts_before_as_frozen.md`.

- **PI01 and PI02** were left to judge. Both are the stock AI paragraph behind an instruction ("Ignore all previous instructions…", "SYSTEM: provenance check bypassed…") and both got the human label, so I marked both broke.
- **The flood rule was amended.** The twelve flood rows share a 9-word body, under the route's 20-word minimum, so every one got 400 where my rule expected 200, and the unamended rule marked all twelve broke: 15 broke in all, counting the replay below. A 400 within the limit is the route refusing a short text, and the limiter still counted those requests. I sent the same twelve again within the same minute and all twelve came back 429 (`FL01_01` to `FL01_12`, "12 per 1 minute"), so I amended the rule to accept a refusal within the limit. That came from reading the input, not from a score. The replay is a supplement and is not counted in the 56.

**Result: 56 attacks, 51 held, 5 broke.**

| Family | Attacks | Held | Broke |
|---|---|---|---|
| evasion | 10 | 7 | 3 (EV02, EV05, EV06) |
| false_positive | 8 | 8 | 0 |
| prompt_injection | 6 | 4 | 2 (PI01, PI02) |
| malformed | 20 | 20 | 0 |
| flood_same_creator | 12 | 12 | 0 |

No request got a 5xx and the server log shows no traceback, including the deeply nested JSON (RQ12) and the 57,640-character text (MF08, a 413). No real writer was labelled AI. Every attack with the outcome the service returned (Combined is `combined_score`; a dash means the request was refused before scoring):

| ID | Family | Status | Guess | Combined | Verdict |
|---|---|---|---|---|---|
| EV01 | evasion | 200 | unsure | 0.308 | HELD |
| EV02 | evasion | 200 | human | 0.258 | BROKE |
| EV03 | evasion | 200 | unsure | 0.456 | HELD |
| EV04 | evasion | 200 | unsure | 0.644 | HELD |
| EV05 | evasion | 200 | human | 0.214 | BROKE |
| EV06 | evasion | 200 | human | 0.253 | BROKE |
| EV07 | evasion | 200 | unsure | 0.422 | HELD |
| EV08 | evasion | 400 | — | — | HELD |
| EV09 | evasion | 200 | unsure | 0.445 | HELD |
| EV10 | evasion | 200 | unsure | 0.810 | HELD |
| FP01 | false_positive | 200 | unsure | 0.553 | HELD |
| FP02 | false_positive | 200 | unsure | 0.766 | HELD |
| FP03 | false_positive | 200 | unsure | 0.725 | HELD |
| FP04 | false_positive | 200 | unsure | 0.715 | HELD |
| FP05 | false_positive | 200 | unsure | 0.839 | HELD |
| FP06 | false_positive | 200 | unsure | 0.549 | HELD |
| FP07 | false_positive | 200 | unsure | 0.517 | HELD |
| FP08 | false_positive | 400 | — | — | HELD |
| PI01 | prompt_injection | 200 | human | 0.228 | BROKE |
| PI02 | prompt_injection | 200 | human | 0.150 | BROKE |
| PI03 | prompt_injection | 200 | unsure | 0.568 | HELD |
| PI04 | prompt_injection | 200 | unsure | 0.491 | HELD |
| PI05 | prompt_injection | 200 | unsure | 0.325 | HELD |
| PI06 | prompt_injection | 200 | unsure | 0.535 | HELD |
| MF01 | malformed | 400 | — | — | HELD |
| MF02 | malformed | 400 | — | — | HELD |
| MF03 | malformed | 400 | — | — | HELD |
| MF04 | malformed | 400 | — | — | HELD |
| MF05 | malformed | 400 | — | — | HELD |
| MF06 | malformed | 400 | — | — | HELD |
| MF07 | malformed | 400 | — | — | HELD |
| MF08 | malformed | 413 | — | — | HELD |
| RQ01 | malformed | 400 | — | — | HELD |
| RQ02 | malformed | 400 | — | — | HELD |
| RQ03 | malformed | 400 | — | — | HELD |
| RQ04 | malformed | 400 | — | — | HELD |
| RQ05 | malformed | 400 | — | — | HELD |
| RQ06 | malformed | 400 | — | — | HELD |
| RQ07 | malformed | 400 | — | — | HELD |
| RQ08 | malformed | 400 | — | — | HELD |
| RQ09 | malformed | 400 | — | — | HELD |
| RQ10 | malformed | 400 | — | — | HELD |
| RQ11 | malformed | 400 | — | — | HELD |
| RQ12 | malformed | 400 | — | — | HELD |
| FL01_01 | flood_same_creator | 400 | — | — | HELD |
| FL01_02 | flood_same_creator | 400 | — | — | HELD |
| FL01_03 | flood_same_creator | 400 | — | — | HELD |
| FL01_04 | flood_same_creator | 400 | — | — | HELD |
| FL01_05 | flood_same_creator | 400 | — | — | HELD |
| FL01_06 | flood_same_creator | 400 | — | — | HELD |
| FL01_07 | flood_same_creator | 400 | — | — | HELD |
| FL01_08 | flood_same_creator | 400 | — | — | HELD |
| FL01_09 | flood_same_creator | 400 | — | — | HELD |
| FL01_10 | flood_same_creator | 400 | — | — | HELD |
| FL01_11 | flood_same_creator | 400 | — | — | HELD |
| FL01_12 | flood_same_creator | 400 | — | — | HELD |

**Ten audit log entries from the run**

Taken from `logs/audit.jsonl`, which holds the whole run: 68 entries, one per request, including the 12 replayed flood rows. The five breaks come first, then the closest a real writer came to being accused (FP05), a short real text that could not be submitted at all (FP08), the 57,640-character text (MF08), the first flood row (a 400 the limiter still counted) and a 429 from the replay. The four refusals are rejections: their scores and `content_id` are null because nothing was decided.

```json
{"timestamp": "2026-11-05T02:56:29+00:00", "content_id": "4dd32993-d538-42cf-b60c-fe030c2b0c13", "creator_id": "attacker_EV02", "guess": "human", "model_score": 0.5943, "style_score": 0.1463, "combined_score": 0.2583, "label": "We think this was probably written by a person.", "status": "decided"}
{"timestamp": "2026-11-05T02:56:29+00:00", "content_id": "6ff578da-143c-423b-a83e-a776c7c9e28d", "creator_id": "attacker_EV05", "guess": "human", "model_score": 0.3212, "style_score": 0.1785, "combined_score": 0.2142, "label": "We think this was probably written by a person.", "status": "decided"}
{"timestamp": "2026-11-05T02:56:29+00:00", "content_id": "b9c39396-bba1-4a4f-8eac-4e81fd40e9bc", "creator_id": "attacker_EV06", "guess": "human", "model_score": 0.5727, "style_score": 0.1467, "combined_score": 0.2532, "label": "We think this was probably written by a person.", "status": "decided"}
{"timestamp": "2026-11-05T02:56:30+00:00", "content_id": "a361b78a-5e77-40f4-bf96-d06bbb371a2b", "creator_id": "attacker_PI01", "guess": "human", "model_score": 0.4625, "style_score": 0.15, "combined_score": 0.2281, "label": "We think this was probably written by a person.", "status": "decided"}
{"timestamp": "2026-11-05T02:56:30+00:00", "content_id": "4c72fca6-c7e3-4b9f-a1c6-1a4428029425", "creator_id": "attacker_PI02", "guess": "human", "model_score": 0.2044, "style_score": 0.1319, "combined_score": 0.15, "label": "We think this was probably written by a person.", "status": "decided"}
{"timestamp": "2026-11-05T02:56:30+00:00", "content_id": "791c2edc-f832-47bc-9728-ad9a1841dc1b", "creator_id": "attacker_FP05", "guess": "unsure", "model_score": 0.8005, "style_score": 0.9539, "combined_score": 0.8388, "label": "We can't tell whether this was written by a person or by an AI tool. This is not a finding against you: our check often can't tell, and many people's own writing gets this result. If you'd like a person to read it, you can ask for a review.", "status": "decided"}
{"timestamp": "2026-11-05T02:56:30+00:00", "content_id": null, "creator_id": "attacker_FP08", "guess": null, "model_score": null, "style_score": null, "combined_score": null, "label": null, "status": "rejected", "event": "rejected", "reason": "bad_input", "http_status": 400}
{"timestamp": "2026-11-05T02:56:30+00:00", "content_id": null, "creator_id": "attacker_MF08", "guess": null, "model_score": null, "style_score": null, "combined_score": null, "label": null, "status": "rejected", "event": "rejected", "reason": "text_too_large", "http_status": 413}
{"timestamp": "2026-11-05T02:56:30+00:00", "content_id": null, "creator_id": "attacker_flood", "guess": null, "model_score": null, "style_score": null, "combined_score": null, "label": null, "status": "rejected", "event": "rejected", "reason": "bad_input", "http_status": 400}
{"timestamp": "2026-11-05T02:56:40+00:00", "content_id": null, "creator_id": "attacker_flood", "guess": null, "model_score": null, "style_score": null, "combined_score": null, "label": null, "status": "rejected", "event": "rejected", "reason": "rate_limited", "http_status": 429, "limit": "12 per 1 minute"}
```

**The single worst outcome** — the one I'd least want to explain to a writer whose work got caught by it:

`FP05`, "technical documentation written by a person". It is seven plain instructional sentences ("To configure the service, edit the settings file in the installation directory. Set the host value to the address the service should bind to. …"). The service returned guess "unsure" with combined score 0.8388, from signal one 0.8005 and signal two 0.9539. Both signals read it as AI. The "ai" label starts at 0.85, so this writer was 0.0112 below being told "Our check thinks this may have been mostly written by an AI tool". They saw the "unsure" label ("not a finding against you") and that is the right outcome. It is the worst because it is luck, not design: the margin is a threshold I set from three texts that an AI imitated, and a person who writes instructions plainly, which is how instructions should be written, sits next to it.

---

## Run Log and Verdicts

`python run_eval.py --label before`, one command, which sends each scenario in `scenarios.py` three times with nothing changed in between, against the service as it stood after Milestone 1. The scenarios and the verdict rules (`eval_verdicts.py`, which applies the five targets from `criteria.md`) were committed before the run (`41ca400`). Real output is in `results/run_2026-11-08_2232_before.md`, the table is `results/eval_verdicts_before.md`.

| Criterion | Target | Run 1 | Run 2 | Run 3 | Verdict |
|---|---|---|---|---|---|
| 1. My own writing flagged as AI | at most 1 of 10 labelled AI | 0/10 | 0/10 | 0/10 | MET |
| 2. Clear AI and clear human score far apart | mean combined gap of AI over human at least 0.30 | 0.369 | 0.369 | 0.369 | MET |
| 3. All three labels reachable | all 3 labels appear and at least 2 of 3 borderline unsure | 2/3 labels, 3/3 unsure | 2/3 labels, 3/3 unsure | 2/3 labels, 3/3 unsure | MISSED |
| 4. An appeal always changes status and is recorded | 5 of 5 appeals: 200, `under_review`, one new entry; unknown id 404 | 5/5, unknown id 404 | 5/5, unknown id 404 | 5/5, unknown id 404 | MET |
| 5. Bad input never crashes the service | 8 of 8 get the listed code, no 500, one rejection entry each | 8/8 | 8/8 | 8/8 | MET |

The three trials are identical on every criterion. That is expected: neither signal has anything random in it, so the same text gets the same score each time. Three matching runs show the result is stable, not that I skipped a step. The server log shows no traceback, no 5xx and no 429.

**How I decided each verdict**

- **1. MET, on stand-ins.** 0 of 10 pieces got "ai" in every trial, so the target (at most 1) held. It holds for the AI-drafted pieces, not for my own prose. The "ai" label can fire (two plain AI texts in the calibration set reach it: 0.905 and 0.856), so the criterion can fail. It was close for the plain pieces: `own_08` scored 0.809, 0.041 below the label, `own_09` 0.708, `own_10` 0.667.
- **2. MET, fragile.** The gap was 0.369 in every trial, above 0.30. It is sample-dependent: with the three plain pieces among the five "human" texts the gap is 0.062, and over all ten pieces it is 0.222. I froze the five before the run and did not pick them by score, so the verdict stays MET as written, but a plain human writer erases the gap.
- **3. MISSED.** All three labels never appeared: "ai" showed up in none of the three trials, because the three ordinary AI texts scored 0.527, 0.514 and 0.706. The three borderline texts all got "unsure" (3 of 3, so that half of the target held).
- **4. MET.** In every trial all 5 appeals returned 200 with `under_review` and added exactly one entry for the right `content_id`, and the id that was never issued returned 404 with no `under_review` entry. The harness counts every entry an appeal added, not just `under_review` ones.
- **5. MET.** In every trial all 8 bad bodies got the listed code, none returned a 500, and each left exactly one rejection entry. It agrees with the attack run, where all 20 malformed requests were refused.

**An argument against my own verdicts.** I gave a fresh Claude agent only the five criteria, my targets, the three runs and my verdicts, and asked it to argue the opposite of each and name evidence that would settle it, without saying which was right. It called criteria 1 and 2 the most fragile, and I went and got the evidence:

- *Criterion 1 can never fail, because "ai" never fires.* False: `ai_plain_01` and `ai_plain_04` are labelled "ai" in the calibration set. But its other point holds: the pieces are not mine, and the plain ones sit within 0.041 of an accusation. I changed the verdict's wording to "MET, on stand-ins".
- *Criterion 2: pick a different five and the gap collapses.* True, computed above (0.369 to 0.062). The verdict stands because the picks were frozen first, and the sensitivity is now stated.
- *Criterion 3 is mis-specified, since the design forbids the "ai" label on ordinary text.* The arithmetic is right: an "ai" label needs the lower signal to be at least 0.80 even if the other is 1.0, and the ordinary AI texts' lower signals were 0.43, 0.41 and 0.64. But the criterion was measurable and my target; a missed target is diagnosed, not rewritten, so it stays MISSED and no criterion was revised.
- *Criteria 4 and 5 only test the happy path or skip the boundaries.* Mostly covered elsewhere: a second appeal on one id, a well-formed unissued id, a malformed id and the exact 20-word and 20,000-character boundaries are in `tests/test_appeal.py` and `tests/test_submit.py`. The attack run covered lists, objects and other wrong types, and the 413 rejection entry is 280 bytes because it stores no text. Not tested: who may appeal, since the service has no authentication, so anyone with a `content_id` can appeal it. That is outside what these criteria claim.

**Things to know about how this was run**

- **Criterion 1 is not yet my own writing.** The ten pieces were drafted by an AI agent that could not see this repo, the detector or any score. I read and checked all ten and used them as the agent drafted them; I did not edit them. So 0 of 10 says how the service treats AI-drafted imitations of student writing (three of them plain), not how it would treat my real prose. The "human" side of criterion 2 (`own_01` to `own_05`) is the same kind of stand-in, and so are the "human" texts in criterion 3 (`human_01` to `human_03`, also AI-written imitations). The pieces and their provenance are in `samples/own_writing/`. I list this under What's Still Broken.
- **Texts were picked by id order, not by score.** Criterion 2 uses `ai_01` to `ai_05` against `own_01` to `own_05`; criterion 3 uses `ai_06` to `ai_08`, `human_01` to `human_03` and `ai_edited_01` to `ai_edited_03`. Ordinary AI text topped out below the "ai" label in the calibration set, so I expected criterion 3 to miss and did not swap in plain AI texts to make it pass.
- **I extended `run_eval.py`** (the starter said I could) to record `combined_score` and the audit log entries each request added, and to send an appeal after each submission. Criterion 4 is therefore run automatically, not by hand. The service itself is untouched.

**Real output from one trial** (trial 1, from `results/run_2026-11-08_2232_before.md`, produced by `run_eval.py::main` calling `POST /submit` and `POST /appeal` in `app.py`). One line per request; the label text is left out because it is the fixed label text from Label Variants, and `new_entries` is the audit log entries that request added.

Criteria 1 and 2 (own writing, then clear AI, then clear human):

```json
// my own writing
  {"status": 200, "content_id": "b3b7f391-dbb1-40a6-86ee-85e10a689bc0", "guess": "unsure", "confidence": 0.6174, "model_score": 0.6356, "style_score": 0.2982, "combined_score": 0.3826, "sent": "The first week I lived in Leeds I locked myself out of my flat twice, ", "new_entries": [{"content_id": "b3b7f391-dbb1-40a6-86ee-85e10a689bc0", "creator_id": "eval_my own writi_1", "event": null, "status": "decided", "reason": null, "http_status": null}]}
  {"status": 200, "content_id": "f3ad94d5-9d05-4963-bbad-5bfb6c9faf11", "guess": "human", "confidence": 0.7717, "model_score": 0.5726, "style_score": 0.1136, "combined_score": 0.2283, "sent": "Hi Mr. Denholm,\n\nI hope you're well. I'm writing about the boiler in f", "new_entries": [{"content_id": "f3ad94d5-9d05-4963-bbad-5bfb6c9faf11", "creator_id": "eval_my own writi_2", "event": null, "status": "decided", "reason": null, "http_status": null}]}
  {"status": 200, "content_id": "a1f9d2cf-056f-44b7-9045-2d48eb125ea1", "guess": "human", "confidence": 0.7223, "model_score": 0.5275, "style_score": 0.1944, "combined_score": 0.2777, "sent": "I think the library should stop letting people reserve the group study", "new_entries": [{"content_id": "a1f9d2cf-056f-44b7-9045-2d48eb125ea1", "creator_id": "eval_my own writi_3", "event": null, "status": "decided", "reason": null, "http_status": null}]}
  {"status": 200, "content_id": "fafee8b6-13b4-4fae-984c-857529b59549", "guess": "human", "confidence": 0.891, "model_score": 0.2415, "style_score": 0.0648, "combined_score": 0.109, "sent": "Tues 14 Oct, titration, practical 4\n\nMade up 0.1 M NaOH this morning b", "new_entries": [{"content_id": "fafee8b6-13b4-4fae-984c-857529b59549", "creator_id": "eval_my own writi_4", "event": null, "status": "decided", "reason": null, "http_status": null}]}
  {"status": 200, "content_id": "b867de90-2f2e-4f45-a9b4-effdcb7b0ec3", "guess": "human", "confidence": 0.7386, "model_score": 0.5394, "style_score": 0.1687, "combined_score": 0.2614, "sent": "I've been thinking about how I don't really call my grandma anymore. W", "new_entries": [{"content_id": "b867de90-2f2e-4f45-a9b4-effdcb7b0ec3", "creator_id": "eval_my own writi_5", "event": null, "status": "decided", "reason": null, "http_status": null}]}
  {"status": 200, "content_id": "6cc5fadf-7480-4a51-9bf2-5d972c7dbcb1", "guess": "human", "confidence": 0.7084, "model_score": 0.5226, "style_score": 0.2146, "combined_score": 0.2916, "sent": "How to get the ancient printer in the common room to actually work (fo", "new_entries": [{"content_id": "6cc5fadf-7480-4a51-9bf2-5d972c7dbcb1", "creator_id": "eval_my own writi_6", "event": null, "status": "decided", "reason": null, "http_status": null}]}
  {"status": 200, "content_id": "d490b85f-7e50-4e99-b627-6263f94adddf", "guess": "human", "confidence": 0.7484, "model_score": 0.4798, "style_score": 0.1755, "combined_score": 0.2516, "sent": "Went to the new ramen place on Mill Street, Kobo, on Saturday with Dev", "new_entries": [{"content_id": "d490b85f-7e50-4e99-b627-6263f94adddf", "creator_id": "eval_my own writi_7", "event": null, "status": "decided", "reason": null, "http_status": null}]}
  {"status": 200, "content_id": "3b1c9849-7545-4730-a251-8ad30b82643c", "guess": "unsure", "confidence": 0.8086, "model_score": 0.7839, "style_score": 0.8827, "combined_score": 0.8086, "sent": "I take the bus to the university every day. The bus stop is near my fl", "new_entries": [{"content_id": "3b1c9849-7545-4730-a251-8ad30b82643c", "creator_id": "eval_my own writi_8", "event": null, "status": "decided", "reason": null, "http_status": null}]}
  {"status": 200, "content_id": "90c4a922-fbc8-4a16-9a72-128cf2c466e2", "guess": "unsure", "confidence": 0.7082, "model_score": 0.7863, "style_score": 0.6821, "combined_score": 0.7082, "sent": "Last Saturday I cooked dinner for my friends. I made chicken curry and", "new_entries": [{"content_id": "90c4a922-fbc8-4a16-9a72-128cf2c466e2", "creator_id": "eval_my own writi_9", "event": null, "status": "decided", "reason": null, "http_status": null}]}
  {"status": 200, "content_id": "4f01b930-e1c4-49a5-9a53-047d0db23a0a", "guess": "unsure", "confidence": 0.6666, "model_score": 0.8017, "style_score": 0.6216, "combined_score": 0.6666, "sent": "I have a part-time job in a bookshop. I work there on Tuesdays and Sat", "new_entries": [{"content_id": "4f01b930-e1c4-49a5-9a53-047d0db23a0a", "creator_id": "eval_my own writi_10", "event": null, "status": "decided", "reason": null, "http_status": null}]}
// clear AI
  {"status": 200, "content_id": "08828048-2ee2-4a2e-b7ca-3ea663d80cfc", "guess": "unsure", "confidence": 0.5107, "model_score": 0.7002, "style_score": 0.419, "combined_score": 0.4893, "sent": "Remote work has fundamentally changed how people think about the relat", "new_entries": [{"content_id": "08828048-2ee2-4a2e-b7ca-3ea663d80cfc", "creator_id": "eval_clear AI_1", "event": null, "status": "decided", "reason": null, "http_status": null}]}
  {"status": 200, "content_id": "bad61e49-031f-4b72-ac5a-ba331d957ce0", "guess": "unsure", "confidence": 0.6249, "model_score": 0.8386, "style_score": 0.5537, "combined_score": 0.6249, "sent": "Subject: Update on the Q3 Product Roadmap\n\nHi team,\n\nI hope this messa", "new_entries": [{"content_id": "bad61e49-031f-4b72-ac5a-ba331d957ce0", "creator_id": "eval_clear AI_2", "event": null, "status": "decided", "reason": null, "http_status": null}]}
  {"status": 200, "content_id": "bc7c9e56-4efd-4c82-b929-4da44e9566db", "guess": "unsure", "confidence": 0.7284, "model_score": 0.7245, "style_score": 0.7402, "combined_score": 0.7284, "sent": "Introducing the AuraBrew Smart Kettle, a thoughtful blend of elegant d", "new_entries": [{"content_id": "bc7c9e56-4efd-4c82-b929-4da44e9566db", "creator_id": "eval_clear AI_3", "event": null, "status": "decided", "reason": null, "http_status": null}]}
  {"status": 200, "content_id": "85b90d4d-9d88-4ea3-bd47-9f0e7c3a3666", "guess": "unsure", "confidence": 0.5309, "model_score": 0.6472, "style_score": 0.4921, "combined_score": 0.5309, "sent": "The lighthouse had been dark for eleven years when Marguerite finally ", "new_entries": [{"content_id": "85b90d4d-9d88-4ea3-bd47-9f0e7c3a3666", "creator_id": "eval_clear AI_4", "event": null, "status": "decided", "reason": null, "http_status": null}]}
  {"status": 200, "content_id": "e3685715-fb3d-444a-a344-58d3615d6ed6", "guess": "unsure", "confidence": 0.7313, "model_score": 0.8097, "style_score": 0.7052, "combined_score": 0.7313, "sent": "A hash table is a data structure that stores key-value pairs and allow", "new_entries": [{"content_id": "e3685715-fb3d-444a-a344-58d3615d6ed6", "creator_id": "eval_clear AI_5", "event": null, "status": "decided", "reason": null, "http_status": null}]}
// clear human
  {"status": 200, "content_id": "3d200185-31d8-45eb-9210-1118477f7eb4", "guess": "unsure", "confidence": 0.6174, "model_score": 0.6356, "style_score": 0.2982, "combined_score": 0.3826, "sent": "The first week I lived in Leeds I locked myself out of my flat twice, ", "new_entries": [{"content_id": "3d200185-31d8-45eb-9210-1118477f7eb4", "creator_id": "eval_clear human_1", "event": null, "status": "decided", "reason": null, "http_status": null}]}
  {"status": 200, "content_id": "2f5f8aa4-67b1-47c0-805c-5930da57e46b", "guess": "human", "confidence": 0.7717, "model_score": 0.5726, "style_score": 0.1136, "combined_score": 0.2283, "sent": "Hi Mr. Denholm,\n\nI hope you're well. I'm writing about the boiler in f", "new_entries": [{"content_id": "2f5f8aa4-67b1-47c0-805c-5930da57e46b", "creator_id": "eval_clear human_2", "event": null, "status": "decided", "reason": null, "http_status": null}]}
  {"status": 200, "content_id": "c9decfc4-892d-4558-84f7-df7eef8109a3", "guess": "human", "confidence": 0.7223, "model_score": 0.5275, "style_score": 0.1944, "combined_score": 0.2777, "sent": "I think the library should stop letting people reserve the group study", "new_entries": [{"content_id": "c9decfc4-892d-4558-84f7-df7eef8109a3", "creator_id": "eval_clear human_3", "event": null, "status": "decided", "reason": null, "http_status": null}]}
  {"status": 200, "content_id": "3f8f1ef9-bb3f-4cac-b9e3-b324e61cb09d", "guess": "human", "confidence": 0.891, "model_score": 0.2415, "style_score": 0.0648, "combined_score": 0.109, "sent": "Tues 14 Oct, titration, practical 4\n\nMade up 0.1 M NaOH this morning b", "new_entries": [{"content_id": "3f8f1ef9-bb3f-4cac-b9e3-b324e61cb09d", "creator_id": "eval_clear human_4", "event": null, "status": "decided", "reason": null, "http_status": null}]}
  {"status": 200, "content_id": "4b99c4ec-7b7a-4389-bd91-4d1ac594d192", "guess": "human", "confidence": 0.7386, "model_score": 0.5394, "style_score": 0.1687, "combined_score": 0.2614, "sent": "I've been thinking about how I don't really call my grandma anymore. W", "new_entries": [{"content_id": "4b99c4ec-7b7a-4389-bd91-4d1ac594d192", "creator_id": "eval_clear human_5", "event": null, "status": "decided", "reason": null, "http_status": null}]}
```

Criterion 3 (the "ai" label never appears):

```json
// labels: AI
  {"status": 200, "content_id": "97f6bf63-ffd1-46ab-9056-d8dca82ec83f", "guess": "unsure", "confidence": 0.5266, "model_score": 0.8211, "style_score": 0.4285, "combined_score": 0.5266, "sent": "Last year, I decided to start waking up at five in the morning, and ho", "new_entries": [{"content_id": "97f6bf63-ffd1-46ab-9056-d8dca82ec83f", "creator_id": "eval_labels: AI_1", "event": null, "status": "decided", "reason": null, "http_status": null}]}
  {"status": 200, "content_id": "617bfd90-92a8-4675-b98e-164c65c1f80c", "guess": "unsure", "confidence": 0.5138, "model_score": 0.8287, "style_score": 0.4089, "combined_score": 0.5138, "sent": "I'm really sorry you're going through this, and I want you to know tha", "new_entries": [{"content_id": "617bfd90-92a8-4675-b98e-164c65c1f80c", "creator_id": "eval_labels: AI_2", "event": null, "status": "decided", "reason": null, "http_status": null}]}
  {"status": 200, "content_id": "190a3ff9-a238-41c7-a11a-74a699a5e758", "guess": "unsure", "confidence": 0.7063, "model_score": 0.9101, "style_score": 0.6384, "combined_score": 0.7063, "sent": "The Water Cycle\n\nThe water cycle is the continuous process by which wa", "new_entries": [{"content_id": "190a3ff9-a238-41c7-a11a-74a699a5e758", "creator_id": "eval_labels: AI_3", "event": null, "status": "decided", "reason": null, "http_status": null}]}
// labels: human
  {"status": 200, "content_id": "623c60f9-9327-45bd-8071-e70469d76d09", "guess": "human", "confidence": 0.8477, "model_score": 0.4036, "style_score": 0.0685, "combined_score": 0.1523, "sent": "ok so I finally did the thing, quit the warehouse job. Tuesday. Didn't", "new_entries": [{"content_id": "623c60f9-9327-45bd-8071-e70469d76d09", "creator_id": "eval_labels: huma_1", "event": null, "status": "decided", "reason": null, "http_status": null}]}
  {"status": 200, "content_id": "156d883b-9bf6-4c41-9d72-b7a226b69786", "guess": "human", "confidence": 0.7914, "model_score": 0.4664, "style_score": 0.1226, "combined_score": 0.2086, "sent": "Right so the funeral was a mess. Auntie Rosa turned up an hour late we", "new_entries": [{"content_id": "156d883b-9bf6-4c41-9d72-b7a226b69786", "creator_id": "eval_labels: huma_2", "event": null, "status": "decided", "reason": null, "http_status": null}]}
  {"status": 200, "content_id": "dbc79a56-1f97-4c39-a278-abcb42f6f1f7", "guess": "human", "confidence": 0.7889, "model_score": 0.482, "style_score": 0.1208, "combined_score": 0.2111, "sent": "Spent the whole weekend trying to fix the bike. Chain kept slipping, n", "new_entries": [{"content_id": "dbc79a56-1f97-4c39-a278-abcb42f6f1f7", "creator_id": "eval_labels: huma_3", "event": null, "status": "decided", "reason": null, "http_status": null}]}
// labels: borderline
  {"status": 200, "content_id": "19e082f5-8bf2-44a7-9661-7b775ff76010", "guess": "unsure", "confidence": 0.5735, "model_score": 0.6446, "style_score": 0.3538, "combined_score": 0.4265, "sent": "Remote work has changed how people think about productivity and place.", "new_entries": [{"content_id": "19e082f5-8bf2-44a7-9661-7b775ff76010", "creator_id": "eval_labels: bord_1", "event": null, "status": "decided", "reason": null, "http_status": null}]}
  {"status": 200, "content_id": "09130d6c-87ab-426f-8630-6b0391a83aab", "guess": "unsure", "confidence": 0.6217, "model_score": 0.6044, "style_score": 0.6737, "combined_score": 0.6217, "sent": "Meet the AuraBrew Smart Kettle, a nice mix of elegant design and cleve", "new_entries": [{"content_id": "09130d6c-87ab-426f-8630-6b0391a83aab", "creator_id": "eval_labels: bord_2", "event": null, "status": "decided", "reason": null, "http_status": null}]}
  {"status": 200, "content_id": "cd359add-fe3b-4072-a9c9-068bcbababf3", "guess": "unsure", "confidence": 0.5032, "model_score": 0.7996, "style_score": 0.3959, "combined_score": 0.4968, "sent": "Last year I decided to start waking up at five in the morning, and hon", "new_entries": [{"content_id": "cd359add-fe3b-4072-a9c9-068bcbababf3", "creator_id": "eval_labels: bord_3", "event": null, "status": "decided", "reason": null, "http_status": null}]}
```

Criterion 4 (five submissions, each appealed, then an id that was never issued):

```json
// appeals
  {"status": 200, "content_id": "9deb37f9-1e37-4c4d-9100-7bc4829852c4", "guess": "human", "confidence": 0.7084, "model_score": 0.5226, "style_score": 0.2146, "combined_score": 0.2916, "sent": "How to get the ancient printer in the common room to actually work (fo", "new_entries": [{"content_id": "9deb37f9-1e37-4c4d-9100-7bc4829852c4", "creator_id": "eval_appeals_1", "event": null, "status": "decided", "reason": null, "http_status": null}], "appeal_status": 200, "appeal_state": "under_review", "appeal_new_entries": [{"content_id": "9deb37f9-1e37-4c4d-9100-7bc4829852c4", "creator_id": "eval_appeals_1", "event": "appeal", "status": "under_review", "reason": null, "http_status": null}]}
  {"status": 200, "content_id": "4ec78527-0dbb-45c0-98c4-e79d6d90d3a4", "guess": "human", "confidence": 0.7484, "model_score": 0.4798, "style_score": 0.1755, "combined_score": 0.2516, "sent": "Went to the new ramen place on Mill Street, Kobo, on Saturday with Dev", "new_entries": [{"content_id": "4ec78527-0dbb-45c0-98c4-e79d6d90d3a4", "creator_id": "eval_appeals_2", "event": null, "status": "decided", "reason": null, "http_status": null}], "appeal_status": 200, "appeal_state": "under_review", "appeal_new_entries": [{"content_id": "4ec78527-0dbb-45c0-98c4-e79d6d90d3a4", "creator_id": "eval_appeals_2", "event": "appeal", "status": "under_review", "reason": null, "http_status": null}]}
  {"status": 200, "content_id": "9fcbbe9e-82b4-4c69-b985-21b98792fa89", "guess": "unsure", "confidence": 0.8086, "model_score": 0.7839, "style_score": 0.8827, "combined_score": 0.8086, "sent": "I take the bus to the university every day. The bus stop is near my fl", "new_entries": [{"content_id": "9fcbbe9e-82b4-4c69-b985-21b98792fa89", "creator_id": "eval_appeals_3", "event": null, "status": "decided", "reason": null, "http_status": null}], "appeal_status": 200, "appeal_state": "under_review", "appeal_new_entries": [{"content_id": "9fcbbe9e-82b4-4c69-b985-21b98792fa89", "creator_id": "eval_appeals_3", "event": "appeal", "status": "under_review", "reason": null, "http_status": null}]}
  {"status": 200, "content_id": "e681eb21-f3b0-4466-a07e-937a512a3d3f", "guess": "unsure", "confidence": 0.7082, "model_score": 0.7863, "style_score": 0.6821, "combined_score": 0.7082, "sent": "Last Saturday I cooked dinner for my friends. I made chicken curry and", "new_entries": [{"content_id": "e681eb21-f3b0-4466-a07e-937a512a3d3f", "creator_id": "eval_appeals_4", "event": null, "status": "decided", "reason": null, "http_status": null}], "appeal_status": 200, "appeal_state": "under_review", "appeal_new_entries": [{"content_id": "e681eb21-f3b0-4466-a07e-937a512a3d3f", "creator_id": "eval_appeals_4", "event": "appeal", "status": "under_review", "reason": null, "http_status": null}]}
  {"status": 200, "content_id": "b2ca2a16-aa85-4a3e-a810-84ace912cbe5", "guess": "unsure", "confidence": 0.6666, "model_score": 0.8017, "style_score": 0.6216, "combined_score": 0.6666, "sent": "I have a part-time job in a bookshop. I work there on Tuesdays and Sat", "new_entries": [{"content_id": "b2ca2a16-aa85-4a3e-a810-84ace912cbe5", "creator_id": "eval_appeals_5", "event": null, "status": "decided", "reason": null, "http_status": null}], "appeal_status": 200, "appeal_state": "under_review", "appeal_new_entries": [{"content_id": "b2ca2a16-aa85-4a3e-a810-84ace912cbe5", "creator_id": "eval_appeals_5", "event": "appeal", "status": "under_review", "reason": null, "http_status": null}]}
  {"unknown_id": "00000000-0000-0000-0000-000000000000", "sent": "00000000-0000-0000-0000-000000000000", "appeal_status": 404, "appeal_state": null, "appeal_new_entries": [{"content_id": null, "creator_id": "unknown", "event": "rejected", "status": "rejected", "reason": "unknown_content_id", "http_status": 404}]}
```

Criterion 5 (the eight bad bodies, in the order in `criteria.md`):

```json
// bad input
  {"status": 400, "content_id": null, "guess": null, "confidence": null, "model_score": null, "style_score": null, "combined_score": null, "sent": "{\"creator_id\": \"eval_bad_1\"}", "new_entries": [{"content_id": null, "creator_id": "eval_bad_1", "event": "rejected", "status": "rejected", "reason": "bad_input", "http_status": 400}]}
  {"status": 400, "content_id": null, "guess": null, "confidence": null, "model_score": null, "style_score": null, "combined_score": null, "sent": "(empty text)", "new_entries": [{"content_id": null, "creator_id": "eval_bad_2", "event": "rejected", "status": "rejected", "reason": "bad_input", "http_status": 400}]}
  {"status": 400, "content_id": null, "guess": null, "confidence": null, "model_score": null, "style_score": null, "combined_score": null, "sent": "   \n\t  ", "new_entries": [{"content_id": null, "creator_id": "eval_bad_3", "event": "rejected", "status": "rejected", "reason": "bad_input", "http_status": 400}]}
  {"status": 400, "content_id": null, "guess": null, "confidence": null, "model_score": null, "style_score": null, "combined_score": null, "sent": "{\"text\": null, \"creator_id\": \"eval_bad_4\"}", "new_entries": [{"content_id": null, "creator_id": "eval_bad_4", "event": "rejected", "status": "rejected", "reason": "bad_input", "http_status": 400}]}
  {"status": 400, "content_id": null, "guess": null, "confidence": null, "model_score": null, "style_score": null, "combined_score": null, "sent": "{\"text\": 12345, \"creator_id\": \"eval_bad_5\"}", "new_entries": [{"content_id": null, "creator_id": "eval_bad_5", "event": "rejected", "status": "rejected", "reason": "bad_input", "http_status": 400}]}
  {"status": 400, "content_id": null, "guess": null, "confidence": null, "model_score": null, "style_score": null, "combined_score": null, "sent": "one two three four five six seven eight nine ten eleven twelve thirtee", "new_entries": [{"content_id": null, "creator_id": "eval_bad_6", "event": "rejected", "status": "rejected", "reason": "bad_input", "http_status": 400}]}
  {"status": 413, "content_id": null, "guess": null, "confidence": null, "model_score": null, "style_score": null, "combined_score": null, "sent": "word word word word word word word word word word word word word word ", "new_entries": [{"content_id": null, "creator_id": "eval_bad_7", "event": "rejected", "status": "rejected", "reason": "text_too_large", "http_status": 413}]}
  {"status": 400, "content_id": null, "guess": null, "confidence": null, "model_score": null, "style_score": null, "combined_score": null, "sent": "{\"text\": \"I walked to the shop on Tuesday because we had run out of milk. The queue was long, so I read the notices by t", "new_entries": [{"content_id": null, "creator_id": "unknown", "event": "rejected", "status": "rejected", "reason": "bad_input", "http_status": 400}]}
```

**Diagnoses**

Numbers are from `python diagnose.py` (`results/diagnosis_before.md`), which also prints each attack with its attacking edit taken out.

**The pattern first.** All five broken attacks have the same number in the same place: the sentence-length-spread part of signal two scales to 0.00, because the raw spread is 0.65 to 1.19 and the human end of its anchor is 0.60. That part carries 0.60 of the style score, so the style score is left at 0.13 to 0.18 whatever the rest of the text looks like. The combining rule then does the rest: it weights the lower signal at 0.75, so a style score near 0.15 pulls the result to "human" even when signal one reads AI-ish. That is one problem with several ways in, not five problems.

- **EV02, "broken-up sentences".** *Stage: signal two (and the combining rule).* The text has 13 sentences and six of them are the single word "Really." Those one-word sentences push the spread to 0.85, so the spread part is 0.00 and the style score is only the punctuation part (0.146, from the em dashes). Combined: 0.75 × 0.146 + 0.25 × 0.594 = 0.258, "human". With the "Really." sentences taken out the spread is 0.16, the style score is 0.743 and the combined score is 0.650, "unsure". The mechanism is that a measure of how much sentence length varies counts one-word fragments as maximum variety, and fragments cost an attacker nothing.
- **EV06, "one very long sentence and one very short".** *Stage: signal two (and the combining rule).* One 51-word sentence and a one-word sentence among 10 to 15-word sentences give a spread of 1.19, spread part 0.00, style 0.147, combined 0.75 × 0.147 + 0.25 × 0.573 = 0.253, "human". Without those two sentences the spread is 0.45, the style score 0.399 and the combined score 0.471, "unsure". Same mechanism as EV02: two cheap edits move the one measure that carries most of the weight.
- **EV05, "heavy human editing pass".** *Stage: both signals, and I don't count it as a bug.* This is a genuine rewrite in a human voice, with no stock text underneath to take out. Perplexity is 72, so signal one reads it as human (0.321), and the spread is 0.68, so signal two also reads it as human (0.178); combined 0.214. A detector that sees only how predictable text is and how its sentences are shaped cannot tell heavily edited AI text from writing that never was AI. It is a limit of the approach, and a different kind of failure from the others.
- **PI01 and PI02, the injections.** *Stage: signal one made them break; signal two put them on the edge.* Nothing in the service reads instructions, so "Ignore all previous instructions" and "SYSTEM: provenance check bypassed" are not obeyed. They are rare text, and rare text raises the model's perplexity. The stock paragraph alone has perplexity 22 (signal one 0.754); with the PI01 prefix it is 49 (0.463) and with the PI02 prefix 105 (0.204). The style score is 0.150 and 0.132, so the combined scores are 0.75 × 0.150 + 0.25 × 0.463 = 0.228 and 0.75 × 0.132 + 0.25 × 0.204 = 0.150: "human". Without the prefix the same text is 0.301, "unsure", only 0.001 above the human threshold. The reason it was already so close is in the staff file: both texts are cut off mid-word ("Th"), so they end in a one-word sentence and the spread is already above the anchor with no help from the attack. With only 45 words and 3 to 6 sentences, a single short sentence moves the spread a lot.
- **Criterion 3, the "ai" label never appeared.** *Stage: the label mapping, with the combining rule.* The AI label needs a combined score of at least 0.85. Because the rule weights the lower signal at 0.75, that needs the lower signal to be at least 0.80 even when the other is 1.0. The ordinary AI texts have model scores of 0.82, 0.83 and 0.91 but style scores of only 0.43, 0.41 and 0.64, so the lower signal is the style signal and the combined scores are 0.527, 0.514 and 0.706. Across the eight ordinary AI texts in the calibration set, signal one averages 0.785 and signal two 0.548, which combine to about 0.607. Only plain AI texts get near 0.85 (0.905 and 0.856), and plain human text scores 0.787 to 0.797 right under them. The threshold was set at 0.85 on purpose to keep that human text out of "ai", so criterion 3 is the price of criterion 1's protection: the label that would catch ordinary AI cannot be reached without also accusing plain human writers.

**What I would tighten.** Criterion 1 is the generous one. "At most 1 of 10" was met with 0, but the plain pieces sit 0.041 to 0.183 below the AI label and the pieces are stand-ins, so I would add a margin: no plain piece within 0.10 of the AI label. `own_08` would fail that. Criterion 2 should be measured with plain human text in the "human" side, where the gap is 0.062, not 0.369. I did not edit any criterion in `criteria.md`: all five were measurable, and a missed target is diagnosed, not changed.

---

## The Improvement

**What I changed:** one thing, in `stylometry.py`: sentences shorter than 3 words are no longer counted when measuring how much sentence length varies (`SPREAD_MIN_SENTENCE_WORDS = 3`). A one- or two-word sentence like "Really." or "True." is a fragment, not a sentence length, so it does not add to the spread any more. If fewer than two real sentences are left, that part of the style signal is neutral (0.5), the same as for a one-sentence text, instead of reading as AI-shaped. No weight, anchor, threshold or label text changed. Commit `1f502b9`.

**Which diagnosis pointed at it:** the pattern in the Diagnoses above. All five broken attacks had the spread part of signal two at 0.00 because fragments (EV02's six "Really." sentences, the single-word sentence in EV05, the cut-off "Th" in PI01 and PI02) or one 51-word sentence (EV06) pushed the spread past the human anchor, and the combining rule turned that into "human". I tried the alternatives against the same texts first, offline, with the model scores already recorded (so the numbers are exact). Lowering the weight on the lower signal to 0.60 or 0.50 fixed some breaks but labelled FP05, a real person's technical documentation, "ai", which is the expensive error. Merging short sentences into the previous one fixed the same attacks but moved more human texts; a cap on sentence length needed a second edit on top of the fragment rule; a robust spread measure (median instead of standard deviation) made one more attack break. Ignoring fragments labelled nobody "ai".

The success test was written before the change: it helped if (a) fewer attacks break, (b) no real writer's text is newly labelled "ai", and (c) no criterion that was MET becomes MISSED.

### Attack Run — After

`python run_attacks.py --set attack_set --label after`, the same 56 attacks, the same rules (`attack_verdicts.py`, including the flood amendment), the service restarted fresh, nothing else changed. Reports: `results/attack_run_2026-11-08_2319_after.md` and its flood replay; verdicts `results/attack_verdicts_after.md`; the before and after side by side in `results/before_after.md` (`python compare_runs.py`). The audit log holds one entry per request, nine fields each, and the server log shows no traceback or 5xx. The log of the before run is kept in `results/audit_before.jsonl`.

**Result: 56 attacks, 54 held, 2 broke** (before: 51 held, 5 broke).

| Family | Attacks | Held before > after | Broke before > after |
|---|---|---|---|
| evasion | 10 | 7 > 9 | 3 > 1 (EV06) |
| false_positive | 8 | 8 > 8 | 0 > 0 |
| prompt_injection | 6 | 4 > 5 | 2 > 1 (PI02) |
| malformed | 20 | 20 > 20 | 0 > 0 |
| flood_same_creator | 12 | 12 > 12 | 0 > 0 |

Every attack, before and after (where a cell has no arrow nothing changed):

| ID | Family | Status | Guess before / after | Combined before / after | Verdict before / after |
|---|---|---|---|---|---|
| EV01 | evasion | 200 | unsure | 0.308 | HELD |
| EV02 | evasion | 200 | human > unsure | 0.258 > 0.632 | BROKE > HELD |
| EV03 | evasion | 200 | unsure | 0.456 > 0.577 | HELD |
| EV04 | evasion | 200 | unsure | 0.644 | HELD |
| EV05 | evasion | 200 | human > unsure | 0.214 > 0.322 | BROKE > HELD |
| EV06 | evasion | 200 | human | 0.253 | BROKE |
| EV07 | evasion | 200 | unsure | 0.422 | HELD |
| EV08 | evasion | 400 | — | — | HELD |
| EV09 | evasion | 200 | unsure | 0.445 > 0.615 | HELD |
| EV10 | evasion | 200 | unsure | 0.810 | HELD |
| FP01 | false_positive | 200 | unsure | 0.553 | HELD |
| FP02 | false_positive | 200 | unsure | 0.766 | HELD |
| FP03 | false_positive | 200 | unsure | 0.725 | HELD |
| FP04 | false_positive | 200 | unsure | 0.715 | HELD |
| FP05 | false_positive | 200 | unsure | 0.839 | HELD |
| FP06 | false_positive | 200 | unsure | 0.549 | HELD |
| FP07 | false_positive | 200 | unsure | 0.517 | HELD |
| FP08 | false_positive | 400 | — | — | HELD |
| PI01 | prompt_injection | 200 | human > unsure | 0.228 > 0.376 | BROKE > HELD |
| PI02 | prompt_injection | 200 | human | 0.150 > 0.241 | BROKE |
| PI03 | prompt_injection | 200 | unsure | 0.568 | HELD |
| PI04 | prompt_injection | 200 | unsure | 0.491 | HELD |
| PI05 | prompt_injection | 200 | unsure | 0.325 | HELD |
| PI06 | prompt_injection | 200 | unsure | 0.535 | HELD |
| MF01 | malformed | 400 | — | — | HELD |
| MF02 | malformed | 400 | — | — | HELD |
| MF03 | malformed | 400 | — | — | HELD |
| MF04 | malformed | 400 | — | — | HELD |
| MF05 | malformed | 400 | — | — | HELD |
| MF06 | malformed | 400 | — | — | HELD |
| MF07 | malformed | 400 | — | — | HELD |
| MF08 | malformed | 413 | — | — | HELD |
| RQ01 | malformed | 400 | — | — | HELD |
| RQ02 | malformed | 400 | — | — | HELD |
| RQ03 | malformed | 400 | — | — | HELD |
| RQ04 | malformed | 400 | — | — | HELD |
| RQ05 | malformed | 400 | — | — | HELD |
| RQ06 | malformed | 400 | — | — | HELD |
| RQ07 | malformed | 400 | — | — | HELD |
| RQ08 | malformed | 400 | — | — | HELD |
| RQ09 | malformed | 400 | — | — | HELD |
| RQ10 | malformed | 400 | — | — | HELD |
| RQ11 | malformed | 400 | — | — | HELD |
| RQ12 | malformed | 400 | — | — | HELD |
| FL01_01 | flood_same_creator | 400 | — | — | HELD |
| FL01_02 | flood_same_creator | 400 | — | — | HELD |
| FL01_03 | flood_same_creator | 400 | — | — | HELD |
| FL01_04 | flood_same_creator | 400 | — | — | HELD |
| FL01_05 | flood_same_creator | 400 | — | — | HELD |
| FL01_06 | flood_same_creator | 400 | — | — | HELD |
| FL01_07 | flood_same_creator | 400 | — | — | HELD |
| FL01_08 | flood_same_creator | 400 | — | — | HELD |
| FL01_09 | flood_same_creator | 400 | — | — | HELD |
| FL01_10 | flood_same_creator | 400 | — | — | HELD |
| FL01_11 | flood_same_creator | 400 | — | — | HELD |
| FL01_12 | flood_same_creator | 400 | — | — | HELD |

The five criteria, three trials each, before and after (same scenarios, same rules, nothing else changed; the three trials are identical every time):

| Criterion | Before: run 1, 2, 3 | After: run 1, 2, 3 | Verdict |
|---|---|---|---|
| 1. My own writing flagged as AI | 0/10 / 0/10 / 0/10 | 0/10 / 0/10 / 0/10 | MET > MET |
| 2. Clearly-AI and clearly-human texts score far apart | 0.369 / 0.369 / 0.369 | 0.369 / 0.369 / 0.369 | MET > MET |
| 3. All three labels are reachable | 2/3 labels, 3/3 unsure / 2/3 labels, 3/3 unsure / 2/3 labels, 3/3 unsure | 2/3 labels, 3/3 unsure / 2/3 labels, 3/3 unsure / 2/3 labels, 3/3 unsure | MISSED > MISSED |
| 4. An appeal always changes status and is recorded | 5/5, unknown id 404 / 5/5, unknown id 404 / 5/5, unknown id 404 | 5/5, unknown id 404 / 5/5, unknown id 404 / 5/5, unknown id 404 | MET > MET |
| 5. Bad input never crashes the service | 8/8 / 8/8 / 8/8 | 8/8 / 8/8 / 8/8 | MET > MET |

**Did it help, and how do I know:**

**Yes, partly: three of the five broken attacks no longer break (5 broke before, 2 after), no real writer's text became "ai", and no criterion moved.** All three parts of the success test passed (`results/before_after.md`). EV02, EV05 and PI01 went from "human" to "unsure" (combined 0.258 to 0.632, 0.214 to 0.322, 0.228 to 0.376), the signal-one scores were untouched, and only 6 of 56 attacks changed in any way. EV03 and EV09 stayed "unsure" but read more AI-like (0.456 to 0.577, 0.445 to 0.615).

What it did not fix, and what it cost:

- **It stops calling these texts human; it does not catch them.** The three fixed attacks are now "unsure", not "ai". The service is less easy to fool into a confident "human" and no better at saying "AI".
- **EV06 and PI02 still break.** EV06 is one very long sentence, which the change does not touch (spread 1.03 after dropping its one-word sentence). PI02 is the injected "SYSTEM:" prefix: it raises the model's perplexity (signal one 0.204), so signal one still reads it as human, and the style signal only rose to 0.353.
- **Writers who use short sentences read less human.** The same rule that removes the attackers' fragments removes a human signal from honest writing that uses them. In the calibration set `human_03` (a messy, fragment-heavy imitation) moved from combined 0.211, "human", to 0.338, "unsure", and `human_01` from 0.152 to 0.194. Among the ten own-writing pieces `own_06` went from "human" to "unsure" (0.292 to 0.357), and the two plain pieces moved toward the AI label: `own_09` 0.708 to 0.767 and `own_10` 0.667 to 0.811, now only 0.039 below it. Criterion 1 still passes (0 of 10), but its margin is thinner than before.
- **EV05 is a trade, not a clean win.** It was a genuine human-voiced rewrite, so "human" was arguably the right answer. The change turned it into "unsure", for the same reason it turned `human_03` into "unsure".
- **Criterion 3 is untouched** (still MISSED, still two labels), as predicted: the change does not move any AI text toward the "ai" label.
- **The evidence is optimistic.** I chose the change with the attack set and the criteria texts in view, and there is no untouched test set, so the improvement may be smaller on new inputs.

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
       [x] The attack set run IN FULL, every input with an outcome
       [x] Ten audit log entries pasted as text
       [x] Five criteria across three trials
       [x] A diagnosis for every miss and every broken attack — stage AND mechanism
       [x] One improvement, with Attack Run — After
       [ ] What's Still Broken, including the production trade
       [ ] At least four new commits
       [ ] The SAME repository URL as last unit

     Do not delete and recreate this repository.
     ═════════════════════════════════════════════════════════════════════ -->

---

📖 **How to run this project: [RUNNING.md](RUNNING.md)**
