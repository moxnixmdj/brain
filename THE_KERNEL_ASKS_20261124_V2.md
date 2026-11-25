# THE KERNEL ASKS — and the answer is not what either of us expected
### 2026-11-24 · branch `arena/50c05c04-brain` · 0 model calls · 0 stored parameters · 0 network at run time

> Requirements that bind this round, restated: own model only with zero runtime model calls; no
> parameter may warehouse world facts; every parameter derived and justified; knowledge lives in an
> external, removable store; research the project before the web; first principles, name the real
> limiting factor; kill ideas before building them; ultimate solution, not incremental; honesty with
> verified / unverified / failed; tests on the hardest real problems; never ask the user anything.
>
> The §2 contradiction stays resolved as before: **forbidden** = weights as a lookup of memorised
> facts or any runtime dependence on another model; **allowed** = an inspectable, editable store plus
> one-shot learning that writes to it, with weights holding only computed mechanism. Nothing this
> round changes that boundary, and nothing in this round made a model call.

---

## 1. The prompt's plays, audited before any of them were built

§4 says to verify, and every identifier below was re-checked by `grep` over the tree at `b70fcf8*`.
The plays are only worth building if the machinery they claim exists really exists.

| claim | status | what the tree actually contains |
|---|---|---|
| `zygote_worker_pool_v1` "1 ms Copy-on-Write shadow forks" | **VERIFIED — and narrower than claimed** | 364 lines, real `os.fork()`, real CoW page sharing. It forks **the Python process**, and what it shares is read-only interpreter pages. |
| `MultiLayerSnapshot` / `MealyAPICompiler` | **1 file, no implementation** | one mention, no module |
| `calculate_separating_projection` | **ABSENT (0 files)** | the play's centrepiece does not exist |
| `epistemic_doc_compiler` | **ABSENT (0 files)** | "already turns SQLite + CLI --help + OpenAPI into typed contracts" — it does not |
| `simulate_plan` / `CUMentalWorldModel.simulate` | **2 files, no simulator** | the "physics engine" is a name |
| `SyPet` / `APIphany` / `SymLLM` | **1 mention each or absent** | no implementation |
| commits `click@fc518e4`, `werkzeug@051fd663` | **ABSENT (0 files)** | two of the five "logged unsolved commits" are not in the log |
| `click@05f6fd0df4` | **VERIFIED** | logged with the exact hunk in `THE_SPACE_IS_THE_ARTIFACT_*` |
| `zygote_worker_pool_v1` count | 62 files (was 42 last round) | grows because the name is *cited*, not because the capability grows |

**Of four plays, the only engine that actually exists is the fork.** Everything else the prompt
described as "already owned" is a name in a document. That is the single most important fact this
round established, because it means the plays cannot be "wired in" — three of them would have to be
invented first.

## 2. Play 3 measured, not argued

The claim: 16 parallel CoW realities, 1–2 ms, pick the verified winner.

`fork_measurement()` in `canonical/tools/ask_instead_of_stare_v1.py` forks two children that each
write the same path and then reports what survived:

```
final_content = "child-b" · isolated = False
why = both children wrote the same path; the last writer won, so the branches were
      one reality observed twice, not two realities
```

**A CoW fork isolates the Python heap. It does not isolate the environment.** The machine's state in
this tree is a directory of files on disk, and two processes writing one directory are two writers of
one reality. So "16 parallel futures" is not available by forking, and the 1–2 ms figure is real for
the wrong object. This is the same class of error as the previous round's aliasing hypothesis: a
plausible mechanism whose measurement says it does not reach the thing it was aimed at.

What *is* available is better and exact: the harness can `reset()` and re-execute a prefix
deterministically, so a **probe is a real observation**, not a speculation. That is what §3 builds.

## 3. The thing that was actually missing — and it is built

Last round closed on this sentence: *a descriptor is only ever as wide as the evidence that
constrains it, and nothing in this kernel ever asks.* `canonical/tools/ask_instead_of_stare_v1.py`
makes the kernel ask.

* A **question** is a prefix (a sequence of atoms) plus a predicate that pins the resulting state,
  computed from the rows by `row_equals`. The predicate is a callable, deliberately **not** a condition
  tuple: the first version returned `("ROWS", "EXACT", …)`, `holds` could not read that relation, and
  the "predicate" was a label no code ever checked. Tests now pin this.
* The question is **asked by executing it**, and the answer is read from the environment.
* A pair that no prefix can reach is recorded **UNASKABLE**, never dropped.

Nine machines, depth 3, budget 8, no query touching a held-out state:

| | before | after |
|---|---|---|
| contradictions | **1,714** | **58** |
| atoms citable | 41 | 32 |
| questions asked | — | 25 (9 answered, 9 predicate-verified) |

## 4. Two ways my own metric lied, both caught

Recording these is the point of the round. Both were found by running, not by reasoning.

**Lie 1 — contradictions can be deleted instead of resolved.** JOURNAL went **63 → 0 contradictions
while its operators went 28 → 7**. Four atoms in five were *excluded*, not explained, and a
contradiction count cannot tell the difference. The fix is a metric that cannot be gamed: `atoms_before`
/ `atoms_after`, reported always. The verdict `the_reduction_kept_the_atoms` is now a gate on the
claim, and the honest reading of 41 → 32 is *some of the reduction is explanation, some is silence*.

**Lie 2 — "every question was checked" is false.** The verdict came back **false**: 25 asked, **9
answered**. Sixteen questions went unasked or unanswered — GIT and GIT2 answered 0 of 8 each, while
their 110 and 90 contradictions stayed at exactly 110 and 90. A system that reports "I asked" when it
could not reach the state is the failure mode this repository keeps having to catch. It is reported,
not smoothed.

## 5. The budget experiment — targeted vs. random vs. nothing

Same budget, same ban on held-out states, three arms. This was built to stop myself claiming that
asking helps when only *more data* helps.

| arm | predictions | wrong |
|---|---|---|
| A — no queries | 33 | 26 |
| B — **targeted questions** | 19 | 12 |
| C — **same budget, random observations** | 4 | 4 |

* `targeted_beats_random_on_the_same_budget` → **true** (19 vs 4)
* `targeted_beats_no_queries_at_all` → **false** (19 vs 33)
* `targeted_stays_sound` → **false** (12 wrong)

Reading it honestly: **asking is a good query policy and a bad learner.** It beats random by 4.75×, so
the *targeting* is real and worth keeping. It loses to not asking at all, because every answered
question produces a tightly-fitting descriptor that then over-generalises — the previous round's
defect, unchanged. Asking cannot rescue a learner that is already wrong; it only picks its inputs
better. That is the correct conclusion and it kills the hope that acquisition was the missing term.

## 6. The hypothesis this round killed with a measurement

Following §10's "reframe", the obvious repair was: the contradictions are **cardinality drift**
(guards admitting 4- and 5-element states), and the pool only offers `count_is` — equality — so it
cannot say "at least 3 rows". A monotone range column should therefore be exactly the missing
distinction. Built and measured on nine machines:

```
TOTAL equality-pool: predictions 31, wrong 25
      range-pool:    predictions 31, wrong 25
```

**Zero effect.** Not one prediction moved, and every one remained wrong. The range hypothesis is dead,
and by the sharper route: `minimal_descriptor`'s guard is the *minimal* cover of the contexts it
observed, and it never had a reason to pick a cardinality literal — with a range column available it
still chooses `count_is`, because that is what separates the sample. The missing distinction is not a
test form. **The guards are separators of observed pairs, not conditions the dynamics obey.**

## 7. The verdict on §3 of the prompt

> Claim: instant learning already works, including in new arbitrary environments.

**False as stated, and now located precisely.** What is real:

* Learning **one transition exactly** is real and sound — full-signature guards, 0 wrong, and the
  ability to say "I refuse" rather than guess.
* Learning **the vocabulary** works: 0 aliases, 0 impure cells, signatures == states, on every machine.
* **Sampling** works: targeted questions beat random ones 19–4 on an identical budget.

What is missing, in one sentence: **an inductive bias with a notion of width.** Every learner in this
tree either names the states it saw (sound, no reach) or names the smallest cover of the pairs it saw
(compact, wrong). Nothing in the tree can propose *"this guard is valid for all states with the same
row identity"* — a hypothesis **wider than its evidence but falsifiable**, which is the only shape that
generalises. That is a representational commitment (`IDENT`-invariance as a stated law with a
re-validation probe), not a column and not a query policy. It is the next bottleneck and it is now
named by two independent measurements rather than inferred.

## 8. Cost and state

```
model_calls 0 · stored_parameters 0 · network_at_run_time 0 · duration 100.46 s
```

Nine machines, three arms, 25 questions, 9 answered, 6 tests green, and one fork experiment.

## 9. What is next, in order

1. **Build the width hypothesis**, per §9.2's "cross-environment laws": a typed law that states the
   invariance, carries its witness, and is *re-probed* before trust. Test it exactly as the last two
   hypotheses were tested — held-out, same budget, arms side by side.
2. Only then wire the §11 adapters, because an adapter for a learner that is 12/19 wrong publishes a
   wrong number.
3. Keep `ask_instead_of_stare_v1` as the query policy it proved to be — 4.75× cheaper than random —
   and stop calling it a learner.
