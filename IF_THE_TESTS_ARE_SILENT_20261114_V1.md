# If the tests are silent, what else is the oracle?

**Date:** 2026-11-14 · **Branch:** `arena/98e3c624-brain` · **Authority:** NONE
**Record:** `canonical/verification/DIFFERENTIAL_WITNESS_REAL_COMMITS_20261114_V1.json`
**Module:** `canonical/swe_kernel/differential_witness_v1.py` · **Tests:** `canonical/tests/test_differential_witness_v1.py`

---

## 1. The question this round had to answer

The previous round ended on a negative number, and it was a good one: **19 of 29 real merged changes
could be reverted to their pre-fix source and the project's own suite still passed.** stem 0 of 6,
packaging 4 of 9, more-itertools 6 of 14.

A negative number is a diagnosis, not a capability. It leaves one question:

> If the tests are silent, what else can serve as the oracle?

The answer does not need a model, a test suite, or a specification. It needs the two versions of the
program. *Shadow of a Doubt* (ICSE 2016) runs old and new in one symbolic execution instance, with the
old shadowing the new, and emits an input every time the two disagree. DiffTestGen (arXiv 2607.16024,
Jul 2026) reports that this exposes behavioural differences in 78.2% of pull requests and that "the
gain comes from directed access information and feedback, not token budget". DiffCodeGen (arXiv
2605.20473) does it with coverage-guided fuzzing "without requiring any existing tests or large
language models".

This round builds the cheap version of that mechanism and points it at the same 57 commits.

---

## 2. What it does

For a pair of versions of one file:

1. **Compare by AST, not by diff.** Every sub-expression of every function is keyed by structural
   path and dumped. A rename, a reformat, a docstring or an annotation change produces no entry —
   correctly. Module-level bindings are compared too, because `re.compile("...{49}")` becoming
   `"...{40,49}"` is an ordinary change site that a function-only comparison calls "nothing changed".
2. **Build inputs from four axes.** The literals the change touches on either side (including ones it
   *deleted* — a removed literal is the strongest hint about the input that separates the versions);
   a fixed value grid; repetition shapes sized around limits the source states (`"("*201 + "a" +
   ")"*201` for a cap at 200); and strings assembled from the change's own literals in the shapes
   grammar uses (`"===1.0,>= 1"`).
3. **Reach private functions through public entry points.** `_parse_marker(tokenizer, depth)` takes a
   Tokenizer; plain values raise identically on both sides, so no input can ever diverge. A name-level
   call graph finds the public function that reaches it, and `parse_marker(source: str)` is an input a
   user would actually write.
4. **Run the two versions in two separate interpreters** over the same candidates. The verdict is the
   first input whose returned value or raised exception differs.

Nothing here reaches for a model. Zero calls, zero network, zero cost.

---

## 3. The result

| verdict | commits |
|---|---|
| `NO_WITNESS_FOUND_ON_GRID` | 32 |
| `WITNESS` | 12 |
| `NO_EXPRESSION_CHANGED` | 7 |
| `UNREACHABLE_PARAMETERS` | 3 |
| `IMPORT_FAILED` | 3 |

16 witnesses were reported and **all 16 were confirmed by an independent script** that never imports
the tool, running each input in two fresh interpreters.

But confirmation is not usefulness, and the honest headline is smaller than 16:

| what the witness actually is | count |
|---|---|
| `PUBLIC_INPUT_BEHAVIOUR` — an input a user could write, on a function a user calls | **6** |
| `PRIVATE_SIGNATURE_OR_TYPEERROR` — differs only because the signature changed | 3 |
| `VERSION_STRING_ONLY` — `__version__` was bumped | 2 |
| `MODULE_CONSTANT_LITERAL` — a module constant is visible to a caller | 2 |
| `TYPE_ALIAS_OR_ANNOTATION` — `MarkerAtom` changed meaning | 2 |
| `LAZY_IMPORT_SET` — an import set changed | 1 |

A witness can be **true and worthless**. `_parse_marker(0, "ABCDEFG")` differs only because the
function gained a parameter. `__version__` differs because the commit bumped it. An early version of
this tool "found" a witness in a docs-only commit because `set_partitions` returns a generator and
`repr` of a generator contains its memory address.

**The unit that survives is six.** Four of the six are on commits that last round's revert ledger
measured as *not noticed by the project's own suite*:

- `packaging` `4d7875f8` · `parse_marker("("*201 + "a" + ")"*201)` · `RecursionError` →
  `ParserSyntaxError: nested more than 200 levels deep`
- `packaging` `5a7d3386` · `parse_requirement("===1")` · token returned as a raw string →
  `SpecifierSet("===1")`
- `more-itertools` `98562cab` · `tail(-1, "ABCDEFG")` · `ValueError` → `()`
- `more-itertools` `fbd55137` · `chunked_even(0, "ABCDEFG")` · `TypeError` about an int →
  `TypeError` about the string comparison

The sentence that survives both rounds:

> For at least four real merged fixes, there exists a specific input — generated with no model and no
> tests — on which the pre-fix and post-fix programs produce different results, and the projects' own
> suites did not notice when the fix was removed.

The sentence that does **not** survive: "those fixes have no tests". The measured fact is narrower.
Those fixes can be reverted green, and the divergence can be found mechanically.

---

## 4. Four instrument errors that would each have produced a publishable false number

This is the part worth keeping. Every one of these was found only by cross-checking, and every one
would have shipped as a result.

1. **A comparison of a version against itself.** Both snapshots were on `sys.path`, so the "before"
   run imported the "after" file. That answers *refactor* — the most confidently wrong verdict
   available — on a real fix. Fixed with `MISLOADED_SNAPSHOT`: a module that did not come from the
   snapshot that was asked for is never measured.
2. **A runner that crashed at candidate 101 of 2,000** and was read as "no witness". Fixed with
   `EXECUTION_INCOMPLETE`, which counts results and refuses to answer when a side dies.
3. **A generator's memory address** made almost every candidate "differ". Fixed by materialising lazy
   results and by refusing address-bearing values — with the guard looking for both `0x…` and the
   renderer's own `<Type at an address>` placeholder, after the first version of the guard checked a
   string that no longer contained an address.
4. **`tail(<docstring>, 0)`.** Literals were harvested by re-parsing `ast.dump` *text*, which turns
   `Name(id="size")` into the string `"size"` and puts prose and identifiers into the argument grid.
   Fixed by collecting real AST constants and excluding prose by shape.

The pattern: **every failure was silent**. None raised. Each produced a plausible verdict. That is why
the module now ships `self_check()`, which pins seven of these properties on hand-written pairs and
costs nothing to run.

---

## 5. What the tests are for

`canonical/tests/test_differential_witness_v1.py` has 8 tests, and they were mutation-tested rather
than trusted:

- inverting the witness-strength ranking → caught
- neutering the address guard → caught (and this mutation exposed the broken guard above)
- removing the docstring exclusion → **not** caught
- replacing the content renderer with `repr` → **not** caught
- restoring the prose filter through the public path → **not** caught

The last two survive because the prose and address guards are belt-and-braces: the grid's own values
never contain a generator, so removing the renderer changes no observable outcome in the cases the
tests exercise. That is stated rather than papered over. A mutation that survives means the guard is
defence in depth, not that the test is useless — but it does mean the reason a witness was rejected
is the value rank, not the renderer, in those cases.

---

## 6. Where the ceiling actually is

32 of 57 commits produced no witness. Some of that is honest — most `perf(...)` commits really are
behaviour-preserving, and the tool is *designed* to say so. Some of it is the search being too poor:
the grid is literals, repetitions and assemblies, and a fix that needs a URL from the user, a socket,
or a parser state machine will not be found by any of them.

The tool reports its own bound (`bounded_search`) so a reader can tell which case they are looking at.
**`NO_WITNESS_FOUND_ON_GRID` is never a proof of equivalence.**

---

## 7. Killed this round, with reasons

- **Asking a model whether the patch is correct.** Not independent, and forbidden — no external model
  is reachable in this work, by design.
- **Widening the grid until a witness appears.** That fits the measurement to the claim. The grid
  axes were added because they are *structurally implied by the source* (a stated limit implies a
  repetition; a separator grammar implies an assembled string), not because a number needed to move.
- **Treating `NO_WITNESS` as equivalence.** It is a bounded search and it says so.
- **Symbolic execution / SMT.** Correct, and far too expensive to run before a lesson is admitted. The
  literal-boundary grid is the cheap shadow of the same idea.

---

## 8. Relationship to the previous claim

The prior record stands unchanged: 19 of 29 revertable, spread 0% / 44% / 46%, clause 3 (`the check can
see the taught change`) **FALSE**, clause 5 **NOT MEASURED**.

This round does not replace it. It answers the question the negative number left open, and it makes
one of the prior record's own caveats concrete: the "unprotected" count overstates risk where the
change is a behaviour-preserving refactor, and this tool is what separates "here are the tests nobody
wrote" from "there is nothing to test here" — imperfectly, bounded, and now with four proven instances
on the first side of that line.
