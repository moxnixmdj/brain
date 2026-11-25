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

## Third case: a signature change, and the boundary of "observable debt"

Moving a function tests one propagation shape. A real fix more often changes a
**signature**. Both were tested:

| root edit | suite immediately after | why |
|---|---|---|
| add `strict: bool = True` (optional) | **28 failed, 1386 passed — unchanged** | backward-compatible: existing calls stay valid |
| add `strict: bool` (required) | **34 failed, 1380 passed** | every existing call is now a `TypeError` |

That pair is worth keeping. **A backward-compatible change creates no observable debt at
all**, and no propagation loop — however clever — has anything to propagate. The debt
exists only when the old form stops working.

For the required-parameter case the failure is unusually precise:

```
httpx/_models.py:135: TypeError: to_bytes_or_str() missing 1 required positional
                      argument: 'strict'
```

Callee, missing parameter, file and line, all named. A SIGNATURE hop was added: append
`{param}={value}` at each call site, taking the parameter's own default when it has one.

| stage | result |
|---|---|
| after the signature change | 34 failed, 1380 passed |
| hop 1 | `to_bytes_or_str(strict=True)` at 1 file |
| hop 2 | **28 failed, 1386 passed** — baseline |

Stable on re-run. Third hop type, same shape: one precise failure, one mechanical repair,
green.

## Four hop types, each validated

| hop | triggered by | repair | validated |
|---|---|---|---|
| IMPORT | `ImportError: cannot import name 'X' from 'M'` | redirect symbol to its new home | yes, 2 cases |
| DEPENDENCY | `NameError` in the new module | import the missing name into it | yes, 1 case |
| SIGNATURE | `missing 1 required positional argument` | supply the parameter at each call | yes, 1 case |
| (per-symbol granularity) | two-symbol thrash over 8 hops | rewrite per symbol, not per line | yes, 1 case |

## Four bugs in my own loop, all found by it failing

Recorded because each is the kind a real patcher would hit:

1. `args` rebound to an AST node inside the loop, clobbering the argparse namespace —
   `'arguments' object has no attribute 'seconds'` on iteration 2.
2. The signature hop matched `def to_bytes_or_str(...)` and appended a keyword to the
   **definition**, producing `strict: bool, strict=True` and a duplicate-argument
   `SyntaxError`.
3. `--tb=line` prints `path:N: Error` with no frame text, so the dependency hop's frame
   regex found nothing and it self-imported the symbol into its own module.
4. A run with no summary line was read as convergence (now return code 3).

Considered together with the three design corrections in the section above, that is seven
distinct failures before the loop did anything correct. The tool is small; the failure
modes were not.
