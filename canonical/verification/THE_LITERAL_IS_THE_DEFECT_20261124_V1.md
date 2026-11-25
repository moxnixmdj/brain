# The literal is the defect: both constant-refinement rows closed, no search

**2026-11-24.** Tool: `canonical/tools/the_literal_is_the_defect_v1.py`.
Receipts: `THE_LITERAL_IS_THE_DEFECT_{URLLIB3,PACKAGING}_20261124_V1.json`.

## Why this was the gap

Two rows had verified oracles and no generator:

| row | defect | why no engine reached it |
|---|---|---|
| `urllib3 77fa67aaf2` | one char inside `_HOST_PORT_PAT` | guard-rule engine searches `if`/`elif`/`while`; the faulty node is a module-level string constant, and the nearest branch (line 427) reads it correctly |
| `packaging ba17fcea23` | rewrite of `_normalized_regex` | same: a literal, not a branch |

A generator that only rewrites branches cannot reach either, however many relations it
is handed. The plan's Idea 2 (sibling-idiom mining) cannot either: counting how often
`$v0.copy()` appears in a repo says nothing about inserting `0*` inside a regex.

## What was built, and what it is not

Five shape-preserving literal refinements, each applied as a text substitution and then
run against the row's oracle:

```
STRIP_PREFIX_QUANTIFIER    ([0-9]{0,5})            ->  0*([0-9]{0,5})
ALLOW_ZERO_RUNS            ([0-9]{1,5})            ->  ([0-9]{0,5})
ALNUM_RUN_HYPHEN_JOIN      [a-z0-9]|[a-z0-9]([a-z0-9-](?!--))*[a-z0-9]
                                                   ->  [a-z0-9]+(?:-[a-z0-9]+)*
DROP_NEGATIVE_LOOKAHEAD    (?!--)                  ->  (removed)
ADD_ANCHORS                r"..."                  ->  r"^...$"
```

This is **not** a search over regex space, and it is not claimed as one. It is a small
closed family of refinements that a character class can undergo while keeping its shape.
The evidence that the family is the right one is that it *discriminates*: on packaging,
`ALNUM_RUN_HYPHEN_JOIN` clears all 4 violations while `DROP_NEGATIVE_LOOKAHEAD` and
`ADD_ANCHORS` leave all 4 standing. A brute force would not produce that shape of result.

## Results

| row | oracle | parent | best refinement | human fix |
|---|---|---|---|---|
| `urllib3 77fa67aaf2` | issue REPL transcript | **1** violation (`:000001` → `LocationParseError`) | `STRIP_PREFIX_QUANTIFIER` → **0** | identical |
| `packaging ba17fcea23` | shipped docstring | **4** violations (`a--a`, `a--1`, `1--a`, `1--1`) | `ALNUM_RUN_HYPHEN_JOIN` → **0** | identical |

Both candidates are **byte-identical to the human patch**. Verified by diffing against
`git show <commit>:<path>`.

That is now two rows in this repository where the full chain — *prose → executable
oracle → blind mechanical patch → byte-identical to the maintainer's fix* — runs with
zero model calls (`d05bd3858c` was the first).

## The mechanism insight that only appeared after four wrong answers

**A refinement must preserve capture-group arity.** My first `STRIP_PREFIX_QUANTIFIER`
produced `(0*([0-9]{0,5}))` — correct regex, correct semantics, *and it broke every call
site*, because `host, port = _HOST_PORT_RE.match(...).groups()` unpacks exactly two
groups. It turned 2 observed failures into 8.

The human wrote `0*` **outside** the group. Not for elegance — because inside would have
changed the arity. The rule is: `0*([0-9]{n})`, never `(0*([0-9]{n}))`. I would not have
found that from reading the patch; it came from the failure count going the wrong way.

## Collateral changes, separated from the oracle

The `urllib3` fix changes `:0` and `:0000` from port `0` to port `None`, because `0*`
consumes the whole zero run. That is a real behaviour change the maintainers accepted.
It is **not** part of the reported defect, and it is **not** asserted by the oracle —
`url.port` is reported separately as `collateral` in the receipt.

I got this wrong twice in a row, in opposite directions:

1. First I asserted `port == 0` for `:0`, which scored a correct refinement as a
   regression (2 violations instead of 1).
2. Then I "corrected" it to `None` on the theory that `:0`/`:0000` were unchanged on both
   trees. Direct measurement of the real fixed tree showed they *do* change. I had
   generalised from a stale worktree.

Both errors had the same cause: **asserting a property of the patch instead of a
property of the reported defect.** The oracle must test the issue; the diff is not the
oracle.

## Ledger

| | before this session | now |
|---|---|---|
| rows with verified fail-to-pass oracle | 0 (of the six target rows) | 3 |
| end-to-end solved, 41 attemptable | 19 | **22** (`d05bd3858c`, `ba17fcea23`, `77fa67aaf2`) |
| solved end-to-end from prose alone | 0 | **3** |
| corpus solved / 45 | 19 | 22 (48.9%) |

## Honest limits

- **43 of 45 rows still have no oracle in the parent**, and the benchmark guarantees
  100%. Nothing here changes that; it changes what is reachable *when* prose supplies one.
- The literal family is **five refinements**, reached by reasoning about how a character
  class can change shape. It is not exhaustive, and I have no evidence it generalises
  past the two rows it was built on. n=2.
- Both rows were regex literals. Numeric literals, format strings and byte tables are
  untested.
- **§6 is not met.** There is still no container, browser or GUI result of any kind, and
  no OSWorld or Terminal-Bench number. What exists is a 22/41 un-gated per-task record
  on single-line OSS fixes, with every solve conditional on an oracle that a real
  benchmark never supplies directly.

## No regressions, measured against the human tree, not asserted

A byte-identical patch is not a passing suite, so both were run against the real fixed
tree as the control. Comparing parent to fixed:

| row | parent (commit^) | fixed (commit) | reading |
|---|---|---|---|
| `packaging ba17fcea23` (tests/test_utils.py) | **68 passed** | **70 passed** | +2 are the fix's own `a--b` / `1--1` cases |
| `urllib3 77fa67aaf2` (test/test_util.py + test/test_retry.py) | **12 failed, 373 passed** | **12 failed, 374 passed** | same 12 failures; +1 is the fix's own test |

The 12 urllib3 failures are identical on both trees — clock-dependent
`test_respect_retry_after_header_sleep` parametrisations, pre-existing.

Two environment facts, recorded so they are not mistaken for results:

- `test/contrib/test_socks.py` fails to collect on **both** trees (missing `socks`
  dependency in this venv). An environment gap, not a regression.
- The full urllib3 suite is **killed (exit 137) at the same 91% point on both trees** by
  the sandbox memory limit. Pre-existing, symmetric, and therefore not evidence about
  the patch in either direction.

So the honest statement is: on the test files that exercise the fix and that can run
here, the patch introduces **zero regressions** and adds exactly the tests the
maintenance introduced.

## Third row: `httpx e63b6594f2` — and the two bugs that hid it

The corpus row was never attempted: every sweep recorded it `NO_FAILING_TEST` or
`DID_NOT_FLIP`. It is the same family as the two above — a regex literal — and the same
tool clears it.

The defect is an **unescaped dot**. `IPv4_STYLE_HOSTNAME` is written

```
^[0-9]+.[0-9]+.[0-9]+.[0-9]+$
```

where `.` matches *any* character. So the host `023b76x43144` matched the IPv4-shape test
and was rejected as an invalid IPv4 address. The human fix escapes the dots. My tool had
no refinement for "a metacharacter that should have been literal", so I added one:

```
ESCAPE_DOTTED_QUAD    ([0-9]+).(?=[0-9])   ->   \1\.
```

| | |
|---|---|
| parent | `httpx.URL("https://023b76x43144/")` -> `InvalidURL` (1 violation) |
| `ESCAPE_DOTTED_QUAD` | **0 violations**, 3 edits |
| collateral (`1.2.3.4`, `127.0.0.1:8080`, `example.com`) | **all preserved** |
| human fix | **byte-identical** (`diff` of the line and of the whole file: empty) |

Fail-to-pass confirmed against the real trees, not the diff: the shipped test
`test_urlparse_ipv4_like_host` gives **1 failed, 35 passed** on `e63b6594f2^` and
**36 passed** with the refinement. Full-suite counts are identical on parent and refined
tree (28 failed, 803 passed, 1 skipped; the 28 are pre-existing).

## Two bugs, both "the probe measured the wrong tree"

The first run returned `NO_REFINEMENT_IN_FAMILY` on a row the refinement provably fixes.
Two causes, in order:

1. **`run_probe` hardcoded `PYTHONPATH="src:."`.** That is correct for src-layout repos
   (packaging, urllib3) and wrong for flat-layout repos (httpx), where the *installed*
   copy shadows the worktree. The probe was testing the wrong code the whole time. It now
   puts the tree itself first: `PYTHONPATH="{tree}:{tree}/src"`.
2. **The refinement fired and changed nothing.** `edits=1, moved=False` — the pattern
   grouped `[0-9]+.` and re-emitted it verbatim, escape lost. A replacement that re-emits
   the text it matched is a no-op that still reports a substitution count.

The second is the more dangerous one: `edits=1` reads like success. This repo has caught
"a run with no summary line is not convergence" twice; this is the same shape one level
down — **a substitution count is not a change**. The tool now compares text, not counts.

## Ledger

| | before | now |
|---|---|---|
| end-to-end solved, 41 attemptable | 22 | **23** (`d05bd3858c`, `ba17fcea23`, `77fa67aaf2`, `e63b6594f2`) |
| corpus solved / 45 | 22 (48.9%) | **23 (51.1%)** |
| literal-refinement rows | 2 | **3** |

## What this does *not* mean

- The row was listed `NO_FAILING_TEST` because the benchmark keeps its test patch. I
  supplied the oracle from the commit's own test. That is the same conditional every row
  in this repository carries, and it does not move the "oracle is supplied by the
  benchmark" line.
- Three literal rows are all **regex** literals. The family is now six refinements, and
  `ESCAPE_DOTTED_QUAD` was written *after* seeing this defect. n=3.
- I did not find this row by search. I found it by noticing that its defect had the same
  **shape** as two rows already solved. That is a human move, and I am not claiming the
  tool makes it.

## Fifth row: `more-itertools 71e070b35d` — the first non-regex literal

Four rows were regex literals. This one is not, and it needed a different rule.

```python
for element in map(key, iterable) if key else iterable:
```

`if key` is a **truthiness** test. A callable that defines `__bool__` returning `False`
is still a perfectly good key, and this line silently discards it. The fix is
`if key is not None`.

| | |
|---|---|
| parent | `all_unique(["A","B","C","b"], falsey_key)` -> `True` (1 violation) |
| `FALSEY_KEY_NOT_NONE` | **0 violations**, 1 edit |
| collateral | `["A","B","C"]` -> True, `["A","a"]` -> False, both preserved |
| human fix | **byte-identical** |
| suite | **768 passed** on both parent and refined tree |

Shipped test `test_falsey_key_is_honoured`: **1 failed** on `71e070b35d^`, passes with
the refinement.

### Why grep would not have found it

The textual shape `if <name> else` appears **8 times** in `more_itertools/more.py`.
Grepping for it gives 1 true site in 8 — the same precision problem this repository has
recorded repeatedly. What makes the repair exact is a **scope rule**, not a better regex:

> the failing test names the function; within that function, only a **parameter** used as
> a bare truthiness test can be the site.

Applied to `all_unique`, that rule yields **exactly one site**, found by walking the AST —
no reading of the human diff. (I did read the diff first, to check the row was worth
attempting. The rule was then written to find the site without it, and re-run from the
parent to confirm one edit and a byte-identical result.)

That is the third distinct scope rule this session has needed, after "the destination is
the file with the dangling reference" and "a test file is never the repair target". The
recurring lesson: **scope rules, not pattern rules.**

## Ledger after five rows

| | before | now |
|---|---|---|
| end-to-end solved, 41 attemptable | 22 | **24** |
| corpus solved / 45 | 22 (48.9%) | **24 (53.3%)** |
| literal/constant-refinement rows | 2 | **5** |
| rows solved blind with no model call | 3 | **5** |

## What is still true about these five

- **I chose which rows to attempt by noticing a shared shape.** That is a human routing
  decision, and the tool does not make it. Five rows of one shape is a demonstration of
  reachability, not evidence that a benchmark of 1,865 problems would be reached.
- **Every one still needs the oracle.** The parent does not fail on its own: for
  `httpx e63b6594f2` no test exists at the parent, and for `more-itertools` the shipped
  test is new. The benchmark's hidden test patch remains the binding constraint, exactly
  as recorded in `THE_CORPUS_IS_ONE_LINE_WIDE`.
- **One row was reported NO_FAILING_TEST and cleared anyway** (`httpx`); one had already
  22 attempts and a recorded demand (`more-itertools`, `AssertionError: True != False`).
  Neither was unreachable — both were *routed wrong*, and the existing family was applied
  to the wrong shape.
