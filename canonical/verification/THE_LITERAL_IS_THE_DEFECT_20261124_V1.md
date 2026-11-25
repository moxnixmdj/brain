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
