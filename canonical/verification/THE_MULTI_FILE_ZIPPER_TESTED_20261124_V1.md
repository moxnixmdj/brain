# The multi-file zipper, tested on the first real multi-file row

**2026-11-24.** Source: `httpx` full clone (1527 commits, `--depth 400` fetches full
blobs so history walks work locally). This closes the gap recorded in
`THE_CORPUS_IS_ONE_LINE_WIDE`: 0 of 45 corpus commits touch more than one source file,
so the plan's Idea 3 had no row on which it could run.

## Finding the row

Mined `httpx` for commits touching **≥2 source files and ≥1 test file**:

```
httpx: 9 commits in 1200
  8e36f2bc68  src=14  lines=533  Introduce new SSLContext API & escalate deprecations
  1805ee0d22  src= 7  lines=155  Graceful upgrade path for 0.28
  e9cabc8e1d  src= 4  lines= 75  lazy certifi/httpcore loading
  7b19cd5f4b  src= 2  lines= 92  Move utility functions from _utils.py to _client.py
  ...
```

**Nine real multi-file source fixes exist.** My 45-commit corpus has zero. That gap was a
property of the mining filter, and it is now measured rather than suspected.

Two of the nine are not what they appear, and I checked rather than counted:
`47f4a96ffa` "2 source files" is `__version__.py` (a version bump) plus one real change;
`8e36f2bc68` "14 files" is a genuine API replacement but 533 lines across an entire
release, far beyond a single task.

`7b19cd5f4b` is the ideal propagation test: **three functions removed from `_utils.py`,
re-added in `_client.py`**, with `_client.py` importing two of them from the old home.

## Stage 1 — detection (static, no oracle needed)

```
names to relocate: port_or_default, same_origin, is_https_redirect
  all three defined in httpx/_utils.py

reference sites that would break if the definition moved:
  httpx/_client.py  imports=[('is_https_redirect','_utils'), ('same_origin','_utils')]
                    calls=[('same_origin',524), ('is_https_redirect',525)]
  httpx/_utils.py   calls=[('port_or_default',43), x2 at 43, 56, 58]
```

Exact. It found the two import edges in `_client.py` and all four internal call sites in
`_utils.py` — precisely the edges a human had to repair. **Detection is solved for this
row and cost no oracle.**

## Stage 2 — the repair, applied blind

Root edit performed mechanically: cut the three `def`s from `_utils.py`, append to
`_client.py`, drop the now-dangling imports. 26 lines moved. `import httpx` succeeded
immediately, so no import-order hop was needed.

Then the test suite, on three trees:

| tree | commit | result |
|---|---|---|
| `/tmp/h0` parent, untouched | `b47d94c` | 28 failed, 1386 passed, 1 skipped |
| `/tmp/h1` the human fix | `7b19cd5` | 28 failed, 1386 passed, 1 skipped |
| `/tmp/h2` my blind move | `b47d94c`+move | 28 failed, **1386** passed, 1 skipped |

**Identical counts on all three.** The blind relocation introduced zero test-visible
regressions, and matched the human fix's outcome exactly.

And the fix's own new tests:

```
git show 7b19cd5f4b:tests/client/test_headers.py  ->  run on my tree
17 passed
```

The tests the maintainers added *for this change* pass 17/17 against my blind move.

## What this does and does not prove

**It does not prove the zipper works.** There was nothing to zip. The zero-regression
result has a deflationary explanation I have to state plainly: I cut the defs **with the
code around them**, so the internal calls in `_utils.py`'s remaining functions went away
with them. The suite never noticed. That means **this project's own tests do not cover
those call sites** — the propagation debt was invisible, not absent. Had I left dangling
references, `httpx` would have imported and the suite might still have gone green.

So the honest reading is narrower and more useful:

> Cross-file relocation on this row is achievable mechanically, and *the oracle cannot
> see the difference between a correct relocation and a broken one at call sites the
> suite does not exercise.*

That is a second, independent sighting of the same limit I found on `62411c16` at the
start of this work: a suite that is green does not constrain the parts it never runs.

## Why the zipper is still untested, and what would test it

A real zipper test needs a row where the root edit **leaves a dangling reference that the
suite does report**. Candidates, in order of how cleanly they would settle it:

1. `1805ee0d22` "Graceful upgrade path for 0.28", 7 source files, 155 lines — an API
   change with real callers.
2. `8e36f2bc68` — 14 files, but a whole-release API replacement; the oracle would be the
   release's own suite, and the task is larger than any single issue.
3. A synthetic probe: take any function with ≥3 in-repo callers that the suite executes,
   rename it, and check that the failures name exactly those callers. That tests the
   *loop* rather than a historical patch, and costs minutes.

Option 3 is the cheapest thing that can falsify the zipper, and it does not depend on
when I find a suitable historical row.

## Ledger

| claim | status |
|---|---|
| corpus has 0 multi-file source fixes | **verified**, still true |
| a real multi-file repo has them | **verified**, 9 in 1200 httpx commits |
| cross-file move is mechanically constructible | **verified**, 3 defs, 26 lines, imports clean |
| the zipper's detection stage | **verified**, exact on 6 edges |
| the zipper's repair stage | **untested** — no dangling reference survived |
| suite detects broken propagation | **falsified on this row** — 1386 passed while 4 call sites vanished |
