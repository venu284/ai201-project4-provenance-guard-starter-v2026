# Before and after (before vs after)

Produced by `compare_runs.py` from the verdict files and the criteria run reports.

## Attack set, by family

| Family | Attacks | Held before > after | Broke before > after |
|---|---|---|---|
| evasion | 10 | 7 > 9 | 3 > 1 |
| false_positive | 8 | 8 > 8 | 0 > 0 |
| prompt_injection | 6 | 4 > 5 | 2 > 1 |
| malformed | 20 | 20 > 20 | 0 > 0 |
| flood_same_creator | 12 | 12 > 12 | 0 > 0 |
| **all** | 56 | 51 > 54 | 5 > 2 |

## Attacks that moved

| ID | Family | Guess before > after | Combined before > after | Verdict before > after |
|---|---|---|---|---|
| EV02 | evasion | human > unsure | 0.258 > 0.632 | BROKE > HELD |
| EV03 | evasion | unsure > unsure | 0.456 > 0.577 | HELD > HELD |
| EV05 | evasion | human > unsure | 0.214 > 0.322 | BROKE > HELD |
| EV09 | evasion | unsure > unsure | 0.445 > 0.615 | HELD > HELD |
| PI01 | prompt_injection | human > unsure | 0.228 > 0.376 | BROKE > HELD |
| PI02 | prompt_injection | human > human | 0.150 > 0.241 | BROKE > BROKE |

50 of 56 attacks are unchanged in guess, combined score and verdict.

## The five criteria

| Criterion | Before (runs 1, 2, 3) | After (runs 1, 2, 3) | Verdict before > after |
|---|---|---|---|
| 1. My own writing flagged as AI | 0/10 / 0/10 / 0/10 | 0/10 / 0/10 / 0/10 | MET > MET |
| 2. Clearly-AI and clearly-human texts score far apart | 0.369 / 0.369 / 0.369 | 0.369 / 0.369 / 0.369 | MET > MET |
| 3. All three labels are reachable | 2/3 labels, 3/3 unsure / 2/3 labels, 3/3 unsure / 2/3 labels, 3/3 unsure | 2/3 labels, 3/3 unsure / 2/3 labels, 3/3 unsure / 2/3 labels, 3/3 unsure | MISSED > MISSED |
| 4. An appeal always changes status and is recorded | 5/5, unknown id 404 / 5/5, unknown id 404 / 5/5, unknown id 404 | 5/5, unknown id 404 / 5/5, unknown id 404 / 5/5, unknown id 404 | MET > MET |
| 5. Bad input never crashes the service | 8/8 / 8/8 / 8/8 | 8/8 / 8/8 / 8/8 | MET > MET |

## What it cost: the ten own-writing pieces (trial 1)

| Piece | Combined before > after | Label before > after | Below the AI label by (after) |
|---|---|---|---|
| own_01 | 0.383 > 0.383 | unsure > unsure | 0.467 |
| own_02 | 0.228 > 0.228 | human > human | 0.622 |
| own_03 | 0.278 > 0.278 | human > human | 0.572 |
| own_04 | 0.109 > 0.109 | human > human | 0.741 |
| own_05 | 0.261 > 0.261 | human > human | 0.589 |
| own_06 | 0.292 > 0.357 | human > unsure | 0.493 |
| own_07 | 0.252 > 0.252 | human > human | 0.598 |
| own_08 (plain) | 0.809 > 0.809 | unsure > unsure | 0.041 |
| own_09 (plain) | 0.708 > 0.767 | unsure > unsure | 0.083 |
| own_10 (plain) | 0.667 > 0.811 | unsure > unsure | 0.039 |

## The success test written before the change

- (a) fewer broken attacks: **PASS** (5 broke before, 2 after)
- (b) no real-writer text newly labelled ai: **PASS** (newly accused: none)
- (c) no MET criterion became MISSED: **PASS** (became MISSED: none)
