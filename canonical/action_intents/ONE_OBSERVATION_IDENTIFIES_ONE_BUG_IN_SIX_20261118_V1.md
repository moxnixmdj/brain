# One observation identifies the fix on one bug in six

*The limit is identifiability. Not speed, not vocabulary, not storage.*

## The claim under test

Give the model the most advanced coding actions, let it experience each one once, and it owns them
permanently -- then the same loop covers anything on a computer. This is the thesis. It has three
parts, and they fail independently: *experience once*, *learn permanently*, and *transfer to an
arbitrary environment*.

"Learned" can only mean one thing operationally: **the set of hypotheses consistent with what was
observed has collapsed to one.** So the number to measure is not "did it find a fix" -- the
enumerator finds fixes -- but *how many candidates remain consistent after k observations, and is the
smallest of them correct on inputs the corpus never saw.*

## The measurement

For each bug's fix site: take the candidates the site's own material builds (399-400 of them), run
each on k corpus cases, keep those producing the expected output on all k. k = 1 is the promise.

| bug | survivors after 1 observation | smallest survivor | correct on perturbed inputs |
|-----|------------------------------:|-------------------|-----------------------------|
| `lis` | **1** | `max(length + 1, longest)` | **12/12** |
| `mergesort` | 7 | `(len(arr)) % (2)` | 3/12 |
| `kth` | 400 | `k` | 4/12 |
| `get_factors` | 3 | `(int(n ** 0.5)) + (n)` | 9/12 |
| `next_permutation` | 23 | `(perm[j]) > (j)` | 8/12 |
| `possible_change` | 0 | -- | -- |

One observation identifies the fix on **one bug in six**, and on that one it is exactly right
(12/12 on inputs the corpus never contained). On the other five, one observation leaves between 3
and 400 live hypotheses, and the smallest of them is wrong on a third to three quarters of new
inputs. `mergesort` needs a second observation before the smallest survivor is right.

That is the whole answer in one table. **Experience does not teach a rule; it eliminates some
hypotheses and hands the rest to a prior.** Whether the survivor is the truth depends on the prior
being right, not on the experience.

## What is actually real

1. **The falsifying mechanism is identifiability, and it is now counted.** A single trace is
   consistent with many programs; the table above puts the multiplier on it (1, 3, 7, 23, 400).
2. **The acceptance predicate is weaker than the truth.** Every corpus-accepted fix except `lis`
   (and `mergesort` from k=2) disagrees with the corpus's own reference program on perturbed inputs.
   This is the mechanism that makes permanence *dangerous*: store what a weak predicate accepts and
   you have stored a wrong program forever, with no signal that it is wrong.
3. **The theory this project was missing has a name and a 2016 date: the angelic forest.** For a
   suspicious expression, its *angelic value* on a path is a value that, if returned there, makes the
   test pass; the forest is the set over paths, and *any expression satisfying every pair repairs the
   program.* A value specification, not an expression specification. It is the right form for
   permanence because a table of (state, demanded value) is a constraint that many expressions can
   satisfy, whereas an expression is one point in a space of 10^9.
4. **And it does not solve the problem by itself.** This build tried to compute the forest by
   execution instead of symbolic execution, and hit the wall that explains the whole literature: at a
   loop-carried site, **no single value repairs anything.** The site runs many times per case and the
   demanded value differs per occurrence -- the angelic unit is the *path*, and forcing one value at
   one occurrence cannot repair a loop. Angelix needs symbolic execution for exactly this reason, and
   the 2026 state of the art still extracts angelic values from the *correct version of the program*
   because Python's symbolic execution is immature. At run time there is no correct version.

So: the value specification is the right object, and **obtaining it is the bottleneck, not using
it.** That is a sharper statement than "the search has no goal" and it survives contact with the
literature.

## What is not real

- **"Once and permanent" is not a property of experience.** It is a property of the prior plus the
  acceptance predicate. With a weak predicate, permanence is how a false belief becomes a fixed one.
- **"Any computer use" does not follow from the coding result.** The table above is about a site in
  a program with an oracle. Computer use has the same structure -- state, action, demanded effect --
  but its oracle is the environment's goal state, which is exactly what is missing when the task is
  new. The recurrence of *shapes* is real (measured here at 59.7% addressable); the recurrence of
  *effects* is what is unmeasured.
- **Sentience is not a target.** It has no falsifier, so it cannot be measured, so it cannot be
  built. What is being built -- and what the numbers above describe -- is a machine that converts
  observations into verified constraints. Every stored item is either checkable against the world or
  it is decoration.

## The single bottleneck

> **Turning an observation into a constraint that is true beyond the observation.**

Everything else in this project has been measured and is cheap: vocabulary is at the site, one
candidate costs a millisecond, a second buys 6,000 questions, storage is free. What is not cheap and
not solved is the step from *this case failed* to *this relation must hold*. The angelic forest is
the correct name for that relation. Computing it without symbolic execution -- from execution alone,
per path -- is the open problem, and it is the one worth attacking.

## Ship list

- `canonical/tools/how_many_hypotheses_survive_an_observation_v1.py` -- the instrument above. Its
  probes are *perturbed* inputs checked against the corpus's reference program, because the first
  version drew them from the corpus and the corpus graded itself.
- `canonical/verification/ONE_OBSERVATION_IDENTIFIES_ONE_BUG_IN_SIX_20261118_V1.json` -- every
  number, with the precondition confound stated rather than hidden.
- A value-table instrument was built during this work and **deleted**: at loop-carried sites its
  table cannot be computed by forcing values, so it did not do what its name said. Its finding is
  paragraph 4 above. The best part is no part.
