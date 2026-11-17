# Solved by the judge that can see: 3 of 4 published bugs, and two claims of mine it overturned

**17 November 2026** · branch `arena/7a191f7f-brain` · base `e2fff59b` · authority **NONE**
(producer-run) · receipt `canonical/verification/SOLVE_WITH_A_CALIBRATED_JUDGE_20261117_V1.json` ·
tool `canonical/tools/solve_with_a_calibrated_judge_v1.py` · 23 tests

Last session measured the instrument and found it blind: the cheap judge rejected the corpus's own
correct program on 7 of 31 published QuixBugs bugs. The next step is not another audit. It is to put
that judge behind a search and see whether bugs get fixed. They do — **three of four**, decided by the
corpus's own `pytest`, with the answer key absent from every copy the search touched — and the run
also overturned two things I said last session.

---

## 1. The result

Run: `canonical/tools/solve_with_a_calibrated_judge_v1.py --quixbugs /tmp/QuixBugs --tasks flatten
hanoi sqrt kheapsort --candidate-cap 20000 --wall-budget 900`, corpus at `4257f44b`, 27,510 candidates
in 304.3 s, zero model calls, zero network calls at run time.

| task | stage | space | judged | seconds | the edit the search found | corpus `pytest` |
|---|---|---|---|---|---|---|
| `flatten` | `CANDIDATE_FOUND` | 5,697 | **4,250** | 4.7 | `REPLACE` line 7 → `x` | **pass** |
| `hanoi` | `CANDIDATE_FOUND` | 17,395 | **11,850** | 12.5 | `REPLACE` line 6 → `end` | **pass** |
| `sqrt` | `CANDIDATE_FOUND` | 7,164 | **3,100** | 94.4 | `REPLACE` line 4 → `(approx) ** 2` | **pass** |
| `kheapsort` | `SPACE_EXHAUSTED` | 8,310 | 8,310 | 192.7 | — none exists in the space | — |

The previous run of the same loop, with the judge calibrated but nothing else measured, solved one of
five tasks in 461.9 s and burned 12,600 candidates on four tasks that ended `BUDGET_EXHAUSTED`. The
difference is not budget. It is four measurements, and every one of them was forced by a specific
failure of the previous run rather than chosen in advance.

## 2. What the failing run taught, one link at a time

### 2.1 The test file transforms the data once, not recursively

`judge_the_judge_v1` already knew that `hanoi`'s test file rewrites its own expectations:

```python
testdata = [[inp, [tuple(x) for x in out]] for inp, out in testdata]
```

I implemented that as a recursive list→tuple walk. It is not the same assertion. The corpus wants
`[(1, 3)]`; the corrected program returns `[(1, 3)]`; the recursive walk turned the expected data into
`((1, 3),)`, so **the judge rejected the corpus's own answer on every case**. The run then judged all
17,395 candidates and reported `SPACE_EXHAUSTED` — a claim about the space that was a defect of the
instrument, which is precisely the failure mode the last session named. Fixed by doing what the line
does, one level, nothing more; `hanoi` was solved twelve seconds after the fix.

### 2.2 The test file also says what *equal* means

`sqrt`'s test is not an equality test:

```python
assert sqrt(*input_data) == pytest.approx(expected, abs=input_data[-1])
```

The tolerance is in the test file, and its value is the last argument of the case. The audit had
recorded `sqrt` as `VALUE_DISAGREES` and called it inadmissible. It was not a disagreement about the
answer; it was my comparison that was wrong. The judge now reads `pytest.approx` from the test file and
applies the same tolerance. `sqrt` was solved in 94 s, and the defective program is still rejected.
**A judge must be as permissive as the test it claims to be, or it is not that test.**

### 2.3 A clock sized from a program that never returns is not a clock

The previous fix was to price each case by what the defective program costs on that case — correct,
and it fixed the exponential references. But `sqrt`'s defective program **hangs** on six of seven cases, so
the "cost" of those cases came out as the 2 s cap, and every looping candidate then cost 2 s. The run
judged 700 candidates in 615 s. A program that never returned has not told you how long an answer may
take; those cases now fall back to the base clock (50 ms), and the space of 7,164 finished in 94 s.
**Cost is measured per case, and an unmeasurable cost is not a large cost.**

### 2.4 The price of judging is measured, not assumed

Chunks were priced by a formula from the clock. `kheapsort` spends 1,318 s on 6,300 candidates that
cost 1 ms each, because 488 of its candidates kill or hang their child, and each kill was bisected with
a 5 s floor — eight levels deep. Two changes: the running estimate of cost per candidate is measured
from completed chunks (0.7 old + 0.3 new), and a sub-chunk gets `max(0.35, 3 × measured × size)`.
`kheapsort`'s whole space then cost **192.7 s instead of 1,318 s**, with more candidates judged.

### 2.5 A child must not outlive its judge

A killed parent left a child spinning at 99.6 % CPU for fourteen minutes, across the following run.
Children now set `PR_SET_PDEATHSIG`, and carry a 256 MB address-space ceiling and a CPU ceiling, so a
candidate that tries to allocate its way out of being wrong fails in the child. `terminate()` is
followed by `kill()`.

## 3. The order of the space

A correct judge is not a search. With natural order, 12,600 candidates found nothing. The space is
ordered by the lines the failure actually executes — `executed_lines()` on a case the defective program
fails. It is knowledge-free: it reads the defective program's behaviour on an input it gets wrong,
never the answer. `hanoi` reached its answer at 11,850 of 17,395 with 7 warm lines; `sqrt` at 3,100 of
7,164. `flatten` (`4,250`) and `kheapsort` had no warm lines recorded, and are un-ordered.

This is the oldest idea in automated program repair — localise, transform, rank — with the ranking
signal taken from the failing execution instead of a model's log-probabilities
([RING, 2022](https://arxiv.org/pdf/2208.11640v1)) or an LLM's reasoning about candidate files
([RGFL, 2026](https://www.arxiv.org/pdf/2601.18044)). The difference is what the ranker costs: this one
is a set of line numbers from one run of a program the solver already had.

## 4. The instrument is certified before any count is made

Every task now opens the corpus's corrected and defective programs once, runs both through this judge,
and searches **only** if the corrected program passes every case and the defective one is rejected.
Otherwise the stage is `JUDGE_NOT_CALIBRATED` and no verdict is counted.

That gate is the only place the answer key is opened, and it is opened to certify the instrument, never
to search: the space is enumerated from the defective program alone. It paid for itself inside this
session. It is what caught §2.1 — the run that reported `hanoi` as `SPACE_EXHAUSTED` would have been
published as a fact about the space. And it caught `sqrt` (§2.2, §2.3) twice.

**No verdict from an uncertified judge** is now enforced by code, not by discipline.

## 5. The four stages, and why they are four

| stage | means | is it a verdict on the task? |
|---|---|---|
| `CANDIDATE_FOUND` | a candidate passed the calibrated judge and the corpus's `pytest` | yes — solved |
| `SPACE_EXHAUSTED` | every candidate in the space was judged, none passed, on a certified judge | yes — this grammar cannot express the fix |
| `BUDGET_EXHAUSTED` | the wall or the cap stopped the run | **no** |
| `JUDGE_NOT_CALIBRATED` | the judge could not see the corpus's own answer | **no** |

`kheapsort` is the only `SPACE_EXHAUSTED`: 8,310 of 8,310, on a judge that passes the corpus's
corrected program and rejects its defective one. That is a real, certified statement — **the edit that
fixes `kheapsort` is not in this space** — and it is the one refusal left on these four tasks that is
about the space rather than the instrument.

## 6. What I said last session that was wrong

- `hanoi` was on the list of tasks with "no answer in the space". **False.** The judge could not read
  `hanoi`'s test file correctly. With the transform the test actually applies, `hanoi` is solved in
  12.5 s. The list drops from 7 to 6, and the judge artifacts in it from 2 to 1.
- `sqrt` was counted *inadmissible* — a task the cheap judge cannot see, so no verdict on it. **It is
  admissible**: the test is a tolerance test and the judge was demanding exact equality. `sqrt` is
  now solved.
- The intermediate claim of this session — `hanoi` `SPACE_EXHAUSTED` at 17,395 — **was an artifact**.
  It is recorded here because it is exactly the error the previous session's doctrine was written to
  prevent, and it happened anyway, in the tool written to enforce it.

## 7. What is still not claimed

- Not that the loop solves what it is given: one of four tasks remains, and it remains because of the
  space, not the search.
- Not any capability credit, not any benchmark rank, not an independent verdict. Authority `NONE`,
  producer-run sandbox; independent verification is open.
- The space is still single-edit, hand-built and task-agnostic; 8,310 candidates for `kheapsort` and
  none of them is the fix. Widening the grammar is the next honest target, and it should be measured
  the same way: on certified judges, with the corpus deciding.

## 8. What would refute this

- A task counted `CANDIDATE_FOUND` whose candidate fails the corpus's own `pytest` on a fresh copy.
- A task counted `SPACE_EXHAUSTED` on which the corrected program fails this judge's calibration while
  the corpus's `pytest` passes it — i.e. a certification that certifies nothing.
- A `BUDGET_EXHAUSTED` reported as a refusal.

Reproduce:

```bash
git clone https://github.com/jkoppel/QuixBugs /tmp/QuixBugs && git -C /tmp/QuixBugs checkout 4257f44b
python3 -m pytest canonical/tests/test_solve_with_a_calibrated_judge_v1.py -q
python3 canonical/tools/solve_with_a_calibrated_judge_v1.py --quixbugs /tmp/QuixBugs \
  --tasks flatten hanoi sqrt kheapsort --candidate-cap 20000 --wall-budget 900 \
  --receipt canonical/verification/SOLVE_WITH_A_CALIBRATED_JUDGE_20261117_V1.json
```
