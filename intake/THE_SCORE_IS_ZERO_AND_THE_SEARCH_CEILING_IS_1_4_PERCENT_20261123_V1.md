# The score is zero on 500, and the search ceiling is 1.4%

**Zero model calls. Zero parameters. Read from two existing records; nothing re-run, nothing
re-derived from memory.**

## The number, against 500

| | tasks | of 500 Verified |
|---|---|---|
| Search ceiling — a resolving candidate exists among the 20 searched | 7 | **1.4%** |
| As shipped — the submission survives the whole suite | 4 | **0.8%** |
| Top agent on the same 500, as recorded in this repo | — | **78.80%** |

Two honest framings, and the second is the one that matters:

- Against **500**, the answer is **0.8%** as shipped and **1.4%** even if selection were perfect.
  The records cover the Django slice only (231 tasks, 225 judged), so 7/225 = 3.1% is being
  extrapolated to 500 by treating the other 269 tasks as zero. That is the pessimistic reading
  and it is the correct one: **no non-Django task was searched at all** in these records.
- Against **231 Django tasks**, the answer is 4/225 = **1.8%** as shipped and 7/225 = **3.1%**
  as a hard ceiling.

## The failure is two failures, and they are not the same size

This is the finding the two records were opened to settle, and it landed somewhere I did not
expect.

```
judged tasks                                         225
search made at least one candidate                   128   (57%)
search ever resolved anything (any of 20 candidates)   7   (3.1%)
shipped, after whole-suite selection                   4   (1.8%)
```

**Failure A — generation, 94×.** The search found a candidate for 128 of 225 tasks and a
*resolving* candidate for 7. Of 2,422 candidates run, 10 resolved anything. So the machinery can
locate the right function (`file-given keeps 0.909` from the earlier ceiling measurement) and
still cannot produce the edit. This is the dominant loss, and no improvement to selection
touches it.

**Failure B — selection, exactly 2 tasks.** Of the 7 tasks that were ever resolvable,
whole-suite confirmation killed 3 under the single submission that was actually run — 5
candidates, which kept the suite on 4 (`11066, 15368, 15814, 16569`) and broke 8 tests elsewhere
on `12155`. But a separate field of the same record,
`tasks_with_a_candidate_run_that_keeps_the_whole_suite`, names **6** tasks where *some* candidate
that was made survives a whole-suite run. The two extra are `11163` and `15467`.

So the loss decomposes exactly:

```
7  resolved under the task's own tests
6  have a candidate that also survives the whole suite
4  shipped, because the submission was the first five candidates in a fixed order
```

**Selection costs exactly 2 tasks — a 50% relative loss (4 vs 6) for no reason but the ordering
of a list and a budget of five runs.** That is the cheapest defect in the whole record, and it
does not require a model or a new mechanism: run more than 5 of the 20 already-generated
candidates. `within__tasks_resolved` in the count record (5 at n=1, 6 at n=5, 7 at n=10, 7 at
n=20) says n=10 recovers the last one.

## What this says about the thesis, stated plainly

The plan's premise is that a zero-model-call organ can substitute for a model by *searching,
not remembering*. On the hardest open benchmark slice that premise is measurably false at the
current stage: **1.4% search ceiling against the 78.80% top agent recorded for these same 500 tasks**, with the dominant gap in
generation, not in anything the interrogation loop controls.

The interrogation work in this PR is not what closes that gap. It is the piece that makes a
surface's behaviour *known* rather than guessed — 17 flags of 17 programs certified, 0 falsified,
6 witnesses proved optimal. But `interrogate` answers "what does this program do", and
SWE-bench asks "write this edit". Those are different organs, and this record is the measurement
that stops anyone claiming the first substitutes for the second.

## Limits of this record, stated so they cannot be forgotten

- Only the Django slice was searched. The 1.4% figure assumes 0/269 on everything else.
- "Resolving" is measured under the task's own tests, not the whole suite; whole-suite
  confirmation was run for one submission of five.
- Selection was run once, on the first five candidates in a fixed order. Nothing here measures
  whether a *better* selection rule over 20 candidates recovers 6 rather than 4 — the
  `within__tasks_resolved` table (5 at n=1, 6 at n=5, 7 at n=10, 7 at n=20) suggests n=10 would.
  That is the next cheap experiment and it is not done.
- No comparison to a model-driven baseline on identical candidates was made here. The 78.80%
  figure is quoted from this repo's own record, not measured in this session:
  `canonical/verification/CANDIDATE_UNDER_THE_TASKS_TESTS_SWEBENCH_VERIFIED_DJANGO_20261113_V1.json`
  -> `"the top score falls from 78.80% to 62.20%"` under stronger tests applied to 50.2% of the
  500 tasks. Even the stronger-test figure, 62.20%, is 44x this record's ceiling.

**Sources (read, not remembered):**
`canonical/verification/CANDIDATE_UNDER_THE_TASKS_TESTS_SWEBENCH_VERIFIED_DJANGO_20261113_V1.json`,
`canonical/verification/RESOLVING_CANDIDATE_UNDER_THE_WHOLE_SUITE_SWEBENCH_VERIFIED_DJANGO_20261113_V1.json`.
