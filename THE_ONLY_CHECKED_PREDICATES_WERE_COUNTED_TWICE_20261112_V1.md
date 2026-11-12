# THE ONLY CHECKED PREDICATES WERE COUNTED TWICE

**Date:** 2026-11-12 · **Branch:** `arena/98b2d92b-brain` · **Base:** `537368bb`
**Authority: NONE.** Every number here is a sandbox measurement, not independent verification.
**Cost:** $0 · **Model dependency:** zero · **truth.achieved: false**

---

## 0. Two findings, one of them about my own last report

**(a) The most flattering number in the report I merged earlier today was wrong by exactly 2×.**
Yesterday's round published *"10 predicates declare an expectation — 1.7% of the corpus."* The
truth is **5 predicates, 0.83%**. The binary-identity corpus is read by **two code paths inside
one function** — an explicit branch (the only place an entry's `name` survives) and the generic
JSON walk (because `predicate_of` also accepts `arg`) — so each of its 5 predicates was yielded
twice. The one layer that was fully checkable was the one being double-counted, and it was the
only thing making the fraction look twice as good as it is.

**(b) A gate on that fraction, designed the obvious way, has a hole that external evidence says
will be exploited by ordinary work.** A ratchet that only blocks rises *above a frozen baseline*
lets a gain be spent back one green step at a time. That is not a hypothetical: AutoBot-AI
[#14498](https://github.com/mrveiss/AutoBot-AI/issues/14498) (2026-08-17) lost **344 spendable
lines** exactly this way and fixed it by re-baselining on every shrink, so that
`ceiling == baseline == actual, always`. My first design had the hole. It shipped without it.

---

## 1. The double count, measured

| | published earlier today | corrected, measured |
|---|---|---|
| predicates run | 605 | **600** |
| declaring an expectation | 10 (**1.7%**) | **5 (0.83%)** |
| declaring none | 595 | **595** (unchanged) |
| PASS | 452 | **447** |
| FAIL | 58 | **58** (unchanged) |
| UNRUNNABLE | 95 | **95** (unchanged) |
| PASS because it was checked | 10 | **5** |
| PASS because it only started | 442 | **442** (unchanged) |

The mechanism, verbatim from the corpus file: it declares **5** predicates (`gnu_tar_identity`,
`gnu_git_identity`, `python3_identity`, `node_identity`, `jq_identity`), every one carrying
`expect_exit` and `expect_stdout_contains`. The iteration yielded **10** results whose `source`
was that file.

Why `declaring_none` did not move: every duplicated entry was one of the *checked* ones. The
double count inflated the denominator by 5 and the numerator of the only favourable fraction by 5
— so it made the tree look twice as well-verified as it is, while leaving the number of
unchecked declarations exactly as bad as it always was. **595 records still ask for nothing to be
checked.** That is the figure the gate now holds.

Reproduced with `--floor` (1.9 s, nothing executed) and confirmed against the executed audit
(13 min): both report 600 / 5 / 595, and the corpus now yields 5 with its entry names intact.

### What I did NOT do about the other duplicates

18 `(source, argv)` pairs still repeat across the tree. They are **counted, not merged**.
Deduplicating them would shrink the denominator by a guess about what a repeated declaration
means, and a smaller denominator flatters the fraction — the same direction as the bug being
fixed. Two records are two declarations until someone shows they are one claim. Pinned by
`test_two_records_declaring_the_same_command_are_still_counted_twice` so nobody "cleans it up"
later.

---

## 2. The gate: why it counts declarations and not outcomes

The obvious gate is the one that measures the interesting thing — run `--audit`, fail if FAIL
rises above 58. **Rejected**, for four measured reasons:

| property | `--audit` (outcomes) | `--floor` (declarations) |
|---|---|---|
| runtime | ~13 minutes | **1.9 seconds** |
| writes into the tree it measures | yes — `live_audit.json` and `.html`, a controller checkpoint, `experience_v1.json`, 3 new DIAGNOSTIC files | **no** |
| machine-dependent | yes — **8** failures name another machine's filesystem (`/home/runner/…`, `/home/sprite/…`, `/workspace/scratch/…`), and **19** predicates land in the 30 s timeout budget | **no** — a property of JSON on disk |
| flaky in CI | by construction | not flaky |

A flaky gate gets muted, and a muted gate is worse than no gate: it produces the *appearance* of
a constraint. Whether a record **asked** for anything to be checked is identical on every runner,
so that is what is gated. It is also the limiting factor — 595 of 600 declarations can only ever
be contradicted by an exit code and never by an output.

`FAIL` on this tree is not a fact about the claims; it is a fact about *this* sandbox and the
claims together. `declaring_none` is a fact about the claims alone.

---

## 3. The spend-back hole, and closing it

First design: pass when `declaring_none <= floor`. Wrong. Improve 595 → 400, leave the floor at
595, and **195 unchecked declarations can come back later with every build green** — each step is
"below baseline". AutoBot-AI hit precisely this and the fix was to re-baseline on every shrink.

So there are now **three** verdicts, and only one is green:

| measurement vs floor | verdict | exit |
|---|---|---|
| `current == floor` | `HELD` | 0 |
| `current < floor` | `IMPROVED_NOT_LOCKED_IN` | **1** |
| `current > floor` | `REGRESSED` | **1** |
| baseline absent / malformed / missing the field | `BASELINE_UNUSABLE` | **1** (fails closed) |

An improvement is red **until it is written down**, and the failure message carries the one
command that fixes it:

```
python3 canonical/tools/auditability_report_v1.py --floor --write-baseline <path>
```

`--write-baseline` regenerates the document **from a live measurement** so no number is ever
retyped by hand, and **preserves the prose a human wrote** (`what_this_gates`,
`why_not_the_fail_count`, `reading`, …) so re-baselining cannot silently delete the justification
for the floor. Pinned end-to-end by `test_a_gain_cannot_be_spent_back`: improve → red, lock in →
green, spend one back → red.

Two related designs were read and deliberately not copied: AIRIA-Systems
[airia-ci#127](https://github.com/AIRIA-Systems-GmbH/airia-ci/issues/127) (2026-11-06) compares
every figure against **the base branch's copy** and adds a hard **90-day expiry**; afonsoft
[agent-harness#252](https://github.com/afonsoft/agent-harness/issues/252) found a coverage gate
sitting ~9 points below measured reality, i.e. "silent regression is currently possible". The
expiry is a good idea and is **not implemented here** — it needs a date policy this repo does not
have yet, and inventing one inside a gate is how gates get ignored. Recorded as a next move.

---

## 4. What was built

| piece | where |
|---|---|
| shared walk, so the floor cannot drift from the audit | `_iter_predicate_specs` in `canonical/tools/auditability_report_v1.py` — `audit(run=True)` and `declaration_floor` iterate this and nothing else |
| the double-count fix | `BINARY_PREDICATE_CORPUS` named once; the walk skips what the explicit branch already yielded |
| the measurement | `declaration_floor()` — 1.9 s, executes nothing, writes nothing, ranks the worst sources |
| the ratchet | `floor_gate()` — `HELD` / `IMPROVED_NOT_LOCKED_IN` / `REGRESSED` / `BASELINE_UNUSABLE`, fails closed |
| the builder | `write_baseline()` + `--floor --write-baseline PATH` |
| the committed floor | `canonical/verification/AUDITABILITY_DECLARATION_FLOOR_20261112_V1.json` — `declaring_none: 595`, `authority: NONE`, producer and carrier named, git head recorded |
| the CI gate | `.github/workflows/declaration-floor.yml` — 3 steps: the ratchet, then the two pytest files that keep the instrument beneath it honest |

The floor is concentrated, which is why it is cheap to move: **one file holds 184 of the 595** —
`canonical/runtime/CAPABILITY_RECEIPT_PROJECTION_V1.json`, 31% of the entire gap. Next
`BOUND_CAPABILITY_REGISTRY_V1.json` (12), then astra runtime state and verification capsules.

---

## 5. Tests and mutations

**26 new tests** in `canonical/tests/test_auditability_declaration_floor_v1.py`. The two that
matter most are properties, not numbers:

- `test_the_floor_counts_exactly_what_the_executed_audit_runs` — if the static floor and the
  executed audit ever disagree, the gate measures a different corpus than the instrument and is
  decoration: it can stay green while the thing it protects gets worse.
- `test_the_floor_executes_no_declared_command` and `…writes_nothing_into_the_tree_it_measures` —
  the moment the floor runs a command it inherits every machine dependence the design exists to
  avoid.

**8/8 mutations killed**, with the suite green beforehand (a mutation harness run against an
already-red suite kills every mutant and reports a perfect score for nothing):

```
KILLED  M1 the gate cannot go red (rise is allowed)
KILLED  M2 a missing baseline passes instead of failing closed
KILLED  M3 an unlocked-in gain is green (spendable headroom returns)
KILLED  M4 the floor executes what it counts
KILLED  M5 the corpus is counted twice again
KILLED  M6 the floor counts a different corpus than the audit runs
KILLED  M7 rewriting a floor deletes the reasoning
KILLED  M8 the ratchet counts declarations instead of unchecked ones
```

**70 passed** across the three auditability suites (26 floor + 26 exit-gate + 18 pre-existing).
`repo_integrity_guard_v1 --static-only` → `rules=11 violations=0 PASS`, and `--self-test` → PASS,
so the new workflow trips no rule (it uses `pull_request`, not the allowlisted
`pull_request_target`; `permissions: contents: read`; no referee environment, no check-run API, no
`continue-on-error`, no merge or push).

---

## 6. Honest limits

- **The gate is visible, not merge-blocking.** The `main-lock` ruleset requires exactly one check,
  `referee/repo-integrity-guard`. Adding a required status check needs Administration permission,
  which the policy says agents do not have. So this workflow goes red on a regression and the PR
  can still be merged. Making it required is a **one-click owner action** and is the single
  highest-value thing left in this round.
- **595 is a floor, not a plan.** Holding it stops the gap widening; it does not close it. Closing
  it means adding expectations to records, and 184 of them live in one file.
- **The 58 FAILs are still untriaged.** This round made the count stable to gate on, not
  adjudicated. Splitting them into refuted-claim / machine-bound-receipt / unprovisioned-sandbox
  is the next diagnostic, and 8 are already known to be machine-bound.
- **The double count was found by a test, not by reading.** It had survived one published report.
  The lesson is about the review, not the code: a number that flatters the author is the number
  most worth re-deriving, and `declaring_an_expectation` was the only flattering figure in the
  document.
- **Authority NONE.** Measured in an Arena session sandbox with the repo's own pinned, hashed
  substrate installed (`requirements/software_engineering_kernel_v1.txt`). Nothing here is a
  verification receipt.

---

## 7. The owner's question, with the corrected number

> *"Why can't we just give our model the most advanced coding actions and let him experience them
> once, and then he will learn them?"*

Because the record of the experience is not a check, and today the number got worse before it got
better. Yesterday I reported that **1.7%** of this tree's declared verifications actually assert
something. The honest figure is **0.83% — five predicates out of six hundred**, and all five are
`tar --version`, `git --version`, `python3 --version`, `node --version`, `jq --version`. They are
identity checks on installed tools. **Not one of the 600 declared verifications in this repository
asserts anything about the work the model did.**

That is the whole answer in one sentence: the model can experience an action once and write it
down permanently, and nothing in the tree can tell it — or you — that the record stopped being
true. 442 records say PASS because a process started. 58 say PASS no longer. 95 cannot run here
at all.

The external record for November 2026 says the same thing from five directions, and it is worth
being precise about how close the shapes are:

- **Pan-agent [#146](https://github.com/pym96/Pan-agent/issues/146)** (2026-10-20) writes the two
  criteria this repo just implemented as governance: **C-EV-02 "assertion outcomes versus process
  outcomes"** — nonzero exit, timeout, launch failure must be classified apart from a failed
  assertion — and **C-EV-05 "reproducible installed/local entry point … Fail on source-machine-only
  paths"**, which is the 8 machine-bound receipts.
- **fak [#14184](https://github.com/anthony-chaudhary/fak/issues/14184)** (2026-11-02): receipts
  that "validate only arithmetic … carry no provenance, so a receipt built from calibrated
  constants or host stand-ins validates identically to one built from real measurement."
- **ripr-swarm [#6595](https://github.com/EffortlessMetrics/ripr-swarm/issues/6595)** (2026-10-04):
  a receipt with no source revision or timestamp means "a stale receipt from a pre-tamper tree is
  indistinguishable from a current one."
- **okl [#265](https://github.com/emeraldleaf/okl/pull/265)**: "Measured claims match every
  receipt" — a test that **recomputes each published sentence from the receipts**, which is why
  `--write-baseline` regenerates rather than accepts a typed number.
- **arXiv 2611.13336 (Veritas, ByteDance, 9 Nov 2026)**: an exploit that solved no task scored
  **100%** on SWE-bench Verified, Pro and Terminal-Bench; **26 of 500** SWE-bench Verified tasks
  still accept wrong patches; the curated oracle **fails its own tests on 22 of 66** tasks.
- **arXiv 2610.20344**: names this a **"vacuous pass"** — "a test case may pass even though the
  feature under test never ran" — and scores over four channels including **the process exit
  code**, with positive controls that force FAIL regardless of the case's own status.

**Am I right or wrong?** Right that a lesson can survive teach → bundle → fresh machine → re-check
(proven last round, 5/5). Wrong that this solves any computer use, and the reason is now a
measured integer rather than an argument: **five of six hundred.** One try is enough exactly when
the interface and the verifier already do the generalising, and this tree has essentially no
verifiers. The frontier numbers did not move either — OSWorld V2 best 21.3%, Terminal-Bench 4.0
64.85%, SWE-bench Pro 61.5%, ARC-AGI-3 semi-private 30.2%.

---

## 8. Next, ranked

1. **Make the gate required** (owner, one click: add `declaration-floor` to the `main-lock`
   ruleset's required checks). Until then it is a red light nobody has to stop at.
2. **Spend the concentration.** 184 of the 595 live in `CAPABILITY_RECEIPT_PROJECTION_V1.json`.
   Adding `expect_exit: 0` to that one file moves the floor by 31% in a single diff — and each
   addition must be a *real* expectation, not a rubber stamp, or the fraction rises while the
   information does not.
3. **Triage the 58 FAILs** into refuted claim / machine-bound receipt / unprovisioned sandbox,
   using the `exit`, `stdout` and `stderr` now carried on every verdict. The 8 machine-bound ones
   are a schema defect worth its own round: a receipt re-runnable only on the machine that wrote
   it is history with extra steps (Pan-agent C-EV-05).
4. **Add an expiry to the floor** (AIRIA's 90-day hard stop), once this repo has a date policy to
   hang it on.
5. **Fix the five declarations in §5 of yesterday's document** by *superseding* them in new
   records, never by editing the old ones, so the evidence that they were wrong survives.

---

## 9. Reproduce

```bash
python3 canonical/tools/auditability_report_v1.py --floor
python3 canonical/tools/auditability_report_v1.py --floor \
        --baseline canonical/verification/AUDITABILITY_DECLARATION_FLOOR_20261112_V1.json
python3 -m pytest -q canonical/tests/test_auditability_declaration_floor_v1.py \
                     canonical/tests/test_auditability_predicate_exit_gate_v1.py \
                     canonical/tests/test_auditability_report_v1.py
python3 canonical/tools/auditability_report_v1.py --audit        # ~13 min, exit 1, red
python3 execution_guard/repo_integrity_guard_v1.py --static-only
python3 canonical/runtime/verify_brain_unified_model_v1.py
```
