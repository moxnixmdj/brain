# Fourth pass: the surfaces I had never opened

**2026-11-25.** You have now asked three times whether I was sure. Each time I said no and
then looked in a new place. This pass went outside `canonical/runtime`, `verification` and
`capabilities` — the three directories my first three answers had been built from — and
found **two entire execution surfaces that change the answer**.

---

## 1. What was outside every previous census

My first three answers were built from these directories only:

```
canonical/runtime, canonical/verification, canonical/capabilities, canonical/corpus
```

They covered roughly 8,000 files. The repository has **~19,000**.

| surface | size | what it is | in my earlier answers? |
|---|---|---|---|
| **`canonical/astra/`** | 30 | **external Wolfram-adjudicated family results** | **no** |
| **`canonical/astra_runtime/`** | **2,571** (57 py) | **321 mission specs + evidence + patches** | **no** |
| `canonical/governance/` | 3,219 | law/gate state | partially |
| `canonical/tests/` | 2,859 | the test corpus for all of the above | no |
| root `*.md` | **440** | dated measurement notes | no |
| `canonical/swe_kernel/` | 146 | repair kernels | partially |
| `canonical/reasoning/`, `canonical/research/` | 166 + 136 | acquisition records | no |
| `qualification_results/`, `intake/`, `execution_guard/` | 17 / 87 / 43 | harnesses and gate results | no |

**440 root documents** and **321 missions** had never been counted. That is the direct
answer to "are you sure."

---

## 2. The two findings that change the comparison

### 2.1 A real, unfamiliar, externally-specified software repair

`canonical/astra_runtime/missions/ASTRA-REAL-SWE-MYPY-21968-001.json`,
status **`COMPLETE_VERIFIED_LOCAL`**:

> **external target:** `python/mypy` issue 21968, "Exhaustiveness of type `tuple[bool, bool]`"
> **diagnosis:** fixed-tuple sequence negative narrowing only preserved complements when
> zero or one subpattern was conditional; multi-conditional patterns discarded the complement
> **repair:** represent the complement as a linear union partitioned by the first subpattern
> that fails — exact negative narrowing without exponential expansion
> **verification:** issue reproduction → "no issues found in 1 source file"; new regression
> 1 passed / 8,292 deselected; exhaustive subset 10 passed; match subset 2 passed

The patch exists (`evidence/ASTRA-REAL-SWE-MYPY-21968-001.patch`, a ~40-line rewrite of
`PatternChecker.visit_sequence_pattern` in `mypy/checkpattern.py`) with a causal diagnosis
that is correct about mypy's actual algorithm.

**This is the strongest single capability artifact in the repository**, and it was absent
from all three of my previous answers. It is materially different from the 45-commit corpus:
an unfamiliar issue, in an unfamiliar repository, with a non-trivial algorithmic fix.

Its limits, stated in the same file: `COMPLETE_VERIFIED_LOCAL`, `external_pr_created:
false`, worktree under `C:\Temp`, and the other three ASTRA-REAL missions are
`BLOCKED_ON_CONCURRENT_CONTROLLER` or empty. **1 real mission out of 4 attempted.**

### 2.2 51/51 proven — but only on the hidden non-global set

`canonical/astra/ASTRA_NON_GLOBAL_51_OF_51_CLOSURE_V1.json`:

```
non_global:  {proven: 51, unproven: 0, total: 51}
global:      {proven: 0,  blocked: 10, total: 10}
full_astra_claim: False
superworker_real: 0
distinct_verifier: WOLFRAM-REMOTE-KERNEL-20260922-HIDDEN-MBTA006-V1
```

and `ASTRA_FINAL_FAMILY_WOLFRAM_ADJUDICATION_V1`:

```
pass_count: 10   fail_count: 0   global_family_gate_pass: True
families passed: NOVEL_ADAPTATION_REASONING, GUI_COMPUTER_USE, WEB_RESEARCH,
                 SOFTWARE_ENGINEERING, MATH_SCIENCE, PROFESSIONAL_WORK,
                 TOOL_ORCHESTRATION, LONG_HORIZON_MEMORY_CONTEXT,
                 SCOPE_JUDGMENT_ALIGNMENT, SPEED_COST_EFFICIENCY
```

Ten of ten families, adjudicated by an **external Wolfram kernel** with
`trust_executor_status_labels: false` — i.e. the verdict was not taken from our own labels.

**And the same file says `full_astra_claim: False`, `superworker_real: 0`, and the global
set is 0/10 proven, 10 blocked.**

So both statements are recorded together, by the system itself: *51/51 on the hidden
non-global predicates and 10/10 families passed, and the full claim is false and zero of
the global predicates are proven.* The bound is in the artifact, not added by me.

### 2.3 A third surface: 595 public-runner verifications

Already reported in pass 3, repeated here because it belongs to this list: 578 distinct
mechanisms independently verified on a public runner, **0 with non-zero credit**.

---

## 3. Why "51 of 51" and "1 real mission" do not overturn the comparison

Because the boundary is written into the same files:

| claim | what it is bounded to |
|---|---|
| 51/51 proven | **non-global** predicates; global = 0/10 proven, 10 blocked |
| 10/10 families pass | **family gate** under a hidden contract; `full_astra_claim: False` |
| mypy-21968 repaired | `COMPLETE_VERIFIED_LOCAL`, no external PR, `C:\Temp` worktree |
| 6/11 Terminal-Bench | 11 **chosen** tasks, not the 89-task set |
| 3.9% SWE-bench Verified | 128 judged tasks of 500, one submission |

A "51 of 51" on hidden non-global predicates is a genuine and externally-adjudicated
result. It is not the same claim as solving SWE-bench Pro, and the repository says so in
its own JSON field.

---

## 4. Corrected verdict table (fourth pass)

| capability | best artifact | external adjudication | verdict vs frontier |
|---|---|---|---|
| **Unfamiliar SWE issue repair, single instance** | **mypy#21968, verified local** | none (local) | **closest thing we have; still 1 instance** |
| **Hidden-predicate family suite** | **51/51 non-global, 10/10 families** | **Wolfram remote kernel** | **a real win on its own contract; global 0/10** |
| Single-line fixes with supplied oracle | 25/41 = 61%, 0 model calls | none | win on cost, not on task |
| SWE-bench Verified | 3.9% | task's own tests | **lose 20x** |
| Computer use | 2.7% MiniWoB | own harness | **lose 30x** |
| Terminal-Bench | 6/11 chosen | official pytest | **lose** |
| DOCX / SA-CCR / schedulers | 9 specs × 2000 instances | none | win on determinism, narrow scope |
| Plain-language file front door | 500/500 ×2 seeds | none | narrow but real |
| HLE / LiveBench / GAIA / OSWorld / Pro | never scored | — | **no contest** |

---

## 5. The answer to "are you sure, 100%"

**No — and the fourth pass is the proof, not the disclaimer.** Three times I said "no" and
then found things anyway: pass 1 missed MiniWoB and Terminal-Bench; pass 2 missed 2,238
runtime modules; pass 3 missed 321 missions, 440 root documents, and the entire
`canonical/astra/` adjudication surface. Each miss was a directory I had not opened, not a
judgement I had made wrongly.

What I now know exists:

```
19 families     · 12 components   · 11 measured specs     · 9 benchmark insertions
595 public-runner verifications   · 578 distinct mechanisms
321 ASTRA missions (1 verified real repair, 3 blocked)
440 dated root measurement notes
2,238 runtime modules / 16,155 functions
51/51 hidden non-global predicates, Wolfram-adjudicated; global 0/10
```

What remains unread: **16,155 functions in 2,238 modules that no human has reviewed**, and
the system's own audit puts ~2,200 of them in `NOT_YET_AUDITED`. There is no point at which
I can say "all of them", because the repository does not contain an enumerable list of its
own capabilities — that is the finding, and it has been the finding every time.

**100% is not available, and the reason is structural: the artifact that would make it
available (`TRUE_CAPABILITY_AUDIT`) explicitly declines to audit ~2,200 modules.**

---

## 6. What actually changes who wins

Before this pass I would have said we have **no** instance of solving an unfamiliar
real-world software defect. That was wrong. **mypy#21968 is one, with a correct causal
diagnosis and a verified patch.**

Before this pass I would have said **no** capability has external adjudication. That was
also wrong: **51/51 hidden non-global predicates and 10/10 families were adjudicated by an
external Wolfram kernel** on 2026-09-22.

Both are real. Neither changes the comparison on task completion, because:

- mypy#21968 is **one** issue; SWE-bench Verified is **500**, and we score 3.9% on a sample.
- 51/51 is on **hidden non-global predicates of our own contract**, and the global set —
  the one that would correspond to "generally capable" — is **0 proven, 10 blocked**.

The honest summary is now: **we have one verified unfamiliar-repo repair and one
externally-adjudicated hidden-predicate sweep, against frontier systems that do thousands
of such repairs per benchmark run.** That is a better description of us than either of my
first three answers, and it is still a loss by roughly two orders of magnitude on the only
axis a user cares about.
