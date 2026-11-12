# One bad transport entry must not drop the next lesson

2026-11-12 · authority NONE · no capability, benchmark, family, or terminal promotion

## A real failure in a real reuse path

`VerifiedSkillStore.import_bundle` promises per-entry refusal and continued import, but converted
`verified_hits` with `int(...)` and `created_ts` with `float(... or time.time())` without validating
them. A malformed string raised and prevented later valid lessons from arriving. An oversized
counter overflowed SQLite; negative, Boolean, fractional, or nonfinite metadata could be accepted
or fail at the storage boundary. Epoch zero was silently replaced by the current time.

These metadata fields are not covered by the rule's content-addressed identity, so a matching rule
ID does not make them valid.

The change is inside the existing importer, before any database lookup/write for the entry:

- `verified_hits`: require a non-Boolean integer in SQLite's signed nonnegative INTEGER range
  (`0 <= n < 2**63`); reject numeric strings rather than coerce them.
- `created_ts`: accept finite nonnegative numeric values, excluding Booleans; refuse conversion
  overflow. Missing/None retains the historical current-time default; an explicit zero stays zero.
- Refuse a malformed entry with its skill ID and a specific reason, then continue with later entries.

This is validation, not authentication: a structurally valid counter is not proof that a verifier
ran. No imported lesson is promoted to greater assurance by this change.

## Executed regression evidence

`canonical/tests/test_skill_bundle_numeric_metadata_v1.py`:

- **Before patch: 14 failed, 1 passed.**
- **After patch: 15 passed.**
- With transport round-trip and learn-path wiring neighbors: **33 passed** locally.
- Expanded transport, wiring, scoped restart, parameterized-skill and load-bearing admission checks:
  **79 passed** locally. Unified-model verification: **33/33**; repository integrity: **0 violations**.
  These are focused producer-local checks, not a full-suite run or independent verification.

Twelve malformed-value cases each place the bad entry before a valid one. The tests assert the
named refusal and successful import, reopen the receiver store, and actually recall the retained
rewrite on a differently named source. Other tests check that a bad merge cannot invalidate/change
existing memory, the largest representable counter and epoch zero round-trip idempotently, and
missing legacy fields still receive defaults. The recall test uses a legacy caller predicate plus
an exact source assertion; it does not establish general task correctness or independent verification.

Scope is deliberately numeric transport metadata. This is not comprehensive bundle hardening,
full schema validation, signature verification, protection against malicious executable lessons,
or a guarantee that all other malformed fields are handled. No broader guarantee is claimed.

## What is already real about one-success learning

Current files were read directly, rather than inferring the answer from a name or an older summary:

`canonical/verification/MINIWOB_ONE_SUCCESS_GENERALISATION_20261111_V5.json` records 130 tasks,
78 with a reproducible first success and 1,560 subsequent test episodes (20 per demonstrated task).
The `version_space` arm reports **1,097/1,560 = 70.32%**, against **408/1,560 = 26.15%** verbatim
replay. On the 67 demonstrated tasks where fixed replay is insufficient, its mean is **65.45%**
versus **14.03%** replay. **45/130** tasks reach at least 18/20 successes. These are archived
producer-local measurements, not rerun here or independently verified; they are meaningful evidence
of bounded generalization, not proof of perfect arbitrary computer use.

Crucially, acquisition allowed **600 exploration actions** per task. 'One success' is not 'one total
attempt'. The practice arm's 77.69% uses additional practice and cannot be called one-shot.

The separate archived `MINIWOB_ONE_MEMORY_FOR_ALL_TASKS_20261111_V1.json` reports **26.62%** mean
success with the current task's own skills withheld (129 tasks scored, 130 listed), versus **38.19%**
with all skills available. This measures that particular memory/system/task suite, not the percentage
of all computer use solved. Neither artifact establishes advanced SWE leadership or sentience.

## First principles, recent research, and the next decision

Retention, identification of the right rule, applicability, composition, current dependencies, and
outcome checking are different contracts. One can work while another fails. The importer defect
illustrates a concrete retention/transport failure without disproving the learner itself.

Recent sources checked on the session date, November 12, 2026:

- [KEEL](https://arxiv.org/html/2610.34043) uses evidence to evolve skill claims rather than keeping
  every experience as permanently valid knowledge. Its reported gains do not establish universal
  mastery, and its model-based analysis is not adopted in Brain's credited producer path.
- [Making Agents More Consistent](https://arxiv.org/abs/2609.25299) distinguishes reliable repetition
  from correct applicability; deterministic errors can also repeat reliably. Its experiment is not
  a Brain evaluation and was not reproduced here.

The fastest defensible path is to reuse the existing learning/retrieval mechanisms on real tasks
within declared scope, verify new instances and contrasting refusals, then compare accepted outcomes
and costs against cold and equal-work controls. Do not repeat broad unrelated exposure campaigns,
rebuild already-owned learners, or substitute paper results for this project's measurements.

This round makes numeric-metadata transport failure local to its entry. It does not teach advanced
coding actions, update production memory, establish permanent correctness, or solve arbitrary
computer use. Durable skills should be revisable when evidence contradicts them, not permanently
trusted just because they were once stored.
