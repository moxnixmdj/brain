# The name comes from the frame — except when the bug is not a name

**Round.** `arena/3fc9b5f0-brain`, 2026-11-24. **Authority:** `NONE__PRODUCER_RUN_SANDBOX`.
Everything below is producer-run and unreviewed by a third party. §6 is not met; no merge.

**Artifacts.** `canonical/tools/the_name_is_a_hole_v1.py`,
`canonical/verification/THE_NAME_IS_A_HOLE_20261124_V1.json`,
`canonical/tests/test_the_name_is_a_hole_v1.py` (5 tests, OK).

## 0. Binding requirements, restated

Own weights, own architecture, own agent. Zero runtime model calls. No world-fact warehouse in
parameters. Every parameter calculated and justified. Instant knowledge lives in the external,
inspectable, editable store; one experience writes an abstracted, goal-conditioned rule there. The
§2 settlement is unchanged: forbidden is a parameter fact lookup or a runtime model dependency;
allowed is an external store computed with, plus one-experience learning. Tests must be the hardest
real tasks, with no leakage, no hand-solving and no borrowed outputs. Work stays on this branch;
one merge only after §6 actually passes. None of that is claimed here.

## 1. Answering the new idea directly

The proposed perfect algorithm — scan an unknown environment, ask the right questions, fetch only
what is missing, save generalized goal-relevant learning — is the right *shape* and an insufficient
*mechanism*, for three measured reasons in this project:

- `THE_REPERTOIRE_IS_A_QUERY_20261129_V1.md`: 437 programs, 4,621 options, 47 s, **0/80** accepted
  options did anything and 0/12 needs were distinguishable. Discovery without a discriminating
  judge produces options, not capability.
- `A_SINGLE_TRACE_DOES_NOT_PIN_THE_RULE_20261120_V1.md`: one trace teaches a tape; only a contrast
  teaches a rule. On 30 real commits the true rule was usually not even in the candidate closure.
- `THE_GOAL_IS_A_QUOTIENT_OF_THE_TRACE_20261128_V1.md`: the statistic the goal is about costs 3–5
  experiences, not 1, and a sufficient statistic on short runs collided 208 times on longer ones.

So: **goal-directed, not broad**. Learn everything in every environment only if "everything" means
"every computed distinction that flips a judge"; raw action traces and prose pages are the wrong
compression. The right saved object is a form plus the constraint that validated it, not the action
sequence. This round is one small instance: the frame contains the value, the test contains the
constraint, and the generalizable object is "substitute the in-scope name whose observed value
explains a spec string the current name's value does not".

The four proposed leaps map onto reality as follows. Data-flow/causal tracing is now real but local
(this tool records the frame at executed name loads). Semantic equivalence over a universal IR is
**not built**. CEGIS is real only as generate-once-and-verify-against-the-suite, not backward
propagation from expected outputs. Executable mental models are **not built**. Anyone claiming the
four leaps are working from these files is claiming more than the receipts contain.

Frontier inputs, not authorities: DynaFix shows that local variable values and control flow matter
greatly for repair, but its proposals come from an LLM [3](https://arxiv.org/html/2512.24635);
TraceFixer feeds traces plus a desired state to a trained neural repair model [2](https://arxiv.org/pdf/2304.12743).
The question tested here is whether the proposal itself can be calculated.

## 2. The bottleneck chosen

After `THE_LITERAL_COMES_FROM_THE_FAILING_INPUT_20261124_V1.md` verified one generated literal but
left 14/15 rows unsolved, the named remaining class was a **name substitution**: on the guard
falsifier's one refinement the human edit was `attr_name`, where the program had used `field_name`.
Both values were in the same executed frame. No expression grammar and no constant mutation can
invent a name that is already there.

## 3. Build, with parts removed

First attempts were deleted, not kept: a `sys.settrace` pytest plugin, then a `pytest_runtest_call`
wrapper, then `trace.Trace` in-process. All three traced module import but not the failing call —
the first plugin additionally had a syntax error that hid the fact. The surviving instrument is one
line inserted before each safe name-load statement, using the same physical line so source line
numbers do not move. That is the whole trace mechanism.

The generator then:
1. runs the post-fix test file twice on the parent; the intersection of stable passes is the oracle
   (this removed two time-dependent node ids whose values were regenerated every collection and
   had falsely accused the correct patch of breaking tests);
2. records `locals()` at every statically possible name-load line during the failing test;
3. treats loaded names as holes and proposes only names observed in that same frame;
4. ranks by alignment with strings from the failing test's own function and node id — specifically
   a proposed value that prefixes a spec string the current value does not;
5. patches one identifier and reruns the whole file.

No commit diff, no human edit, no model, no stored rule, no network.

## 4. Honest results

Development probe, **excluded from the receipt**: commit `252090c7c707` (already used in an earlier
receipt). The generator found hole `657:29:field_name`, observed `attr_name='address'` against the
failing test's `"address.zip_code"`, replaced `field_name` with `attr_name`, and passed all 382
tests with zero broken tests at rank 4 of 41 candidates. This establishes that the mechanism can
derive the edit; it is **not** a fresh-corpus result.

Fresh corpus: 15 one-source/one-test commits unused by any earlier receipt or corpus file — 3 from
marshmallow, 12 from click. Gates N1–N5 returned **FAIL**: 0/15 verified, 543 candidate-file
executions, 1,816.6 s, zero parameters/model calls/network calls. All 15 rows ended
`NO_FRAME_NAME_PASSED`. Three rows produced no candidate at all (no frame value aligned with a spec
string); twelve produced candidates and none survived the whole file.

Post-hoc diff census, reported only after the verdict: the fresh commits are mostly multi-line
structural changes (adding code, changing signatures, removing a translation call, adding a dash
branch). Only one row is primarily a name/call-shape change, and that one needs a call removed, not
an identifier swapped. So 0/15 is a fact about this corpus and this generator, not proof that name
substitution is impossible; it is proof that another single-edit generator does not move the
frontier on a fresh, mostly structural corpus.

Rejected here: a stored rule from the development probe (it would be memorizing one site under the
name of learning); more candidate names (the closure already contained the right one on the probe);
trusting a single baseline (two flaky, time-parametrized tests produced false accusations).

## 5. Verdict and next bottleneck

Real: trace-observed frames plus test-supplied constraints can calculate a name substitution and
the whole suite can confirm it. Real: double-baseline removes a class of flaky accusations.
Failed: generalization to a fresh corpus (0/15). Unproven: single-experience transfer, IR-level
semantic equivalence, backward synthesis, GUI/browser, unseen environments, independent verification.

The next bottleneck is no longer "which name/constant": it is **multi-region structural repair**.
The remaining fresh rows add or remove statements, change signatures, and split branches. The next
build must treat a typed AST sketch as the hole, propagate the failing assertion's constraint
backward through executed data flow to the responsible region, and synthesize the missing
statement or call shape. Per Elon's law: delete the frame-name selector as soon as a structural
generator subsumes it; keep only the double-baseline oracle and the causal localization that each
pay for themselves.

## 6. Limits

Producer-run, two repositories, no independent verifier. Corpus freshness is SHA exclusion against
existing receipts, not a third-party blind split. The development probe is disclosed and excluded.
The generator edits one identifier on one executed line. §6 remains unmet. No merge.
