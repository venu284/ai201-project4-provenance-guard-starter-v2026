# Criteria verdicts — before

- Report read: `run_2026-11-08_2232_before.md`; rules: `eval_verdicts.py` (committed before the run)

| Criterion | Target | Run 1 | Run 2 | Run 3 | Verdict |
|---|---|---|---|---|---|
| 1. My own writing flagged as AI | at most 1 of 10 labelled AI | 0/10 | 0/10 | 0/10 | MET |
| 2. Clearly-AI and clearly-human texts score far apart | mean combined gap of AI over human at least 0.30 | 0.369 | 0.369 | 0.369 | MET |
| 3. All three labels are reachable | all 3 labels appear; at least 2 of 3 borderline are unsure | 2/3 labels, 3/3 unsure | 2/3 labels, 3/3 unsure | 2/3 labels, 3/3 unsure | MISSED |
| 4. An appeal always changes status and is recorded | 5 of 5 appeals: 200, under_review, one new entry; unknown id 404, no under_review entry | 5/5, unknown id 404 | 5/5, unknown id 404 | 5/5, unknown id 404 | MET |
| 5. Bad input never crashes the service | 8 of 8 get the listed code, no 500, one rejection entry each | 8/8 | 8/8 | 8/8 | MET |

- Trials identical on every criterion: **yes**
