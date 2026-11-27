# The guide example is a spot check: 85% of faults, 33% of the guards

*Round `GUIDE_EXAMPLE_IS_A_SPOT_CHECK_20261127_V1` · 2026-11-27 · branch `arena/4d7c568f-brain`, base `7121e93c`*
*Receipt: `canonical/verification/GUIDE_EXAMPLE_DETECTION_POWER_20261127_V1.json` · instrument: `canonical/tools/guide_example_detection_power_v1.py` · tests: `canonical/tests/test_guide_example_detection_power_v1.py`*
**Model calls 0 · stored parameters 0 · network at run time 0 · 6.3 s for 131 faults**

---

## 0. The question this round had to answer

The previous round measured that a real guide's examples **run**, and that 130 of 138 printed
their own answer back (`THE_GUIDE_IS_A_TEST_SUITE_20261204_V1`). That is a statement about
*reproduction*. The system's next step -- "file the receiver's behaviour as confirmed because the
guide's example passed" -- needs a different statement, about **detection**:

> if the implementation is wrong, does the documented example say so?

This round injects real faults into real library code and counts what the documentation catches.
The answer is not the one I predicted when I designed it, and the correction is the round's result.

| claim | verdict | measurement |
|---|---|---|
| a documented example refuses a broken implementation | **true, usually** | **92 of 108** separated faults killed (85.2%) |
| a documented example is a *test suite* | **false** | it enters **12 of 36** decision branches (33%); **24** guards are never exercised |
| the guide therefore validates a receiver | **only grossly** | `const` faults escape **33%** of the time (`median([-1])` -> `StatisticsError`); operator faults, 0-8% |
| one example is worth one hand-written test | **no, it is worth ten** | 1 random regression case kills 62%, 3 -> 72%, **10 -> 93%**, 40 -> 100%. The guide's 2-5 author-chosen examples buy 85% |
| the residue is unknowable without another oracle | **true, and now named** | **13 of the 24** unexercised guards get a concrete input from a boundary lattice alone; their expected output is a *named gap*, not a value |

The useful one-line form: **a guide's example is a high-yield admission test and a poor regression
suite.** It says "this receiver implements the documented contract on a typical input". It does not
say "this receiver is correct at the boundaries", and the boundaries are where the faults that
escape actually live.

---

## 1. Method, and the four things that were wrong with the first version

| step | what it does | why it is not optional |
|---|---|---|
| receiver | a module from this interpreter's standard library (`statistics`, `difflib`, `textwrap`, `enum`) | real code, real docs, version-matched, offline -- not a fixture written for the experiment |
| fault | one AST-level edit inside one function body: swap a comparator, swap an arithmetic/boolean operator, move a constant by one, return `None` | mechanical, so the fault set cannot be chosen to flatter the guide |
| equivalence control | a fault counts **only** if an independent 40-input random corpus separates the mutant from the original (value or exception type) | a mutant no input can see is not a fault; counting it as a miss would blame the guide for the mutant's degeneracy |
| oracle A | the function's own docstring examples, replayed in the module's namespace | this is the 2026-12-04 oracle, unchanged |
| oracle B | *k* random inputs with expected values taken from the unmutated function | what *k* real regression cases would buy, on the same fault set |
| guard audit | every `if`/`else` branch of the function, and whether the examples execute it | the mechanism, not just the score |

Four defects were found and fixed **before** the numbers were believed. Each is now a test:

1. **A mutant compiled from `ast.unparse` renumbers every line.** The branch cross-tab matched
   mutation sites against the original source's line numbers and reported `guide_reached: 0` on all
   sixteen functions -- a tidy table meaning nothing. The control is now compiled from the original
   source so its line numbers are the analysed ones.
2. **The first corpus perturbed the documented argument.** That scores the example against inputs
   centred on itself: it read 88% and was measuring nothing but the example's own input. The corpus
   is now drawn independently of the documented values, keeping only their *types*.
3. **Boundary probes were returned as bare tuples** while the caller unpacked pairs, so the guard
   search crashed on exactly the two modules that had untested branches.
4. **Docstring and error-message constants were being mutated.** Mutating the docstring edits the
   oracle; mutating an error message changes nothing the corpus compares. Both inflated
   `not_separated` with faults that were never faults.

---

## 2. Results

### 2.1 Detection power

| oracle | faults killed | of 108 separated | note |
|---|---:|---:|---|
| the function's documented examples | **92** | **85.2%** | 2-5 author examples, average |
| 1 random regression case | 67 | 62.0% | |
| 3 random cases | 78 | 72.2% | |
| 10 random cases | 100 | 92.6% | more than the guide |
| 40 random cases | 108 | 100% | the corpus that defines the denominator |

The independent-draw columns are not nested samples, so a single module can move by one case
between columns (`difflib`: 15 at k=1, 11 at k=3); the aggregate is monotone.

Per receiver:

| module | documented functions | faults | separated | guide kills | k=1 | k=10 |
|---|---:|---:|---:|---:|---:|---:|
| statistics | 11 | 87 | 74 | 59 | 39 | 72 |
| difflib | 3 | 20 | 15 | 15 | 15 | 11 |
| enum | 1 | 21 | 17 | 16 | 12 | 16 |
| textwrap | 1 | 3 | 2 | 2 | 1 | 1 |
| fractions, calendar, string | 0 | 0 | 0 | 0 | -- | -- |
| json | package, not audited | -- | -- | -- | -- | -- |

`fractions`, `calendar` and `string` have no *module-level function* with an example of its own:
their documentation lives in class docstrings, module docstrings or `.rst` files. That is a scope
limit of this instrument, and it is the same limit that makes "read the guide" narrower than it
sounds.

### 2.2 What escapes, and what it looks like

16 faults are separated by the corpus and invisible to the guide. By operator family:

| family | separated | missed | miss rate |
|---|---:|---:|---:|
| constant moved by one | 39 | 13 | **33.3%** |
| comparator swapped | 27 | 2 | 7.4% |
| returned value -> `None` | 13 | 1 | 7.7% |
| arithmetic operator swapped | 23 | 0 | 0% |
| unary / boolean operator | 6 | 0 | 0% |

Every missed fault has a witness -- the call, the value the real function returns, and the value
the mutant returns. These are the *requirement-specific failing observations* the project keeps
asking for, with the provenance stated: an injected fault, not a bug claimed in the standard
library.

| function | fault | call | real | mutant |
|---|---|---|---|---|
| `mean` | `const:1->2` | `mean([2])` | 2 | `StatisticsError` |
| `harmonic_mean` | `const:0->1` | `harmonic_mean([2])` | 2 | `IndexError` |
| `harmonic_mean` | `const:0->1` | `harmonic_mean([0, 2, 1])` | 0 | 1 |
| `harmonic_mean` | `compare:Is->IsNot` | `harmonic_mean([2], weights=[-1, 1])` | `StatisticsError` | 2 |
| `median` | `const:0->1` | `median([-1])` | -1 | `StatisticsError` |
| `median` | `const:2->3` | `median([2, 1000000, 17, 2, 9])` | 9 | 2 |
| `median_low` | `const:0->1` | `median_low([])` | `StatisticsError` | `IndexError` |
| `median_low` | `const:2->3` | `median_low([37, 37, 1, -14, -1])` | 1 | -1 |
| `median_high` | `const:0->1` | `median_high([1000000])` | 1000000 | `StatisticsError` |
| `stdev` | `const:2->3` | `stdev([0.0, 21.135])` | 14.9447 | `StatisticsError` |
| `pstdev` | `const:1->2` | `pstdev([-22.926])` | 0.0 | `StatisticsError` |
| `bin` | `const:0->1` | `bin(0)` | `'0b0'` | `'-0b 10'` |

Read the first column of the calls: **singleton list, empty list, zero, negative, duplicate.** Every
one of the sixteen is at a boundary. The documented examples use `[1, 3, 5]`, `[1, 3, 5, 7]`,
`"Hello  world!"` -- the interior of the function's domain.

### 2.3 Why: the examples never enter two thirds of the guards

For each documented function, every `if`/`else` branch was traced while the guide's own examples ran.

| measurement | value |
|---|---:|
| documented functions traced | 16 |
| decision branches in their bodies | **36** |
| branches the examples enter | **12 (33%)** |
| branches the examples never enter | 24 |
| never-entered branches reachable by a pure boundary lattice | **13 (54%)** |

Cross-tabulated against the fault set:

| fault site | separated | killed by guide | power |
|---|---:|---:|---:|
| inside a branch the examples enter | 33 | 30 | 90.9% |
| inside a branch the examples never enter | 4 | 0 | **0.0%** |
| not inside any branch | 71 | 62 | 87.3% |

The counts are small (4), but the direction is the one predicted by the guard table: the guide is
informative exactly where it has been, and silent exactly where it has not. `mean`'s single guard,
`fmean`'s four, `harmonic_mean`'s twelve -- the examples touch three of them.

---

## 3. What this buys the system, and what it refuses

**Buys: a gap channel.** `reach_guards` takes the guard's own boundary lattice and finds an input
that enters a branch the guide never entered. 13 of 24 unexercised guards get one, with no model and
no new knowledge. The artefact is not an answer -- it is a *named unknown with a witness*:

```
median_low: guard at line 587 never entered by its two documented examples
            witness input: ([],)          <- a real, executable question
            expected output: UNKNOWN      <- not available from the guide
```

That is the shape §9.2 asks for ("unknown is an explicit gap that triggers a targeted question"),
and it is the only form in which the residue can honestly be stored. A store that recorded
"`median_low` confirmed by its guide" would be recording a claim the guide cannot support.

**Refuses: the two obvious shortcuts.**

* *Augment the example with perturbations and check them.* Rejected, and measured: a perturbation
  has no expected output, so it kills nothing. Boundary augmentation does not raise detection power
  by one case; only a new **oracle** does, and the guide does not contain it.
* *Derive a property from the example and check it on new inputs.* Rejected as self-confirming: a
  property that holds on the receiver for the whole sample is unfalsifiable by that sample, and the
  one property that is genuinely documented (`textwrap.shorten` fits the width and ends in the
  placeholder) is exactly the 2026-12-04 round's two admitted rules -- already counted there, not
  re-counted here.

So the boundary oracle has to come from somewhere else. The three places that can supply it, in the
order this repository should try them:

1. **the receiver's own test suite** -- it exists, it is written by the author, and it is the only
   source with expected values at the boundaries (the 2026-11-26 round already reads and runs it);
2. **a second implementation of the same documented contract** -- differential execution needs no
   expected values at all, only agreement, and a disagreement is a failing observation;
3. **a targeted question to the owner**, asked once, with the witness input attached.

That ordering is the round's architectural recommendation, and it is falsifiable: if (1) or (2) does
not raise detection power on the same fault set, it should not be built.

---

## 4. What is real, what is not

**Real.** 92 of 108 injected, independently separated faults refused by real documentation, with
per-fault witnesses. 36 guards traced; 12 entered. 13 named unknowns with executable witnesses.
Every number above comes from one command in this session. Two further seeds reseed only the random
corpus: 92/108 (85.2%) and 92/109 (84.4%) against 92/108 here, with the branch tally unchanged
(30/33 reached, 0 of 3-4 untested, 62/71-72 outside) and the same 13 guard witnesses.

**Not real.** That this is a benchmark result -- no OSWorld, Terminal-Bench or SWE-bench was run and
none is runnable here. That the standard library is buggy -- the table above lists *injected* faults.
That 85% generalises -- the receivers are four stdlib modules whose docstrings are unusually rich
(`statistics` carries 82 examples); a library with one example per function has less power, and this
instrument would report that too. That `not_separated` proves equivalence -- a wider corpus can only
*lower* the guide's score. That the boundary lattice finds every unexercised guard -- it finds 54% of
them; the rest need the guard predicate solved, which is the next round's job.

**Not measured, and the honest reason.** Wall-clock and CPU cost per *task*: there is no task here.
What is measured is 6.3 s of compute for 131 faults, i.e. ~48 ms per fault including a full module
rebuild, and $0 of model spend.

---

## 5. Where this leaves §6

§6 is not met and this round does not move it. What it does is remove one over-claim from the path:
*"the guide is a test suite"* is now *"the guide is an admission test with 85% gross-fault detection
and 0% boundary-guard detection"*, which is a usable instrument and a much smaller claim.

The next decisive experiment, stated so it can fail:

> Take one receiver whose guide's examples pass and whose own test suite is available. Run the
> same fault set against (a) the guide's examples and (b) the receiver's own tests, and report
> detection power for both on the identical mutants. If (b) does not beat 85% by a margin that
> covers the boundaries in §2.2, the ordering in §3 is wrong and the boundary oracle must come
> from differential execution instead.

---

## 6. Reproduce

```bash
python3 canonical/tools/guide_example_detection_power_v1.py \
        --receipt canonical/verification/GUIDE_EXAMPLE_DETECTION_POWER_20261127_V1.json   # ~6 s
python3 -m pytest canonical/tests/test_guide_example_detection_power_v1.py              # 8 tests
```

`pytest` is not installed in this sandbox (`/usr/bin/python3: No module named pytest`), so the eight
tests were executed here through an eight-line stand-in that supplies `pytest.fixture` and calls each
test directly: 8 passed, 0 failed. That stand-in was scratch, has been deleted, and is not part of
the change; the guard's own scan caught it as a `sys.modules` injection before it was removed, which
is the guard working.

---

*A guide is the cheapest oracle on the machine, and it is an oracle about the interior of a
function's domain. The boundary is where the bugs are, and the guide has never been there.*
