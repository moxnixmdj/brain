# The remaining gap at two showings is a census, not a mystery

Date: 2026-11-13.  Base: `d9318588` (T35 merged).  This is a diagnosis artifact,
not a declared measurement: no benchmark table below is a re-draw; every number
cited from the tables is the T35 declared run's recorded result, and everything
new here is learn-time and per-file diagnosis of the kind every prior turn ran
before declaring its mechanism.

## Why this census exists

After T35, the corpus state at two showings is: held_out 166/182 strict
answers, different 0, extra 0, 16 questions left, 3 files refused; fresh and
seen analogous.  The honest question is no longer "what mechanism is missing"
in the plural — it is: **of the 19 remaining non-answers, which are knowable
from the shown evidence at all, and which are the information-theoretic price
of example-bound learning?**  This census walks every one.

## The census (held_out at two showings, every gap)

| gap | count | cause | verdict |
|---|---|---|---|
| np_bool targets write `np.bool8` | 6 left | the showings only ever contained `np.bool`; `np.bool8 -> bool` is a second lesson nobody showed | **unknowable** — leaving it is correct |
| isin target changed code inside a string literal | 1 left | the person edited code quoted inside a string; the engine does not rewrite string contents | **unknowable at this tier** (rewriting quoted code from an AST lesson is a category error) |
| exception_message `str(e.message)` -> `str(e)` | 3 left | the lesson shows `{e.message} -> {e}`; the target site composes it with a simplification `str(str(e)) -> str(e)` nobody showed | **unknowable** — writing `str(str(e))` would have been a wrong write; leaving is correct |
| exception_message f-string `{e.message}` -> `{str(e)}` | 1 left | the shown f-strings and the target's differ in the surrounding string text; blanking string content across showings is not yet a mechanism | **knowable** (same family as below) |
| fromtimestamp in a lambda / dict literal | 2 left | the two showings spell the SAME objects two ways — `datetime.datetime` vs `datetime`, `datetime.timezone.utc` vs `timezone.utc` — because one file does `import datetime` and the other `from datetime import datetime, timezone`.  `generalize` refuses to merge: on the pattern side the qualifier is an imported name (the subject of the change), and on the template side `timezone.utc`'s variance is new code not copied from the old, so `blanks_in(template) <= blanks_in(pattern)` fails.  Two literal rules result; targets fit neither | **knowable — the one real mechanism left** |
| math_gcd 2 files refused | 2 files | both showings moved `fractions.gcd` to `diofant.core.compatibility.gcd` — a project-specific destination; the targets' truth went to `math.gcd` instead.  The needs-gate refused because the targets lack diofant | **the refusal calculus working**: writing what the showings said would have been 2 wrong files.  The showings themselves are unrepresentative; no engine change is licensed |
| yield_fixture 1 file refused | 1 file | line 48 holds `pytest.yield_fixture` not called, the examples showed it only called; fail-closed on an unshown shape | **borderline** — a bare-reference occurrence of a call-shown lesson; small, genuine, low value (1 file) |

## The one mechanism the census licenses next

**Two spellings of the same imported object are one subject.**  When showings
disagree at a node only because each file binds the same origin `(module,
inner)` under a different spelling, that is apparent dissent, not real dissent:

- pattern side: the varying part becomes a blank constrained to the origin —
  at fit time the target's node must resolve, through the target's own imports
  with no local shadowing, to that same origin; at write time the blank copies
  the target's own spelling, as blanks already do;
- template side: a varying part of the new code whose variants all resolve to
  one origin is not "something that varies and was not copied" — it is one
  object, written into each target with the spelling that target's imports
  already give it, or brought through the existing bring/needs gates
  (`rule.bring`, `rule.standing`, T34's origin machinery) when the target does
  not bind it yet.

This closes the fromtimestamp 2 and is the exact lineage of T32–T34 (aliases,
import bookkeeping, origins): referential identity over import spellings.  It
must NOT weaken utcnow's @2 refusal — there the showings disagree in substance
(different transformations), not in spelling, and no origin equality exists to
merge them.  The pinning tests for the mechanism must include: (a) a
spelling-pair that merges and writes each target in the target's own spelling;
(b) a substance-pair that still refuses; (c) a template-side object the target
does not import, entering only through the resolution gate.

## What the one-showing wrong writes prove (and why they stay)

The fresh @1 tables keep 6 different + 13 extra.  The census of those:

- np_object: the example shows `dtype == np.object -> dtype == object`; the
  target's truth DELETES the `np.object` element from a dtypes list rather
  than substituting it (substituting would duplicate `object` beside
  `np.object_`).  Substitute-vs-delete at an unshown site is not decidable
  from one showing.  **No mechanism may claim these without guessing.**
- fail_unless: the single example tangles two habits (`failUnless ->
  assertTrue` and `assertEquals -> assertEqual`); the target person applied
  only one of them in that commit.  Which habit was "the lesson" is harness
  metadata, invisible in the example by construction.

That is: at one showing, the remaining wrong writes are the irreducible price
of acting at all; the engine's zero-wrong-writes guarantee is, and should stay,
a two-showings guarantee.  This is the measured, honest boundary of "instant
learning" here: **one showing identifies a transformation only up to the
example's silence, and the corpus contains live cases where that silence is
exactly where targets diverge.**

## Standing doctrine this census confirms

- Refusals are not failures to fix: 2 of the 3 remaining @2 file refusals
  prevented wrong writes (math_gcd), and the third (yield_fixture) fails
  closed on an unshown shape.
- The gap census at two showings contains exactly ONE general mechanism
  (origin-identity across spellings, ~3 questions here but class-widening),
  one borderline crumb (1 file), and otherwise only unknowables.  Mechanism
  yield has entered diminishing returns on this corpus; the binding constraint
  is now corpus breadth and showing diversity, not engine cleverness.
- Therefore the next marginal hour goes further into (a) the origin-identity
  mechanism, declared first, and (b) widening the corpus (more kinds, more
  heterogeneous showings per kind), than into any further tail-chasing.
