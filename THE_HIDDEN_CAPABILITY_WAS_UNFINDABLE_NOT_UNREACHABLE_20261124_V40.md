# The hidden capability was unfindable, not unreachable

Date: 2026-11-24 · V40 · branch `arena/093433b0-brain`

## The claim under test

> We have solved all of this somewhere under non-obvious names. We have tremendous
> hidden capabilities. They need to be at the unified runtime, at the unified model.

This is a claim of the form "Brain can do X", so it is governed by
`TRUE_CAPABILITY_TEST_LAW_V1` and it has to be measured rather than agreed with.
It is also two claims wearing one sentence, and they have different answers:

1. **Existence** — the capability is present in the tree under another name.
2. **Reachability** — the model that runs the solver can find it.

## What the model actually contained

`brain_unified_model_v1.py status` at the base commit (`316caa3e`):

```
capabilities 447 · bound 153 · receipt_backed 294 · engines 26
skills 18 · knowledge 701 · research_index 7377
source_index_modules 2027 · source_index_entry_points 462
source_index_is_addressable_not_executable: true
```

The gap between 447 capabilities and 2027 indexed modules is the gap the claim
points at. It is real, and the compiler had already named it honestly: those
modules are *addressable source*, never executable, and `solve()` cannot select
them.

## The measured defect

The claim predicted a wiring problem. The measurement found a *discovery* problem.
Both the index scan and the partition test were hard-coded to one directory,
`canonical/runtime`:

```python
runtime_root = root / "canonical" / "runtime"
for path in sorted(runtime_root.rglob("*.py")):
```

`canonical/swe_kernel/` — 204 modules containing the repair engines, the CEGIS
synthesizers, the epistemic loop, the causal dataflow graph, the concept library
— was **outside the domain entirely**. Not indexed, not classified, not orphaned.
Absent.

| probe | before | after |
|---|---|---|
| SWE-kernel modules in the source index | 0 of 204 | 204 of 204 |
| `find_source` returns target at rank 1 | **0 / 8** | **8 / 8** |
| source_index_modules | 2027 | 2237 |
| source_index_entry_points | 462 | 557 |

Before the fix, an operator asking the model "cegis repair" was answered with
`canonical/runtime/r2_existing_policy_adequacy_repair_v1.py`. Asking where the
angelic lens repair engine lives returned the same unrelated module. The model
could not answer "where is this?" about the code that implements its own solver.

## The fix, and what it deliberately is not

The scan domain became one stated constant, `_SOURCE_ROOTS`, holding
`canonical/runtime` and `canonical/swe_kernel`. `canonical/tests` is excluded on
purpose and for the standing reason: the tests are the oracle, and indexing them
would let a goal be answered with the test that is supposed to judge the answer.

Every guarantee the old code made is still made, and pinned by test:

- indexed rows claiming `capability: true` → **0**
- `find_source` rows reporting `executable` → **0**, reason stays
  `SOURCE_LOCATED__NOT_EXECUTABLE__NO_RECEIPT_OR_BOUND_ADAPTER`
- `solve()` on a goal only indexed source could serve → **`FAIL_CLOSED`**
- the capability/index partition is still exact, now over the declared roots

## Does it solve anything now? No.

This is the part the claim gets wrong, and it is the part that matters.

A genuine fail-to-pass task was constructed from the corpus's own rule — apply
the added test to the parent commit, leave source untouched:

```
repo     pypa/packaging
parent   dec6213e562b69ffb680d5b9a82a899fafe4dc02
test     tests/test_markers.py::TestMarker::test_invalid_marker_defers_argument_formatting
state    genuine TEST FAILURE
         AttributeError: 'Message' object has no attribute 'text'
         tests/test_markers.py:399
```

Brain's epistemic loop, `solve(goal, mode="EPISTEMIC")`, on that workspace:

| | before fix | after fix |
|---|---|---|
| status | `ABSTAINED__NO_VERIFIED_LOCAL_POSTCONDITION` | `ABSTAINED__NO_VERIFIED_LOCAL_POSTCONDITION` |
| `actions_taken` | `pytest_repair:UNSOLVED` | `pytest_repair:UNSOLVED` |
| model_calls | 0 | 0 |

The repair engine directly, `angelic_lens_cow_repair_v1.repair_git_repo_from_pytest`:

```
status UNSOLVED · candidates_screened 0 · angelic_sites_found 0
```

The kernel was **already reachable** through `solve(EPISTEMIC)` before this round —
it imported and executed, scanned 82 files, and produced zero patch candidates.
Making it *findable* changed nothing about its *ability*, because discovery was
never the binding constraint on this task. The machinery is genuinely there; the
generation is genuinely empty.

## What this round establishes, and what it does not

**Established, verified:**

- The project's solver machinery was invisible to its own unified model. Measured
  0/8, now 8/8 at rank 1.
- The cause was a directory literal, not a governance decision.
- The widening broke no guarantee; each one re-checked and pinned.
- The negative control holds: the new regression test **fails** on the pre-change
  compiler, naming
  `canonical/runtime/r2_existing_policy_adequacy_repair_v1.py` where
  `canonical/swe_kernel/angelic_cegis_repair_v1.py` was expected. A test that
  cannot fail would prove nothing.

**Not established, and not claimed:**

- No capability gain. `capability_credit_delta` 0, `terminal_credit_delta` 0.
- No benchmark row. **§6 DONE is not met.**
- The solve rate on the measured task is unchanged: 0 before, 0 after.
- The 1900+ runtime modules still outside the capability registry are still
  outside it. Widening the *index* did not promote anything to capability, and
  should not: most are entry scripts or orphans that no receipt ever exercised.

## One correction I had to make to my own instrument

My first routing probe used the synthetic goal `"fix the failing test <name> in
<repo>"` and returned an identical top-3 with identical scores for all 28 tasks.
Read carelessly that says "the router is a constant" — a damning finding. It was
my instrument, not the router. Re-run on the 80 real issue texts the system is
actually handed, `route()` distinguishes 68 distinct top-3 tuples and 32 distinct
top-1 choices. The router discriminates. The constant was the phrase I invented.

## The honest summary of the claim

The hidden capability is real but it is **unbuilt in the decisive place**. The
tree contains an enormous amount of solver machinery, and until this round the
unified model could not point at any of it. That is now fixed and pinned. But
"hidden" was not the reason it never solved anything: the generation step is
empty, and that emptiness is unchanged by being able to find the file that
contains it.

The next lever is not wiring. It is the zero-candidate emission measured above:
`candidates_screened 0` on a task whose failure is a single `AttributeError` on a
missing attribute, in a file the engine was told to look at.
