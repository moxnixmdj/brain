# Where the SWE-bench loss actually is

**Round 14. The tree held a real SWE-bench Verified run. I decomposed its loss instead of building another layer on an assumption — and the answer redirects the next several rounds.**

Date: 2026-11-24 · Base: `1da0b549` · Branch: `arena/c312a4bc-brain`

---

## 1. What was already measured, and not repeated

The tree holds one real run scored under **the tasks' own tests**: 231 Django tasks of SWE-bench Verified.

| | |
|---|---|
| **one submission** (no test seen) | **5 resolved** = 3.9% of the 128 judged tasks with a candidate |
| within twenty (needs hidden tests to choose) | 7 |
| **control: another task's text** | **0 resolved** |
| pre-registered expectation for one submission | `[4, 10]` — **held** |

I did not re-run any of this. I decomposed it.

## 2. The decomposition

| step | measurement |
|---|---|
| tasks that never get a candidate | **101 of 231 = 44%** |
| candidates that resolve | **10 of 2,422 = 0.41%** |
| ceiling from *perfect selection* | **+2 tasks** of 128 |
| tasks where **every** candidate sat in **one file** | **128 of 128** |
| expert's file is rank 1 by score alone | **40.0%** |
| tasks whose target test starts passing yet don't resolve | **18 of 25** |
| of those, never even reached the whole-module run | **16 of 18** |

## 3. Two findings that change the plan

### Finding A — selection is worth almost nothing

Perfect ranking reaches 7 instead of 5. **All of ranking is worth +2 tasks of 128 (<2%).** Building a better ranker would have optimised the wrong thing — and it is the thing one would naturally build next.

### Finding B — there are two different failures, not one

**FINDING:** 44% of tasks never get a candidate, and **every** candidate for **every** task sat in a single file, while the expert's file is rank 1 only 40% of the time. The generator never considers a second location.

**PRECISION:** 25 tasks had a candidate that made the *failing test pass* — the edit found the right file and did the asked-for thing — and 18 still didn't resolve. **16 never even reached the whole-module run**, so the breakage was visible cheaply and nothing was reading it.

These need different fixes. Conflating them is why "improve the coding agent" is not a plan.

## 4. Why precision is the cheap half

A candidate that breaks a neighbour is detectable **locally and for free**: re-run the tests the edit touches. Sixteen tasks died at a check that costs seconds and was never taken.

That is the same lesson as round 13, arriving from a different direction: **the bill falls when an observation removes candidates**, and here the observation is running a test you already have.

## 5. The honest reading of 3.9%

It is a real number, measured under the tasks' own tests, with a pre-registered expectation that held and a control that resolved nothing. **It is also 5 tasks.** A rate from 5 successes has a wide interval and must not be quoted as stable. The receipt says this in those words.

## 6. What this round does not do

- It **does not run SWE-bench**; it reads a receipt that did, and inherits that run's commit and its 225/231 judged.
- It does **not** claim the generator can't be improved — it says the generator **is** the bottleneck.
- It does **not** propose an untested mechanism. The next round must test one.
- No model calls, no network, no parameters.

## 7. The next bottleneck

**Coverage and precision, in that order** — can the machine produce a candidate in the *right* file, and can it make the change without breaking a neighbour? Sixteen tasks were lost at a breakage a local re-run would have shown for free.

## 8. Verification

- 11 tests asserting the decomposition, the ceiling on selection, the control, and the single-file fact
- One test **caught a real gap**: my first receipt omitted the PRECISION finding entirely. The receipt was corrected, not the test.
- `model_calls = parameters = 0`, `authority = NONE__READS_RECORDED_RECEIPTS`

Authority `NONE`. This reads recorded receipts; it is not independent verification of anything.
