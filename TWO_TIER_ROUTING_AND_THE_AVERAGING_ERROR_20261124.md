# The 67% was two populations averaged. One of them is at 98.8%.

**2026-11-24 · `15cef0dd` · `arena/283e85a5-brain`**

Last turn's stated gap: *"67% full-library, not 98.9%. Against all 447, family siblings compete and
win. That's the next fix."*

**The hypothesis was wrong, and the measurement says why.**

---

## 1. Family structure: there isn't any

| | |
|---|---|
| capabilities | 447 |
| families (by id prefix) | **376** |
| median family size | **1** |
| largest family | **12** |
| families with >10 members | **1** |

There is no hierarchy to build. And the 2026 routing literature says building one would hurt:
**tool-level retrieval beats pack-level by 2–4 pp consistently, "since pack expansion loads
irrelevant sibling tools that dilute the candidate set."** Hierarchical routing scored **47.9% F1**
at scale, *below every other shortlisting approach*.

So "shared family vocabulary" is not the defect. I had the shape wrong.

---

## 2. What the 62 failures actually are

| (true, predicted) | count |
|---|---|
| **stub lost to another stub** | **41** |
| stub lost to a real capability | 20 |
| **real capability lost to another real capability** | **1** |

**61 of 62 failures involve an auto-registered stub as the true answer.** A real, askable capability
loses to another real one **once in 127**.

The failures are `current_escape_o_proof_instantiations_v1` losing to
`current_escape_o11_proof_instantiations_v1` — a v1 competing with its own v11 on a path-shaped
name. Those capabilities' triggers are filenames because a filename is all the compiler ever gave
them.

---

## 3. The number, reported per population

| population | self-locate | answered by an askable capability |
|---|---|---|
| **askable** (83 described BOUND) | **82/83 = 98.8%** | **100.0%** |
| auto-registered (105 described) | 44/105 = 41.9% | 87.6% |
| whole library (188 described) | 126/188 = 67.0% | — |

**67.0% was the average of a 98.8% population and a 41.9% population, and it described neither.**

And it is not a near thing. In every askable-vs-stub contest the askable capability outscores the
best stub by **2.2× to 19.9×, median 8.4×**. There is no tie to break.

> **This is not a tiebreak. It is a population that should not be in the candidate set for a
> written request.**

---

## 4. What I built

`route(goal, askable_only=False)` — a **margin rule with a threshold of zero**, because the
measurement says the stubs cannot win, not that they narrowly lose.

| | default | `askable_only=True` |
|---|---|---|
| known-goal routing | 5/5 | **5/5** |
| out-of-domain falsely confident | 0/6 | **0/6** |
| askable self-location | 98.8% | **98.8%** |
| stubs able to answer a written request | 44/105 | **0/105** |

**The default is unchanged and a test pins it.** Nothing downstream moves unless a caller opts in.

The census now reports self-location **per population and refuses to average it**, with two new
guards: askable self-location ≥ 90%, and an askable capability's own description must be answered
by an askable capability ≥ 95% of the time.

---

## 5. Test state

| suite | result |
|---|---|
| `test_brain_unified_model_v1` | **61 passed / 919 subtests** |
| `test_unified_model_library_census_v1` | 12 passed |
| `test_measured_boot_and_repair_speed_v1` | 7 passed |
| `test_instruction_contract_v1` | 21 passed |
| `test_capability_reachability_v1` | 13 passed |
| fabric + invoker | **2 failed** — the pre-existing R1 blob-drift, unchanged |

**80 passed, 2 failed, and both failures are on `main`.**

Artifact regenerated (`e6b66cea…`) because editing the runtime moves the compile-determinism and
fixed-point tests — they compare the shipped artifact against a fresh compile, so any runtime edit
requires a recompile. That coupling is real and worth knowing.

---

## 6. Where this leaves the plan

| item | status |
|---|---|
| L1 — descriptions from the repo's own docstrings | **done.** 11% → 47% askable; recall curve **.984→.756** became **1.000→.989** |
| Two-tier routing | **done.** askable population at **98.8%**, opt-in, default frozen |
| L2 — collapse 176 duplicate ids | **withdrawn.** They register 176 *different real modules* through one adapter; deleting unregisters real bindings |
| L3 — keep BM25, tune it | **done implicitly.** The scorer was never the problem; the text was |
| D4 — widen the forge (0/12 → ≥4/12) | **open** |
| R1 governance re-attestation | **open — your decision.** 5 tests fail on `main` for this reason |

**The pattern across every round is now unmistakable and it is the actual strategy:**

> Every time the system underperformed, the cause was a fact already present in the repository
> that nothing connected — a docstring no compiler read, a swap table no repair chain imported, a
> 27-import table loaded eagerly, a coverage gate that counted an undistinguishing token. **The
> frontier problem here has never been missing capability. It has been unread evidence.**

That is also why "best part is no part" keeps winning: each fix removed a component (27 imports,
an 11.6 MB read, a crash, a candidate population) rather than adding one.

---

## Honest limits

- **98.8% is self-location**, using each capability's own recorded description. It is a necessary
  condition for findability, **not** a benchmark score, and it is optimistic: the query is the text
  that was indexed.
- **83 askable capabilities with descriptions** is a small population. One failure moves the number
  by 1.2 points.
- **The 105 auto-registered descriptions are largely templated**, which is why they score 41.9%; that
  number measures the registration, not the router, and is reported separately for that reason.
- `askable_only=True` **hides capabilities**. For an agent that must invoke a stub by id, the default
  remains correct. This is a routing mode, not a deletion.
