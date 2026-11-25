# The literal comes from the failing input — and the guard never had it

**Round.** `arena/3fc9b5f0-brain`, 2026-11-24. **Authority:** `NONE__PRODUCER_RUN_SANDBOX`.
Producer-run measurements, no third party, no independent verifier. Nothing here is a §6 claim.

**Artifacts.** Tools `canonical/tools/the_replacement_expression_v1.py` and
`canonical/tools/the_constant_is_a_hole_v1.py`; receipts
`canonical/verification/THE_REPLACEMENT_EXPRESSION_20261124_V1.json` and
`canonical/verification/THE_CONSTANT_IS_A_HOLE_20261124_V1.json`; tests
`canonical/tests/test_the_generated_literal_v1.py` (8 tests, OK). The existing guard tests
(10 pytest cases) and effect-witness tests (18 unittest cases) still pass after the fit-injection
edit; static integrity reports `rules=11 violations=0 -> PASS`.

---

## 0. Requirements restated before acting

Weights are computed mechanisms only; an external, inspectable and editable store is the instant
knowledge; one experience compiles an abstracted, goal-conditioned rule into that store. No world
fact lives in parameters, no runtime model call, no runtime world-knowledge warehouse, every
parameter derived and justified. Tests must be the hardest available real tasks with no leakage,
no hand-solving, no borrowed outputs, and only our agent taking them. Work stays in this branch;
merge once, only if §6 is actually met. This round did not meet §6, so nothing was merged.

The §2 contradiction remains resolved exactly as before: forbidden is a parameter fact lookup or a
runtime dependency on another model; allowed is an external computed-with store plus one-experience
learning. The two falsifiers below add no parameters and no store entries — they are mechanism
measurements, not a change to that settlement.

## 1. What the project and the frontier already said

- `A_NEW_LITERAL_IN_AN_EXISTING_CONSTRUCT_20261119_V1.md` measured that **selection cannot produce
  what is absent**, and named the only remaining route: a generator whose bits are calculated,
  with the check's asserted behaviour as constraint and a site element as hole. It also measured
  that the literal is frequently absent from the check's text.
- `THE_DEMAND_IS_A_RELATION_20261125_V1.md` and
  `THE_SAME_GUARD_TWICE_IS_THE_DISCRIMINATOR_20261119_V1.json` established that a flipped guard
  reaches the human line 3/15 but the human expression 0/15; every test-green flip broke the suite
  or lacked exact fit.
- `THE_REPERTOIRE_IS_A_QUERY_20261129_V1.md` measured 4,621 options over 437 programs: 0/80
  accepted options did anything. Adding vocabulary is not the bottleneck.
- Frontier inputs, not truths: A-CEGIS uses deterministic regex counterexamples as feedback and
  reports 90% within four turns on NL-RX-Turk, but with an LLM generator [2](https://arxiv.org/abs/2609.02892);
  Meta's agentic repair uses a fine-tuned Llama-70B with 15 tools and static/test feedback [1](https://arxiv.org/pdf/2507.18755).
  Both buy generation with weights; neither is ours, and neither is credited as our result.

The question this round asked was therefore narrow and hard: **can a calculated generator produce
the absent expression from the failing run, with no model, and survive the project's own suite?**

## 2. Fresh corpus, not a stale one

The earlier attempt to mine `/tmp/packaging` produced 15 candidates whose SHAs were all already in
receipts. This round cloned `marshmallow-code/marshmallow` (HEAD `fa913ca`, 3,767 commits), installed
the missing test dependencies (`pytest 9.2.0`, `pytest-asyncio 1.5.0`, `hypothesis 6.170.17`,
`simplejson`, `pytest-mock`), and screened one-source/one-test commits against real oracles. Fifteen
commits were retained whose full SHA appears in **no** existing receipt or corpus file. These are
fresh by that exclusion only: producer-run, single repository, no independent blinding. The mining
candidates came from `canonical/tools/the_space_is_the_artifact_v1.py`.

## 3. Falsifier one: a better synthesizer for the guard still finds nothing

`the_replacement_expression_v1.py` reuses the existing flip oracle and whole-suite judge unchanged
and replaces only the candidate selector. Its atoms come from the source operand labels, the literal
values and types actually logged at the guard, `len`/`isinstance`/string methods, and conjunctions
of two. A candidate is admitted only by exact fit — false at the flipped firing, true at every
other firing the guard passed — then the uninstrumented project file decides.

Preregistered gates R1 (≥1 verified on a fresh commit), R2 (≥1 verified expression outside the
four hand-written identity/truth forms), R3 (no accusations), R4 (zero parameters/model/network),
R5 (real oracle) returned:

| gate | result |
|---|---|
| R1 | **false** — 0 / 15 verified |
| R2 | **false** — 0 novel verified |
| R3–R5 | true |

15 rows took 751.3 s. Stages: 7 `NO_SWITCH__NO_SINGLE_OCCURRENCE_FLIP_PASSES`,
7 `FLIP_PASSED_THE_TEST__BROKE_THE_SUITE__NO_FIT`, 1 `FLIP_FOUND__REFINEMENT_NOT_VERIFIED`.
The single refinement, `(errors) and (data == {'city': 'Springfield'})`, broke 69 of 383 tests;
the human edit for that commit was the name `attr_name`. For another commit the human edit was the
literal `#` inside a regex character class. **The guard family cannot generate either thing.**
This is not a vocabulary failure: it is an edit-kind failure. Widening the expression grammar
would not have helped, because the correct edit was not an expression at the guarded `if`.

## 4. Falsifier two: a literal can be generated from the failing input

`the_constant_is_a_hole_v1.py` takes the other route. On the parent source it:
1. runs the post-fix test file and records the failing node ids;
2. traces which source lines the failing test actually executed;
3. treats string/number/bytes constants on those lines as **holes**, not as candidate answers;
4. generates missing values from the characters of the failing inputs — most importantly, inserts
   an unseen character inside an existing regex character class;
5. ranks by computed properties only (pattern syntax, class-insertion shape, punctuation seen in
   the failure, length) and executes each candidate against the **whole** test file;
6. accepts only if every originally failing test passes and no originally passing test breaks.

No diff and no human edit are read by the generator; the human edit is not needed for a verdict.

Preregistered gates: C1 ≥1 fresh commit verified by a literal absent from the parent source;
C2 no verified candidate breaks a passing test; C3 no diff read; C4 zero parameters/model/network;
C5 real oracle on every row.

**Result on 15 fresh commits: PASS on C1–C5, 1 / 15 verified.** Stage counts:
14 `NO_GENERATED_LITERAL_PASSED`, 1 `VERIFIED`. The tool made 842 whole-file oracle executions
in 2,433.8 s of measured row time (shards ran in parallel, so wall time was shorter). Zero model
calls, zero parameters stored, zero network calls.

The verified row is commit `902f99c4151d` (`Fix URL validator rejecting a fragment after an empty
path`). The trace-localized hole at line 160, column 28 held the literal
`(?:/?|[/?]\S+)\Z`; the generator inserted the `#` that the failing input
`http://example.org#fragment` contained and that the literal did not, producing
`(?:/?|[/?#]\S+)\Z`. The project's own 221 tests then passed with zero broken tests. This is
the human expression, but it was reached from the failing input and the whole-suite judge, not from
the commit diff.

The accepted candidate was found at rank 2 after 2 whole-file executions.
This success is sensitive to the ranking rule: an earlier rule that penalised any character
appearing in a passing example pushed the same `#` insertion below the 60-candidate cap, turning
the row into `NO_GENERATED_LITERAL_PASSED`. The final rule rewards punctuation seen in a failing
input instead. That is a computed priority, not a stored repair fact, but the sensitivity is real
and is reported rather than hidden.

## 5. Verdict

Real:
- A parameter-free generator can **produce an absent literal** from a failing input and pass the
  project's whole test file, on a commit unused by any prior receipt. It is not selection.
- The whole-suite judge refuses false positives: the first class insertion (a space) left the
  failure in place and was rejected; 69-test regressions in falsifier one were rejected.

False:
- "A better expression synthesizer fixes the guard bottleneck." 0/15 on fresh commits.
- "One experience gives a coding capability." The generated fix is recomputed from a fresh
  failing run; no abstract rule was stored or transferred in this round.

Unproven / missing:
- Held-out transfer of the generated rule to another program, another repository, or another bug
  shape; multi-hole and name-substitution repairs; structural edits; GUI/browser tasks; unseen
  environments; any independent verifier. §6 is not met.

Rejected ideas, with reasons:
- *more guard predicates* — the human edits were a name and a regex literal, not guards;
- *equality/type binding to site values* — already falsified in earlier rounds and would destroy
  numeric repairs;
- *fetching more prose pages* — only 5.96% of a large doc corpus was checkable;
- *counting test-green flips as repairs* — 7 test-green flips in the guard receipt broke the suite.

## 6. The next bottleneck, and the law applied

The narrow generator works where **one constant on an executed line is the whole repair**. The
remaining 14 rows need a name substitution, several co-ordered edits, or new structure. The next
experiment must therefore make the *hole set* an output of causal analysis — data/control flow from
the failing assertion to the trace-executed lines — and allow multi-hole CEGIS with the suite as
oracle. Every added part must pay for itself: no selector layer that only reorders what a computed
causal score already orders; no stored repair templates; no model calls. Delete the guard-expression
selector entirely unless a future row shows a guard that is genuinely the edited site.

The frontier's A-CEGIS result says counterexamples are strong feedback for regex repair, but it
uses a model to propose. This round shows the proposal can be calculated for one real class. The
unresolved half is proposing **structure**, not characters.

## 7. Limits

- Fifteen real commits from one library, producer-run; no external or independent verification.
- Corpus freshness is SHA exclusion against existing receipts and corpus files, not a blind third-party split.
- The generator covers single constants only; a 60-candidate cap is a resource budget, not a law.
- `pytest` dependencies were installed into this sandbox; no runtime dependency on a model or network.
- No §6 criterion was claimed, and no merge was made.
