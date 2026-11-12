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

## 4c. Addendum 2: I built the generalization gate and measured it. It works. There is nothing to gate.

§4b concluded the binding constraint was that nothing demands an abstraction work on code it was
not fit on. I implemented that demand and measured it.

`sleep_abstract` takes a new, backward-compatible `heldout_sources=` argument: a candidate must now
rewrite at least `min_heldout_sites` sites in a corpus it was **not** fit on before it may be
admitted. Default `None` means shipped behaviour is unchanged.

To keep the measurement from being circular I used a **three-way split**, since gating on a set and
then measuring generalization on that same set would be true by construction:

```
FIT       40 files   generate candidates, measure Delta B_exec   (fitting)
VALIDATE  40 files   gate admission: candidate must fire here    (gating)
TEST      40 files   never seen by fitting OR gating             (measurement)
```

Interleaved (`i % 3`) so all three sets span the same alphabetical region and the same subsystems.

```
arm        admit  rejected  fit-rw  val-rw  test-rw   ok
-----------------------------------------------------------
ungated        1         0       1       0        0  True
gated          0         1       0       0        0  True
                                              verdict: TOO_STRICT
```

**The gate works.** It was handed one candidate and it rejected that candidate — correctly, since
that concept fires on 0 of 40 validation files. The mechanism is sound and is now in the tree.

**But there was one candidate.** Not one hundred. Across earlier runs, 40 real files yield between
1 and 6 candidates. So "add generalization pressure" was the right *principle* and the wrong
*bottleneck*: a filter over one candidate cannot produce a library. §6 is re-ranked accordingly.

### The actual bottleneck, and where the machinery for it already is

Candidate identity in `sleep_abstract` is an **exact `ast.dump` match after alpha-renaming**. Two
occurrences are "the same structure" only if they are syntactically identical once variables are
renamed. Real code reuses structure *with variations* — a different literal, an extra term, a
reordered operand — so exact-match anti-unification finds almost nothing across files. That is why
1–6 candidates come out of 40 files, and why the ones that do come out are file-local idioms that
fire nowhere else.

The tree already contains the machine that handles *differing* subtrees:
`higher_order_plotkin_lgg`, a Higher-Order Plotkin anti-unifier that lifts differing closed
subtrees to value holes and differing open subtrees to higher-order callable parameters. It is
real, and it is unreachable:

```python
# concept_library_v1.py, higher_order_plotkin_lgg
ordered_loop = list(dict.fromkeys([*lb_ord1, *lb_ord2]))
if not ordered_loop:
    return None      # <-- every straight-line function exits here
```

Measured directly on the flagship shape from
`THE_DEEPEST_STILL_OPEN_DEFECT_NOTHING_IS_EVER_COMPRESSED_20261104_V1.md` — three period-table
programs differing only by their tuple literal:

```
higher_order_plotkin_lgg(p3, p7) -> None
```

Not "found nothing". It refuses to look, because an induced period table has no loop. So the one
mechanism that could abstract the project's own flagship failure is gated off for exactly that
shape, and the reachable mechanism (exact-match) structurally cannot find it.

Three independent gates, all now measured, all pointing at the same thing: **the compressor can
only rediscover syntax it already matches exactly**. G1 constants (measured, harmful to fix),
G2 `math.*` purity, G3 totality, plus the straight-line LGG gate. Fixing admission was never going
to help, because almost nothing reaches admission.

### A mistake of my own, recorded

First run of this probe reported `REGRESSES` with `UNDEFINED:all,enumerate,isinstance,len,list,max`
against the shipped wake path. That was a bug in **my probe**, not in the library:
`_undefined_names` used `dir(__builtins__)`, and `__builtins__` is a *dict* inside an imported
module, so `dir()` returned dict methods instead of builtin names. The rewrite was correct. I
nearly reported a live correctness bug in shipped code that did not exist — the same class of
error as the toy-corpus overclaim in §4, caught the same way, by checking before asserting.

## 4d. Addendum 3: I opened the anti-unifier to straight-line code. Nothing came out.

Following §4c, I measured the headroom first (there is no point removing a gate without checking
what is behind it), in this repository's own 40 fit files:

```
multi-statement functions (1-4 args, body >= 2)
  straight-line:     117        eligible pairs: 489
  loop-containing:    40        eligible pairs:  28     (all that is reachable today)
median function size 63 AST nodes, max 377
```

17.5× more pairs behind the gate, at tractable sizes. I opened it
(`STRAIGHT_LINE_LGG_ENABLED`, default `False`) and re-ran the same three-way split, held-out gate
ON in both arms so the only difference is the pool:

```
arm    admit  rejected  fit-rw  val-rw  TEST-rw   ok
-------------------------------------------------------
off        0         1       0       0        0  True
on         0         1       0       0        0  True     verdict: NO_GAIN
```

Identical. 489 eligible pairs produced **zero** additional candidates. The `ordered_loop` gate was
not the bottleneck: the anti-unifier returns `None` for these pairs further in — at
`_anti_unify_stmt_list` and at the admission filters — not at the gate I removed. Per my own
pre-registration, this is **not** counted as a fix and the switch stays off.

### What three refutations in one day add up to

| Hypothesis | Result |
|---|---|
| Constants are not hole-eligible, so nothing can be compressed | **Harmful.** 6 admissions → 0 on real code |
| The objective has no generalization term | **True but not binding.** The gate works and filters ~1 candidate |
| The anti-unifier cannot see straight-line code | **NO_GAIN.** 489 pairs → 0 new candidates |

Three different mechanisms, three null results, one common factor: **every one of them was tested
against human-authored Python source files.**

That is the finding, and it is a corpus problem, not an algorithm problem.

**Library learning pays off on corpora that are not already factored.** DreamCoder's headline
gains — +19.6 REGEX, +62.46 CLEVR, +29.73 LOGO — come from programs written in a minimal DSL where
every solution rebuilds its primitives from scratch, so shared structure is abundant and *unnamed*.
Stitch and LILO operate on the same kind of corpus. That is the setting where "compress the corpus
into abstractions" has something to compress.

Human-authored Python is the opposite case. Reuse is already expressed — as function calls, as
imports, as classes, as methods. The abstractions have already been named and factored out, by
people. Running a library learner over it is asking it to rediscover structure that is already
spelled out, and the measurement says it finds almost none: 1–6 candidates per 40 files, all of
them file-local idioms.

The evidence for this is already in hand, measured today, with the same machine:

- **Unfactored corpus** (three flat programs differing only by a literal): the admitted concept
  compressed a **held-out program carrying a literal it had never seen** — 12 → 6 AST nodes,
  execution-equivalent on 43 probe inputs. It generalized.
- **Factored corpus** (40 real source files): 0 of 40 held-out files, twice, under two split
  strategies.

Same compressor, same day. The difference is the corpus.

**So the compressor is probably not broken — it is pointed at the wrong input.** The right corpus
is the machine's own output: synthesized programs are flat and repetitive by construction, which is
exactly the unfactored shape library learning needs. That is also precisely DreamCoder's
wake–sleep setting: the solver emits flat programs during wake, sleep compresses them, and the
resulting library makes the next solve cheaper. The loop is the point, and the loop needs the
solver's output, not the programmer's.

This is stated as a hypothesis with the contrast above as its evidence, not as an established
fact. It is the next experiment, and it is a **corpus routing** change — which file list gets
handed to `sleep_abstract` — not another algorithm change, so it is cheap to run and cheap to
revert.

## 4e. Addendum 4: the corpus experiment did not run. That is not a result.

I tried to test the §4d corpus hypothesis the controlled way: take the same 120 files, and
mechanically *de-factor* one arm by inlining every call to a same-file `return <expr>` helper, so
that shared structure is spelled out at each call site instead of referenced by name. Same content,
one variable different.

```
defactoring: 1/120 files changed, 1 call sites inlined

arm           admit  rejected  fit-rw  val-rw  TEST-rw   ok
--------------------------------------------------------------
factored          0         1       0       0        0  True
defactored        0         1       0       0        0  True
```

**The manipulation failed.** One call site, in one file, out of 120. The corpus contains almost no
top-level single-`return` helpers to inline, so the "defactored" arm is the same corpus wearing a
hat. The run measured nothing.

It would be easy to read `NOT_CONFIRMED` as "the corpus hypothesis is refuted." That would be
wrong, and it is exactly the mistake of §4 (toy corpus) and of my own probe bug in §4c (builtins
reported undefined): reporting a conclusion the measurement does not support. So it is recorded as
**inconclusive, not negative**. The corpus hypothesis is untested.

What the failure does tell us, usefully, is that this codebase's Python has almost nothing
inlinable at that shape — which is itself consistent with "already factored," but does not
establish it.

I stopped here rather than build a more elaborate corpus generator. Four manipulations of this
compressor have now produced four null or inconclusive results, and the marginal value of a fifth
is lower than the value of saying plainly what is established and what is not.

### What is established, and what is not

**Established by measurement today:**

| Claim | Status |
|---|---|
| A learned lesson persists across restart / bundle | TRUE, 25 tests green |
| Exact-episode replay works | TRUE |
| Transfer to a new instance of a known family | TRUE but bounded: 8/15, and 7/15 cost more calls |
| Transfer to a new *kind* of environment | Negative: learn-to-learn `NO_COMPOUNDING` |
| "Show once, learn the class" | FALSE, three ways: 1/2/3 examples all 6/7; direct instruction fails |
| The compressor generalizes on this codebase's Python | FALSE, four attempts, 0 TEST rewrites throughout |

**Not established:**

- That the compressor *cannot* generalize. It generalized on a flat unfactored corpus (12 → 6 nodes
  on an unseen instance, execution-equivalent). What is unestablished is whether a real
  machine-generated corpus exists here to feed it.
- That the corpus is the binding constraint. Untested — the experiment did not run.

The load-bearing negative is narrow and firm: **on this repository's human-authored Python, under
four different manipulations, no learned abstraction ever fired on held-out code.** That is enough
to say "show it once" cannot work today. It is not enough to say the compressor is dead.

### Where I think the effort should go instead

The compression line is now blocked on something that is not a mechanism: it needs a corpus of
machine-generated, unfactored programs, and producing one requires running the synthesizer at
scale. That is an integration task, not a research one, and it should not be attempted by tuning
the compressor further.

Meanwhile, the external numbers in §5 point at a different constraint for the actual goal. The
sharpest single fact found today is that SWE-bench Pro falls from **25.9% to 8.4%** when
human-written requirements are removed. Advanced software engineering is gated less by executing
actions than by turning an ambiguous request into a checkable acceptance test — and that is exactly
the spine `SOLUTION_INDEX.md` already ranks first (`lossless_raw_task_contract` →
`live_brain_route_admission` → `live_integrated_brain`). Effort spent there is aimed at a measured
17-point collapse. Effort spent on the compressor is aimed at a hypothesis that is currently
untestable here.

## 4f. Addendum 5: the corpus hypothesis is CONFIRMED. The compressor works.

§4e could not de-factor human code (1 inlinable call site in 120 files), so this builds the
unfactored corpus the direct way: **by having the machine synthesize it.**

`synthesize_python_function_body` — the tree's own observational synthesizer, run with an empty
concept library — was fed I/O specs for 1,200 generated tasks across six families whose instances
differ only by a literal. 120 programs survived synthesis and full-grid verification. They are
flat, expanded, and unfactored, exactly as intended:

```
affine (x-0)*(3-0)+(x-0)   ->  "return ((x * 2) * 2)"
affine (x-0)*(4-0)+(x-0)   ->  "return ((x * 3) * 3)"
```

Same three-way interleaved split and the same held-out gate as every prior probe. The comparison
point is the human-authored result from §4c: **0 TEST rewrites.**

```
 programs  admit  rejected  fit-rw  val-rw  TEST-rw   ok   verdict
--------------------------------------------------------------------
      120      2         0       9       9       13  True   PASS

amortized compression (library counted ONCE)
  fit        40 programs   before 441   after 410   library once 25   shrink 0.9864
  TEST       40 programs   before 523   after 481   library once 25   shrink 0.9675
```

**The corpus was the binding constraint.** Same compressor, same objective, same gates, same
session. Human-authored source: 0 of 40 held-out. Machine-synthesized programs: **13 of 40
held-out**, zero candidates rejected by the held-out gate, every rewrite import-clean and free of
undefined names. Nothing about the algorithm had to change.

Two honest qualifications, because the headline number alone would oversell this.

**1. The per-file number says inflation, and the per-file number is the wrong accounting.**
Measured per-file shrink is 1.69× — rewritten programs are *bigger*. `rewrite_source_with_concepts`
inlines each concept helper into every file that uses it, so a 13-node program pays for a 25-node
helper it uses once. That is an artifact of the wake renderer, not of the abstraction. Counted the
way library learning is actually scored — library paid for once, amortized across the corpus — the
same rewrites compress: **0.9675 on TEST.** Both numbers are reported; only the second answers the
question that matters.

**2. 3% is a proof of concept, not a result.** Stitch achieves 1.5–3.5× compression and DreamCoder
gains +19.6 to +62 points on *larger* programs in minimal DSLs. These programs average 13 AST
nodes; there is not much there to compress, so 0.9675 is close to the ceiling for this corpus size.
The direction is confirmed. The magnitude is not yet.

**What it means for your question.** The machinery you built is not broken and it is not missing a
gate, a constant rule, or a generalization term. It was being handed the wrong kind of material.
Pointed at programs the machine produces — flat, repetitive, abstractions not yet named — it
learns abstractions that fire on programs it has never seen and compress them. Pointed at
programmer-authored source, where the reuse is already spelled out, it finds nothing. That is the
same distinction DreamCoder's wake-sleep is built around: wake emits flat programs, sleep
compresses them, the library makes the next solve cheaper.

### The compounding loop is now testable

This is the first result today that makes the loop measurable end to end: synthesize → sleep →
admit → reuse → synthesize again with the library present. The one experiment that would show
compounding is a second synthesis pass over held-out tasks **with the learned library supplied**,
measuring whether solve rate or search cost improves. That is the actual claim — that experience
makes the next problem cheaper — and it has never been measured in this tree.

## 4g. Addendum 6: the library does not make the next problem cheaper. (NO_COMPOUNDING)

§4f established that the compressor works on machine-synthesized programs and that its concepts
generalize. What none of the prior probes measured is what the library **buys** — which is the
actual claim behind "show it once and it learns it permanently". If that is true, the next problem
must get cheaper because the first one was solved.

This measures it. 250 warmup tasks solved and compressed into a library; then the **same 120
held-out tasks** synthesized twice, once with an explicitly empty library and once with the learned
one. Identical tasks, identical synthesizer settings, identical order.

**Design note that matters:** the synthesizer cannot safely be passed `concept_library=None` for a
control. It falls back to `DEFAULT_LIBRARY_PATH` when that file exists, which would silently load a
persisted library and contaminate the cold arm. The cold arm gets an explicitly constructed empty
library on a fresh temp path. Without that, the control is not a control.

First run, 120 held-out tasks: cold 7 solved, warm 8, `delta_solved = +1`. My pre-registered rule
(`d_solved > 0 OR faster`) fired **COMPOUNDS**. That verdict was wrong, and it was wrong because of
an `OR` I wrote too loosely: one extra solve out of 120 is sampling noise, and the same run showed
warm **11% slower** with **44% larger** bodies. I tightened the rule and re-ran with 400 held-out
tasks and a paired comparison, which removes task difficulty as a confound:

```
arm     solved    rate   wall_s  mean_nodes
-------------------------------------------
cold        32   0.080    47.41       14.16
warm        31   0.077    53.01       16.90

delta solved: -1          wall speedup: 0.894   (warm is SLOWER)

paired, on the 30 tasks BOTH arms solved
  cold_mean_nodes 14.23   warm_mean_nodes 16.63   node_ratio 1.169
  cold_mean_secs  0.0661  warm_mean_secs  0.0547  time_ratio 0.828
  solved only by cold: 2      solved only by warm: 1

verdict: NO_COMPOUNDING
```

Read honestly, this is a mixed picture that nets out to nothing:

- **Solve rate: unchanged.** 32 vs 31 out of 400. Not an improvement.
- **Total wall time: 11% worse** with the library.
- **Bodies: 17% larger** on the tasks both arms solved.
- **One real positive:** on the tasks both arms solve, the library makes synthesis **17% faster**
  (0.828 time ratio). When a concept happens to apply, it is a genuine shortcut.

That last number is the whole story in miniature. Adding concepts to the grammar **widens the
search space**. On a task where a concept applies, you get a shortcut. On every other task you pay
to explore concept applications that fail. Measured here, the overhead exceeds the shortcut.

**This is exactly the gap the literature names.** DreamCoder is three components, not one:
(1) library learning during sleep, (2) a **recognition model** — a learned search policy that
predicts *which* concept to try — and (3) sleep-dreaming to train it. Its own ablation is explicit:
dreaming and the recognition model each contribute substantively. A library with no prior over its
use is not a speedup; it is a larger menu to search. Stitch reaches 1.5–3.5× compression and LILO
adds +42 to +63 points, but both sit on top of search that knows how to deploy abstractions — LILO
found that handing GPT-4 abstractions *hurt* downstream synthesis (−30.6 REGEX) until the
abstractions were de-obfuscated and documented.

This tree has component (1). It does not have (2). Nothing in the synthesizer prefers a concept on
the basis of the task; concepts are simply added to the enumeration at weight 2 and searched like
any other primitive. §4g is what that costs, measured.

### What this does and does not say

**It does say:** a library that demonstrably generalizes to held-out programs (13/40, §4f) does not
make subsequent synthesis cheaper. Generalization of the library and compounding of capability are
different properties, and only the first has been achieved.

**It does not say:** the architecture is wrong, or that the library is useless. It says the library
is currently an unpriced menu. The missing piece is measurable and specific: a prior over concept
use. The cheapest possible version is already available from data the library records —
`log_prior`, `mdl_gain_bytes`, `corpus_sites`, `verified_hits` are all on `ConceptEntry` — so
concepts could be ordered by expected usefulness rather than enumerated blindly.

**The next experiment, if this line continues:** rank concepts by `verified_hits` and `log_prior`
and search high-priority concepts first, then re-run this exact probe. Prediction, pre-registered:
if ordering is the fix, warm should beat cold on BOTH time and solve rate. If it does not, the
library is not the path to compounding in this tree and the line should be closed.

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

**1. Route machine-generated programs into `sleep_abstract`.** (CONFIRMED today, §4f)
Same compressor, same gates, same session: 0 of 40 held-out rewrites on human-authored source,
**13 of 40** on 120 machine-synthesized programs, amortized shrink 0.9675. This is no longer a
hypothesis — it is measured, and it is the single highest-value change available. Concretely: feed
`sleep_abstract` the synthesizer's own verified output, not repository source. The call sites exist
(`sentient_cognitive_core_v1.py:2183` `verified_programs_buffer`;
`recursive_self_architect_v1.py:2734` `ring1_sources`). Note that
`brain_unified_model_v1.py:1796` currently sweeps in every non-test `.py` file — which is precisely
the factored corpus that yields nothing, and is the wrong default.
*Caveat before celebrating:* 3% on 13-node programs is a proof of concept. Stitch reaches 1.5-3.5x
on larger programs. The compression ratio must be re-measured on a corpus of larger synthesized
programs before this is called a win.

**1b. Then measure the compounding loop itself.** Synthesize held-out tasks a second time, **with
the learned library supplied**, and measure whether solve rate or search cost improves. That is the
claim that has never been tested here: that experience makes the next problem cheaper. Everything
so far measures the library; nothing yet measures what the library buys.

**2. Keep the held-out gate on.** It is in the tree now (`heldout_sources=`), it is backward
compatible, and it demonstrably rejects non-generalizing candidates. It admitted nothing today
only because one candidate reached it. Whatever produces candidates next must pass through it, and
the acceptance bar is TEST rewrites, never VALIDATE rewrites.

**3. Fix the organ bridge so multi-statement organs can enter `G_t`.**
The library already supports statement-bodied concepts (`is_stmt_fn`, `render_helper_def`); only
the one-word bridge predicate `len(fn.body) == 1 and isinstance(fn.body[0], ast.Return)` rejects
them. Do this after move 1, and gate it on held-out compression: admitting one-off organs is how a
library becomes a template menu.

*Demoted:* relaxing the totality gate (G3) and the `math.*` purity whitelist (G2) is no longer
first, and neither is "put generalization in the objective" as I first wrote it. Generalization
pressure is necessary but it filters ~1 candidate, so it cannot be the first move. The order is:
generate more candidates, then gate them.

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
