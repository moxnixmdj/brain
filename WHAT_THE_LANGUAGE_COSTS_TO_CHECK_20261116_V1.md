# The language at the site is ten to the fifty

*2026-11-16. Producer-run, 87 real fixes, 0 model calls, 0 parameters, no network, no test-suite execution.*

## What this round does

Last round priced the words and found them present: 54.0% of real fixes need only names already in scope at the
site, 17.2% need a value threaded, 27.6% need a name the file does not contain, and 11 operators cover 90% of
operator occurrences. The conclusion I drew was that the missing object is a **pruner** — something that rejects a
candidate term before it is executed.

This round prices the pruner, and the pricer kills it.

## Measured

| quantity | value |
|---|---|
| fixes where the term language can be sized | **87 / 87** |
| median depth the real fix needed | **4** |
| **median size of the term language at that depth** | **2.33 × 10⁵⁰** |
| measured cost of checking one candidate | **0.189 µs** (1,002,240 evaluations timed) |
| median time to check the whole language | **4.4 × 10⁴³ seconds** |
| fixes whose language is checkable in under a minute | **2 / 87** |
| HARD decoys — same words, same kind, same arity, different meaning | **574** |
| of those, rejected by every free pruner (arity, literal-type clash) | **0.0%** |
| deliberately MALFORMED decoys (wrong arity, clashing literal types) | **64** |
| of those, rejected by the same free pruners | **4.7%** |
| free pruners that reject the true term | **0** |

The size is exact, not an estimate: it is counted **by level** (a term of depth *k* has operands of depth exactly
*k−1*), the operator basis is *read* from the previous round's census rather than written here, and gate K5 requires
the closed form to **equal** brute-force enumeration at depth 2 — not bound it.

## The kill

Checking is essentially free. One candidate costs **0.189 microseconds**, on this machine, measured over a million
evaluations. Enumeration is not blocked by the verifier at all.

It is blocked by the **language**. At the depth real fixes actually need, the site can express ~10⁵⁰ distinct terms.
Even at 0.189 µs each, that is 10⁴³ seconds per fix. Free structural pruning — arity against local definitions, literal
type clashes — removes **3.5%** of shape-preserving decoys, and it does so soundly (it never rejects the true term,
which is what makes it a pruner and not a bug). Three and a half percent of 10⁵⁰ is 10⁴⁹.

So: **enumerating the site's language is dead**, and the route I named one round ago — "a computed pruner over a finite
term language at the site" — is dead with it. It was right that the words are there and the basis is small. It was
wrong that the object to build is a pruner. A pruner that removes 0% of the hard decoys and 4.7% of the broken ones
has not pruned a space of 10⁵⁰; it has described it.

(The first run of this probe reported 1.7%, then 3.5%, for decoy rejection. Both were artifacts: the decoys were drawn
from a set, so string hash randomisation changed which ones existed between runs — 920 one time, 917 the next. A test
caught it, the selection is now sorted, and the decoy classes are separated hard from malformed so the two questions
cannot be confused again.)

## What actually cuts 10⁵⁰

Not structure, and not more checking. **Evidence.** A term of depth 4 over twenty names has 10⁵⁰ syntactic
possibilities, but the failure also *instantiates* one: at the moment of failure, the site held particular values, and
the answer it should have produced is a particular value. A term that maps the observed inputs to the observed answer
survives; almost everything else dies on contact with one example. That is not a prior, it is not learned, and it is
not a heuristic — it is the only thing that reduces 10⁵⁰ to one at a stroke, and it is exactly what
`synthesized_expression_from_the_failure_v1` does when it evaluates candidates **in the scope the buggy program
produces**.

Which is why the numbers from earlier rounds are the ones that matter now. The value at the site is available for
**1.2%** of fixes, and 84% of failures are **unframed** — the test that fails does not say what the answer should have
been. The *insufficiency certificate* was never a statement about vocabulary. Priced, it is the difference between
10⁵⁰ and one.

**The single bottleneck: the causal observable at the site — the value the term should have produced — and the fact
that in most failures nobody states it.**

This also explains, without appealing to benchmarks, why computer use and code repair behave so differently under the
same learning law. For an action, the observation is *free and immediate*: the state after the action is displayed, and
`COMPUTER_USE_CHECK_DENSITY` measured that a full-state observation separates **1.0 of 34** wrong actions (0.7647 at
name level, 0.5 in novel work with no reference). Evidence arrives with every action, so instant learning is exact. For
a repair, the observation arrives once, at the end, and usually as a single bit.

## What to build, and it is not a pruner

**Manufacture the oracle instead of waiting for the test to state it.** The project already has this machinery and has
only ever pointed it at actions: `distinguishing_projection_v1` synthesises the *observation* — "given the action and
the space of ways it can be wrong, which observation distinguishes them?" — and it works because the projection is
searched for, not assumed. The same search applies one level down: at a failing site, search over *what to observe*
(which name, at which moment, in which of the failing and passing runs) until the observations of the passing and
failing executions separate. Then the term is constrained by data, and the 10⁵⁰ collapses to something a machine can
walk.

That is the whole difference between an agent that learns and an agent that searches blind: evidence is not a
convenience, it is the only cut.

## Bounds, stated so this cannot be over-read

- No repair was attempted. This is a cost and size result.
- The size counts distinct *syntactic* terms over a read basis and in-scope names; type filtering would lower it, but
  the free pruners that approximate type filtering here reject 3.5%, so the order of magnitude is not in doubt.
- 0.189 µs is this machine, measured; it is not a claim about any other machine, and it is 10⁴³ seconds away from
  mattering either way.
- The decoys are near-misses, not an exhaustive set of wrong terms; they probe pruner strength, not the space.
- The size counts distinct syntactic terms; the in-scope name count is generous, which can only make the language
  larger, i.e. the 10⁵⁰ is not an artifact of stinginess about the vocabulary.

Receipt: `canonical/verification/WHAT_THE_LANGUAGE_COSTS_TO_CHECK_20261116_V1.json`. Instrument:
`canonical/tools/what_the_language_costs_to_check_v1.py`.
