# A perfect action is not an available action

**2026-11-12.** Base `94a105fe`. Branch `arena/ec0ff57a-brain`. Round 4 of the owner's question.

Round 3 answered *what one success teaches* and ended on a claim: that the 11 premises the front
door cannot see are the bounded, highest-gain work item. This round audits that claim against the
live registry, and it does not survive unqualified. Two of its three parts were wrong in opposite
directions — one overstated, one understated — and the audit found a real defect that had been
eliminating seven capabilities from every goal that named a file.

Authority **NONE**. One machine, no independent verifier, $0, zero model dependency.
`truth.achieved` stays `false`; no capability is registered; no family flips.

---

## 1. What round 3 got wrong, in order of cost

### 1.1 Overstated: "the premise is the blocker"

Round 3 measured 10 dependent capabilities, all rejected at the perception stage with
`PRECONDITION_NOT_TRUE_OF_WORLD`, and concluded the premise was the thing to close. Re-measured
here by asserting the premise (`established_effects=`) and re-running the same census:

| Stage | Measurement |
|---|---|
| Premise | **10/10** rejected `PRECONDITION_NOT_TRUE_OF_WORLD` |
| Premise asserted | **7/10** then rejected `NOT_CALLABLE_WITH_WHAT_GOAL_PROVIDES` · 3/10 selected |

So the premise is the *first* blocker, exactly as written — but for 7 of 10 it is not the only
one. Removing it changes the rejection's name, not the outcome. The round-3 sentence should have
read "the premise is the first obstacle", never "the blocker".

### 1.2 Understated: this is not a blind-premise problem at all

A full census of **all 145 capabilities**, each probed with its own keywords through the real
front door (`grounded_action_v1.act`, bridge off, no memory):

| Fate | Count |
|---|---|
| `SELECTED` | **59** |
| `NOT_CALLABLE_WITH_WHAT_GOAL_PROVIDES` | **54** |
| not a candidate for its own keywords | 14 |
| `PRECONDITION_NOT_TRUE_OF_WORLD` | 12 |
| no keywords declared | 4 |
| adapter raised | 2 |
| **total** | **145** |

The 11 "blind premises" that round 3 centred are **12 capabilities, 8% of the registry**. The
dominant failure mode is **binding: 54 capabilities, 37%** — capabilities that are correctly
identified, whose premise is satisfiable, and which still cannot be called because the front door
cannot supply their arguments. Round 3 was auditing the small number.

This also kills a framing worth stating plainly, because it is the one the owner's plan assumes:

> Supplying the smartest actions does not make them available. **Availability is a separate
> property from capability, and at present it fails 54 times for every 12 times perception does.**

### 1.3 The probe artifact, resolved

Round 3's 7-of-10 caveat was that the failures might be caused by the keyword-salad probe
sentences. They are not. Re-probed with realistic sentences and a real file, the ceiling is
binding, not phrasing:

```
"read the git log"                        -> AMBIGUOUS,  missing 7 of 8 args
"read the git log of the repository"      -> routed to python.repository.acceptance.measure.v1
"read the git log from ."                 -> AMBIGUOUS,  missing 7 of 8 args
"read the axis title unit binding of the chart at <real.png>"  -> AMBIGUOUS, eliminated
```

The keyword-salad did inflate the count; the conclusion survives on better evidence.

---

## 2. The defect the audit found

The interesting failure was not the one round 3 was looking for. It was this: a sentence naming a
real PNG, asking a capability whose *own registry row* declares `requires: ['image.file.available']`,
was eliminated with `INPUT_KIND_CONTRADICTS_GOAL_FILE` — the file contradicted the capability.
The image contradicted the image reader.

The cause, in `world_probe_v1._kinds_of`:

```python
return {k for k in _KIND_TOKENS if k in low}   # substring test
```

`_kinds_of("chart.r**ast**er.axis_title_unit_binding.v1")` returns `{'ast'}`. Every `chart.raster.*`
capability silently declared itself a Python-AST consumer. `kind_contradiction` then turned that
accident into an **elimination**, which is a fact, not a down-rank — binding was never attempted.

Blast radius across the live registry: **8 of 145** capability ids announce a kind nobody declared.

```
chart.raster.axis_title_unit_binding.v1        -> 'ast'    ("ch-art.r-ast-er")
chart.raster.curve_value_query.v1              -> 'ast'
chart.raster.curve_x_at_y_query.v1             -> 'ast'
chart.raster.direct_curve_label_family_rank.v1 -> 'ast'
chart.raster.legend_style_binding.v1           -> 'ast'
chart.raster.scene_graph.v1                    -> 'ast'
auto.npm.shelacek-ubjson                       -> 'json'   ("ub-json")
terminal.kstar.root.assess.stdlib              -> 'tar'    ("ks-tar")
```

The module already contained the correct rule and did not apply it. `kind_keys_for`, ten lines
below, splits on word boundaries and carries this comment:

> *"Separate from `_kinds_of` on purpose: that one feeds CONTRADICTION, where a loose match would
> wrongly eliminate a capability."*

The comment was right; the code contradicted it.

**Measured effect of the one-line repair** (whole words via `re.findall(r"[a-z0-9]+")`), on eight
capabilities each given a real file of the right kind:

| | eliminated before selection |
|---|---|
| before | **7 / 8** |
| after | **0 / 8** |

Each of the seven now reaches a real, honest refusal *after* selection — `ACTION_FAILED`,
`PRECONDITION_NOT_TRUE_OF_WORLD`, `NOT_CALLABLE_WITH_WHAT_GOAL_PROVIDES`. That is the correct
behaviour: the chart reader was given a fabricated 8-byte "PNG" and should fail. The point is that
it now fails **as a capability that was tried**, not as one that was ruled out by its own name.

Why this matters beyond eight rows: **a hypothesis that is eliminated before it can be tried can
never be learned from**, no matter how many demonstrations it receives. For those eight, the whole
round-3 learning question was moot.

---

## 3. The real structure of the binding blocker

`NOT_CALLABLE_WITH_WHAT_GOAL_PROVIDES` is not one failure. Reading the binder against real
sentences separates three, and only one of them is a modelling problem:

**(a) Over-specification.** `git.repository.operate.v1` declares **8** placeholders —
`limit, message, message_source, op, repo_root, rev, staged, target` — because its template
flattens the argument lists of seven *different* operations into one dict. Measured: the adapter
needs exactly one of them.

```
run({"op": "log"})            -> OK, rows, output_verified: true
run({"op": "status"})         -> OK, rows, output_verified: true
```

So "read the git log" is refused for lacking `staged`, `message`, `rev`, `target` — arguments that
belong to `commit`, `show`, `blame` and `cherry_pick`. The registry's own `limitations` field states
the intended design: *"the sentence chooses the operation, never the argv"*. The binder asks for
the argv anyway.

**(b) Unstructured selection.** A selector slot (`op`, `operation`) is a small enum, and nothing
in the binder reads an enum. It is treated as a free-text placeholder with no default and no
candidate set. Four capabilities carry one: `git.repository.operate.v1`,
`code.polyglot.transform_and_verify.v1`, `python.swe.transform_and_synthesize.v1`,
`software.analysis.diagnose_and_architect.v1`. These are the four "do many things" capabilities —
the ones closest to the owner's "most advanced actions" — and they are precisely the ones the
front door cannot dispatch.

**(c) Absent path.** A destination that does not exist yet, or an input outside the workspace, is
genuinely unbound. That is correct behaviour, not a gap.

The repair already exists in the tree as a **data** mechanism, not a code change:
`declared_argument_default_v1` supports `"${input.search_root | canonical/runtime}"` — the goal's
value if stated, the declared default otherwise, reported in `filled_from_declared_default` so a
constant is never mistaken for a binding. Its own docstring names the exact tension seen here:

> *"frozen literal → goal can never win; bare placeholder → goal must always speak."*

`git.repository.operate.v1` declares **no** default for any of its eight slots. The primitive is
built and unused on the capability that needs it most.

---

## 4. Where the owner is right, and it is the same place as before

The owner's claim is that stable typed interfaces are the leverage. Round 3 confirmed it; round 4
sharpens it into a statement about *this* tree:

> An interface is a **hypothesis space that arrives pre-loaded**. The registry's 145 rows are
> exactly that — 59 of them are invocable today with no learning at all. That is the owner's
> optimum, already realised, and it is why the front door reaches `SELECTED` at all.

And the reason it stops there is also about interfaces. `_kinds_of` mis-described eight
capabilities' *inputs*; the flat template mis-describes four capabilities' *arity*. Both are
interface defects, not learning defects, and both are cheaper to fix than any learner. That is the
owner's instinct, and it is correct.

What does not follow is the step to permanence. A capability that cannot be selected is not
learned by being tried; a capability that can be selected and fails has still taught only that it
*can* run somewhere (round 3, unchanged: **one success buys the HOW, never the WHEN**).

---

## 5. What this changes about the plan

Round 3 proposed closing the 11 blind premises as the highest-gain work item. Corrected ordering,
by measured count:

| Work item | Reaches | Status |
|---|---|---|
| Interface correctness (`_kinds_of` whole-word) | 8 capabilities | **done this round** |
| Arity over-specification + selector defaults | up to 4 of the largest capabilities | not started |
| Binding repair generally | 54 capabilities | not started |
| Blind premises | 12 capabilities | round-3 target |

The instruction the owner gave — *kill bad ideas before implementing* — applies to the round-3
proposal itself, which is why it is being revised rather than built on.

---

## 6. What was verified

- `canonical/tests/test_a_declared_kind_is_a_word_not_a_substring_v1.py` — **6/6 pass**, pinning
  the accident, the honest declarations that must still work, the registry-vs-probe agreement, the
  "not knowing is not contradicting" invariant, and the end-to-end reachability.
- Regression: **124 pre-existing failures before the change, the same 124 after** (missing optional
  modules such as `cv2`; unrelated). **Zero new failures, zero tests fixed by accident.**
- `enforce_goal_hierarchy.py --base 94a105fe…` → `DRIFT_GUARD_PASS`.
- Adapter cross-check: `git_repository_operate.run({"op":"log"})` → `output_verified: true`.

**Not claimed:** that any of the eight capabilities works. They fail after selection, on fabricated
inputs, as they should. Nothing here shows a chart was read, a claim was verified, or a GUI was
driven.
