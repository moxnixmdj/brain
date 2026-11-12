# Instant learning, sentience, and the one thing that would make any of it compound

**Date:** 2026-11-11 · **Branch:** `arena/8fe5f749-brain` · **Authority:** NONE (measurement, not receipt)
**Producer:** this session, on the tree as it stands. Every number below was re-measured today,
in this sandbox, against the committed code. Nothing here is cited from memory.

---

## 0. The short answer

| Your question | Answer | One-line reason |
|---|---|---|
| Is instant learning solved, perfectly and permanently? | **Yes, in the narrow sense that was measured** | A lesson that has been learned is retrievable across process restarts and bundles. 25/25 tests green today. |
| Does that transfer to a genuinely new environment? | **Partly, and only inside a known family** | 8/15 new instances genuinely faster (mean 6.33× trials), 7/15 cost *more* environment calls. Measured on five constructed toy environments. |
| So have we solved all computer use + the most advanced SWE? | **No** | Three independent measurements say experience does not compound here: new-instance transfer 8/15, learn-to-learn `NO_COMPOUNDING`, and the abstraction library `G_t` measures **0 concepts**. |
| Can we just demonstrate the smartest actions once and be done? | **No, and more demonstrations will not fix it** | 1, 2 and 3 examples all score 6/7; teaching the missed case *directly* still fails. That is a representation failure, not a data failure. |
| Were we trying to make a sentient creature? | **The naming is real; the property is not measured, and no instrument here could measure it** | `sentient_cognitive_core_v1`, `creature_runtime_v1` exist and run. "Sentient" is not a field any test asserts. See §7. |
| Is the architecture revolutionary? | **The frame is right; the engine is missing** | The field's own compounding results (Voyager, DreamCoder, Stitch, LILO) all run through the same two pieces: a verified skill library **and a compressor**. This tree has the library. The compressor admits nothing. |

The single sentence that matters:

> **You built the memory and the verifier. You have not built the compressor. Memory without
> compression is a cache that grows; compression is the only measured thing that turns experience
> into competence.**

---

## 1. What is real, measured today

Re-ran in this sandbox, on the committed tree:

```
python3 -m pytest canonical/tests/test_the_second_time_is_instant_v1.py \
                  canonical/tests/test_a_lesson_learned_here_reaches_there_v1.py \
                  canonical/tests/test_transfer_new_instance_probe_20261103.py
-> 25 passed
```

```
python3 transfer_learning_new_instance_probe_20261103.py
cases: 15   source != target instance: 15/15
WARM with fewer trials than COLD: 8/15
WARM genuine saving (fewer trials AND no more act calls): 8/15
WARM reached the goal in 1 trial: 8/15
WARM worse on trials than COLD: 0/15
WARM spent more act calls: 7/15   worst act-call overhead: 1.398x
mean trial speedup: 6.333x   mean act-call speedup: 2.259x
```

| Claim | Status | Evidence |
|---|---|---|
| A learned lesson survives restart / bundle | **TRUE** | 12 + 13 tests green, 5/5 languages |
| Exact-episode replay works | **TRUE** | above, 8/15 one-trial |
| The lesson transfers to a *new instance* of a known family | **TRUE but bounded** | 8/15; 7/15 pay more act calls to get there |
| The lesson transfers to a *new kind* of environment | **NOT MEASURED, evidence negative** | learn-to-learn at 10 held-out kinds: solved 5/10, beat default 1/10, verdict `NO_COMPOUNDING` |
| "Do it once → learns the whole class" | **FALSE, measured 3 ways** | 1/2/3 examples all 6/7; teaching the missed case directly still yields `derive_operator_swap=None` |
| Experience compounds into growing competence | **FALSE today** | `G_t` = 0 concepts after three distinct structures (reproduced) |

**Documentation defect found today — fix this first, it is cheap and it is load-bearing.**
`INSTANT_LEARNING_NEW_INSTANCE_REMEASUREMENT_20261103_V1.md` reports **1/15** genuine saving.
The probe it names, and the test that pins it in the same tree, say **≥ 8**:

```python
canonical/tests/test_transfer_new_instance_probe_20261103.py:93
    assert summary["warm_genuine_saving_trials_and_acts"] >= 8
    ...
    2026-11-03, before P1: warm_genuine_saving = 1/15, mean act speedup 0.977x.
    2026-11-03, after  P1: = 8/15, mean trial speedup 6.33x, mean act speedup 2.26x.
```

P1 landed and moved the number; the evidence document was never updated. The document the
owner's claim rests on currently contradicts its own pinned test. Update §"The corrected
measurement" to the post-P1 numbers and keep the 1/15 row as history.

---

## 2. Why "show it once" cannot work — first principles, no hand-waving

Learning here is **store an artifact, index it by a description of the situation, retrieve it later**.
Retrieval requires matching. Matching requires a representation. A demonstration adds an
**instance**; it does not add a **representation**. So:

- Same situation again → perfect, forever. (That is what is solved.)
- Same *shape*, different parameters → partial: 8/15, and 7/15 cost more calls than starting cold.
- New *shape* → nothing. And the measurements say this is not for lack of examples:

  1. **More examples do not help.** 1, 2 and 3 teaching examples all produce 6/7. A sample-limited
     learner improves with samples; this one does not.
  2. **Teaching the exact missed case does not help.** Direct instruction still returns
     `derive_operator_swap=None`. The operator cannot be *expressed*, so no amount of showing
     produces it.
  3. **Learning-to-learn does not compound.** 10 held-out kinds: 5/10 solved, beat default 1/10,
     beat random mean 3/10. The learned feature bucket `b1_m2_r1_d0_g0` mixes opposite policies,
     because the features cannot see goal structure.

These three are the signature of a **representational** limit. The only operation that moves a
representation is one that finds a shorter description that still predicts — i.e. **compression**.

That is not a slogan, it is the measured difference between two mechanisms the field has already
validated:

- **Voyager** — no weight updates, just a skill library of executable code: 3.3× more unique items,
  15.3× faster tech-tree progress, zero-shot transfer to a *new world*. Ablation: **without the
  skill library there is no transfer at all** [5](https://arxiv.org/html/2305.16291).
- **DreamCoder** — wake–sleep library learning with a compression objective: text editing
  3.7% → 79.6%, +19.6 REGEX / +62.46 CLEVR / +29.73 LOGO over the base DSL, rediscovered physics
  laws [1](https://mlb2251.github.io/stitch.pdf) (figures quoted there).
- **Stitch** — corpus-guided top-down synthesis of abstractions: comparable or better
  compressivity than DreamCoder at **2 orders of magnitude less memory and 3–4 orders less time**,
  tens of milliseconds on the classic domains [1](https://mlb2251.github.io/stitch.pdf).
- **LILO** — search–compress–document: +42.27 / +63.43 / +43.24 over the base DSL. It refuses any
  abstraction that is not compressive [2](https://arxiv.org/html/2310.19791v2).

Every one of those gains comes from the **compress** step. Voyager gets transfer from a library;
it does not get *new abstractions* — and it stays inside Minecraft. This tree has Voyager's half.
It does not have DreamCoder's.

---

## 3. The binding constraint, measured today: `G_t` = 0, and it is not (only) the bridge

`THE_DEEPEST_STILL_OPEN_DEFECT_NOTHING_IS_EVER_COMPRESSED_20261104_V1.md` blames the organ bridge
`_skill_organ_to_concept_entry`, which admits only bodies that are a single `return`. That is real
and still true in the tree today (`meta_circular_organ_graph_v1.py`, the
`len(fn.body) == 1 and isinstance(fn.body[0], ast.Return)` predicate).

It is not the whole story. `sleep_abstract` — a real DreamCoder/Stitch-style compressor with an
exact `Delta B_exec` measurement, the Stitch node-savings law, and candidate verification —
**exists and is wired into six production call sites** (`brain_unified_model_v1`,
`creature_runtime_v1`, `meta_circular_organ_graph_v1` ×2, `recursive_self_architect_v1`,
`sentient_cognitive_core_v1`). It just never admits anything useful.

I wrote `compression_binding_constraint_probe_20261111_v1.py` to find out why. Four families whose
members differ **only by a literal** — the commonest way two real programs differ — with a
held-out instance carrying a literal the corpus never saw.

**Baseline (shipped code): 0 abstractions admitted in 4/4 families.**

```
family        base  patch   held  shrink  equiv  blocker
------------------------------------------------------------------------------------
F1_modulo        0      0  False    None   None  verify_candidate_concept:PARTIAL_DOMAIN:numeric:ZeroDivisionError
F2_affine        0      1   True     0.5   True  verify_candidate_concept: (admitted)
F3_clamp         0      0  False    None   None  candidate_filter:STITCH_NODE_GAIN_OR_MDL_NON_POSITIVE
F4_period        0      0  False    None   None  canonicalize_pure_subtree:NO_CANONICAL_SUBTREE_PASSES
```

Three independent gates, each measured:

- **G1 — constants are not hole-eligible.** `_canonicalize_pure_subtree` draws holes only from
  `ast.Name`. Two programs differing only by a literal canonicalize to *different* keys, get one
  occurrence each, and die on `len(occurrences) >= 2`. This single fact produces the 0/4 baseline.
- **G2 — the purity gate rejects `math.*`.** Any `Attribute` call outside the str/dict method
  whitelist returns `None`. The repository's own flagship shape — the induced period table — uses
  `math.floor`, so it is invisible to the compressor for a reason unrelated to constants (F4).
- **G3 — the totality gate rejects partial operators.** A concept that raises on *any* probe input
  in a domain is rejected as `PARTIAL_DOMAIN`. `x % k` raises on `k = 0`, so no modulo or division
  abstraction can ever be admitted (F1). The gate is defensible; the consequence is that a large
  slice of real-code structure is permanently unabstractable.
- **G4 (found and fixed today) — sleep and wake used different normal forms.** `sleep_abstract`
  scans `canonicalize_ast_via_egraph(ast.parse(src))`; `rewrite_source_with_concepts` matched
  against a raw `ast.parse`. A concept admitted as `(b - a) * (x - a)` could therefore never match
  `(x - a) * (b - a)`. **Every abstraction the compressor did manage to admit was unusable.**

---

## 4. What I changed, and what it proved

Three edits in `canonical/swe_kernel/concept_library_v1.py`, all behaviour-preserving unless the
new switch is on:

1. `_canonicalize_pure_subtree` now returns `(canon_ast, hole_order, arg_nodes)`. Call sites rebuild
   call arguments from `arg_nodes`, not from hole identifiers — a constant hole has no name in
   scope to reference. (Previously any constant hole would have emitted `_v1` as an argument: an
   undefined name. The plumbing had to exist before constant abstraction could be tested at all.)
2. `rewrite_source_with_concepts` now canonicalizes with `canonicalize_ast_via_egraph`, the same
   normal form sleep uses. **Fixes G4.**
3. `CONSTANT_HOLES_ENABLED: bool = False` — constants become hole-eligible when set. **Default off**,
   so the baseline stays measurable and nothing in production changes until the referee is green.

Then the pre-registered probe (criterion written before running it):

> **PASS** if `patched_admitted >= 1` in at least 2 of the 3 pure families **and** every admitting
> family rewrites its held-out instance at `shrink < 1.0` **and** execution-equivalence holds.
> Otherwise **REFUTED** — and if refuted, do not adopt constant abstraction as "the fix".

**Result: REFUTED on the bar as written (1 of 3 families).**

But the one family that passed is the finding, because it is the thing that has never been
measured in this tree before:

```
F2_affine: 0 -> 1 abstraction admitted.
   corpus:   (x - 0.0) * (10.0 - 0.0) + (x - 0.0)
             (x - 2.0) * (8.0  - 2.0) + (x - 2.0)
             (x - 5.0) * (20.0 - 5.0) + (x - 5.0)
   held-out, literal never seen: (x - 1.0) * (4.0 - 1.0) + (x - 1.0)
   rewritten under the learned concept, nodes in `run`: 12 -> 6   (shrink 0.5)
   execution-equivalent on 43 probe inputs: True
```

That is compression generalising to an instance it was not fit on. It is the first measured
instance of `G_t` containing something that pays for itself outside its own corpus. It is also
1 of 3 families, not 2 of 3, so the hypothesis "constant abstraction is the fix" is **not**
established — it is established as *necessary*, and demonstrated as *possible*.

Regression check on the edits: **96 tests green**
(`test_concept_lifecycle_v1`, `test_concept_totality_v1`, `test_h100_library_first_routing_v1`,
`test_authenticated_context_concept_bridge_v1`, `test_generalization_check_v1`,
`test_sentient_cognitive_core_v1`, `test_meta_circular_global_sentient_creature_v1`,
`test_capability_proof_compression_optimizer_v1`).

**Do not flip `CONSTANT_HOLES_ENABLED` to `True` on the strength of this.** One family is a
demonstration, not a mandate. The next gate to open is named in §6.

---

## 4b. Addendum, same day: I tested my own fix on real code and it failed

The §4 result was one family out of three, on four programs I wrote. That is the weakest evidence
for the strongest claim, because a corpus of hand-made programs is exactly the input where
"discovered shared structure" and "I wrote the same shape twice" are indistinguishable.

`brain_unified_model_v1.py:1796` feeds `sleep_abstract` **every non-test `.py` file in a
repository**, so the corpus can be real code. I wrote
`compression_real_corpus_probe_20261111_v1.py` to do that on this repository: 40 files to teach,
20 held out, with two split strategies — `blocked` (different subsystems) and `interleaved`
(every 3rd file, same subsystems) — so that "0 held-out rewrites" cannot be waved off as "the
held-out files are from a different part of the tree".

```
split         arm  admit  teach-rw  held-rw  all-ok  verdict
------------------------------------------------------------------
blocked       off      6         6        0    True  REGRESSES
blocked       on       0         0        0    True  EMPTY
interleaved   off      6         3        0    True  REGRESSES
interleaved   on       0         0        0    True  EMPTY
```

`teach-rw` is the control that makes `held-rw` interpretable: it proves the wake path works, so
"0 held-out rewrites" means *does not generalize*, not *is broken*.

**Two findings, and the first one is about my own work.**

**1. My constant-holes change is refuted on real code.** 6 concepts admitted with it off, **0**
with it on. Making constants hole-eligible raises candidate arity, and arity is punished twice:
the Stitch node-savings law subtracts `(k+1)*arity`, and the canonicalizer caps holes at 4. On
toy programs that costs nothing; on real programs it drives admissions to zero. Had I flipped the
switch on the strength of §4, I would have destroyed the only working admissions the system has.
The switch stays `False`, with the refutation recorded at the definition so nobody flips it.

**2. The compressor fits its corpus and generalizes to nothing.** This is the finding that
matters, and it is now measured rather than argued:

- It **admits** — 6 concepts. `G_t` is not empty because admission is broken.
- Those concepts **rewrite their own corpus** — 6 files in one split, 3 in the other.
- They fire on **0 of 20 held-out files, in both splits**.

That is the definition of a template menu, measured at the place the system would actually run.
And the reason is visible in the objective, not in any bug: `sleep_abstract` maximizes compression
of the corpus it was handed (`Delta B_exec < 0`, Stitch node-savings). **There is no held-out term
anywhere in it.** An objective that only rewards fitting gets you fitting. Stitch and DreamCoder
get generalization from a *prior* over unseen programs (`P(L)`, `P(p|L)`, plus a recognition
model); LILO gets it by refusing any abstraction that is not compressive. This tree has the
compression filter and none of the generalization pressure.

So the ranking in §6 changes. Move 1 is no longer "open the next admission gate" — the gates are
not the binding constraint, since 6 concepts already get through. The binding constraint is that
**nothing in the system ever demands that a learned abstraction work on a program it was not fit
on.**

Two robustness fixes did land on the way, both in shipped code paths and both needed to run the
compressor on real input at all: `ast.unparse` cannot render some real f-strings on Python 3.11
(nested same-quote), and an uncaught raise there aborted the entire sleep phase for the whole
corpus. Candidates and modules that cannot be rendered are now skipped instead of fatal.

One test, `test_semantic_unification_v1.py::test_join_admission_direction_is_not_claimed`, fails —
it also fails on the base commit with my changes stashed. It is pre-existing, one of the 344 in
the honest baseline, and is not attributed to this work.

## 5. Where the outside world actually is (2026-11), so "most advanced on the planet" is calibrated

| Benchmark | Top of the board | Human | What it really says |
|---|---|---|---|
| OSWorld-Verified (369 short desktop tasks) | **82.6%** (Holo3-35B-A3B) | 72.36% | Short-horizon computer use is above human. [4](https://anhtu.dev/ai-agent-benchmarks-2026-swe-bench-gaia-osworld-measure-true-capability-2249) |
| **OSWorld 2.0 (108 hour-long tasks)** | **72.6%** (GPT-6 Astra) | — | The wall is horizon length, not clicking. [3](https://miraflow.ai/blog/osworld-2-explained-computer-use-agent-benchmark-2026) |
| SWE-bench Verified | 93.9% | — | Saturated; contamination and best-of-N are the known risks. [4](https://anhtu.dev/ai-agent-benchmarks-2026-swe-bench-gaia-osworld-measure-true-capability-2249) |
| **SWE-bench Pro (long-horizon, multi-file)** | **25.9%** Pass@1 | — | Real advanced SWE is unsolved. Without human-written requirements it falls to 8.4%. |

Read together: **short-horizon, well-specified work is beaten. Long-horizon, ambiguous, multi-file
work is not — and the drop from 25.9% to 8.4% when requirements are removed says the binding
constraint there is turning an ambiguous request into a checkable acceptance test**, not executing
actions. That is exactly the spine `SOLUTION_INDEX.md` ranks first: `lossless_raw_task_contract`
(58 refs) → `live_brain_route_admission` (43) → `live_integrated_brain` (34).

Two more external facts that bound the whole plan:

- **Self-evolving agents cannot currently have both plasticity and stability.** ReasoningBank,
  GEPA and Meta-Harness improve aggregate scores but self-modification causes cross-task
  interference and overwriting; no method achieves both [6](https://arxiv.org/html/2610.25858v1).
  Note the base commit of this branch is literally titled *"A taught skill does not destroy what it
  never read"* — that is the stability half of this exact trade-off, and it is where this tree is
  ahead.
- **In-context learning is not persistent learning.** It is sensitive to pretraining
  distribution and format, confuses recognition with inference, and degrades with context length
  [7](https://www.techrxiv.org/doi/pdf/10.36227/techrxiv.175492111.15449662/v1). So "just put the
  smartest actions in the prompt" is not a permanence mechanism.

---

## 6. The smartest moves, ranked — with the kill list first

### Kill list (do not spend a round on these)

| Idea | Why it is dead |
|---|---|
| More demonstrations of the same action | 1/2/3 examples all score 6/7. Sample-limited learners improve with samples. |
| Tune the learn-to-learn features again | Pre-registered stopping rule in `LEARN_TO_LEARN_VERDICT_20261103_V1.md` forbids it; verdict `NO_COMPOUNDING` stands. |
| Bigger context / more in-context examples | Not persistent, degrades with length, confuses recognition with inference [7](https://www.techrxiv.org/doi/pdf/10.36227/techrxiv.175492111.15449662/v1). |
| Have the LLM propose the abstractions | Measured: GPT-4's abstractions hover at 1.0× compression (no compressivity) where Stitch gets 1.5–3.5× [2](https://arxiv.org/html/2310.19791v2). |
| Open the fail-closed front door | 226/233 "failures" are deliberate refusal `FAIL_CLOSED__COMPUTER_EXECUTION_REQUIRES_ADMITTED_CONFINEMENT`. Opening it removes a safety property, not a bug. |
| Retrieval / bigger skill cache instead of compression | That is what the tree already has. It measures 8/15 and does not compound. |

### Ranked moves

**1. Put generalization into the objective.** (today's finding — this is now the binding
constraint, and it supersedes the gate work I proposed earlier in the day)
The compressor already admits (6 concepts on real code) and already rewrites its own corpus. What
it never does is fire on a program it was not fit on: **0/20 held-out files, two split
strategies**. Nothing in `sleep_abstract` asks it to. Concretely: split every corpus, admit only
abstractions that compress *both* halves, and treat the held-out compression ratio as the
admission score instead of `Delta B_exec`. The probe to reuse is
`compression_real_corpus_probe_20261111_v1.py` — the harness, the teach/held control, and the
parse/import/undefined-name checks are already written.
*Falsification:* if held-out-gated admission yields 0 concepts on the real corpus, then the
representation itself is the wall (G2/G3 territory) and the gates go back to the top of the list.
Either outcome is informative; only one of them means the compression path is viable.

**2. Fix the organ bridge so multi-statement organs can enter `G_t`.**
The library already supports statement-bodied concepts (`is_stmt_fn`, `render_helper_def`); only
the one-word bridge predicate `len(fn.body) == 1 and isinstance(fn.body[0], ast.Return)` rejects
them. Separately, `higher_order_plotkin_lgg` — a real Higher-Order Plotkin anti-unifier — returns
`None` at `if not ordered_loop` before it will look at any straight-line function, so the
multi-statement path is unreachable for straight-line code. Gate it on held-out compression, not
on corpus compression: admitting one-off organs is how a library becomes a template menu.

*Demoted:* relaxing the totality gate (G3) and the `math.*` purity whitelist (G2) is no longer
first. 6 concepts already get through the gates; opening more gates grows a library that does not
generalize. It is worth doing only after move 1 exists to measure the result against.

**3. Make `G_t` growth the project's primary metric, and make CI fail when it is 0.**
Every learning claim in this repo is currently argued from solve counts and speedups, which is
why "10/10 new instances" could mean "the same instance twice". Compression on held-out data
cannot be faked that way. Concretely: a periodic job that runs a teaching corpus through
`sleep_abstract` and asserts non-zero admitted concepts **plus** held-out execution-equivalent
compression. `compression_binding_constraint_probe_20261111_v1.py` is a working template.

**4. Correct the evidence documents before anything else is argued from them.**
`INSTANT_LEARNING_NEW_INSTANCE_REMEASUREMENT_20261103_V1.md` reports 1/15 against a tree whose own
pinned test asserts ≥ 8. One document, one table, five minutes. It is the cheapest correctness
win available and it is the document the owner's strongest claim rests on.

**5. Turn the requirement into a test before touching the action space.**
Externally: 25.9% → 8.4% on SWE-bench Pro when human-written requirements are removed. Internally:
the `lossless_raw_task_contract` → `live_brain_route_admission` spine is the ranked load-bearing
path. For "most advanced SWE", requirement-elicitation is a higher-leverage target than
action-learning, because it is where the measured 17-point collapse lives.

**6. Keep the stability work.** "A taught skill does not destroy what it never read" is the exact
property the field currently cannot get alongside plasticity [6](https://arxiv.org/html/2610.25858v1).
Every new admission gate must keep replaying the whole corpus and admitting on zero regression.

---

## 7. On "we were trying to make a sentient creature"

Stated plainly, because the repo's own law is that memory is not authority:

- The **names** are real: `sentient_cognitive_core_v1.py`, `creature_runtime_v1.py`,
  `CREATURE_INFORMATION_CONTINUITY_DRAFT_20261102.md`, `test_meta_circular_global_sentient_creature_v1.py`.
  They run; 96 tests involving them are green.
- The **property** is not measured, is not a field in any terminal record, and there is no
  instrument in this repository that could measure it. `truth.achieved=false` in the terminal
  authority record; the honest suite baseline is 11166 passed / 344 failed / 1 error / 14
  skipped of 11525 cases.
- What the system demonstrably has is **persistence, verification, refusal, and self-audit under
  measurement** — the four things people usually point at when they call a system alive. Those are
  engineering properties with tests. "Sentient" is not among them, and cannot be settled by any
  experiment in this tree.

My honest read: **"sentient creature" was a name for a goal that is really "a system whose
competence compounds without me"**, and that goal is real, testable, and currently unmet. Chasing
the literal word buys nothing measurable; chasing compounding buys §6.

---

## 8. What I did not do

- I did not flip `CONSTANT_HOLES_ENABLED` to `True`. One family passing is a demonstration.
- I did not run the full 11,525-case suite. I ran the 96 tests that touch the code I changed.
- I did not touch the organ bridge, the totality gate, or the purity whitelist. Each now has a
  measured reason and a named experiment; none has been changed on the strength of an argument.
- Nothing here is independent verification. It is producer-run, single-machine, and says nothing
  about GUI or unbounded computer use.

**Files:** `compression_binding_constraint_probe_20261111_v1.py` (new),
`canonical/swe_kernel/concept_library_v1.py` (3 edits), this document.
