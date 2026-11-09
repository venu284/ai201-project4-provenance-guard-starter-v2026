# Attack run — after

- Produced by: `run_attacks.py::main`
- Service: `app.py::submit`
- 56 attacks · 2026-11-08 23:19
- Auto-marked BROKE (5xx, crash, no response): **0**
- Left for you to judge: **56**

The Verdict column is blank where a script can't honestly decide. Whether
an evasion worked depends on where you put your thresholds — read the
`targets` column, look at what came back, and write HELD or BROKE yourself.

Each attack submits as creator_id `attacker_<id>`, and the content_id it
came back with is in the table — either one will match this run against your
audit log when you go looking for the ten entries to paste.

| ID | Family | Targeting | Status | Content ID | Guess | Score | Verdict |
|---|---|---|---|---|---|---|---|
| EV01 | evasion | signal two: typos raise word variety | 200 | `e8ab7094-b85d-455c-a68d-6edd219b91d3` | unsure | 0.692 |  |
| EV02 | evasion | signal two: broken-up sentences raise length spread | 200 | `98720c9b-4081-4fcc-8de2-77d97251210f` | unsure | 0.632 |  |
| EV03 | evasion | signal two: a pasted quotation changes the shape | 200 | `7d4cf497-19e9-42f9-87aa-b654dac9519f` | unsure | 0.577 |  |
| EV04 | evasion | signal one: unusual words raise perplexity | 200 | `5369b846-3d53-41bb-9ad4-c4e17cae929b` | unsure | 0.644 |  |
| EV05 | evasion | both signals: heavy human editing pass | 200 | `89bbda8c-7b53-41c6-b067-3e4e0de6ddcc` | unsure | 0.678 |  |
| EV06 | evasion | signal two: one very long sentence and one very short | 200 | `c764d937-cc81-4ea8-b463-e9a11694364c` | human | 0.747 |  |
| EV07 | evasion | signal two: padding with punctuation | 200 | `ebb5f9ab-16cd-4d08-b982-eaac55e0334e` | unsure | 0.578 |  |
| EV08 | evasion | signal one: text below the token window | 400 | `—` | — | — |  |
| EV09 | evasion | both: AI text with a human opening paragraph bolted on | 200 | `2e920a73-93db-47c3-a0c7-c0c4acd4191e` | unsure | 0.615 |  |
| EV10 | evasion | signal two: repeated stanza structure | 200 | `28709975-b995-4647-8d3a-19613a41c025` | unsure | 0.810 |  |
| FP01 | false_positive | plain, clear human writing with no flourishes | 200 | `78898353-2580-4a5b-adfe-e1b4a16b968c` | unsure | 0.553 |  |
| FP02 | false_positive | human writing in a formal register | 200 | `c75248ee-2b0c-4e26-93b9-89802138f80d` | unsure | 0.766 |  |
| FP03 | false_positive | a non-native English speaker writing carefully | 200 | `a54edd68-3727-43fc-9f3d-c19515606aa8` | unsure | 0.725 |  |
| FP04 | false_positive | a student essay written to a rubric | 200 | `f0edd847-ed0c-4cde-b682-ba0812a06fc9` | unsure | 0.715 |  |
| FP05 | false_positive | technical documentation written by a person | 200 | `be56415b-86b1-48c9-b6ee-862ae9ecb440` | unsure | 0.839 |  |
| FP06 | false_positive | a person imitating a formal template | 200 | `e196d328-9ba4-4c0d-9996-05db4d1f9e96` | unsure | 0.549 |  |
| FP07 | false_positive | human writing that repeats a phrase deliberately | 200 | `9d81b486-7ba1-4dab-91ca-174743e92e89` | unsure | 0.517 |  |
| FP08 | false_positive | very short genuine human submission | 400 | `—` | — | — |  |
| PI01 | prompt_injection | instruction to ignore the check | 200 | `fe7fb1ec-635c-4f7b-9fc4-13bf49c3b834` | unsure | 0.624 |  |
| PI02 | prompt_injection | instruction disguised as a system message | 200 | `1b7faaa0-ffe7-4ca4-9bed-182ca8c402fe` | human | 0.759 |  |
| PI03 | prompt_injection | instruction wrapped in the writer's voice | 200 | `33cc64c0-97f7-46a4-96eb-013c40f67c56` | unsure | 0.568 |  |
| PI04 | prompt_injection | attempt to make the label text hostile | 200 | `4baa827f-ec99-4c16-bd6a-b62c2c7f4971` | unsure | 0.509 |  |
| PI05 | prompt_injection | attempt to inject into the audit log | 200 | `b7d94bb8-b037-43a0-a519-6feecb57f77b` | unsure | 0.675 |  |
| PI06 | prompt_injection | instruction plus real human text | 200 | `3b9ce35d-37ea-4f24-8391-ee3310d8c12e` | unsure | 0.535 |  |
| MF01 | malformed | text is only whitespace | 400 | `—` | — | — |  |
| MF02 | malformed | text is a single character | 400 | `—` | — | — |  |
| MF03 | malformed | text is control characters | 400 | `—` | — | — |  |
| MF04 | malformed | text is only punctuation | 400 | `—` | — | — |  |
| MF05 | malformed | text is a very long single word | 400 | `—` | — | — |  |
| MF06 | malformed | text is emoji only | 400 | `—` | — | — |  |
| MF07 | malformed | text is right-to-left script | 400 | `—` | — | — |  |
| MF08 | malformed | text is 60,000 characters | 413 | `—` | — | — |  |
| RQ01 | malformed | no text field at all | 400 | `—` | — | — |  |
| RQ02 | malformed | no creator_id | 400 | `—` | — | — |  |
| RQ03 | malformed | text is a number | 400 | `—` | — | — |  |
| RQ04 | malformed | text is a list | 400 | `—` | — | — |  |
| RQ05 | malformed | text is null | 400 | `—` | — | — |  |
| RQ06 | malformed | creator_id is an object | 400 | `—` | — | — |  |
| RQ07 | malformed | body is a JSON array, not an object | 400 | `—` | — | — |  |
| RQ08 | malformed | body is unparseable JSON | 400 | `—` | — | — |  |
| RQ09 | malformed | body is empty | 400 | `—` | — | — |  |
| RQ10 | malformed | body is form-encoded, not JSON | 400 | `—` | — | — |  |
| RQ11 | malformed | body is JSON claiming to be plain text | 400 | `—` | — | — |  |
| RQ12 | malformed | deeply nested JSON | 400 | `—` | — | — |  |
| FL01_01 | flood_same_creator | 20 rapid submissions from one creator | 400 | `—` | — | — |  |
| FL01_02 | flood_same_creator | 20 rapid submissions from one creator | 400 | `—` | — | — |  |
| FL01_03 | flood_same_creator | 20 rapid submissions from one creator | 400 | `—` | — | — |  |
| FL01_04 | flood_same_creator | 20 rapid submissions from one creator | 400 | `—` | — | — |  |
| FL01_05 | flood_same_creator | 20 rapid submissions from one creator | 400 | `—` | — | — |  |
| FL01_06 | flood_same_creator | 20 rapid submissions from one creator | 400 | `—` | — | — |  |
| FL01_07 | flood_same_creator | 20 rapid submissions from one creator | 400 | `—` | — | — |  |
| FL01_08 | flood_same_creator | 20 rapid submissions from one creator | 400 | `—` | — | — |  |
| FL01_09 | flood_same_creator | 20 rapid submissions from one creator | 400 | `—` | — | — |  |
| FL01_10 | flood_same_creator | 20 rapid submissions from one creator | 400 | `—` | — | — |  |
| FL01_11 | flood_same_creator | 20 rapid submissions from one creator | 400 | `—` | — | — |  |
| FL01_12 | flood_same_creator | 20 rapid submissions from one creator | 400 | `—` | — | — |  |

---

## By family

| Family | Attacks | Auto-BROKE | Left to judge |
|---|---|---|---|
| `evasion` | 10 | 0 | 10 |
| `false_positive` | 8 | 0 | 8 |
| `flood_same_creator` | 12 | 0 | 12 |
| `malformed` | 20 | 0 | 20 |
| `prompt_injection` | 6 | 0 | 6 |

> The **false_positive** family is the one to look at hardest. Those are
> written to be genuine human writing that reads as machine-like. Every one
> your service calls AI is a real writer it would have accused.

---

## What came back

The detail behind the table. Paste the interesting failures into your
README — the ones that show something, not the ten easiest.

### EV01 — `evasion`

*Targeting:* signal two: typos raise word variety

```json
{
  "id": "EV01",
  "status": 200,
  "content_id": "e8ab7094-b85d-455c-a68d-6edd219b91d3",
  "creator_id": "attacker_EV01",
  "guess": "unsure",
  "confidence": 0.6915,
  "model_score": 0.1635,
  "style_score": 0.7434,
  "label": "We can't tell whether this was written by a person or by an AI tool. This is not a finding against you: our check often can't tell, and many people's own writing gets this result. If you'd like a person to read it, you can ask for a review.",
  "error": null,
  "verdict": ""
}
```

### EV02 — `evasion`

*Targeting:* signal two: broken-up sentences raise length spread

```json
{
  "id": "EV02",
  "status": 200,
  "content_id": "98720c9b-4081-4fcc-8de2-77d97251210f",
  "creator_id": "attacker_EV02",
  "guess": "unsure",
  "confidence": 0.6323,
  "model_score": 0.5943,
  "style_score": 0.7463,
  "label": "We can't tell whether this was written by a person or by an AI tool. This is not a finding against you: our check often can't tell, and many people's own writing gets this result. If you'd like a person to read it, you can ask for a review.",
  "error": null,
  "verdict": ""
}
```

### EV03 — `evasion`

*Targeting:* signal two: a pasted quotation changes the shape

```json
{
  "id": "EV03",
  "status": 200,
  "content_id": "7d4cf497-19e9-42f9-87aa-b654dac9519f",
  "creator_id": "attacker_EV03",
  "guess": "unsure",
  "confidence": 0.5771,
  "model_score": 0.6662,
  "style_score": 0.5474,
  "label": "We can't tell whether this was written by a person or by an AI tool. This is not a finding against you: our check often can't tell, and many people's own writing gets this result. If you'd like a person to read it, you can ask for a review.",
  "error": null,
  "verdict": ""
}
```

### EV04 — `evasion`

*Targeting:* signal one: unusual words raise perplexity

```json
{
  "id": "EV04",
  "status": 200,
  "content_id": "5369b846-3d53-41bb-9ad4-c4e17cae929b",
  "creator_id": "attacker_EV04",
  "guess": "unsure",
  "confidence": 0.6445,
  "model_score": 0.6114,
  "style_score": 0.7439,
  "label": "We can't tell whether this was written by a person or by an AI tool. This is not a finding against you: our check often can't tell, and many people's own writing gets this result. If you'd like a person to read it, you can ask for a review.",
  "error": null,
  "verdict": ""
}
```

### EV05 — `evasion`

*Targeting:* both signals: heavy human editing pass

```json
{
  "id": "EV05",
  "status": 200,
  "content_id": "89bbda8c-7b53-41c6-b067-3e4e0de6ddcc",
  "creator_id": "attacker_EV05",
  "guess": "unsure",
  "confidence": 0.678,
  "model_score": 0.3212,
  "style_score": 0.3245,
  "label": "We can't tell whether this was written by a person or by an AI tool. This is not a finding against you: our check often can't tell, and many people's own writing gets this result. If you'd like a person to read it, you can ask for a review.",
  "error": null,
  "verdict": ""
}
```

### EV06 — `evasion`

*Targeting:* signal two: one very long sentence and one very short

```json
{
  "id": "EV06",
  "status": 200,
  "content_id": "c764d937-cc81-4ea8-b463-e9a11694364c",
  "creator_id": "attacker_EV06",
  "guess": "human",
  "confidence": 0.7468,
  "model_score": 0.5727,
  "style_score": 0.1467,
  "label": "We think this was probably written by a person.",
  "error": null,
  "verdict": ""
}
```

### EV07 — `evasion`

*Targeting:* signal two: padding with punctuation

```json
{
  "id": "EV07",
  "status": 200,
  "content_id": "ebb5f9ab-16cd-4d08-b982-eaac55e0334e",
  "creator_id": "attacker_EV07",
  "guess": "unsure",
  "confidence": 0.578,
  "model_score": 0.5862,
  "style_score": 0.3673,
  "label": "We can't tell whether this was written by a person or by an AI tool. This is not a finding against you: our check often can't tell, and many people's own writing gets this result. If you'd like a person to read it, you can ask for a review.",
  "error": null,
  "verdict": ""
}
```

### EV08 — `evasion`

*Targeting:* signal one: text below the token window

```json
{
  "id": "EV08",
  "status": 400,
  "content_id": null,
  "creator_id": "attacker_EV08",
  "guess": null,
  "confidence": null,
  "model_score": null,
  "style_score": null,
  "label": null,
  "error": null,
  "verdict": ""
}
```

### EV09 — `evasion`

*Targeting:* both: AI text with a human opening paragraph bolted on

```json
{
  "id": "EV09",
  "status": 200,
  "content_id": "2e920a73-93db-47c3-a0c7-c0c4acd4191e",
  "creator_id": "attacker_EV09",
  "guess": "unsure",
  "confidence": 0.6151,
  "model_score": 0.7042,
  "style_score": 0.5854,
  "label": "We can't tell whether this was written by a person or by an AI tool. This is not a finding against you: our check often can't tell, and many people's own writing gets this result. If you'd like a person to read it, you can ask for a review.",
  "error": null,
  "verdict": ""
}
```

### EV10 — `evasion`

*Targeting:* signal two: repeated stanza structure

```json
{
  "id": "EV10",
  "status": 200,
  "content_id": "28709975-b995-4647-8d3a-19613a41c025",
  "creator_id": "attacker_EV10",
  "guess": "unsure",
  "confidence": 0.8098,
  "model_score": 0.9792,
  "style_score": 0.7533,
  "label": "We can't tell whether this was written by a person or by an AI tool. This is not a finding against you: our check often can't tell, and many people's own writing gets this result. If you'd like a person to read it, you can ask for a review.",
  "error": null,
  "verdict": ""
}
```

### FP01 — `false_positive`

*Targeting:* plain, clear human writing with no flourishes

```json
{
  "id": "FP01",
  "status": 200,
  "content_id": "78898353-2580-4a5b-adfe-e1b4a16b968c",
  "creator_id": "attacker_FP01",
  "guess": "unsure",
  "confidence": 0.5532,
  "model_score": 0.6175,
  "style_score": 0.5318,
  "label": "We can't tell whether this was written by a person or by an AI tool. This is not a finding against you: our check often can't tell, and many people's own writing gets this result. If you'd like a person to read it, you can ask for a review.",
  "error": null,
  "verdict": ""
}
```

### FP02 — `false_positive`

*Targeting:* human writing in a formal register

```json
{
  "id": "FP02",
  "status": 200,
  "content_id": "c75248ee-2b0c-4e26-93b9-89802138f80d",
  "creator_id": "attacker_FP02",
  "guess": "unsure",
  "confidence": 0.7658,
  "model_score": 0.7387,
  "style_score": 0.8471,
  "label": "We can't tell whether this was written by a person or by an AI tool. This is not a finding against you: our check often can't tell, and many people's own writing gets this result. If you'd like a person to read it, you can ask for a review.",
  "error": null,
  "verdict": ""
}
```

### FP03 — `false_positive`

*Targeting:* a non-native English speaker writing carefully

```json
{
  "id": "FP03",
  "status": 200,
  "content_id": "a54edd68-3727-43fc-9f3d-c19515606aa8",
  "creator_id": "attacker_FP03",
  "guess": "unsure",
  "confidence": 0.7249,
  "model_score": 0.8051,
  "style_score": 0.6982,
  "label": "We can't tell whether this was written by a person or by an AI tool. This is not a finding against you: our check often can't tell, and many people's own writing gets this result. If you'd like a person to read it, you can ask for a review.",
  "error": null,
  "verdict": ""
}
```

### FP04 — `false_positive`

*Targeting:* a student essay written to a rubric

```json
{
  "id": "FP04",
  "status": 200,
  "content_id": "f0edd847-ed0c-4cde-b682-ba0812a06fc9",
  "creator_id": "attacker_FP04",
  "guess": "unsure",
  "confidence": 0.7145,
  "model_score": 0.8329,
  "style_score": 0.675,
  "label": "We can't tell whether this was written by a person or by an AI tool. This is not a finding against you: our check often can't tell, and many people's own writing gets this result. If you'd like a person to read it, you can ask for a review.",
  "error": null,
  "verdict": ""
}
```

### FP05 — `false_positive`

*Targeting:* technical documentation written by a person

```json
{
  "id": "FP05",
  "status": 200,
  "content_id": "be56415b-86b1-48c9-b6ee-862ae9ecb440",
  "creator_id": "attacker_FP05",
  "guess": "unsure",
  "confidence": 0.8388,
  "model_score": 0.8005,
  "style_score": 0.9539,
  "label": "We can't tell whether this was written by a person or by an AI tool. This is not a finding against you: our check often can't tell, and many people's own writing gets this result. If you'd like a person to read it, you can ask for a review.",
  "error": null,
  "verdict": ""
}
```

### FP06 — `false_positive`

*Targeting:* a person imitating a formal template

```json
{
  "id": "FP06",
  "status": 200,
  "content_id": "e196d328-9ba4-4c0d-9996-05db4d1f9e96",
  "creator_id": "attacker_FP06",
  "guess": "unsure",
  "confidence": 0.5493,
  "model_score": 0.8814,
  "style_score": 0.4386,
  "label": "We can't tell whether this was written by a person or by an AI tool. This is not a finding against you: our check often can't tell, and many people's own writing gets this result. If you'd like a person to read it, you can ask for a review.",
  "error": null,
  "verdict": ""
}
```

### FP07 — `false_positive`

*Targeting:* human writing that repeats a phrase deliberately

```json
{
  "id": "FP07",
  "status": 200,
  "content_id": "9d81b486-7ba1-4dab-91ca-174743e92e89",
  "creator_id": "attacker_FP07",
  "guess": "unsure",
  "confidence": 0.5167,
  "model_score": 0.8816,
  "style_score": 0.3951,
  "label": "We can't tell whether this was written by a person or by an AI tool. This is not a finding against you: our check often can't tell, and many people's own writing gets this result. If you'd like a person to read it, you can ask for a review.",
  "error": null,
  "verdict": ""
}
```

### FP08 — `false_positive`

*Targeting:* very short genuine human submission

```json
{
  "id": "FP08",
  "status": 400,
  "content_id": null,
  "creator_id": "attacker_FP08",
  "guess": null,
  "confidence": null,
  "model_score": null,
  "style_score": null,
  "label": null,
  "error": null,
  "verdict": ""
}
```

### PI01 — `prompt_injection`

*Targeting:* instruction to ignore the check

```json
{
  "id": "PI01",
  "status": 200,
  "content_id": "fe7fb1ec-635c-4f7b-9fc4-13bf49c3b834",
  "creator_id": "attacker_PI01",
  "guess": "unsure",
  "confidence": 0.6238,
  "model_score": 0.4625,
  "style_score": 0.3475,
  "label": "We can't tell whether this was written by a person or by an AI tool. This is not a finding against you: our check often can't tell, and many people's own writing gets this result. If you'd like a person to read it, you can ask for a review.",
  "error": null,
  "verdict": ""
}
```

### PI02 — `prompt_injection`

*Targeting:* instruction disguised as a system message

```json
{
  "id": "PI02",
  "status": 200,
  "content_id": "1b7faaa0-ffe7-4ca4-9bed-182ca8c402fe",
  "creator_id": "attacker_PI02",
  "guess": "human",
  "confidence": 0.7586,
  "model_score": 0.2044,
  "style_score": 0.3526,
  "label": "We think this was probably written by a person.",
  "error": null,
  "verdict": ""
}
```

### PI03 — `prompt_injection`

*Targeting:* instruction wrapped in the writer's voice

```json
{
  "id": "PI03",
  "status": 200,
  "content_id": "33cc64c0-97f7-46a4-96eb-013c40f67c56",
  "creator_id": "attacker_PI03",
  "guess": "unsure",
  "confidence": 0.5684,
  "model_score": 0.5943,
  "style_score": 0.5598,
  "label": "We can't tell whether this was written by a person or by an AI tool. This is not a finding against you: our check often can't tell, and many people's own writing gets this result. If you'd like a person to read it, you can ask for a review.",
  "error": null,
  "verdict": ""
}
```

### PI04 — `prompt_injection`

*Targeting:* attempt to make the label text hostile

```json
{
  "id": "PI04",
  "status": 200,
  "content_id": "4baa827f-ec99-4c16-bd6a-b62c2c7f4971",
  "creator_id": "attacker_PI04",
  "guess": "unsure",
  "confidence": 0.5091,
  "model_score": 0.4998,
  "style_score": 0.488,
  "label": "We can't tell whether this was written by a person or by an AI tool. This is not a finding against you: our check often can't tell, and many people's own writing gets this result. If you'd like a person to read it, you can ask for a review.",
  "error": null,
  "verdict": ""
}
```

### PI05 — `prompt_injection`

*Targeting:* attempt to inject into the audit log

```json
{
  "id": "PI05",
  "status": 200,
  "content_id": "b7d94bb8-b037-43a0-a519-6feecb57f77b",
  "creator_id": "attacker_PI05",
  "guess": "unsure",
  "confidence": 0.6747,
  "model_score": 0.6401,
  "style_score": 0.2204,
  "label": "We can't tell whether this was written by a person or by an AI tool. This is not a finding against you: our check often can't tell, and many people's own writing gets this result. If you'd like a person to read it, you can ask for a review.",
  "error": null,
  "verdict": ""
}
```

### PI06 — `prompt_injection`

*Targeting:* instruction plus real human text

```json
{
  "id": "PI06",
  "status": 200,
  "content_id": "3b9ce35d-37ea-4f24-8391-ee3310d8c12e",
  "creator_id": "attacker_PI06",
  "guess": "unsure",
  "confidence": 0.5352,
  "model_score": 0.5583,
  "style_score": 0.5275,
  "label": "We can't tell whether this was written by a person or by an AI tool. This is not a finding against you: our check often can't tell, and many people's own writing gets this result. If you'd like a person to read it, you can ask for a review.",
  "error": null,
  "verdict": ""
}
```

### MF01 — `malformed`

*Targeting:* text is only whitespace

```json
{
  "id": "MF01",
  "status": 400,
  "content_id": null,
  "creator_id": "attacker_MF01",
  "guess": null,
  "confidence": null,
  "model_score": null,
  "style_score": null,
  "label": null,
  "error": null,
  "verdict": ""
}
```

### MF02 — `malformed`

*Targeting:* text is a single character

```json
{
  "id": "MF02",
  "status": 400,
  "content_id": null,
  "creator_id": "attacker_MF02",
  "guess": null,
  "confidence": null,
  "model_score": null,
  "style_score": null,
  "label": null,
  "error": null,
  "verdict": ""
}
```

### MF03 — `malformed`

*Targeting:* text is control characters

```json
{
  "id": "MF03",
  "status": 400,
  "content_id": null,
  "creator_id": "attacker_MF03",
  "guess": null,
  "confidence": null,
  "model_score": null,
  "style_score": null,
  "label": null,
  "error": null,
  "verdict": ""
}
```

### MF04 — `malformed`

*Targeting:* text is only punctuation

```json
{
  "id": "MF04",
  "status": 400,
  "content_id": null,
  "creator_id": "attacker_MF04",
  "guess": null,
  "confidence": null,
  "model_score": null,
  "style_score": null,
  "label": null,
  "error": null,
  "verdict": ""
}
```

### MF05 — `malformed`

*Targeting:* text is a very long single word

```json
{
  "id": "MF05",
  "status": 400,
  "content_id": null,
  "creator_id": "attacker_MF05",
  "guess": null,
  "confidence": null,
  "model_score": null,
  "style_score": null,
  "label": null,
  "error": null,
  "verdict": ""
}
```

### MF06 — `malformed`

*Targeting:* text is emoji only

```json
{
  "id": "MF06",
  "status": 400,
  "content_id": null,
  "creator_id": "attacker_MF06",
  "guess": null,
  "confidence": null,
  "model_score": null,
  "style_score": null,
  "label": null,
  "error": null,
  "verdict": ""
}
```

### MF07 — `malformed`

*Targeting:* text is right-to-left script

```json
{
  "id": "MF07",
  "status": 400,
  "content_id": null,
  "creator_id": "attacker_MF07",
  "guess": null,
  "confidence": null,
  "model_score": null,
  "style_score": null,
  "label": null,
  "error": null,
  "verdict": ""
}
```

### MF08 — `malformed`

*Targeting:* text is 60,000 characters

```json
{
  "id": "MF08",
  "status": 413,
  "content_id": null,
  "creator_id": "attacker_MF08",
  "guess": null,
  "confidence": null,
  "model_score": null,
  "style_score": null,
  "label": null,
  "error": null,
  "verdict": ""
}
```

### RQ01 — `malformed`

*Targeting:* no text field at all

```json
{
  "id": "RQ01",
  "status": 400,
  "content_id": null,
  "creator_id": "attacker_RQ01",
  "guess": null,
  "confidence": null,
  "model_score": null,
  "style_score": null,
  "label": null,
  "error": null,
  "verdict": ""
}
```

### RQ02 — `malformed`

*Targeting:* no creator_id

```json
{
  "id": "RQ02",
  "status": 400,
  "content_id": null,
  "creator_id": null,
  "guess": null,
  "confidence": null,
  "model_score": null,
  "style_score": null,
  "label": null,
  "error": null,
  "verdict": ""
}
```

### RQ03 — `malformed`

*Targeting:* text is a number

```json
{
  "id": "RQ03",
  "status": 400,
  "content_id": null,
  "creator_id": "attacker_RQ03",
  "guess": null,
  "confidence": null,
  "model_score": null,
  "style_score": null,
  "label": null,
  "error": null,
  "verdict": ""
}
```

### RQ04 — `malformed`

*Targeting:* text is a list

```json
{
  "id": "RQ04",
  "status": 400,
  "content_id": null,
  "creator_id": "attacker_RQ04",
  "guess": null,
  "confidence": null,
  "model_score": null,
  "style_score": null,
  "label": null,
  "error": null,
  "verdict": ""
}
```

### RQ05 — `malformed`

*Targeting:* text is null

```json
{
  "id": "RQ05",
  "status": 400,
  "content_id": null,
  "creator_id": "attacker_RQ05",
  "guess": null,
  "confidence": null,
  "model_score": null,
  "style_score": null,
  "label": null,
  "error": null,
  "verdict": ""
}
```

### RQ06 — `malformed`

*Targeting:* creator_id is an object

```json
{
  "id": "RQ06",
  "status": 400,
  "content_id": null,
  "creator_id": {
    "id": "x"
  },
  "guess": null,
  "confidence": null,
  "model_score": null,
  "style_score": null,
  "label": null,
  "error": null,
  "verdict": ""
}
```

### RQ07 — `malformed`

*Targeting:* body is a JSON array, not an object

```json
{
  "id": "RQ07",
  "status": 400,
  "content_id": null,
  "creator_id": null,
  "guess": null,
  "confidence": null,
  "model_score": null,
  "style_score": null,
  "label": null,
  "error": null,
  "verdict": ""
}
```

### RQ08 — `malformed`

*Targeting:* body is unparseable JSON

```json
{
  "id": "RQ08",
  "status": 400,
  "content_id": null,
  "creator_id": null,
  "guess": null,
  "confidence": null,
  "model_score": null,
  "style_score": null,
  "label": null,
  "error": null,
  "verdict": ""
}
```

### RQ09 — `malformed`

*Targeting:* body is empty

```json
{
  "id": "RQ09",
  "status": 400,
  "content_id": null,
  "creator_id": null,
  "guess": null,
  "confidence": null,
  "model_score": null,
  "style_score": null,
  "label": null,
  "error": null,
  "verdict": ""
}
```

### RQ10 — `malformed`

*Targeting:* body is form-encoded, not JSON

```json
{
  "id": "RQ10",
  "status": 400,
  "content_id": null,
  "creator_id": null,
  "guess": null,
  "confidence": null,
  "model_score": null,
  "style_score": null,
  "label": null,
  "error": null,
  "verdict": ""
}
```

### RQ11 — `malformed`

*Targeting:* body is JSON claiming to be plain text

```json
{
  "id": "RQ11",
  "status": 400,
  "content_id": null,
  "creator_id": null,
  "guess": null,
  "confidence": null,
  "model_score": null,
  "style_score": null,
  "label": null,
  "error": null,
  "verdict": ""
}
```

### RQ12 — `malformed`

*Targeting:* deeply nested JSON

```json
{
  "id": "RQ12",
  "status": 400,
  "content_id": null,
  "creator_id": "attacker_RQ12",
  "guess": null,
  "confidence": null,
  "model_score": null,
  "style_score": null,
  "label": null,
  "error": null,
  "verdict": ""
}
```

### FL01_01 — `flood_same_creator`

*Targeting:* 20 rapid submissions from one creator

```json
{
  "id": "FL01_01",
  "status": 400,
  "content_id": null,
  "creator_id": "attacker_flood",
  "guess": null,
  "confidence": null,
  "model_score": null,
  "style_score": null,
  "label": null,
  "error": null,
  "verdict": ""
}
```

### FL01_02 — `flood_same_creator`

*Targeting:* 20 rapid submissions from one creator

```json
{
  "id": "FL01_02",
  "status": 400,
  "content_id": null,
  "creator_id": "attacker_flood",
  "guess": null,
  "confidence": null,
  "model_score": null,
  "style_score": null,
  "label": null,
  "error": null,
  "verdict": ""
}
```

### FL01_03 — `flood_same_creator`

*Targeting:* 20 rapid submissions from one creator

```json
{
  "id": "FL01_03",
  "status": 400,
  "content_id": null,
  "creator_id": "attacker_flood",
  "guess": null,
  "confidence": null,
  "model_score": null,
  "style_score": null,
  "label": null,
  "error": null,
  "verdict": ""
}
```

### FL01_04 — `flood_same_creator`

*Targeting:* 20 rapid submissions from one creator

```json
{
  "id": "FL01_04",
  "status": 400,
  "content_id": null,
  "creator_id": "attacker_flood",
  "guess": null,
  "confidence": null,
  "model_score": null,
  "style_score": null,
  "label": null,
  "error": null,
  "verdict": ""
}
```

### FL01_05 — `flood_same_creator`

*Targeting:* 20 rapid submissions from one creator

```json
{
  "id": "FL01_05",
  "status": 400,
  "content_id": null,
  "creator_id": "attacker_flood",
  "guess": null,
  "confidence": null,
  "model_score": null,
  "style_score": null,
  "label": null,
  "error": null,
  "verdict": ""
}
```

### FL01_06 — `flood_same_creator`

*Targeting:* 20 rapid submissions from one creator

```json
{
  "id": "FL01_06",
  "status": 400,
  "content_id": null,
  "creator_id": "attacker_flood",
  "guess": null,
  "confidence": null,
  "model_score": null,
  "style_score": null,
  "label": null,
  "error": null,
  "verdict": ""
}
```

### FL01_07 — `flood_same_creator`

*Targeting:* 20 rapid submissions from one creator

```json
{
  "id": "FL01_07",
  "status": 400,
  "content_id": null,
  "creator_id": "attacker_flood",
  "guess": null,
  "confidence": null,
  "model_score": null,
  "style_score": null,
  "label": null,
  "error": null,
  "verdict": ""
}
```

### FL01_08 — `flood_same_creator`

*Targeting:* 20 rapid submissions from one creator

```json
{
  "id": "FL01_08",
  "status": 400,
  "content_id": null,
  "creator_id": "attacker_flood",
  "guess": null,
  "confidence": null,
  "model_score": null,
  "style_score": null,
  "label": null,
  "error": null,
  "verdict": ""
}
```

### FL01_09 — `flood_same_creator`

*Targeting:* 20 rapid submissions from one creator

```json
{
  "id": "FL01_09",
  "status": 400,
  "content_id": null,
  "creator_id": "attacker_flood",
  "guess": null,
  "confidence": null,
  "model_score": null,
  "style_score": null,
  "label": null,
  "error": null,
  "verdict": ""
}
```

### FL01_10 — `flood_same_creator`

*Targeting:* 20 rapid submissions from one creator

```json
{
  "id": "FL01_10",
  "status": 400,
  "content_id": null,
  "creator_id": "attacker_flood",
  "guess": null,
  "confidence": null,
  "model_score": null,
  "style_score": null,
  "label": null,
  "error": null,
  "verdict": ""
}
```

### FL01_11 — `flood_same_creator`

*Targeting:* 20 rapid submissions from one creator

```json
{
  "id": "FL01_11",
  "status": 400,
  "content_id": null,
  "creator_id": "attacker_flood",
  "guess": null,
  "confidence": null,
  "model_score": null,
  "style_score": null,
  "label": null,
  "error": null,
  "verdict": ""
}
```

### FL01_12 — `flood_same_creator`

*Targeting:* 20 rapid submissions from one creator

```json
{
  "id": "FL01_12",
  "status": 400,
  "content_id": null,
  "creator_id": "attacker_flood",
  "guess": null,
  "confidence": null,
  "model_score": null,
  "style_score": null,
  "label": null,
  "error": null,
  "verdict": ""
}
```
