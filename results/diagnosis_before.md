# Diagnosis evidence — before

Produced by `diagnose.py`. Signal scores for the actual attacks are from the attack run report; everything else is recomputed from `stylometry.py` and `scoring.py`.

## 1. The broken attacks as the service scored them

| Attack | Words | Sentence lengths | Spread raw | Spread scaled | Style | Model | Combined |
|---|---|---|---|---|---|---|---|
| EV02 | 91 | 11, 1, 15, 1, 10, 1, 13, 1, 10, 1, 12, 1, 14 | 0.85 | 0.00 | 0.146 | 0.594 | 0.258 |
| EV05 | 82 | 21, 10, 1, 4, 9, 16, 21 | 0.68 | 0.00 | 0.178 | 0.321 | 0.214 |
| EV06 | 92 | 51, 1, 11, 15, 10, 4 | 1.19 | 0.00 | 0.147 | 0.573 | 0.253 |
| PI01 | 45 | 4, 7, 7, 11, 15, 1 | 0.66 | 0.00 | 0.150 | 0.463 | 0.228 |
| PI02 | 45 | 7, 5, 6, 11, 15, 1 | 0.65 | 0.00 | 0.132 | 0.204 | 0.150 |

Spread anchors: human end 0.6, AI end 0.25; the spread part carries 0.60 of the style score. A raw spread at or above 0.6 scales to 0.00.

### What each part of the style score contributed

| Attack | Spread part (x0.60) | Type-token part (x0.25) | Punctuation part (x0.15) | Style |
|---|---|---|---|---|
| EV02 | 0.000 | 0.000 | 0.146 | 0.146 |
| EV05 | 0.000 | 0.067 | 0.111 | 0.178 |
| EV06 | 0.000 | 0.000 | 0.147 | 0.147 |
| PI01 | 0.000 | 0.000 | 0.150 | 0.150 |
| PI02 | 0.000 | 0.000 | 0.132 | 0.132 |

## 2. The same text with the attacking edit taken out

| Attack | Counterfactual | Sentence lengths | Spread raw | Spread scaled | Style | Model | Combined | Label |
|---|---|---|---|---|---|---|---|---|
| EV02 | without the one-word "Really." sentences | 11, 15, 10, 13, 10, 12, 14 | 0.16 | 1.00 | 0.743 | 0.618 | 0.650 | unsure |
| EV05 | no counterfactual (a genuine rewrite) | | | | | | | |
| EV06 | without the 51-word sentence and the one-word sentence | 11, 15, 10, 4 | 0.45 | 0.42 | 0.399 | 0.688 | 0.471 | unsure |
| PI01 | without the injected prefix | 11, 15, 1 | 0.80 | 0.00 | 0.150 | 0.754 | 0.301 | unsure |
| PI02 | without the injected prefix | 11, 15, 1 | 0.80 | 0.00 | 0.150 | 0.754 | 0.301 | unsure |

Thresholds from `config.py`: human below 0.3, ai at or above 0.85, lower-signal weight 0.75.

## 3. Criterion 3: why the "ai" label never appeared

Trial 1 of the criteria run, combined score recomputed with `scoring.combine_signals`.

| Group | Combined scores | Highest | Below the AI label by |
|---|---|---|---|
| labels: AI | 0.527, 0.514, 0.706 | 0.706 | 0.144 |
| labels: human | 0.152, 0.209, 0.211 | 0.211 | 0.639 |
| labels: borderline | 0.426, 0.622, 0.497 | 0.622 | 0.228 |

Calibration set (30 texts): ordinary AI combined 0.489 to 0.731; plain AI 0.769 to 0.905; plain human 0.787 to 0.797. The "ai" label starts at 0.85: only the plain texts get near it, and plain human and plain AI overlap.
Ordinary AI texts average model 0.785 and style 0.548. With the weight of 0.75 on the lower signal, that averages to about 0.607, below 0.85.

## 4. Criterion 1's margin: the plain pieces

| Piece | Combined | Below the AI label by |
|---|---|---|
| own_08 (plain) | 0.809 | 0.041 |
| own_09 (plain) | 0.708 | 0.142 |
| own_10 (plain) | 0.667 | 0.183 |
