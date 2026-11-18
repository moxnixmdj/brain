# The assertion is the demand — and one point of demand is not a specification

*canonical/tools/the_assertion_is_the_demand_v1.py · 12 tests · receipt `canonical/verification/THE_ASSERTION_IS_THE_DEMAND_20261119_V1.json` · 30 commits never touched by any earlier round · zero parameters, zero model calls, zero network calls at run time*

---

## The claim, and what the year's literature says about it

The standing claim is that **the failing test is not a signal to search under — it is the specification itself**, and that reading its demand converts selection from a sequence of oracle *questions* (0.5 s each) into a table of frame *evaluations* (≈50 µs each). The three named limits were identifiability, vocabulary insufficiency, and the ~2.2 % synthesis–verification asymmetry. This round was to prove or refute the claim's mechanism on fresh commits.

The 2026 literature says what the gain actually is. SkillRevise (arXiv 2606.01139) measures SkillsBench at 36.05 % with no skill, **39.53 %** with a one-shot self-generated skill, and **61.63 %** after three rounds of trace-conditioned revision — the experience is worth three points, the *verification loop* another twenty-two. Skill-Pro (ICML 2026) reaches the same conclusion by ablation: remove the verifier gate and the agent begins reusing skills that look plausible and are wrong. Both papers are describing, in a different vocabulary, exactly the thing this tree has been building: **a free verifier is worth more than a prior.**

That is why the demand mattered. It is the only verifier that costs nothing.

## What was built

One instrument, and the honesty of it is in how little it does.

`instrument()` wraps the changed site in `__brain_site__(0, lambda: <expression>)`, which records the frame that computed the value and appends the value itself. A pytest plugin then runs **the whole test file once**, in a subprocess, with per-test frame slices. The table it produces has, per test, the frames of the site and the values it produced; for the failing tests, the demanded value, read out of the assertion that failed.

Then the space is not *searched*, it is **filtered**: each candidate is evaluated inside the recorded frames at ~10 µs, and is discarded unless it produces the demand somewhere and differs from what the site produced (`site_demand` alignment: DIRECT / ELEMENT / UNWRAPPED). Survivors are ordered by how many passing rows keep their value, and are then verified against the corpus's own pytest, whole file, at the parent commit.

Nothing is learned. `parameters_stored: 0` in every row.

## The measurement

Thirty fresh commits — none of the corpus was used in any earlier round — across click, jinja and attrs, mined at stride to avoid neighbouring commits of one fix. The whole sweep costs **74.9 s**, worktrees and verification included.

| stage | rows | what it means |
|---|---|---|
| `EXCLUDED__THE_FIX_IS_NOT_A_SINGLE_EXPRESSION_REPLACEMENT` | 15 | the human's repair is a structural edit; this instrument does not apply, and says so |
| `THE_SITE_NEVER_RAN_IN_THE_FAILING_TEST` | 1 | the demand is not a value the site can ever produce (`relation: NONE`) |
| `NO_VALUE_MATCHES` | 13 | demand known and no candidate produced it (twelve of the thirteen admit nothing at all once constants are refused; one keeps a survivor) |
| **`DEMAND_MET`** | **1** | the whole file passes (47 tests) and the patch is the human's own — see the two receipts below |

## The instrument's first success was wrong, and that is the result

The row (attrs `1c962d15a7`): the site produced `'Type annotation and type argument cannot both be present'`, the failing test demanded the version ending `… for 'x'.`. The instrument found

```python
"Type annotation and type argument cannot both be present for 'x'."
```

— a **literal constant**. All 47 tests pass with it. It is not the human's fix, which is an f-string over the frame's `name`; it would raise the wrong message for any other name. The human's rule *was* in the space (153 021 candidates offered, induced f-strings among them) and was not chosen, because the ordering that decides among survivors prefers the source that comes first, and test-derived literals come before induced expressions.

**The first receipt of this round therefore recorded 1 patch that greened the file and 0 that generalised.** It is the exact patch a constant-fitter produces, it won the instrument's own ordering, and the only gate the tree permits — the corpus's own suite — could not reject it.

This is the round's sharpest finding and it is about us, not about the world: **the demanded value is a point, so the constant that reproduces the point at that point is admitted, and the suite — the only gate — cannot reject it, because the suite is also a point set.** The synthesis–verification asymmetry the third limit names at ~2.2 % is not borrowed from the literature here; it is measured inside this instrument, on its single success, with the suite green and the patch wrong. The same mechanism produced the earlier prose-patch false positive. A verifier that asks only "does it behave correctly on these inputs" answers yes to every constant that fits.

The repair is not more search. It is an **admission rule the tree already has a name for**: a candidate that names none of the frame's values is a constant, no matter what it is made of, and the site's inputs are right there. A candidate must reference at least one name bound in the frame — "the best part is no part" applied to the patch. The human's f-string does; the literal does not.

That is one line, `names_something(expression, bound)` over the names the recorded frames hold, and it was added before this round closed. On the same row, with the same demand and the same space, the instrument then returned

```python
f"Type annotation and type argument cannot both be present for '{name}'."
```

— the human's own repair, `found_is_the_human_fix: true`, 47 tests green. Nothing about the demand changed. What changed was that the instrument stopped accepting a patch that names nothing.

## The mistake that mattered most

Four versions of the gate were built in sequence, each repaired by a real row:

1. **Universal.** A passing test's recorded value had to be preserved at *every* frame. This rejected **thirteen of fourteen** real human fixes. A passing test constrains behaviour, not an intermediate value: the fix may change what the site computes and the test may stay green, because the value was never asserted on. Preservation became an *ordering signal*; the suite stayed the gate.
2. **Value-identity.** Still one row of fourteen. The first gate's error was not its strictness but its reading of what a passing test witnesses.
3. **Existential.** The demand must hold at *some* frame, and somewhere the candidate must differ from the original. One measured row runs the site **184 times** inside a single failing test; the demand is due at the failing *occurrence*, and demanding it everywhere is a universal where the truth is an existential.
4. **Predicate.** `assert not X` does not demand X. It demands that the site's value be *falsy*, and X is the **witness** that the demand was violated. The first instrument read X — sometimes an `AssertionError` object, sometimes pytest's own rendering — as the demand. It "verified" a patch made of the test runner's prose against a green file. That row is kept in the record as the demonstration that **a green suite plus a plausible expression is not a fix**, and it is the strongest local evidence for the third limit: the asymmetric verifier accepts any patch when the *demand source* is wrong.

Across all four gates the count stayed at one. That invariance is the result: the boundary is not how strict the gate is. **It is what the demand can say.**

## What the demand can and cannot say — measured, not argued

For every in-class row the human's own replacement was scored by the table after the search (never fed to it). It is admissible in **1 of 14**.

Then its shape was classified by AST over the same fourteen:

| form the human fix uses | rows |
|---|---|
| attribute of another object (`self._help_option`, `a.converter`, `comp.source()`) | 6 |
| method call on such an attribute | 3 |
| guard: `is None` / `is not None` / `or` / ternary | 4 |
| bare name already in the frame (`last`, `cmd_params`) | 2 |
| f-string over a name in the frame | 1 |

Only one of those fourteen is a *value* the frame can compute in the ordinary sense. Six reach for **another object's state**, and the demanded value pins the value while saying nothing about which attribute produced it — infinitely many attributes agree on the frames observed. Four are **predicates** on the site's value rather than values, and a predicate is satisfied by any falsy (or truthy) result, so it prunes and does not identify. Two are names the site already had, which means the demand was right and the alignment to the site was not.

This is the precise answer to the question the claim poses. **A failing test supplies a predicate and a witness. It almost never supplies an identifier.** The demand is necessary, it is free, and on its own it identifies a value, not a program.

## Where the ten-thousandfold went

The arithmetic in the previous round stands: 0.5 s per oracle question against 50 µs per frame evaluation is a factor of 10 000, and this round spent **79.3 s on 30 commits** — 2.6 s per commit, including cloning a worktree, instrumenting a module, running the whole test file, and verifying survivors. That is real.

But the factor is per *candidate*, and the amortised win is bounded by something else: the number of demands a row offers (1 to 8, median 2), and the fraction of those demands that are selective. The measured conversion is not 30 repairs, it is one. **The instrument is not slow; it is narrow.** Cheap selection only helps to the degree the selector is selective, and selectivity is a property of the *predicate*, not of the price.

## The ultimate form, stated as the next falsifier

The law this round establishes, in one line:

> **Selection cost falls only to the degree the demand is selective, and a demand is selective only when it names an object.**

Everything follows from that. Not more search — the space was 153 021 and the answer was in it. Not a better prompt — a prompt cannot add a grammar. Not a guardrail — the verifier is sound; only the demand source was ever wrong.

The next instrument, with its acceptance number declared before it is built:

1. **No free constants — done in this round.** A candidate that references no frame-bound name is a point fit; it is refused. This is what turned the one green-but-wrong patch into the human's rule, on the same row, at no cost.
2. **Demand as a predicate, derived from the assert's own AST and the crash entry's path** — `falsy`, `truthy`, `is None`, `is not None`, `==` to a live value, `not in`, string containment, exception type. Today's reader recovers the statement's form only when the crash entry is the failing assert; when the assert is nested in a helper it falls back to prose, and prose is a witness. This is why thirteen rows kept prose demands. The symptom is measured; the fix is to carry the crash path *and* to parse the enclosing assert.
3. **Reference space** — `name.attribute` for every attribute of every value in the frame (`dir()`, bounded), which is already in the instrument, plus `name.method(...)` over the arguments the frame has.
4. **Admission rule**: the predicate must *flip* between the failing occurrence and the passing ones. That is the selectivity test the table needs and does not yet apply.

Acceptance, declared now: the human's own fix must become admissible in **≥ 10 of 14** rows, verified repairs must go from 1 to **≥ 8 of 30**, and every verified patch must reference at least one frame-bound name — a green constant counts as zero. If those three numbers do not move, the claim is refuted in this tree's own terms, not deferred.

## The computer-use half

The same law, and the same mistake, transfer without modification. A click is a predicate on state; the demanded postcondition ("the page shows X") is a predicate; the reference space is the finite set of *elements × actions*, discovered by inspection from the accessibility tree rather than recalled. CUA-Skill's 2026 numbers (50.26 % overall, Excel 25 %, Settings 100 %) show the same shape as ours: the capability is form-specific, not general, and it tracks how many distinct things the observation can *name*. Work2Skill still needs a human demonstration per workflow, and SkillRevise's own conclusion is that self-generated skills are unreliable until verified — the loop again.

So the answer to "guardrails, better prompts, or what" is the measurement: **none of the three is the missing term.** The missing term is that a specification is a *set of predicates over an enumerable reference space*, and we had been treating it as a value. That is a grammar, and grammars are built, not prompted.

## Reproduction

```
/tmp/venv/bin/python canonical/tools/the_assertion_is_the_demand_v1.py \
  --commits /tmp/corpus/fresh30.json \
  --receipt canonical/verification/THE_ASSERTION_IS_THE_DEMAND_20261119_V1.json \
  --cap 400000 --survivors-cap 16 --verifications 12 --seconds 180
/tmp/venv/bin/python -m pytest canonical/tests/test_the_assertion_is_the_demand_v1.py -q   # 12 passed
```

Authority NONE. Producer-run. No judge, no model, no stored parameter.
