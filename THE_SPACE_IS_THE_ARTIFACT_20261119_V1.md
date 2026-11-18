# The space is the artifact, and the artifact is the whole problem

**Date** 2026-11-19 · **Branch** `arena/a449ff95-brain` · **Authority** NONE__PRODUCER_RUN_SANDBOX ·
**Parameters stored** 0 · **Model calls** 0 · **Spend** $0

The claim under test, verbatim:

> "Instant learning + instant learning in new arbitrary environments -- we already solved those
> perfectly. Doesn't this solve all our problems and all computer use? Give the model the smartest
> coding actions once and it owns them permanently, so we have the most advanced coding agent on the
> planet. Is this true, or are there things wrong? What is real and what is not, and what are the
> smartest things we can do? What is the single bottleneck that, if fixed, would unlock the most
> capability?"

---

## 1. What was already measured, and therefore what is not being re-argued

Four rounds of this conversation have produced numbers, not opinions. They stand:

| question | measured answer |
|---|---|
| does one demonstration transfer to the same kind of act later | **yes**, no parameters, ~0.5 s per act, cache-blind 2355× |
| is the address of a fault findable without a model | **yes**, one bit per candidate firing; reached the human's changed line 3 times in 15 |
| does the address give the fix | **no**: the human's expression was found **0 of 15** by either channel |
| are parameters needed to identify | **no**: 0 measured, and the identification device is now executed rather than approximated |
| what is left | **the replacement expression** |

So the question in front of this round is not "does instant learning work". It does, for retention. The
question is whether the *thing that is missing* -- the expression -- is missing because of memory,
because of addressing, because of parameters, or because of something that none of those three can
supply. That is measurable, and it was measured this round on commits nobody had looked at.

## 2. The question this round actually answers

Previous rounds gave the model the *address*. This round gives it the address **for free** -- the
human's changed line, handed over, an upper bound that no system could beat on this population -- and
asks the only question left:

> With the site given, can a zero-parameter space over the artifact's own vocabulary and the
> language's own grammar even *say* a real human's replacement, and what does it cost to reach it?

If the answer is low, no amount of retention, indexing, flipping, forcing or instant knowledge closes
the gap, and the "best part is no part" law has to be read differently than it has been read so far.
If the answer is high, the wall was the space's construction and the next round is ordering.

## 3. Population, declared before either arm ran

19 fresh commits from `click`, `jinja`, `attrs` and `httpx`, mined by a mechanical rule and screened
before anything was measured:

* the commit touches at least one file under `tests/` and one `.py` outside it;
* every 4th--5th such commit, going back past everything earlier rounds used, and **every commit from
  the previous round's 15 is excluded by SHA** -- nothing here was read while the instrument was built;
* at the **parent** commit with the **post-fix** test file, at least one test must actually FAIL
  (a skip is not a failure, an empty verdict map is not a pass);
* the failing share of the test file must be under 10% (a commit that breaks a quarter of the suite is
  a rewrite, not a repair).

`canonical/verification/THE_SPACE_IS_THE_ARTIFACT_CENSUS_20261119_V1.json` records what the population
is made of, with no oracle calls:

| kind | count |
|---|---|
| a single-expression replacement | **9** |
| an edit of more than one line | **10** |

That split is itself the first result, and it is not a defect of the instrument: the excluded ten
change several lines (a moved block, a new guard, a signature) and no space over *expressions* could be
asked to say them. **A real fix is often not one expression**, which is already a fact that "give it the
action once" does not survive: the action is not atomic.

The nine that are single expressions, all nine, mechanically extracted:

| repo | commit | the human replaced | with |
|---|---|---|---|
| click | `05f6fd0df4` | `records` | `[arg.get_help_record(ctx) for arg in args]` |
| jinja | `baff54fe1d` | `'_get_default_module(context)'` | an f-string calling `self.choose_async('_async')` |
| attrs | `862696afb5` | `True` | `name != 'alias_is_default'` |
| attrs | `6e3786c599` | `False` | `None` |
| attrs | `937b1e2328` | `args` | `', '.join(pre_init_args)` |
| click | `607316f9de` | `isinstance(self.show_default, bool)` | `self.show_default is not None` |
| attrs | `fd7538f0e2` | `self.options` | `self._original_options` |
| attrs | `7d55876ed3` | `list` | `(list, tuple)` |
| attrs | `0f6a9b4753` | `hash_` | `hash` |

## 4. The instrument

`canonical/tools/the_space_is_the_artifact_v1.py`. One site, one space, one blind search, two arms:

* **the site** is the smallest enclosing expression the human rewrote. `x + 1 -> x * 2` changes the
  operator *and* the operand; requiring exactly one differing node rejected every repair of that shape
  and made the first version of this measurement report 10 of 19 commits as "not a single expression".
  That number was a property of this file, not of the world. The rule is now: take the change points,
  take their common enclosing node, and it must be an expression.
* **the space** is atoms ordered by ring and then by size -- the site's own operands (ring 0), every
  name in scope (1), the names in scope **crossed with the attribute vocabulary of the file** (2),
  literals the file or the machine already has (3) -- closed under the language's own grammar
  (`expressions_from_a_site_v1`), and, in the second arm, under the four productions the misses named
  (a call, a comprehension, a membership test, a subscript) plus **the attribute vocabulary of the
  running interpreter** (`dir(str)`, `dir(list)`, ... computed in 4 µs, stored nowhere).
* **the search** is blind. It walks the order and runs the failing test on each candidate until one
  passes; only then does it run the whole file. It never reads the human's expression, and the human's
  expression is read *after* the run, to score a rank. Zero parameters.
* **the cap is declared**: 200k candidates in the base arm, 400k in the wide arm, 32 oracle questions.
  A fix outside the cap is `UNRESOLVED WITHIN THE CAP`, never `IMPOSSIBLE` -- the tree has already paid
  for that mistake once.

## 5. The measurement

Three closures, the same 19 commits. The first two were *searched* (32 oracle questions per row, blind,
one candidate per question). The third is a **membership census with zero oracle questions**: it asks
only whether the human's expression is sayable at all, which costs no test run.

| arm | closure | rows measured | the human's expression is in it | rank | oracle questions | verified repairs | seconds |
|---|---|---|---|---|---|---|---|
| **base** | site operands, names in scope, scope x the file's attribute vocabulary, the file's literals, closed under the language's grammar | 9 | **1 of 9** | 2887 | 288 | **0** | 195.4 |
| **wide** | + a call, a comprehension, a membership test, a subscript; + `dir()` of the live types; + literal bases | 9 | **1 of 9** | 2887 | 288 | **0** | 195.7 |
| **full** (census) | + `dir(builtins)` -- the machine's own names | 9 | **2 of 9** | 186 and 3034 | 0 | not searched | 50.2 |

Not one repair was verified in either searched arm. The two rows that are sayable sit at rank 186 and
rank 3034, which at half a second per oracle question is **93 seconds** and **25 minutes** for one line
of code, against a budget of 32 questions (16 seconds).

## 6. What each miss was missing, named and computed

The useful half of the measurement is not the count, it is that every one of the nine has a name, and the
name came from the artifact by computation:

| # | commit | the human replaced ... with | verdict under **full** |
|---|---|---|---|
| 1 | click `05f6fd0df4` | `records` -> a list comprehension whose element is a method call | in the language, not in this closure: a call **nested inside** a comprehension |
| 2 | attrs `862696afb5` | `True` -> `name != 'alias_is_default'` | the comparison is the language; the literal is in `tests/test_functional.py` **four times** -- it is in the specification, and the space does not read it |
| 3 | attrs `6e3786c599` | `False` -> `None` | **sayable, rank 3034** |
| 4 | attrs `937b1e2328` | `args` -> `', '.join(pre_init_args)` | in the language and in `dir(str)`; not in this closure because the argument name fell outside the enumeration cap |
| 5 | click `607316f9de` | `isinstance(...)` -> `self.show_default is not None` | in the language, not generated: no identity comparison |
| 6 | jinja `baff54fe1d` | a string -> an f-string calling a method on `self` | in the language; 8 nodes against the enumerator's cap of 7, and one literal is the specification's |
| 7 | attrs `fd7538f0e2` | `self.options` -> `self._original_options` | **nowhere**: not in the parent file, not in any test. The only genuine gap in the nine |
| 8 | attrs `7d55876ed3` | `list` -> `(list, tuple)` | in the language, not generated: no tuple display |
| 9 | attrs `0f6a9b4753` | `hash_` -> the builtin `hash` | **sayable, rank 186** -- but only once `dir(builtins)` was admitted, which it was not at first |

Eight of the nine are ordinary Python that the machine itself can enumerate. Five are missing
*productions* of this construction, two are missing *vocabulary the machine already has*, one needs the
words of the specification, and exactly one -- the renamed attribute -- needs something that exists
nowhere but in the author's head.

So the ceiling is not in the world. **The ceiling is in the construction, and the construction is
cheap.** The expensive thing is the rank.

## 7. The bottleneck, stated as arithmetic

Closure is what makes a space large: once it can say a call, a comprehension, a member and a subscript,
a single site admits 10^5 candidates.

* one oracle question (put a candidate in place, run the failing test) = **0.5 s**
* rank 186 = **93 s**; rank 3034 = **25 minutes**, for one line
* a value forced into a recorded frame and compared = **50 µs** -- **10,000x** cheaper, and no test run
  at all

The bottleneck is therefore not memory, not addressing, not parameters, not the absence of a model. It is
**selecting one expression out of the closure**, and the only zero-parameter instrument that collapses
that selection is the *value the failing assertion demanded*: force it at the site, evaluate every
candidate in the recorded frame, keep only those that produce it, and let the suite judge the survivors.

That is not a new mechanism. It is the composition of two things this tree already has --
`force_the_value_and_see_v1` (the value at a site) and `expressions_from_a_site_v1` (the closure) -- with
the closure widened by `dir()` and the grammar, and the ordering replaced by a filter. The literature
arrived at the same design from the other side and called it angelic fix localization with micro-oracles;
it repaired real Java bugs and its stated ceiling was the vocabulary of the collected values. This tree's
version differs in one place: the value is forced by execution rather than collected from a symbolic
engine, and the gate is the whole suite rather than one test.

## 8. What is real, what is not

**Real.** Instant retention: learned once, replayed at 0.5 s, zero parameters, no cache. The address:
one bit per candidate firing, no model. The oracle: a whole test file, green or not, 0.5 s per question.
Verification: the only sound gate there is.

**Not real.** "Give it the action once and it owns it." The action is not atomic -- half of the real
fixes measured here are not one expression. And even when it is one expression, the action is not a
*thing* to remember; it is a *choice* among 10⁵ constructions of the language, and one demonstration
supplies one chosen element and no ordering over the rest. Memory of the choice cannot substitute for
the ability to choose.

**The thing that would make it real** is a selection instrument, not a memory instrument. That is the
whole content of this round.

## 9. Computer use is a different question, and it is the one where the claim is closest to true

A GUI action is drawn from a *finite, given* set: the elements on the screen, each with a role and a
label, all of them supplied by the environment at the moment of action. There is no closure to search,
so there is no rank to be wrong about -- the bottleneck measured here does not exist there. That is why
"one demonstration and it owns computer use" is a defensible claim and "one demonstration and it owns
software engineering" is not: the first has a finite action space, the second has the language.

The distinction is testable and it is the next honest experiment on the computer-use side: measure the
rank of the demonstrated action inside the set of actions the environment offered at that moment. If
that rank is 1, the claim holds there.

## 10. Falsifier

This round's reading dies if, on a fresh corpus, a closure that includes the four productions, `dir()`
vocabulary and the words of the failing test reaches the human's expression at a rank that a
value-filtered search (50 µs per candidate) can afford -- say under 10⁴ -- for most single-expression
commits. In that case the bottleneck is engineering, not selection, and the next round is the filter.
It also dies if the 10-of-19 multi-line share does not reproduce, because that share is the reason the
"one action" framing fails at all.

What it does **not** claim: that a model is needed. Nothing here needs one, and the parameters stored
remain zero.

## 11. Limits

* 19 commits from four Python libraries; nothing here speaks for other languages, other test styles, or
  compiled code.
* The site is given for free in both arms. Every number is an **upper bound** for any system that has to
  find the site first.
* The rank is measured within a declared cap. A rank beyond the cap is reported as unresolved, never as
  impossible.
* The nine-row taxonomy is nine rows. It names the walls, it does not weight them for the world.
* Producer-run sandbox. No independent verifier re-ran these numbers.

## 12. Reproducing

```
python3 canonical/tools/the_space_is_the_artifact_v1.py --mine click jinja attrs --stride 5 --skip 2 \
    --want 4 --receipt /tmp/corpus_space.json
python3 canonical/tools/the_space_is_the_artifact_v1.py --commits /tmp/corpus/fresh_all.json \
    --census-only --receipt canonical/verification/THE_SPACE_IS_THE_ARTIFACT_CENSUS_20261119_V1.json
python3 canonical/tools/the_space_is_the_artifact_v1.py --commits /tmp/corpus/fresh_all.json \
    --receipt canonical/verification/THE_SPACE_IS_THE_ARTIFACT_20261119_V1.json --budget 32
python3 canonical/tools/the_space_is_the_artifact_v1.py --commits /tmp/corpus/fresh_all.json \
    --receipt canonical/verification/THE_SPACE_IS_THE_ARTIFACT_WIDE_GRAMMAR_20261119_V1.json \
    --budget 32 --cap 400000 --grammar wide
python3 canonical/tools/the_space_is_the_artifact_v1.py --commits /tmp/corpus/fresh_all.json \
    --receipt canonical/verification/THE_SPACE_IS_THE_ARTIFACT_FULL_VOCABULARY_20261119_V1.json \
    --budget 0 --cap 400000 --grammar full
python3 -m pytest canonical/tests/test_the_space_is_the_artifact_v1.py -q
```
