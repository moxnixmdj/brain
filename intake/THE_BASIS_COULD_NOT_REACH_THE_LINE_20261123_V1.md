# The basis could not reach the line, and then the verifier lied about it

**Date:** 2026-11-23 · **Branch:** `arena/eac85348-brain` · **Base:** `68bf0400`
**Authority:** NONE__PRODUCER_RUN_SANDBOX_MEASUREMENT · **Model calls:** 0 · **Weights:** unchanged
**Corpus:** 82 materialised trees from the repository's own mined fixes
(`pypa/packaging` 71, `hukkin/tomli` 15, `pallets/itsdangerous` 1)
**Tests:** 8 new (`canonical/tests/test_the_basis_could_not_reach_the_line_20261123_v1.py`),
66 passed with the neighbouring suites

---

## 0. Requirements confirmed, and the §2 boundary

Own weights, **zero model calls at runtime**, **zero knowledge house**, every parameter
derived, instant knowledge external, Elon's law, hardest-open tests, honesty separating
verified from failed, no questions, one branch, never stop at a milestone.

§2 stands as recorded: forbidden is *parameters as a lookup of memorised world facts* and any
runtime dependency on another model; allowed is an external, inspectable, editable store the
system computes with. This round adds no weight, saves nothing, and calls nothing. Every
number below is computed from the repository's own test output on a real host.

---

## 1. The missing number this round finally measured

Every document in this project argues about the bottleneck. **None reported what the repair
loop actually scores on the mined real-fix corpus.** Measured first, before any change:

| quantity | measured |
|---|---|
| bugs the loop could attempt | 17 |
| **solved** | **0** |
| candidates accepted | 0 |
| `OPEN__NO_STRICTLY_IMPROVING_CANDIDATE` | 13 |
| hard exceptions | 4 |

That is the baseline every earlier claim of progress sat on. It is zero, and it had never
been printed.

---

## 2. The bottleneck, measured rather than assumed

The basis generates candidates from an AST walk. The loop sorts specs near-a-failing-frame
first — **but then walks them in generation order**, and the renderer is applied inside the
loop. On real bugs:

| quantity | measured |
|---|---|
| candidates generated per bug | median **7,129** |
| first candidate within 3 lines of a traceback frame | median position **3,025** |
| default budget per file | 30–250 |
| bugs where the focus is reached within 30 | **0 / 39** |

The search spent its entire budget one hundred times over before reaching the line the
traceback named — and on `packaging` 46167dcd every one of the first twelve candidates was at
**line 4, deleting the module docstring**.

Two fixes followed, both minimal: render before ordering, and round-robin by **family** so a
defect class with 24 candidates is not starved by one with 2,596.

---

## 3. What a real fix actually is

Classified from the diff on all 87 fixes (381 hunks):

| shape | hunks |
|---|---|
| `TOKEN_COUNT_CHANGE` | **129** |
| `REPLACE_MULTILINE` | **108** |
| `INSERT` | 92 |
| `MULTI_TOKEN_SWAP` | 26 |
| `DELETE` | 14 |
| `NAME_SWAP` | **11** |

The basis can swap an operator, replace a constant, and insert an operand into a binop. It
could not express the single largest shape. Specifically, **20 fixes rewrite an attribute to
a bare name that is already in scope** and a further **22 add a bare name alone** — and a swap
can only ever write `a.x` → `a.y`, never `x`.

So one family was added: `NAME_SCOPE`, drawing its pool from the module's **own declared
fields**, never from the test's literals (a test literal would be the answer, and copying it
is leakage).

---

## 4. The verifier lied, four times

Chasing why the loop still accepted nothing turned up four defects that each issued a false
certificate. Each was measured, not guessed.

1. **A green exit with no tests scored perfect.** `_score` returned 0 on `returncode == 0`
   without asking whether anything ran. A candidate that destroyed collection reported
   *"0 failed, 0 passed"* — and the loop accepted it as a repair.
2. **A collection error was counted as one failure.** `ERROR collecting <module>` — the
   program cannot be imported, the worst state — scored **better** than the four real
   assertion failures it replaced. `4 -> 1` was logged as progress.
3. **A wrapped pytest exit was still an exit.** The in-process runner wraps a non-zero status
   in `RuntimeError: PYTEST_EXECUTION_FAILED:4` *and still prints a summary line*, so a usage
   error (rc=4, module never collected) reached the generic counter and scored 1.
4. **A stale bytecode cache replayed the old program.** The purge removed only each touched
   file's own `.pyc`; a candidate that made a *different* module stale measured as an
   improvement it did not have.

Each is now refused, and each is pinned by a test. The rule underneath all four:
**a verifier that can be satisfied by running nothing is not a verifier.**

---

## 5. What converts

With the four refusals in place, on the 82-fix corpus (10 eligible bugs, budget 45–110 s):

| | result |
|---|---|
| genuine repairs (`PASS__BOUNDED_MULTI_ROUND_REPAIR_FOUND`) | **1** |
| false acceptances after the fixes | **0** |
| false acceptances before the fixes | 3 |

The one repair is real and verified independently:

> **`pypa/packaging` 8efde605** — `f"{__spec__.parent}.errors"` → `f"{parent}.errors"`
> inside `__lazy_modules__`. `__spec__.parent` is the module's own name; the fix needs the
> `parent` variable. Buggy: **4 failed, 344 passed**. Repaired candidate: **0 failed,
> 348 passed** — four more tests pass, none is weakened, and the test file is never written.
> The `NAME_SCOPE` family found it; before this round the family did not exist and the loop
> scored 0/17.

Isolated (family only, small budget), `NAME_SCOPE` strictly improves **9 of 14** eligible
bugs, every one reaching zero failures. End-to-end through the unmodified loop it converts
**1 of 10**, because the family is competed against a much larger grammar inside one budget.

---

## 6. Honest limits

- **This is not a SWE-bench score.** Three Python repositories, 82 fixes, one host, one
  interpreter. No SWE-bench, no SWE-bench Pro, no Terminal-Bench. **§6 remains open.**
- **1 of 10 end-to-end is one bug.** The isolated 9/14 is a strong signal that the family is
  the right one; it is *not* a repair rate, because the search is not restricted to it.
- **The corpus is not fully reachable.** `prepare_corpus` sampled 82 of 87, and 4 fixes flip
  zero tests even at the fixed source (a foreign-install defect) — they are unfixable by
  construction and are excluded rather than counted as failures.
- **17 pre-existing test failures** in `test_measured_repair_portfolio_v1.py` (7) and
  neighbouring suites are **not** caused by this round: verified by stashing every change and
  reproducing them at the branch tip. They are recorded, not hidden, and not fixed here.
- **A library function still kills its caller.** On a bug whose source lives in a
  sub-package (`licenses/__init__.py`), the loop's in-process pytest harness exits the
  process instead of returning. Diagnostic only; not fixed this round.
- **`dropped_operand` remains a source of nonsense candidates** (wrapping names in
  multiplication). It no longer produces false certificates, but it still wastes budget.

---

## 7. What I will not claim

- Not that advanced SWE is solved, approached, or narrowed to a benchmark number.
- Not that the basis is now adequate: 129 of 381 hunks are `TOKEN_COUNT_CHANGE` and
  `NAME_SCOPE` addresses one corner of that.
- Not that `1/10` is a rate. It is one verified repair where the previous honest number was
  zero, and the difference between those two things is the point of the round.

---

## 8. Next bottleneck, named

**The budget is now the binding constraint, not the grammar.** `NAME_SCOPE` converts 9 of 14
in isolation and 1 of 10 inside the full grammar, and the loop still treats every family as
interchangeable. The next round should ask a scheduling question — which family deserves the
next candidate given what the last one taught — rather than adding a seventh family to a
grammar that already generates 7,129 candidates per bug. Anything that adds candidates
without adding information will repeat round 21's measured result: **more seeds, one part
lost, zero gained.**

---

## Reproduce

```sh
python3 -c "import sys,pathlib;sys.path.insert(0,'.');\
from canonical.swe_kernel import structural_rewrite_induction_v1 as S;\
S.prepare_corpus(pathlib.Path('canonical/corpus/real_fix_commits_20261116_V1.json'),\
                 pathlib.Path('/tmp/hist'), pathlib.Path('/tmp/histwork'), limit=200)"
python3 -m pytest canonical/tests/test_the_basis_could_not_reach_the_line_20261123_v1.py -q
```
