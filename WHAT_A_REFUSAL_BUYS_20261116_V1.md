# What a refusal buys

**The question.** The previous round ended where every honest account of learning from one execution ends: a
verdict that says *no reading of what I can see explains what just happened*. That verdict is not an answer, it
is the only place a vocabulary can be grown without lying. So: given a real action the current vocabulary cannot
explain, what is the minimal extension that makes it explainable — and how would the agent know the extension is
worth keeping, given that by assumption it has no criterion that can see the value yet?

**Why it cannot be answered by inventing.** This tree already tried the obvious version of growth and measured
it dead: an induced action-law vocabulary (`SET`, `STORE_CONSTANT`, `ADD`, `MOD`, `TABLE`) was wrong on **6,261
of 19,648** reachable transitions, and still wrong on 98 after the first defect was removed —
*"a law vocabulary that must happen to contain the right distinction is the same defect as the index, rebuilt
inside the model."* Free invention is a bigger vocabulary with the same flaw. Growth has to be *bought* against
an observed failure, and *verified* on executions it was not derived from. That is the whole method here.

**Why the order of the tests is the content.** The loop asks five things in a fixed order, and the first one is
not the refusal:

| # | outcome | what it means | what to do |
|---|---|---|---|
| 1 | `EXPLAINED` | the flat grammar already reproduces it | nothing |
| 2 | `INVISIBLE_IN_THE_CURRENT_VIEW` | the view shows no change, but a derived view does | grow the observable |
| 3 | `NOT_A_FUNCTION_OF_THE_STATE` | the view shows changes that disagree | quotient to a set |
| 4 | `OUTSIDE_THE_FLAT_GRAMMAR` | one stable consequence, no reading produces it | compose |
| 5 | `BEYOND_THIS_OBSERVABLE` | nothing in the family sees it, and the effect is real | stop, and name the sensor |

Outcome 2 is checked before 3 because it is the *silent* failure, and it is worse than a refusal. An action the
view cannot see is never refused. It is accepted as `identity`. The agent then "learns", with full confidence and
no signal to the contrary, that the action does nothing.

## Five real actions, five outcomes, nothing asserted

Real directories, real programs from `PATH`, repeated executions, held-out states, no model anywhere
(`VOCABULARY_GROWTH_20261116_V1.json`).

| action | outcome | growth bought |
|---|---|---|
| `cp payload.dat out.dat` | `EXPLAINED` | **none** — the negative control |
| `touch keep.dat` | `INVISIBLE_IN_THE_CURRENT_VIEW` | `DERIVED_PREDICATE(mtime_changed)` |
| `sort -R payload.dat -o out.dat` | `NOT_A_FUNCTION_OF_THE_STATE` | `PERMUTATION_OF_INPUT(payload.dat)` |
| `sort -u -r payload.dat -o out.dat` | `OUTSIDE_THE_FLAT_GRAMMAR` | `sort_unique_then_reverse` |
| `mkdir newdir` | `BEYOND_THIS_OBSERVABLE` | **refused** |

**5/5 diagnoses correct, 5/5 transfers** to a second action of the same kind (`touch payload.dat`,
`shuf payload.dat > out.dat`, `sort -r -u …`, `mkdir -p newdir`).

## Finding 1 — the dangerous failure is silence, not refusal

`touch keep.dat` under a content-only view leaves the state **bit-identical**. There is no refusal to react to;
`identity` is a hypothesis in the grammar and it fits perfectly. The agent has learned a falsehood.

The repair is not "expose `mtime`". Exposing the field is what the tree's own projection synthesis would discard
by stability, and the measurement says why: on a freshly written file, the raw timestamp field reported the
action in **5 of 6** unnormalised repeats (3 of 6 and 5 of 6 on other runs). The field is a coin flip. What is
stable is the *derived predicate* `mtime changed`, and only that separates the action from `true` — the contrast
fires no view at all, so the predicate is not merely always-true.

A field is a value; an observation is a predicate over a transition. The vocabulary gap is a gap in predicates.

## Finding 2 — some actions have no exact consequence, and the honest model is a set

`sort -R` produced a different file on every repeat. The coarsest stable projection of the output *alone* is
degenerate (`byte_count` — true, and useless). The strongest relation that every repeat satisfies is
`permutation_of_input`, and it survives a fresh execution it was not derived from.

What that buys is exactly what a caller needs before running a shuffling transform over a data file: **nothing
is lost**. What it costs is printed rather than buried — at that resolution the action is indistinguishable from
`identity`, `copy`, `sort` and `reverse`, while it *does* exclude `sort_unique` (which drops a duplicate line)
and `digest`. Order carries no information; conservation does. The same test transfers to `shuf`.

## Finding 3 — the boundary is a sensor, not a word

`mkdir newdir`. Every view in the admissible family is empty: content, `delta_content`, `delta_mtime`,
`delta_mode`, `delta_name`. And yet:

```
effect_on_disk                = true
every_admissible_view_empty   = true
```

The directory exists. The effect is real. No predicate built from the same readings can ever reach it, because
the observation enumerates **files**. So the loop refuses to grow, and names the missing dimension rather than
producing a word for it:

> the observation enumerates regular files; a directory is not a file… this is a missing **sensor**, not a
> missing word; unblocking it needs an observation that reports path kind, which is an interface change and must
> be requested, not inferred.

That distinction is the most useful thing in this round. **Some vocabulary is derivable from within the state
(quotients, compositions, derived predicates). Some is not, and no amount of experience closes it.** An agent
that conflates the two will invent a name for a distinction it cannot draw, which is precisely the 6,261-transition
failure rebuilt one level up.

## The verifier gap, closed by construction

A primitive is retained only if all four hold, each checked against executions it was not derived from:

| check | how it is decided | result here |
|---|---|---|
| **necessity** | without it the action is unidentified, or silently accepted as identity | flat readings = `[]` for `sort -u -r`; identity accepted for `touch` |
| **stability** | a repeat of the same state reproduces it | fresh execution still inside the permutation set; `delta_mtime` stable on normalised fixtures |
| **transfer** | a *second* action of the same kind is identified by it, from one execution | 5/5 |
| **narrowness** | the distinctions it collapses are printed | 4 alternatives admitted for the permutation set; `sort_unique` excluded |

Narrowness is the one nobody measures, and it is the one that costs something. Every growth in this round has a
price printed next to it, and none of the prices are zero.

## What this says about the standing answers

- *One execution + a computed sufficiency verdict* — unchanged, and now with a consequence for the refusals:
  a refusal is a **question with a computable answer**, not a dead end. Of the five real actions here, four
  refusals resolved into an exact growth, one into a proven impossibility.
- *"Permanently"* — still false as a blanket claim, and now with a sharper reason: what is permanent is what
  the survivors agree on; what is grown is what the failure forces; and what is *unreachable* is what no view
  in the family can see, which permanence can never repair.
- *"Instantly learn any concept it needs"* — false, and this round is where it becomes precise. The agent can
  grow a predicate, a set, or a composition from within its own readings. It cannot grow a sensor. Asking an
  interface for a new observation is not learning; it is a request, and it should be visible as one.
- *Repetition* — still null. Repeats are used here for one purpose only: to establish whether the consequence is
  a function of the state. They never add knowledge; they decide a classification.

`p_correct` is unchanged at **0.5469 × 0.5445 = 0.2978**. Nothing in this round raises it, because growth that is
bought against a failure cannot raise the starting point — it can only stop a failure from being permanent.

## The scale of the same wall

Same tree, real coding tasks: median **1,037** survivors after one demonstration, **4 of 23** identified,
**7 of 23** still insufficient after *every* example (`IDENTIFICATION_COST_IN_A_REAL_SPACE_20261116_V1.json`).
Those 7 are the vocabulary wall at coding scale. This round supplies the procedure that decides, for each of
them, whether the answer is *grow a predicate*, *grow a set*, *grow a composition*, or *the observation cannot
reach it and must be widened first* — and the last of those is the one an agent cannot decide by trying harder.

What is not yet done, and is stated in the receipt's `limit`: the loop searches a **stated** family of derived
views, relations and one-step compositions. A two-step composition is not reached, and a primitive that needs a
sensor the agent does not have is refused rather than invented. Both boundaries are per-chain observable.

## Law block

```
canonical/verification/CAPABILITY_LAW_20261116_V1.json, `vocabulary_growth` block, sha-pinned
  actions                    = 5
  outcomes_realised          = all five
  diagnoses_correct          = 5/5        transfer_holds = 5/5
  raw_mtime_field_fires_of   = [5, 6]     (unreliable, by measurement)
```

`p_correct` unchanged at 0.2978; `what_remains_unmeasured` now carries the outer edge of growth.

## Reproduce

```
python3 canonical/swe_kernel/vocabulary_growth_v1.py \
  --json canonical/verification/VOCABULARY_GROWTH_20261116_V1.json
python3 -m pytest canonical/tests/test_vocabulary_growth_v1.py -q          # 16 tests
python3 -m pytest canonical/tests/test_capability_law_v1.py -q             # 8 tests, re-pinned
python3 canonical/swe_kernel/capability_law_v1.py --pinned                 # refuses if a receipt moved
```

The sixteen tests run real programs and assert the properties, not the shape: that touching a file is invisible
to the content view, that a directory is invisible to every view while on disk, that the permutation relation
rejects a duplicate-dropping transform, that `mkdir` never yields a primitive, that `cp` grows nothing, and that
the whole measurement reproduces. No mocks: the thing under test is whether a real consequence is stable, and a
mock has no consequences.
