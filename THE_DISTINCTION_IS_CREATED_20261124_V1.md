# THE DISTINCTION IS CREATED, NOT SELECTED
### 2026-11-24 · branch `arena/50c05c04-brain` · cost: 0 model calls, 0 stored parameters, 0 network at run time

> The previous round ended with a named defect and an unbuilt fix: guards are built by tagging every
> true condition, so a state's identity is stored three to five times over across redundant frames,
> and a tagged guard admits exactly the states that were tagged — which is why held-out coverage was
> **structurally 0.0 on all nine machines**. The missing primitive was the **minimal descriptor**.
>
> It is built, its crash is fixed, and it works — 10,050 guard literals collapse to **210**, a 48×
> reduction. And it does not buy a single correct held-out prediction: **29 of 30 are wrong**.
>
> That is the finding of this round, and it is the most useful one available. The bottleneck was
> never the vocabulary and it is not the descriptor. It is that **a descriptor is only ever as wide
> as the evidence that constrains it**, and evidence is what we have been refusing to collect.

---

## 1. What was built

**`canonical/swe_kernel/the_distinction_is_created_v1.py`** — the closed probe that rules out the
vocabulary hypothesis. Seven computed properties (`sorted_content`, `unique_content`,
`content_tail`, `runs_of_equal_content`, `inversions`, `duplicate_count`, `id_content_agree`), a
greedy `minimal_extension` set cover that returns its leftovers instead of pretending to have
covered them, `purity`, and `register_derived` so a created column is read by the **same** `holds`
as every written one. No second mechanism.

**`canonical/swe_kernel/safe_action_model_v1.py`** — `minimal_descriptor()`, the learner the last
round said was missing: for each `(atom, context)`, the smallest conjunction of pool conditions
that holds here and fails in every context where the atom is **known to do something different**.

**`canonical/tools/what_the_vocabulary_cannot_say_v1.py`** — the instrument, now scoring four
learners on identical splits: frames-only, frames-then-trimmed, minimal descriptor, minimal-then-
trimmed.

## 2. The measurement

Nine machines, depth 3, train 3/4 shuffled seed 13, held-out 1/4.

| learner | literals | held-out predictions | wrong | coverage |
|---|---|---|---|---|
| full signature, then trimmed (stock) | **10,050** | 0 | 0 | **0.000** |
| **minimal descriptor** | **210** | 30 | **29** | 0.09–0.37 |
| minimal, then trimmed | 0 | 0 | 0 | 0.000 |

And the number that decides how to read the middle row:

> **On its own training data the minimal descriptor makes 115 predictions and is wrong 0 times.**
> On held-out states it makes 30 predictions and is wrong 29 times.

The descriptors are not buggy. They are **exact for the evidence they were built from and
unauthorised everywhere else**. A guard formed by ruling out the contrasting contexts *we happened
to observe* is, in effect, a statement "no other context exists" — which the sample cannot support.

## 3. Three traps walked into, and what each one teaches

Each of these was measured, not reasoned about; each is now a test.

1. **Ruling out sibling contexts over-fits.** The first implementation ruled out every other
   pre-state of the atom, including ones with an *identical* effect. That is a set cover forcing the
   guard to name one state while the evidence supports a class: 32 of 40 predictions wrong, perfect
   on training data. **A guard must separate effects, not states.**
2. **"No observed context disagrees" is not "unconditional".** ARCHIVE2's append had one observed
   effect across four contexts, so an empty guard was emitted — and it then asserted that effect in
   a state where the atom really does something else (18 predicates added where the truth added
   none). Talk about the sample is not talk about the state space.
3. **A no-op is a fact and was silently dropped.** An atom whose effect is empty has no contrasting
   context, so the cover produced nothing and the atom vanished from the table — then got refused in
   states it had actually been run in. It now emits an unconditional no-op, which is the one empty
   guard that is honest.

## 4. The verdicts, verbatim from the artifact

```json
{"the_frames_alone_cannot_separate_some_states":        false,
 "a_computed_extension_separates_them_all":             true,
 "the_extension_reduces_inexpressible_contexts":        false,
 "the_extension_buys_predictions_on_held_out_states":   false,
 "safety_is_preserved_by_the_extension":                true,
 "the_frames_are_redundant_by_a_large_factor":          true,
 "a_minimal_descriptor_is_exact_on_what_it_saw":        true,
 "a_minimal_descriptor_is_WRONG_on_states_it_did_not_see": true,
 "trimming_is_sound_only_because_it_never_cites":       true}
```

The last one is recorded as a **false win, deliberately**. Hoisting a guard to `True` gives
`WRONG == 0` because it never cites anything. Soundness with no citations is not a result; calling
it one would be the tautology this repository's guard exists to catch.

## 5. What this closes

**The vocabulary hypothesis is dead, by measurement.** Across all nine machines: aliases **0**,
impure cells **0**, distinct signatures **== number of states**, and the literal-free extension
columns were needed **zero times**, in every machine, at every depth tried. There is nothing for a
computed column to fix. `the_distinction_is_created_v1` is kept as the closed probe that proved it,
not as a candidate.

**The descriptor hypothesis is now also dead, and by a sharper argument.** 10,050 → 210 literals is
a 48× compression and it moved coverage from exactly 0.000 to 0.09–0.37 — with 29/30 wrong. The
compactness was real; the generalisation was not. Compression is not reach.

## 6. The reframing this forces

The two terms were never independent, and the artifact now says so numerically:

```
coverage  ∝  compactness  ×  evidence
                 ↑              ↑
            10,050 → 210    what we actually constrained
```

The stock table maximises evidence and pays for it in over-specificity: coverage 0.000. The minimal
descriptor maximises compactness and pays for it in under-constraint: coverage 0.37 with 97% error.
**Neither dial is the missing part.** Both learners are drawing a boundary from a sample and then
treating the boundary as a fact about the world. The missing term is the one the mission statement
already names and the code has never implemented:

> **diff memory against what it must know, and fetch only the unknown.**

Nothing in this kernel ever *asks*. `explore` runs a fixed enumeration to a fixed depth; the
learner then closes over whatever that produced. Where the descriptor's boundary is unsupported, the
correct action is not to tighten it or widen it — it is to **run the atom in the context that
distinguishes the two candidates and observe**. That turns an unanswerable question ("does this
guard generalise?") into an answerable one ("which of these two contexts is real?"), and it is
exactly the acquisition problem the literature has already solved optimally.

This is the same move the mission prescribes, applied to the kernel's own ignorance: **diff instead
of stare**. The kernel currently stares.

## 7. Cost

```
model_calls 0 · stored_parameters 0 · network_at_run_time 0 · duration 56.12 s
```

Nine machines, four learners, five scores each, all from executed transitions over real fixtures.

## 8. Test status

`canonical/tests/test_what_the_vocabulary_cannot_say_v1.py` — **10 passed**, covering the
distinction machinery and all three traps above. Together with the three adjacent suites:
**50 passed**. Repo integrity guard: **PASS**, 17 rules, 0 violations.

35 failures exist elsewhere in `canonical/tests/` (native-artifact preflight, vocabulary-growth
suites). **They are pre-existing**: the preflight suite fails identically with this round's kernel
changes stashed. They are not introduced here and are not fixed here.

## 9. Next, in order

1. **Build the acquisition policy the kernel lacks** — the learner names the contexts that would
   separate its live candidates, and the instrument executes them. The measured quantity becomes
   *predictions bought per query*, not literals saved.
2. **Wire it into the §11 adapters** once predictions are bought, not before.
3. **The identifier audit report** (verified / unverified / failed) and the **four plays' verdicts**
   are owed from the prompt and are written up separately.
