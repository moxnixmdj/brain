# The zip works when the debt is visible — and only then

**2026-11-24.** Tool: `canonical/tools/the_zip_propagates_v1.py`.
Supersedes the failure recorded in `THE_ZIP_NEEDS_A_SCOPE_RESOLVER`.

## The correction that made it work

The previous attempt failed for a reason I had written down and then ignored: it moved
`same_origin`, whose call sites **the suite never executes**. Both my blind relocation and
the human fix produced identical counts (28 failed / 1386 passed), so there was no
observable propagation debt and nothing for a loop to repair. The loop "converged" while
corrupting `tests/conftest.py`, because a run that collects nothing prints no summary
line, and I read `0 FAILED` as success.

Two changes fixed it:

1. **Choose the moved symbol by coverage, not by convenience.** A trace hook counted
   executed functions during the suite. `_models.py:_normalize_header_key` executes
   **1891 times**; its four call sites are inside the fixture paths every header test
   walks.
2. **Destination comes from the dangling reference, not from the definition.** A
   `NameError` names only the symbol. Where the import belongs is the file that still
   *references* it — the innermost traceback frame that is not the module that already
   defines it. Without that rule the loop performed a self-import
   (`import _normalize_header_key into _hdr.py from ._hdr`) and span for eight hops.

## The experiment

Move `_normalize_header_key` out of `httpx/_models.py` into a new module
`httpx/_hdr.py`, leaving both references in `_models.py` dangling. Run the loop.

| stage | result |
|---|---|
| untouched parent `b47d94c` | **28 failed, 1386 passed, 1 skipped** |
| after the blind move | **586 failed, 828 passed** |
| hop 1 | `NameError` at `_models.py:150` names the symbol |
| hop 1 repair | `from ._hdr import _normalize_header_key` inserted into `_models.py` |
| hop 2 | **28 failed, 1386 passed, 1 skipped** — baseline exactly |

Two runs after convergence: identical, `28 failed, 1386 passed, 1 skipped`. The moved
function is still the real implementation (verified by reading `_hdr.py`), not a stub.

**586 failures → one inserted import → baseline restored.** The hop was derived from the
error text plus a static definition lookup. No search, no model call, no human edit.

## What is actually proven, and it is narrow

Proven:
- Cross-file relocation of a live function is constructible mechanically.
- The dangling reference is **reported with file and line**, and that suffices to place
  a repair.
- A single error-driven hop can restore a 586-failure suite to baseline.
- The loop now refuses to call a summary-less run convergence (it returns 3).

Not proven:
- **That this generalises to real multi-file patches.** This was a *synthetic* move I
  constructed, not a historical fix. It shows the loop closes debt that a single missing
  import creates. Real SWE-bench Pro fixes change a representation and repair several
  call sites with *different* repairs — that is a different, harder problem.
- That it handles more than one hop of dependency. Here one import sufficed.
- Anything about the 45-commit corpus: still 22/45, unchanged. Nothing here adds a solved
  row.

## Why this matters anyway

The plan's Idea 3 is the only pillar aimed at Wall 3, and it had **zero rows and zero
evidence** in this repository — 0 of 45 corpus commits touch more than one source file.
The wall was unexamined. It is now examined on one constructed case with a measured
result, and the mechanism it needs is stated precisely:

> the error picks the **site**; the root edit's **scope** picks the destination; and the
> debt must be **executed** or no loop can see it.

That last clause is the same law that has governed every null in this project —
`62411c16`'s aliasing bug, the docstring relations, the metamorphic witnesses, the store
ablations. A green suite does not constrain what it never runs. Here it is finally
demonstrated in the *positive* direction: make the suite run it, and one mechanical hop
repairs the whole thing.

## Second case: two importers, one hop, and the per-symbol correction

Moving `_normalize_header_key` had all its call sites in a single file, so the first
success did not test the interesting case. `to_str` does:

```
defined      httpx/_utils.py:115          executed 386 times
imported by  httpx/_auth.py:13            "from ._utils import to_bytes, to_str, unquote"
             httpx/_models.py:49          "from ._utils import to_bytes_or_str, to_str"
```

**Two importers, each on a line that also imports symbols which must NOT move.**

First run of the loop against this: eight hops, no convergence, thrashing between
`to_str -> ._strconv` and `to_bytes_or_str -> ._utils`. The cause was a single mistake in
my rewriter, and it is worth stating because it is the kind a real patcher would make:

> a line-level move drags every symbol on the line. Repairing `to_str` also relocated
> `to_bytes_or_str`, which never moved, so the next hop relocated it back.

The repair must be **per symbol**, not per import statement. After rewriting at symbol
granularity:

| stage | result |
|---|---|
| after the blind move | `ImportError: cannot import name 'to_str' from 'httpx._utils'` |
| hop 1 | `to_str -> ._strconv`, **2 files** |
| hop 2 | **28 failed, 1386 passed, 1 skipped** — baseline exactly |

Final state, verified by reading both files:

```
_auth.py:13    from ._utils import to_bytes, unquote      <- unchanged symbols stay
               from ._strconv import to_str               <- only the moved one moves
_models.py:49  from ._utils import to_bytes_or_str        <- unchanged symbols stay
               from ._strconv import to_str               <- only the moved one moves
```

That is the correct minimal diff, produced without knowing anything about the fix.

## The three rules the loop needed, all learned from failures

1. **Target selection**: move the symbol with the most *executed* call sites. Otherwise
   the debt is invisible (proven: the human commit moved three functions that execute
   zero times).
2. **Destination**: the file holding the dangling reference, never the file that defines
   the symbol (otherwise: self-import loop, observed over 8 hops).
3. **Granularity**: per symbol, not per import statement (otherwise: two-symbol thrash,
   observed over 8 hops).

Each of the three was found by watching the loop fail in a specific, diagnosable way. None
was guessed.
