# The pasted plan, verified — and the bottleneck it gets wrong

**Date:** 2026-11-24. **Authority:** NONE (producer-run sandbox). **Method:** fetched all 14 named
branches at depth 1 and read their own artifacts. Every claim below is marked **verified**,
**unverified**, or **failed**. A claim that appears in a document is not a measurement; a claim that
appears in a *receipt* is.

---

## §1 The load-bearing claim, and what it actually rests on

The plan's Pillar 0 says: unify 7 branches and you immediately get "244+ verified OSS commits +
100% 45-commit corpus + 84.6% 8-repo blind suite in one binary." That is the foundation everything
else is built on. It does not hold.

| claim | verdict | evidence |
|---|---|---|
| 14 named branches exist | **verified** | all fetched; tips `aab1b545 e5fd2f53`, `b81b2217 8098519b`, `06dc079e 48e9d366`, `1412289d 1580fb01`, `f7ec1162 90fe0fc2`, `50c05c04 85931f97`, `cd5bfaaa 45a1cc44`, `d86a0174 21000edf`, `4260e934 e96c8079`, `39d26eb4 54caecbb`, `94363358 88806cc9`, `80a7e8eb 9e2e186c`, `0964738f cb0d2aee`, `8fe5f749 1d2e4dcb` |
| "244 verified real OSS commits" | **unverified** | the string `244` appears in 855 files on `b81b2217` — the signature of SHA/hash noise. No receipt states it as a measured result. |
| "45/45 = 100% on the 45-commit corpus" | **failed as a score** | `45/45` occurs in exactly **one** file on `b81b2217`, and it is `01a1ab04-….patch` — a literal patch, not a measurement. |
| "51.11% 1-shot cross-commit transfer (23/45)" | **unverified** | `51.11` appears in 55–61 files per branch (noise); `23/45` in 1 file on `94363358`. No receipt isolated. |
| "84.6% (11/13) blind multi-repo" | **unverified** | `84.6` appears in ~692 files per branch (noise). `11/13` in 2–4 files, not read as a receipt. |
| "15.4% blind real C commits" | **unverified** | `15.4` in ~822 files per branch (noise). |
| "0.9796 cross-codebase accuracy" | **unverified** | 3 files on most branches, **14 on `50c05c04`** — the most plausible of the batch, still not isolated as a receipt. |
| "SWE-bench Pro patches average 107.4 lines across 4.1 files" | **unverified** | not located in any receipt this round. |

**The decisive artifact.** `b81b2217` carries its own benchmark run:
`SWE_BENCH_PRO_V2_FIRST_MEASURED_RUN_20261125_V1.md`. It is the branch measuring *itself*, un-gated,
on official container images, each task graded by its own test:

| arm | resolved | rate | model calls | cost |
|---|---|---|---|---|
| **causal (the engine, un-gated)** | **0 / 51** | **0.0%** | 0 | $0.00 |
| `nop` (do nothing) | 0 / 51 | 0.0% | 0 | $0.00 |
| `oracle` (upstream reference patch) | 50 / 51 | 98.0% | 0 | $0.00 |

Composition of the 0: **44 `NO_EDITS`** (43 of them `FAIL_CLOSED`), **3 `EDITS_UPLOADED`** — each
self-status `PASS`, each verifier **0.0** — and 4 `HARNESS_ERROR`. Engine-attributable: **0 / 47.**
The branch's own §6 verdict: **"NO. Zero resolve rate, store ablated, one benchmark."**

So "already proved they work" is **false**. The mechanisms are **built, not proved** — and the one
branch that measured itself on a real board scored exactly what a do-nothing arm scores.

---

## §2 The four "superpowers": real code, or prose?

Checked for a `class`/`def` at the branch that actually holds the engine (`b81b2217`,
`canonical/runtime/repo_component_and_cow_engine_v1.py`):

| claimed superpower | status | where |
|---|---|---|
| 1 ms Copy-on-Write shadow forks | **code exists** | `zygote_worker_pool_v1.py` (the 1 ms figure is unverified) |
| Backward residual propagation | **code exists, measured 0/79** | `witness_inversion_v1.py`; my own run, 79 candidates, 0 passed |
| Mealy state tomography (`MealyAPICompiler`) | **prose only** | no `class MealyAPICompiler` anywhere in 14 branches |
| Petri-net morphism composition | **half real** | `class UnifiedCrossModalPetriNet` at L901 — real; `MorphismSkillStore` — **no class**, prose only |

| claimed next-level mechanism | status |
|---|---|
| Bidirectional FST lens synthesis | **code exists** — `def synthesize_fst_lens(` at L1442 |
| Articulation-point sub-goal slicing | **no symbol found** |
| Angelic value perturbation | **code exists** — `angelic_cegis_v1.py` (on this branch, not the 14) |
| Negative-space L3 invariants | **no symbol found** |

**Two of four superpowers and one of four next-level mechanisms are real code. The other five are
sentences in documents.** That is not a minor discrepancy: the plan's Step 1, Step 2 and Step 3 are
each built on one of the five.

---

## §3 The corrected bottleneck — two independent measurements agree, and neither is the one the plan names

The plan names Wall 1 ("the oracle that cannot choose": a green suite gives no selection gradient).
That wall is real and it is measured: **44 of 51** refusals on `b81b2217`, all carrying
`FAIL_CLOSED`, because with no failing test there is nothing to bind a demand to.

But my own corpus is the **opposite** condition, and it is the more uncomfortable result. In
`real_fix_pairs_20261119_V1` I *hand the engine the oracle*: source reverted to `before`, the
upstream fix's own tests kept. The failing test is present. There is no Wall 1 at all. Result:

| arm | oracle given? | solved |
|---|---|---|
| path-literal (literals in the top-6 path functions) | **yes** | **0 / 11** |
| local repair | **yes** | **1 / 56** |
| guard synthesis | yes | 0 / 27 |
| witness inversion | yes | 0 / 79 |

**Even with the answer's own test in hand, the repair operator is 0/11.** So Wall 1 is necessary but
not sufficient — and the plan's ordering is backwards in a way that is now measurable:

> Fixing Wall 1 without fixing the repair operator does not raise the score. It converts honest
> refusals into confident wrong answers. The branch already ran that experiment for us: 3 trials
> where the engine acted, **3/3 self-status `PASS`, 0/3 verifier `PASS`**. Refusal and wrong patch
> both score 0.0; only one of them is respectable.

The single bottleneck is therefore **the repair operator, in the oracle-given setting, on the 26
single-function-on-path tasks** — because that is the *necessary* condition, it is measurable today
without a container fleet, and it is the one place where my corpus supplies a real oracle. If the
operator cannot work when the failing test is handed to it, no amount of oracle manufacturing upstream
will help.

Why localisation is not the bottleneck (already measured, `33415ef5`): the modified function is on the
executed path in **50/68 = 73.5%** of tasks; it sits at median depth-rank 6, top-5 recall **50%**.
We know *where*. We cannot produce *what*.

And the vocabulary argument is already written down in this tree, in
`canonical/swe_kernel/induced_edit_basis_v1.py`: *"A capability bounded at 0 by vocabulary is not a
search problem."* That file also states its own limit honestly — templates substitute one leaf for
another inside an existing node, so "a fix that needs a new statement (a guard, an early return) has
no context-preserving substitution." 19.4% of upstream hunks add a statement; the other 80.6% are
modifications the basis could in principle reach — and still the measured result is 0/11.

---

## §4 Rejected ideas, and why

| idea | verdict | reason |
|---|---|---|
| **Pillar 0 — unify the 7 branches first** | **rejected** | unites *unverified* code. `45/45` is a patch file; the one self-measured branch is 0/51. A union of unmeasured mechanisms is not a multiplier, it is an unmeasured union. |
| **Metamorphic Witness Splitter as Step 1** | **rejected as first** | necessary, not sufficient. Oracle-given repair is already 0/11, so manufacturing more oracles upstream cannot move the score until the operator works. Build it *second*. |
| **A bigger mutation grammar** | **rejected** | measured: 75.2% of real fix pieces are unreachable by a fixed grammar (1,638/2,178). Adding entries moves the reachable set, not the class. |
| **16-way parallel CoW rollouts** | **rejected for now** | 16 × a 0% operator is 0%. Parallelism multiplies the operator; it does not create one. |
| **Federated skill distiller / self-play harvest over the 344** | **rejected as stated** | `b81b2217` §7 forbids feeding a store mined from the target repos back into those tasks — it warehouses the benchmark in the store exactly as §2 forbids in weights. The store must come from the house's own experience. |
| **Seeding the store to lift the 0/51** | **rejected** | same §7; the run was the **empty-store arm** (`STORE_FILE_ABSENT`), so 0/51 is the ablation floor, not the system. Lifting it by seeding is cheating the ablation. |

---

## §5 What is actually true, and what to do next

**True and verified:** the engine runs end-to-end on the official SWE-bench Pro V2 harness (153
trials in one run, artifacts committed by CI), at $0.00 and 0 model calls, ≈17.2 s/task engine time.
That infrastructure is real and it is the expensive part. **The 0/51 is the empty-store ablation
floor** — the with-store arm has never been measured, so no one, including this document, may quote
0/51 as the system's score.

**Next, in order — the necessary condition first:**

1. **Repair operator, oracle-given, 26 tasks.** Known function, real failing test, upstream fix as
   ground truth. Measure solved/26, and report the operator's *reach* separately from its *precision*.
   This is the gate: if it stays near 0, Wall 1 work is premature.
2. **Then Wall 1**, on the 44 refusals — a green suite turned into a failing oracle from the repo's
   own tests and the instruction's relational words. Baseline to move: 0/47.
3. **Then the with-store arm** of the §6 ablation, which has never been run.

**Nothing here meets §6**, and the honest summary is unchanged from the comparison: the frontier
scores 89.9% on SWE-bench Pro; our one measured run on its hardest subset is 0/51 at $0.00.
