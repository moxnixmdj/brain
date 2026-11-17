# Judge the judge: the cheap oracle rejects the corpus's own answer on 7 of 31 published bugs

**17 November 2026** · branch `arena/4ca38180-brain` · base `d2e0aa07` · authority **NONE**
(producer-run) · receipt `canonical/verification/JUDGE_THE_JUDGE_20261117_V1.json` · tool
`canonical/tools/judge_the_judge_v1.py` · 9 tests

Last session's conclusion was that the instrument, not the space, loses answers. This session tested
the instrument itself, and it fails in a way nobody had looked at: **the cheap oracle the loop uses
rejects correct programs.**

---

## 1. The rule, and the number

> A judge is **admissible** for a task only if it passes the corpus's corrected program **and** fails
> the corpus's defective one.

Run over all 31 published bugs that ship example data:

| | count | tasks |
|---|---|---|
| the corpus's **real** judge (`pytest`) passes the corrected program | **31 / 31** | — |
| the corpus's **cheap** judge (in-process, `json_testcases`, `==`) passes it | **24 / 31** | — |
| **inadmissible** judge | **5** | `hanoi`, `knapsack`, `levenshtein`, `longest_common_subsequence`, `sqrt` |
| **naive** comparison rejects the answer | **7** | the 5 above + `flatten`, `kheapsort` |
| repaired by materialising a bounded iterator | **2** | `flatten`, `kheapsort` |

Causes, mechanically named by the tool:

- `GENERATOR_NOT_MATERIALISED` — `flatten` is a generator function; comparing a generator object to a
  list is not a verdict. **2 tasks** (with `kheapsort`).
- `TIMEOUT_TOO_SHORT` — `levenshtein`, `longest_common_subsequence` are exponential; a 50 ms clock
  recorded "does not run" for a correct program. **2 tasks.**
- `VALUE_DISAGREES` — `hanoi`, `sqrt`, `knapsack`. For `hanoi` the reason is now exact and it is the
  sharpest thing found this session: the published data stores **lists**, the program returns
  **tuples**, and the corpus's own test file repairs it in one line —
  `testdata = [[inp, [tuple(x) for x in out]] for inp, out in testdata]`. **The representation the
  answer must satisfy lives in the test file, not in the data.** It is the only task of the 31 whose
  test file transforms its own data, and it is exactly the task the cheap judge could not see.

`cheap_judge_accepts_the_bug` is empty: the cheap judge never let the defective program through. Its
error is one-directional — **false reject only** — which means every previous number computed through
it was, if anything, an *under*-count.

## 2. What this corrects, including my own last two sessions

- Last session: *"16 of 23 published bugs have an answer in the enumerable space, and 7 have none."*
  Restated over the **22 admissible** tasks of those 23: **16 have an answer in the space**, the
  corpus's first case finds **4**, the exactly chosen case finds **13**, and all 16 pass the corpus's
  own pytest. The 7 "no answer" tasks were **4 genuine space failures** (`powerset`,
  `shunting_yard`, `subsequences`, `to_base`), **2 of my own judge artifacts** (`flatten`,
  `kheapsort`), and **1 inadmissible task** (`hanoi`). Two of my three claims about those seven were
  wrong, and the wrong ones were wrong in the *pessimistic* direction — I blamed the grammar for
  failures of my comparison.
- Session before: *"6 tasks could not be measured because a candidate defeated the timer."* At least
  three of those (`levenshtein`, `longest_common_subsequence`, `sqrt`) were the **clock**, not the
  candidate: the reference itself does not finish in 50 ms.

Nothing about the space, the grammar, the search or the demonstrations changes. What changes is which
verdicts were ever measurements.

## 3. Two hazards found the hard way, both part of the instrument

1. **Bounded materialisation.** Repairing the comparison to `list(value)` on a defective generator
   that never stops killed the measurement process with an out-of-memory abort. The repair must be
   `islice(value, len(expected) + 1)`: a judge that can be made to allocate without bound is not a
   judge.
2. **A candidate can kill the judge.** On `flatten`'s space the in-process evaluator died silently at
   roughly candidate 3,000 — a C-stack overflow inside candidate code, not a Python exception. The
   measurement survived only because the same candidates were later evaluated in **child processes
   with bisection on a hang**; a candidate that crashes a child is charged as `HUNG`, never as a
   verdict. This tree already has the industrial form of that (`zygote_worker_pool_v1`); the lesson is
   that calibration and isolation are the same requirement.

## 4. The doctrine this registers

> **No verdict from an uncalibrated judge.** Before any number is computed on a task, the judge must be
> shown to pass the corrected program and fail the defective one on that task. Where it cannot, the
> task is `INADMISSIBLE` — not solved, not failed, not counted.

This is the same law the tree already applies to tolerances (`NEVER_WIDEN_THE_TOLERANCE`), turned on
the thing that produces the tolerance. The frontier's own 2026 reports are this finding at scale:
SWE-bench Pro's verifier measured at 8.5% false accept / 24.0% false reject; SWEPatchTest's best
configuration reaching 9.21% joint validation; OpenAI's audit calling ~30% of SWE-bench Pro's public
tasks broken; *Accepted but Wrong* showing one chosen input moves wrong releases 0.410 → 0.065. Ours
is the same defect in the smallest possible object — **a JSON file compared with `==`** — and it is
measurable in 14 seconds.

## 5. What it means for the question that keeps being asked

**Is "give it the actions, let it experience each once, it knows them permanently" the answer?** On the
cost axis it is real and it is measured. On the capability axis the chain still has four terms, and
this session moved the *first* one:

1. **the judge** — measured here: 26 of 31 admissible, 5 blind, 2 repairable by a comparison, 2 ways a
   candidate can kill it. **A capability claim on an inadmissible task is a claim about the judge.**
2. **the space** — the tree's own audit: 14 of 40 published fixes are a single edit the generator
   cannot express.
3. **the search** — 6 refusals had the answer inside the space and did not reach it; last session's
   measurement says the screen is why.
4. **the observable** — 9 bugs ship no example data at all.

Nothing in that list is "the agent has not seen it once". Every item is a term in *whether a verdict
is possible*, and the fastest capability in this tree has always come from making a verdict possible —
not from adding experience, actions or parameters.

## 6. The single bottleneck, fifth statement

> 1. the space's **size** is the vocabulary; its reach per demonstration is the invariant set.
> 2. the invariant is the **effect vocabulary**; the constraint is **composition**.
> 3. composition is 40 lines and 0 trials; the constraint is the **specification**.
> 4. the specification is not missing, it is **mis-asked** (one case, believed).
> 5. **the judge is not trustworthy until it is calibrated — and 5 of 31 tasks cannot be judged by the
>    cheap instrument at all.**

So the single bottleneck is still the instrument, and it now has a precise first step that costs
seconds: **calibrate the judge per task, and refuse to count anything where calibration fails.**

## 7. Honest limits

- One corpus (QuixBugs `4257f44b`), one session, producer-run, authority **NONE**, no independent
  verification.
- The audit **reads the answer key** (`correct_python_programs`). That is legitimate for calibrating an
  instrument and illegitimate for solving: no solve in this tree may see it, and none does.
- The cause classifier is triage. `knapsack` is labelled `VALUE_DISAGREES` while its real difficulty is
  that the reference is slow at capacity 750; a longer clock would reclassify it.
- **No solve mode ships with this.** A repaired comparison that I tried to run over a space containing
  crashing candidates did not finish inside 15 minutes and was removed rather than shipped broken: what
  ships is the audit, which is what the claim rests on. A bounded, child-isolated solver using this
  gate is the next build, not this one.
- Not claimed: any capability credit, family flip, weight change, leaderboard number or sentience
  result.

## 8. Reproduce

```
git clone --depth 1 https://github.com/jkoppel/QuixBugs /tmp/QuixBugs
python3 canonical/tools/judge_the_judge_v1.py --quixbugs /tmp/QuixBugs --out /tmp/judge.jsonl \
    --receipt canonical/verification/JUDGE_THE_JUDGE_20261117_V1.json
python3 -m pytest canonical/tests/test_judge_the_judge_v1.py -q      # 9 passed
```
