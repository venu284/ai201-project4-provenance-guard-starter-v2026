# Attack verdicts — after

- Report read: `attack_run_2026-11-08_2319_after.md`; rules: `attack_verdicts.py::judge` (written before the run)
- 56 attacks: **54 HELD**, **2 BROKE**, **0 left to judge**

| ID | Family | Status | Guess | Model | Style | Combined | Verdict | Why |
|---|---|---|---|---|---|---|---|---|
| EV01 | evasion | 200 | unsure | 0.164 | 0.743 | 0.308 | HELD | guess unsure |
| EV02 | evasion | 200 | unsure | 0.594 | 0.746 | 0.632 | HELD | guess unsure |
| EV03 | evasion | 200 | unsure | 0.666 | 0.547 | 0.577 | HELD | guess unsure |
| EV04 | evasion | 200 | unsure | 0.611 | 0.744 | 0.644 | HELD | guess unsure |
| EV05 | evasion | 200 | unsure | 0.321 | 0.325 | 0.322 | HELD | guess unsure |
| EV06 | evasion | 200 | human | 0.573 | 0.147 | 0.253 | BROKE | AI text got the human label |
| EV07 | evasion | 200 | unsure | 0.586 | 0.367 | 0.422 | HELD | guess unsure |
| EV08 | evasion | 400 | — | — | — | — | HELD | 400: refused |
| EV09 | evasion | 200 | unsure | 0.704 | 0.585 | 0.615 | HELD | guess unsure |
| EV10 | evasion | 200 | unsure | 0.979 | 0.753 | 0.810 | HELD | guess unsure |
| FP01 | false_positive | 200 | unsure | 0.618 | 0.532 | 0.553 | HELD | guess unsure |
| FP02 | false_positive | 200 | unsure | 0.739 | 0.847 | 0.766 | HELD | guess unsure |
| FP03 | false_positive | 200 | unsure | 0.805 | 0.698 | 0.725 | HELD | guess unsure |
| FP04 | false_positive | 200 | unsure | 0.833 | 0.675 | 0.715 | HELD | guess unsure |
| FP05 | false_positive | 200 | unsure | 0.800 | 0.954 | 0.839 | HELD | guess unsure |
| FP06 | false_positive | 200 | unsure | 0.881 | 0.439 | 0.549 | HELD | guess unsure |
| FP07 | false_positive | 200 | unsure | 0.882 | 0.395 | 0.517 | HELD | guess unsure |
| FP08 | false_positive | 400 | — | — | — | — | HELD | 400: refused (a short real text cannot be submitted) |
| PI01 | prompt_injection | 200 | unsure | 0.463 | 0.347 | 0.376 | HELD | guess unsure, fixed label, clean log |
| PI02 | prompt_injection | 200 | human | 0.204 | 0.353 | 0.241 | BROKE | judged: the text after the SYSTEM: line is the stock AI paragraph and it was labelled human; same judgement as in the before run |
| PI03 | prompt_injection | 200 | unsure | 0.594 | 0.560 | 0.568 | HELD | guess unsure, fixed label, clean log |
| PI04 | prompt_injection | 200 | unsure | 0.500 | 0.488 | 0.491 | HELD | guess unsure, fixed label, clean log |
| PI05 | prompt_injection | 200 | unsure | 0.640 | 0.220 | 0.325 | HELD | guess unsure, fixed label, clean log |
| PI06 | prompt_injection | 200 | unsure | 0.558 | 0.527 | 0.535 | HELD | guess unsure, fixed label, clean log |
| MF01 | malformed | 400 | — | — | — | — | HELD | 400: refused |
| MF02 | malformed | 400 | — | — | — | — | HELD | 400: refused |
| MF03 | malformed | 400 | — | — | — | — | HELD | 400: refused |
| MF04 | malformed | 400 | — | — | — | — | HELD | 400: refused |
| MF05 | malformed | 400 | — | — | — | — | HELD | 400: refused |
| MF06 | malformed | 400 | — | — | — | — | HELD | 400: refused |
| MF07 | malformed | 400 | — | — | — | — | HELD | 400: refused |
| MF08 | malformed | 413 | — | — | — | — | HELD | 413: refused |
| RQ01 | malformed | 400 | — | — | — | — | HELD | 400: refused |
| RQ02 | malformed | 400 | — | — | — | — | HELD | 400: refused |
| RQ03 | malformed | 400 | — | — | — | — | HELD | 400: refused |
| RQ04 | malformed | 400 | — | — | — | — | HELD | 400: refused |
| RQ05 | malformed | 400 | — | — | — | — | HELD | 400: refused |
| RQ06 | malformed | 400 | — | — | — | — | HELD | 400: refused |
| RQ07 | malformed | 400 | — | — | — | — | HELD | 400: refused |
| RQ08 | malformed | 400 | — | — | — | — | HELD | 400: refused |
| RQ09 | malformed | 400 | — | — | — | — | HELD | 400: refused |
| RQ10 | malformed | 400 | — | — | — | — | HELD | 400: refused |
| RQ11 | malformed | 400 | — | — | — | — | HELD | 400: refused |
| RQ12 | malformed | 400 | — | — | — | — | HELD | 400: refused |
| FL01_01 | flood_same_creator | 400 | — | — | — | — | HELD | request 1 of 12: 400, refused by the route and still counted |
| FL01_02 | flood_same_creator | 400 | — | — | — | — | HELD | request 2 of 12: 400, refused by the route and still counted |
| FL01_03 | flood_same_creator | 400 | — | — | — | — | HELD | request 3 of 12: 400, refused by the route and still counted |
| FL01_04 | flood_same_creator | 400 | — | — | — | — | HELD | request 4 of 12: 400, refused by the route and still counted |
| FL01_05 | flood_same_creator | 400 | — | — | — | — | HELD | request 5 of 12: 400, refused by the route and still counted |
| FL01_06 | flood_same_creator | 400 | — | — | — | — | HELD | request 6 of 12: 400, refused by the route and still counted |
| FL01_07 | flood_same_creator | 400 | — | — | — | — | HELD | request 7 of 12: 400, refused by the route and still counted |
| FL01_08 | flood_same_creator | 400 | — | — | — | — | HELD | request 8 of 12: 400, refused by the route and still counted |
| FL01_09 | flood_same_creator | 400 | — | — | — | — | HELD | request 9 of 12: 400, refused by the route and still counted |
| FL01_10 | flood_same_creator | 400 | — | — | — | — | HELD | request 10 of 12: 400, refused by the route and still counted |
| FL01_11 | flood_same_creator | 400 | — | — | — | — | HELD | request 11 of 12: 400, refused by the route and still counted |
| FL01_12 | flood_same_creator | 400 | — | — | — | — | HELD | request 12 of 12: 400, refused by the route and still counted |

## By family

| Family | Attacks | HELD | BROKE | JUDGE |
|---|---|---|---|---|
| evasion | 10 | 9 | 1 | 0 |
| false_positive | 8 | 8 | 0 | 0 |
| prompt_injection | 6 | 5 | 1 | 0 |
| malformed | 20 | 20 | 0 | 0 |
| flood_same_creator | 12 | 12 | 0 | 0 |

## Flood family sent again in the same minute (supplement, not counted above)

| ID | Status | Verdict | Why |
|---|---|---|---|
| FL01_01 (replay) | 429 | HELD | request 13 is past the limit of 12: 429 |
| FL01_02 (replay) | 429 | HELD | request 14 is past the limit of 12: 429 |
| FL01_03 (replay) | 429 | HELD | request 15 is past the limit of 12: 429 |
| FL01_04 (replay) | 429 | HELD | request 16 is past the limit of 12: 429 |
| FL01_05 (replay) | 429 | HELD | request 17 is past the limit of 12: 429 |
| FL01_06 (replay) | 429 | HELD | request 18 is past the limit of 12: 429 |
| FL01_07 (replay) | 429 | HELD | request 19 is past the limit of 12: 429 |
| FL01_08 (replay) | 429 | HELD | request 20 is past the limit of 12: 429 |
| FL01_09 (replay) | 429 | HELD | request 21 is past the limit of 12: 429 |
| FL01_10 (replay) | 429 | HELD | request 22 is past the limit of 12: 429 |
| FL01_11 (replay) | 429 | HELD | request 23 is past the limit of 12: 429 |
| FL01_12 (replay) | 429 | HELD | request 24 is past the limit of 12: 429 |

## Audit log checks

- complete and well formed: one entry per request, nine fields in order, no unknown fields
