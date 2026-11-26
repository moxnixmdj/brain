# The Reach Ledger: real fixes measured by operation, not by claim

**Date:** 2026-11-24 · **Branch:** `arena/39d26eb4-brain`
**Commit:** `1f9d2b41` + this one
**Measured on:** `canonical/corpus/real_fix_pairs_20261119_V1.json` — 87 fixes, each
admitted only because its test **fails at the parent and passes at the fix, verified
by execution**. No synthetic data.
**Authority:** NONE. Zero model calls, zero network calls, $0.

---

## 1. What the brief claimed, and what is actually true

| Brief's claim | Verdict | Evidence |
|---|---|---|
| Five "logged unsolved commits" `c53d373, 05f6fd0, fc518e4, 884437ae, 051fd663` | **FAILED — all five absent** | `git cat-file -t` returns nothing for each |
| `typed_invention_v1`, `MealyAPICompiler`, `epistemic_doc_compiler`, `CUMentalWorldModel`, `calculate_separating_projection`, `simulate_plan`, `APIphany`, `SymLLM`, `SyPet` | **FAILED — absent** | grep over the tree |
| `zygote_worker_pool_v1` exists, 1ms CoW forks | **VERIFIED** | `canonical/swe_kernel/zygote_worker_pool_v1.py`, ~1.5 ms measured |
| 344 failing cases in `HONEST_SUITE_BASELINE` | **VERIFIED** | `FAILURE_ROOT_CAUSE_PROFILE_20261015_V1.md` |
| "75.2% of hunks sit outside fixed mutation grammars" | **MISATTRIBUTED** | The repo says 75.2% of fix pieces are rebuilt by **no operator any other task produced**. That is cross-task transfer, not grammar coverage. |
| "Buy the 75.2% with more search/parallelism" | **FALSE** | The repo states it directly: *"The search does not fail on out-of-grammar defects; it exhausts and correctly reports OPEN."* |
| Repo-native component mining is needed to break the ceiling | **ALREADY BUILT** | `REACH_OF_THE_GRAMMAR_20261116_V1.json` → `grammar.reads_repository_symbols: true` |

All four proposed plays (component mining, dual-program splicing, 16-way CoW
rollouts, cross-modal Petri nets) improve **SEARCH** or **VERIFICATION**, the two
solved terms. The evidence for that is not opinion: `p_correct = REACH × SEARCH ×
VERIFICATION = 0.2978`, and search/verification are the terms with mechanisms.

## 2. The bottleneck, measured

`grammar` reports `can_insert_a_node: false`, `can_delete_a_node: false`,
`can_rename_a_name: false`. The grammar can swap and replace only. AST-diffing all
87 verified fixes gives the edit kind each one requires:

| Operation | Fixes | Share | Covered by |
|---|---|---|---|
| `MIXED_SWAP` | 24 | 27.6% | existing grammar (`python_test_guided_patch_search_v1`) |
| `NEW_GUARD` | 18 | 20.7% | `distinction_creation_v1` *(built this session)* |
| `NEW_STATEMENT` | 17 | 19.5% | partial — wrapping only |
| `NEW_CALLABLE` | 12 | 13.8% | `inverse_completion_v1` when it is an inverse pair |
| `DELETE` | 7 | 8.0% | `distinction_creation_v1.clause_to_delete` *(built this session)* |
| `CONSTANT_ONLY` | 6 | 6.9% | existing grammar `CONSTANT_REPLACE` |
| `RENAME_OR_REORDER` | 3 | 3.4% | **not covered** |

**Reach: 24/87 = 27.6% → 56/87 = 64.4%.**

### The number I got wrong, stated first

My first classification reported 9 fixes as `RENAME_OR_REORDER` and scored them
**uncovered**. That was wrong. Inspecting them showed they are constant
substitutions — `^...$` → `...\Z` in regexes, `split` → `rsplit`, a URL regex
rewritten. The existing `CONSTANT_REPLACE` family already performs exactly those
edits. My AST multiset compared **node types only** and was blind to string
content. Re-measuring with constants included moved 6 of the 9 into
`CONSTANT_ONLY` (covered) and shrank the true uncovered remainder to 3.

Had I not checked, the gap would have been overstated by 7 points. The corrected
figure is the one above.

## 3. What was built, and why each part earns its existence

### `inverse_completion_v1.py` — complete the pair instead of inventing the function

Of the 12 `NEW_CALLABLE` fixes, inspecting all 27 invented callables showed they
arrive in **pairs**: `_point_state`/`_point_from_state`,
`_intervals_state`/`_intervals_from_state`, `__reduce_ex__`/`_restore_version_range`,
`make_safe_parse_float`/`safe_parse_float`.

A pair is not free invention, because the round-trip property is **executable**:

```
for every x the test builds:   load(save(x)) == x
```

Given the writer, the reader's arity is *read off the writer's own payloads*, not
searched for. On the real `a03bde12` case the writer emits a 3-tuple, the module
derives arity 3 → `__setstate__(self, _0, _1, _2)`, and the executable check
proves it: correct reader residual **0**, the pre-fix reader that dropped the
third element residual **2**.

**Honest limit:** it cannot invent the **writer**. `a03bde12`'s third element is
not derivable from `assert load(save(x)) == x`; it comes from the test's fixture
semantics. So this buys one half of a pair, and only 1 of the 12 `NEW_CALLABLE`
fixes is an inverse pair at all. That is a 1/87 contribution, and it is reported
as 1/87.

### `distinction_creation_v1.clause_to_delete` — deletion is the inverse of a guard

4 of the 7 `DELETE` fixes remove a condition a test now contradicts. `5a7d3386`
dropped `"===" in token.text` from a skip rule because strict-pin tokens had to be
kept. Given the clauses present plus the two demanded sets, the module ranks
clauses by how many required inputs each wrongly excludes, and refuses
`NO_CLAUSE_EXPLAINS_THE_FAILURE` when none does — because then the bug is not an
over-broad condition and DELETE is the wrong operation.

### `emit_placements` — one condition, every placement the code admits

The 17 `NEW_STATEMENT` fixes are dominated by `Try`/`ExceptHandler`/`Raise` (4
each). Inspecting them showed they are **the same condition in a different
position**, not a different mechanism: a guard inside a `try`, or as an `or`
operand. So placement is a choice of emitter, not a second synthesiser. One
derived condition now emits as `statement_guard`, `negative_guard_first`, or
`wrapped_call`, and the module declares `not_claimed: THAT_A_PLACEMENT_WAS_CHOSEN_FOR_YOU`.

## 4. Three bugs found by executing, not reading

1. **The emitted branch raised on every valid input.** It emitted
   `if n gt 0: raise` for the region `n > 0` — inverting the meaning. The guard
   describes what is **valid**, so the branch is its **negation**. Now
   `if n <= 0: raise`, and a test executes it against 1, 2, 5 (must pass) and
   0, −1, −100 (must raise).
2. **`n gt 0` is not Python.** `render()` was a human-readable report string being
   emitted as source. Added `render_python()`; the emitted branch is now compiled
   in tests so it can never again be un-runnable.
3. **Strings were ordered by codepoint.** `kind < 'strict_pin'` is a coincidence,
   not a distinction — it accepts `'strict_pina'` and rejects `'none'`. Strings are
   now equality-only. A consequence is that several distinct positive strings with
   no shared structure **refuse** instead of inventing an order; two of my own
   earlier tests asserted the invention and were corrected.

Plus, in `inverse_completion_v1`: **optionality was mistaken for a shape change.**
`bool | None` is one field; the first version refused consistent payloads because
`NoneType` and `bool` differ. Ragged arity is the only thing that breaks a reader.

## 5. What this is not

- **Not a §6 pass.** 64.4% reach on 87 fixes from one repo family is not SWE-bench
  Pro, not Terminal-Bench, not OSWorld. No benchmark was run this session.
- **Not an end-to-end capability gain.** Reach is necessary, not sufficient.
  `p_correct = REACH × SEARCH × VERIFICATION`; raising reach from 0.276 to 0.644
  multiplies the first term only, and only for fixes where the test carries the
  evidence.
- **The guard share is conditional.** 18 of the 87 fixes need a new guard, but
  `distinction_creation_v1` only reaches those when the test exercises the
  boundary (previous turn: 4/4 with edge evidence, 0/4 with random evidence).
  So a large part of the 64.4% is *potentially* reachable, not actually reached,
  until a demand carrying an edge is present.
- **`RENAME` (3), most `NEW_CALLABLE` (11/12), and most `NEW_STATEMENT` remain
  uncovered.**

## 6. Next bottleneck

The remaining 35.6% is not one thing. Ranked by what would unblock most:

1. **`NEW_CALLABLE` (12%)** — only 1 is an inverse pair. The other 11 invent a
   helper with no executable constraint tying it to a second half. This is where
   the real difficulty is, and no mechanism in this repo touches it.
2. **`NEW_STATEMENT` (19.5%)** — placement now covers the guard-shaped ones; the
   remainder need `__slots__` restoration and statement reordering, which are
   structural rather than conditional.
3. **`RENAME` (3.4%)** — genuinely unreachable by swap/replace; needs a rename
   atom, which is the cheapest remaining addition.

The single next thing to attack is **`NEW_CALLABLE`**, because it is the largest
bucket with no mechanism at all — and because the inverse-pair work showed the
only leverage that exists there: an executable property that ties two halves
together. Finding more such properties is the question.
