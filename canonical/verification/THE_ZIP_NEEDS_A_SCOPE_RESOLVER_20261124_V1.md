# The zip needs a scope resolver, not an error matcher

**2026-11-24.** Tool: `canonical/tools/the_zip_propagates_v1.py`. Outcome: **partial, and
I am recording it as a failure of my design, not a success.**

## What worked

Detection is solved and was never in doubt. On `httpx 7b19cd5f4b` (three functions moved
`_utils.py` → `_client.py`), static analysis named all six edges exactly — two imports and
two calls in `_client.py`, four internal calls in `_utils.py` — with no oracle and no
search.

Constructing the root move is also mechanical: cut three `def`s, append them to the target
module, drop the dangling imports. `import httpx` succeeded immediately.

## What failed

I built the propagation loop as an **error matcher**: read the pytest output, extract a
symbol name, find where it now lives, rewrite the importer. It converged in two hops on
every attempt and **every convergence was wrong**:

| hop | what the loop did | why it was wrong |
|---|---|---|
| 1 | `ImportError: cannot import name 'same_origin' from 'httpx._utils'` → redirected the importer | correct |
| 2 | `NameError: name 'URL' is not defined` → inserted `from ._urls import URL` into **`tests/conftest.py`** | the frame regex matched the *importer*, not the module that raised |
| 2' (earlier) | same failure → inserted the import above `from __future__ import annotations` | `SyntaxError: from __future__ imports must occur at the beginning` |
| 2'' (earlier) | same failure → `from .httpx._relocated import ...` | package path doubled |

And after "converging", the loop printed `0 FAILED` while the real suite could not even
import:

```
ImportError while loading conftest 'tests/conftest.py'
tests/conftest.py:1: from ._urls import URL
ModuleNotFoundError: No module named 'tests._urls'
```

**`0 FAILED` from a run that collected nothing is the same lie I have caught six times in
this repository**, this time inside my own tool: `SUMMARY` matched no line, `FAILED` lines
were zero because tests never ran, and the loop read that as success. It is not success.
The loop must treat "no summary line" as failure, and it does not.

## The design error, stated plainly

An error message tells you **what** is undefined. It does not tell you **where the
definition belongs**. Those are different questions, and I conflated them:

- Hop 1 works because the error *names the destination* (`from 'httpx._utils'` → the
  symbol's new home is discoverable and the rewrite site is the importer).
- Hop 2 does not, because `NameError` names only the symbol. Deciding that `URL` belongs
  in `_relocated.py` requires knowing that `_relocated.py` is where the moved code lives
  — i.e. **the scope of the root edit**, which the loop never tracked.

So the zip is not an error-matching loop. It is **a root edit plus its declared scope**:
the set of modules touched by the root edit, into which dependent names must be imported.
My loop had no scope because it had no model of the root edit beyond "a file changed".

That is the real finding, and it is more useful than a passing loop would have been: the
plan's Idea 3 describes the zipper as propagating "each new `TypeError`/`AttributeError`
at a caller as the next sub-goal". That framing is what fails here. The error picks the
*site*; only the root edit's scope can pick the *destination*.

## What I am not claiming

- Not that the zipper is impossible. Two of the three bugs above are ordinary
  implementation mistakes (frame selection, `__future__` placement) and one is a design
  error (no scope). A version that carries `(root_edit_scope, moved_symbols)` as explicit
  state and inserts dependencies into scope members would be a different program.
- Not that `7b19cd5f4b` needs a zipper at all. Both my earlier blind relocation and the
  human fix produced identical suite counts (28 failed / 1386 passed), and the fix's own
  17 tests passed on my tree. **That row has no propagation debt the suite can see.**
- Not a score. Nothing here adds a solved row. The corpus remains 22/45.

## The honest next step, and it is smaller

The zipper only matters where propagation debt is *observable*. Two ways to get there,
and the second is cheap:

1. A historical row where the root edit leaves a dangling reference the suite reports.
   `httpx 1805ee0d22` (7 source files, 155 lines, "Graceful upgrade path for 0.28") is the
   best remaining candidate — it is a deprecation path, so callers genuinely break.
2. **Construct the debt**: take a function with ≥3 callers the suite *executes*, move it,
   and require the loop to repair it while `tests/` goes from red back to the baseline.
   This tests the loop rather than a patch, and it is what I effectively did — except my
   move landed on a function whose callers the suite never runs, which is why the debt was
   invisible and the loop had nothing real to fix.

Doing (2) properly means choosing the moved function **by coverage**, not by convenience.
That is the correction, and it is measurable: pick the symbol with the most executed call
sites, move it, and see whether the red→green transition happens and stays.
