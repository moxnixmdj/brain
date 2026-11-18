# The site is not where the fix comes from

*2026-11-18 · measurement: `canonical/verification/THE_SITE_IS_NOT_WHERE_THE_FIX_COMES_FROM_20261118_V1.json`
· tools: `canonical/tools/is_the_fix_a_widening_of_the_site_v1.py`,
`canonical/tools/identify_a_real_bugs_fix_v1.py`,
`canonical/tools/what_a_real_fix_needs_from_the_site_v1.py`
· population: 241 real single-line edits and 29 real fix commits in `requests`, `click`, `tqdm`, `httpx`
— no QuixBugs, no synthetic corpus, no model, no network at run time*

## The question, in the words it was asked

> "We solved instant learning in new arbitrary environments. Give the model the most advanced actions,
> let it experience each once, and it owns them permanently. Isn't that a perfect solution for all
> computer use? What is real, what is not, and what is the smartest thing to do?"

Two claims hide in that sentence and they have different walls.

**Real.** For *actions in repeated contexts*, learning once and keeping it is exact, and the cost law is
already measured in this tree: the crossover is the second or third request, cost is
`O(machines × adaptation) + O(requests)` (`INSTANT_LEARNING_IN_A_NEW_ENVIRONMENT_20261116_V1`). That
half of the claim survives every measurement this branch made.

**Not real.** For *coding*, the same mechanism cannot be the answer, and this round measured why. It is
not that the system fails to remember. It is that **the thing to remember is not decided by the site**.
A stored repair is a fact about one expression at one site; real fixes replace the site's expression
with material the site does not contain, so there is nothing to key the fact on, and the repeat rate that
would make a table pay is small (repeat-edit coverage ≈ 2.2% on published bug sets, carried measurement).

## What the four measurements say

**1. Writability — 241 real single-line edits, classified by what the fix needs from the site**

| verdict | edits | rate |
|---|---:|---:|
| single expression, every name already in scope | 153 | 63.5% |
| needs a form the enumerator cannot write | 22 | 9.1% |
| statement form, not an expression | 18 | 7.5% |
| two expressions, jointly addressable | 8 | 3.3% |
| too large | 5 | 2.1% |
| needs a name the site does not have | 1 | 0.4% |
| not code (comment or docstring) | 33 | 13.7% |

Of the 208 *code* edits, **77.4% are one expression the enumerator can already write.** The previous
round's conclusion — "the vocabulary is the bottleneck" — came from QuixBugs, where three sites could
not build the demanded value. On real code the vocabulary is not the wall: it is 9.1%, and adding
attribute material (`self.envvar` is not a name) already cut that from 35 edits to 22.

**2. Geometry — 136 real single-expression edits, where the fix lives relative to the site**

| relation | edits | rate |
|---|---:|---:|
| the site is **replaced** (neither contains the other) | 115 | 84.6% |
| the site **survives inside** the fix (a widening) | 17 | 12.5% |
| the fix **is inside** the site (a narrowing) | 4 | 2.9% |

This is the fact the whole design rests on, and it was never measured before: **the fix usually throws
the site's expression away.** `self.verbose` → `hasattr(self, 'batch_bar')`. `False` → `None`.
`ln.lstrip('Extracting')` → `ln[len('Extracting'):]`. `self.show_envvar` → `self.show_envvar and
self.envvar is not None` is the *minority* shape (12.5%).

**3. Reachability — the same 136 edits, where the fix sits in a pool built from the site's material**

The pool is site-rooted: every candidate is one edit applied to the site's own tree, ordered by
material distance (the site itself, then the block the site guards, then the function, then the class,
then the module). 400 candidates, no execution.

| geometry | measured | in the pool at 400 | rate |
|---|---:|---:|---:|
| the fix is inside the site | 4 | 2 | **50.0%** |
| the site survives inside the fix | 17 | 4 | **23.5%** |
| the site is replaced | 115 | 2 | **1.7%** |
| all | 136 | 8 | **5.9%** |

Median rank when the fix *is* in the pool: **22**. So there are two different failures and they are both
material failures, not grammar failures: for 94% of real edits the pool cannot *write* the fix, and for
the ones it can write it usually orders them late.

**4. End-to-end, on the project's own tests as the oracle**

A real fix commit is checked out at its parent, the post-fix test file is copied in, and the project's
suite fails — an oracle nobody in this tree wrote. On `click@1b0e19f505` (`src/click/core.py:2679`):

- the failing test is `test_missing_envvar`, and its failure message is
  `Error: Missing option '--foo' (env var: 'None').`
- the human's fix is `if self.show_envvar and self.envvar is not None:`
- the fix is at **rank 1** of the site-rooted pool, because `self.envvar` is printed **one line below**
  the guard, inside the block the guard controls
- running all 119 tests in that file against all 40 first candidates leaves **2 survivors**:
  `self.show_envvar and self.envvar` and `self.show_envvar and self.envvar is not None`
- the human's fix is one of them; the suite cannot separate them, and that is a fact about the oracle,
  not about the search — an empty-string envvar would separate them, and no test asks for it.

Across the **29** real commits that qualify the same loop is run unchanged, with the same budget and the
same oracle. The stages are the result:

| stage | commits | what it means |
|---|---:|---|
| `NO_ORACLE` | 10 | the post-fix tests pass on the parent: a tidy-up, not a behaviour fix |
| `MEASURED` | 7 | a real oracle, the pool ran |
| `FIX_LINE_DOES_NOT_PARSE` | 7 | the changed line is a fragment or a continuation, not one expression |
| `FIX_IS_NOT_A_SINGLE_EXPRESSION` | 5 | a structural or multi-site edit |

Of the 7 with a real oracle, **one is identified end-to-end** — the `click` widening above, whose material
is on the next line. One more has its fix in the full 400-candidate pool at **rank 396**, outside the
budget of 32 that was actually executed. The other five are not in the pool at all, and every one of
them is a replacement. That is the geometry measurement reproduced end-to-end on the project's own
tests: **the loop identifies the fix when the fix is a widening whose material is one line away, and fails
when the fix replaces the site.**

## The single bottleneck

> **Candidate material is chosen from the source text. The evidence that chooses it lives in the failing
> run's values. Everything else on the list is a smaller population than that one.**

Every other gap is bounded and measured: grammar 9.1%, statements 7.5%, search size — median rank 22
once a fix is writable. The gap that is neither bounded nor measured is that 84.6% of real fixes need
material the file does not nominate, and the only thing that nominates it is what actually went wrong
when the code ran: the value the site produced, the value the test wanted, and the message that carried
one to the other. In the `click` case the failure printed `'None'`, the guarded block printed
`self.envvar`, and the fix was the conjunction of those two facts. Nothing in the source's name table
says `self.envvar`; the failing output does.

That is also why *instant learning cannot be the answer to coding*: a stored fact has to be indexed by
something stable, and the stable thing here is not the site's text — it is the site's *behaviour under
the failing case*, which is exactly what the stored fact would have to contain.

## The smartest thing to do, stated as one build

Not a bigger grammar. Not a larger budget. Not more experience. **Invert the search: from the failing
value to the expression, instead of from the source text to the expression.**

1. Run the failing case with the site instrumented and record the value the site produced, its type,
   and the value the test demanded (both are already in the failure message or one probe away).
2. Nominate material by *provenance of the demanded value*, not by proximity of the text: every place
   in the failing run where a value of that type was produced, and every attribute or subscript of the
   objects that carried it — `self.envvar` is nominated because the block printed it, not because it is
   on line 2680.
3. Search only the expressions that can produce the demanded value from that material — for a
   replacement this is one hole, sized by the demanded value's type, not by the site's text.
4. Keep the oracle: the project's own tests. Cost stays `candidates × suite latency` (≈0.4 s per
   candidate on a 119-test file), so ordering is the whole game — and value provenance is an ordering.

This needs no weights, no external model, no corpus, and no parameters. It uses what the sandbox already
does — run the code — and it targets the 84.6% instead of the 12.5%.

**What would falsify it, stated before the build.** On the same 136 real single-expression edits, material
nominated by value provenance must put the human fix in the pool for **more than 5.9%** of them, and put
it within the first 40 candidates for more than the current 6 edits. If it does not beat proximity, the
thesis is wrong and the next round says so.

## What was not measured, so it is not claimed

- 62 of the 241 edits (25.7%) are code that spans lines; they are excluded from the geometry set, not
  explained away. The classifier resolves 18 of them at statement level and calls them statement-form.
- The 29-commit sweep is a population of *one-line source changes that also touched a test*, not of
  bugs. **10 of the 29 have no oracle at all** — the post-fix tests pass on the parent — which is the
  correct verdict for a behaviour-preserving tidy-up and is reported as `NO_ORACLE`, never as a success.
  A third of the population being invisible to the project's own tests is itself a fact about the
  population, not a defect of the run.
- Two survivors on the `click` bug is an identifiability result about that suite. It is not evidence
  that the search is right; it is evidence that the oracle is weaker than the fix.
