# The oracle was never handed to us: 2 of 45

**2026-11-24.** Instrument: `canonical/tools/the_oracle_was_not_handed_to_us_v1.py`.
Receipt: `canonical/verification/THE_ORACLE_WAS_NOT_HANDED_TO_US_20261124_V1.json`.

## What was measured

Every prior number in this repo — 19/45, 6/30, 10/13 — was obtained by a tool that
does this, in `the_harness_must_prove_it_can_see_v1.py` and in both engines:

```python
(worktree / test_path).write_text(
    identify.show(repo_path, entry["commit"], test_path), encoding="utf-8")
```

It **writes the fix commit's version of the test file into the parent tree.** That is
how the failing oracle appears. The benchmarks do not grant this. So the first honest
question about any row is not "can we generate a patch" but "is there a failing test
in the parent at all".

I deleted that convenience and classified each of the 45 rows at commit^ by what the
parent actually contains:

| outcome | count | share |
|---|---|---|
| `ORACLE_NEW_TEST_CASE` — test file exists, the named test functions do not | **37** | 82.2% |
| `ORACLE_GREEN` — named test exists and passes at parent; the fix changed it | **5** | 11.1% |
| `ORACLE_ALREADY_RED` — named test exists and already fails at parent | **2** | 4.4% |
| `ORACLE_ABSENT` — the fix introduced the test file | **1** | 2.2% |

**43 of 45 rows (95.6%) require a test that does not yet exist in the tree we are
given.** Only 2 rows ship their own failure.

Both `ORACLE_ALREADY_RED` rows were then opened by hand, because "already red" can
mean an unrelated import error rather than the defect:

- `attrs 1c962d15a7` — `assert ('Type annota... be present',) == ("Type annota...nt for 'x'.")`
  Expected error message text. A genuine defect failure.
- `urllib3 644124ecd0` — `assert ['authorization', 'cookie'] == ['authorization']`
  `proxy-authorization` not stripped on redirect (GHSA-v845). A genuine security defect.

Both real. **2/45 = 4.4% is a verified ceiling, not an estimate.**

## The benchmark is stricter still

My corpus measures 95.6% because 2 rows happen to carry a pre-existing red test. That
is luck, not structure. SWE-bench Pro's own paper defines the task so that this cannot
happen:

> We define the **test patch** as the diff of test related files between the two
> commits. In other words, it consists of the new or modified tests introduced in the
> instance commit **but absent in the base commit**. […] A valid problem requires a
> commit pair that satisfies two conditions. First, the instance commit must either fix
> a bug or introduce a feature. Second, the commit pair must include a test patch that
> verifies the correctness of the fix through a fail2pass transition: **applying the
> test patch to the base commit should cause test failures**, while applying both the
> test patch and the gold patch should result in all tests passing.
> — *SWE-Bench Pro: Can AI Agents Solve Long-Horizon Software Engineering Tasks?*,
> arXiv:2509.16941 §4.1

A task where the test is already red at base **cannot be admitted to the dataset**. So
on SWE-bench Pro the free-oracle rate is **0/100% by construction**, and my 4.4% is an
*over*-estimate of what a real benchmark offers. The 45-commit corpus has been a more
generous sample than the benchmark it was standing in for.

## What this does to the plan's equation

The plan's own decomposition:

```
P(solve) = P(oracle discriminates) × P(generator reaches) × P(horizon)
```

with the values now measured:

| factor | measured | source |
|---|---|---|
| P(oracle) from an issue alone | **0.00** (benchmark) / **0.044** (our generous corpus) | this receipt; arXiv:2509.16941 |
| P(gen) given a supplied oracle | **0.463** (19/41) | `THE_UNION_RECEIPT_20261124_V2` |
| P(horizon) | unmeasured here | — |

```
end-to-end upper bound = 0.044 × 0.463 = 2.1%
on a real SWE-bench Pro task                    = 0.0%
```

**Every one of the plan's seven pillars attacks the second factor, and the first
factor is zero.** Pillar 0 merges four engines that all hard-refuse without a failing
test (`the_demand_is_learned_from_the_run_v1.py:834`) — merging them multiplies 0.463
by nothing. Ideas 2, 3, 5, 6 and 7 are all generation mechanisms. Idea 4 is horizon.
Only Idea 1 touches P(oracle), and I have already measured it at **0/19**.

This also explains the four nulls in one stroke, and it explains the GitHub Actions
result from the previous audit: on four real benchmark tasks the agent's status was
`BLOCKED_NO_MODEL_PROPOSAL` with `patch_bytes: 0`. No proposal was produced — not
because the patch generator is weak, but because **there was no demand to generate
against**. The engines are not failing at generation. They are refusing entry.

## Where the demand actually has to come from

The plan's Idea 1 tries to *synthesise* a test from the existing green suite, by
injecting metamorphic relations into the arguments that flow through the named symbols.
That is the wrong source. It fires on intentional mutation — I measured 400 violations
on click `d340b0c1` and 213 on attrs `a572c3a4` **identically at the fix** — because
the relation is checked against the suite's behaviour, and the suite's behaviour is
already correct.

But a human handed an issue almost never faces the blank-page oracle either. The issue
text itself usually *is* the oracle, in compressed form:

> calling `X` with `Y` raises `Z` — but it should return `W`

That sentence is an executable assertion. Extracting it is parsing, not synthesis. And
if the issue contains a reproducer, the expected-vs-actual pair is given outright.

So the reframing is:

> **The oracle is not synthesised from the test suite. It is extracted from the issue as
> an executable assertion, then confirmed by running it — which is exactly what the
> benchmark's own construction pipeline does when it validates fail2pass.**

Two consequences, both testable at zero cost:

1. **P(oracle) is measurable on real issue text.** Fetch the issue/PR bodies behind the
   45 commits via the GitHub API and measure the fraction that state a concrete call
   with an expected-vs-actual pair, or contain a runnable reproducer. That is the true
   P(oracle) for an issue-only task, from the honest source, and it can be counted
   rather than assumed.
2. **`ORACLE_ALREADY_RED` = 2 is not a limit on capability, it is a limit on this
   corpus.** If the issue-body rate comes back materially above 4.4%, the binding
   constraint moves from P(oracle) to P(gen) — and the plan's pillars become relevant
   for the first time.

That measurement is the next action. It is the only one that can change the product.

## Measured: 10 of 45 issues carry the oracle

Instrument: `canonical/tools/does_the_issue_contain_the_oracle_v1.py`.
Receipt: `canonical/verification/DOES_THE_ISSUE_CONTAIN_THE_ORACLE_20261124_V1.json`.

The first run of this tool returned **1/45**. That was wrong, and the reason matters:
the script was fetching the **pull request body**, which is almost always the literal
string `"Fixes #1354"` — twelve characters. The content is in the **linked issue**.
The corpus rows I printed as `PROSE_ONLY 12ch` were not prose; they were an empty
field. After following `Fixes #N` into the issue and its comments, and adding
retry/caching so a transient GitHub 502 cannot silently downgrade a row to
`PROSE_ONLY`, the number is:

| verdict | count | share |
|---|---|---|
| `ORACLE_IN_ISSUE` — a fenced block carries a traceback, a `raises`, or an assertion | **10** | 22.2% |
| `PROSE_ONLY` | 35 | 77.8% |

Spot-checked by hand: `attrs 1c962d15a7`'s issue body contains the actual raise site —

```python
elif ca.type is not None:
    raise ValueError(
        f"Type annotation and type argument for {name} cannot both be present"
    )
```

— which is the expected message the fix must produce, in executable form. The parser
is conservative: it needs a fenced block with an operation, not merely identifiers. So
**22.2% is a lower bound on the extractable-oracle rate**, from an unimpeachable source
(the human who filed the bug), with zero model calls.

### The joint picture, which is the first honest one

| quantity | value | meaning |
|---|---|---|
| rows needing a test that does not exist | 43/45 = 95.6% | the product problem |
| rows whose issue carries an executable excerpt | 10/45 = 22.2% | the recoverable demand |
| of those, already solved by the union | 4 | no new capability |
| **of those, still unsolved** | **6** | **the honest target set** |

The six are `1c962d15a7`, `2eb4542cba`, `42ee8a1f60`, `77fa67aaf2`, `d0f040a65b`,
`e7ce051e91`. That is a small set — six rows — and any pipeline built against it must
be reported as n=6, not as a rate.

But it changes the nature of the next build. The plan's Idea 1 tries to *synthesise* a
test by injecting metamorphic relations into the green suite; measured 0/19. What the
data says instead is:

> the excerpt gives the **expected value** and the **code site**; what it does not give
> is the **triggering call**. So the task is not test synthesis, it is *reachability*:
> construct the minimal input that reaches the quoted site.

That is a precisely scoped synthesis problem — backward from a known raise site to a
call that reaches it — and it is tractable in a way that "write the hidden test" is not.
It is also the one thing in the plan that no branch has attempted.

## Corrections this forces

- **Do not quote 19/45 as an solve rate.** It is conditional on an oracle the benchmark
  never supplies. Label it "given a failing test".
- **Do not merge the branches (Pillar 0).** Four engines that share one hard-refusal
  gate compose to one hard-refusal gate.
- **The `1432289d` receipt already knew this** and said it better than I did: *"every
  graded commit ships the test that specifies the repair, so the store competes with a
  specification that is already present."* Its 10/13 is measured on the same generous
  footing as my 19/45 and has the same ceiling above it.

## Demonstrated: an issue-derived oracle that actually discriminates

The 22.2% figure is a parsing statistic. It says nothing until one of those excerpts is
turned into a test that fails on the buggy tree and passes on the fixed tree. Done once,
by hand, on `attrs 1c962d15a7`, to establish that the path is real:

**Source of the oracle — the issue body alone.** No model call, no hidden test:

```python
elif ca.type is not None:
    raise ValueError(
        f"Type annotation and type argument for {name} cannot both be present"
    )
```

**Test assembled from it** (expected string from the quoted raise site; class `Attribute`
and argument `ca` from the quoted signature):

```python
import attr, pytest
from attr._make import Attribute

def test_issue_derived():
    ca = attr.ib(type=int)
    with pytest.raises(ValueError, match=r"cannot both be present for 'x'\."):
        Attribute.from_counting_attr("x", ca, type=str)
```

**Result across the two trees:**

| tree | head | result |
|---|---|---|
| `6bde361` (parent) | `Unpin towncrier` | **FAILED** — `AssertionError: Regex...` |
| `1c962d1` (fix) | `Mention what argument has both annotation...` | **passed** |

Fail-to-pass, constructed from the issue, `model_calls = 0`.

### Three wrong answers on the way, because the instrument lied three times

1. **First version passed on both trees.** `ca` was built as an `Attribute` rather than a
   `_CountingAttr`, so `from_counting_attr` never reached the quoted branch. Fixed by
   reading the real signature from the tree.
2. **Second version also passed on both trees — because of import contamination.**
   `import attr` inside `/tmp/rx` resolved to
   `/home/user/venv/lib/python3.11/site-packages/attr/__init__.py`, the **installed
   attrs 26.1.0**, not the worktree at 2494-line `src/attr/_make.py`. Both trees were
   therefore being tested against the *same fixed package*. The bug was invisible until
   I printed `attr.__file__` from inside the pytest process.
3. **The verified fix**: `PYTHONPATH=<worktree>/src`, then a provenance assertion that
   `attr.__file__.startswith("/tmp/")` inside the pytest run. Only then did the
   discrimination appear.

### The near-miss that matters more than the result

Because of (2) I checked whether the **engine** has the same defect, since five
src-layout packages (`click`, `packaging`, `pluggy`, `urllib3`, `attr`) are installed
from PyPI into the driver venv at versions different from the corpus commits:

```
packaging worktree, no PYTHONPATH  -> packaging at: /home/user/venv/.../packaging/__init__.py
packaging worktree, PYTHONPATH=src:. -> packaging at: /tmp/ct2/src/packaging/__init__.py
```

**The engine is correct.** `identify_a_real_bugs_fix_v1.fresh_bytecode()` returns
`{"PYTHONPATH": "src:.", ...}`, relative to the worktree cwd, so `src` wins and the
patch is compiled. The 19/45 is **not** contaminated. No editable installs or stray
`.pth` entries exist in the venv.

But the margin is one dictionary entry. Remove `PYTHONPATH="src:."` and 15 of the 19
"VERIFIED" rows (attrs ×3, click ×3, packaging ×6, pluggy ×1, werkzeug ×1) would
silently verify against a *different version of the library*, and every one of them
would still print PASSED. Any future tool in this repo that shells out to pytest on a
corpus worktree **must** route through `fresh_bytecode()` or reproduce its `src:.`
env, and should assert module provenance on at least one row per repo.

## What is now established, and what is not

Verified:
- 43/45 rows (95.6%) have no failing test in their parent; the benchmark requires that
  by construction, so the real figure is 100%.
- 10/45 issues (22.2%, a conservative lower bound) carry an executable excerpt.
- 6 of those 10 are unsolved by the union → the honest target set of 6.
- One of the six is solved end-to-end from its issue text with zero model calls.

Not established:
- That the remaining 5 generalise. n=1 is a demonstration, not a rate.
- That the 22.2% survives on SWE-bench Pro's own issues, which are human-rewritten and
  may be either richer (requirements + interface sections) or poorer (stripped of
  code blocks). Their augmented descriptions *do* include an "interface" artifact,
  which is likely to raise the rate, but that is a guess until measured.
- Anything about OSWorld or Terminal-Bench, where there is no issue text at all —
  the goal is the only spec, and P(oracle) there is a different problem entirely.

## Correction to record

The oracle is **not synthesised from the green suite** (measured 0/19 across three
independent implementations). It is **extracted from the issue as an executable
excerpt**, and the residual synthesis problem is *reachability*: the excerpt supplies
the expected value and the code site, but not the triggering call. That is a far
smaller search than "write the hidden test", and it is the only route in this repository
with a measured non-zero rate behind it.

## The route is real but it stops at Wall 2 — and now I can say exactly where

Following the demonstration above, the same mechanism was automated
(`run_the_reproducer_the_user_wrote_v1.py`) and run over all 10 `ORACLE_IN_ISSUE` rows.
It extracts fenced code from the issue, **including REPL transcripts**, executes each
block on the parent and on the fix with `PYTHONPATH="src:."`, and keeps only blocks
whose verdicts differ.

First run reported 2 discriminating blocks. That was wrong again, for the fourth time in
this document: I had `if ">>>" in block: continue`, which discarded every REPL
transcript — and a transcript is the *richest* oracle an issue can carry, because the
prompt line states the call and the traceback states the expected outcome. After the
fix:

Then run over **all 45 rows** rather than only the 10 flagged `ORACLE_IN_ISSUE`, since
the fenced-block classifier is conservative and a real reproducer can hide in a row it
called `PROSE_ONLY`:

```
REPRODUCER_DISCRIMINATES   4     3b0378dd66, d05bd3858c, cca32949f1, 77fa67aaf2
NO_SEPARATION              7
REPRODUCER_DOES_NOT_REACH  4
NO_REPRODUCER_IN_ISSUE    30
```

Four, not three: `jinja d05bd3858c` was invisible to the 10-row pass because the
issue-level classifier had called it `PROSE_ONLY`. **Two of the four are on the six-row
unsolved set** (`d05bd3858c`, `77fa67aaf2`); the other two were already solved by the
union and add no capability.

Four fail-to-pass oracles, derived from prose, zero model calls. Two (`3b0378dd66`,
`cca32949f1`) were already solved by the union and add no capability. **The other two,
`urllib3 77fa67aaf2` and `jinja d05bd3858c`, were both on the six-row unsolved set** —
the first time anything in this repository has produced a discriminating oracle on a row
that no engine could previously enter.

### End to end on that row

1. **Oracle.** The issue carries `urllib3.util.parse_url("http://example.com:000001")`
   with the traceback. Pasted into a test asserting `url.port == 1`.
2. **Provenance-checked fail-to-pass** (no venv contamination, `PYTHONPATH=src:.`):

   | tree | head | result |
   |---|---|---|
   | `fe39ebfb` (parent) | `Use the typing namespace...` | **FAILED** — `urllib3.exceptions.LocationParseError` |
   | `77fa67aa` (fix) | `Strip leading zeros from ports` | **passed** |
3. **PASS_TO_PASS anchor.** The engine requires one (`NO_PASSING_TEST` without it), so a
   second assertion was added from the issue's own sentence *"Shouldn't be a problem"*:
   `parse_url("http://example.com:8080").port == 8080`.
4. **Engine run** (`the_demand_is_learned_from_the_run_v1.py`, with a new `oracle_file`
   corpus field so a supplied test patch can be applied the way a benchmark applies it):

```
stage            NO_SEPARATING_RULE
control          VERIFIED   (applying the human fix flips the issue-derived oracle)
guard_sites      44
observations     33
attempts         0
seconds          4.36
```

**The control is `VERIFIED`.** The oracle built from the issue text is validated by the
human fix — that is the strongest statement available that the derived oracle is correct
and not a self-deception. And the engine learns **no rule at all** from it.

### Why, exactly

The human fix is one character, on line 66 of `src/urllib3/util/url.py`:

```diff
-_HOST_PORT_PAT = ("^(%s|%s|%s)(?::([0-9]{0,5}))?$") % (
+_HOST_PORT_PAT = ("^(%s|%s|%s)(?::0*([0-9]{0,5}))?$") % (
```

The engine's 44 guard sites are `if`/`elif`/`while`/boolean-clause decisions. The
defective expression is a **module-level regex constant**. The nearest guard — line 427,
`host, port = _HOST_PORT_RE.match(host_port).groups()` — is *correct* code; the fault is
in a string it reads. So this row is not a guard-rule problem and not a literal problem:
**it is a constant-refinement problem outside the searched node class**, which is the
measured form of Wall 2 that the incoming plan's Idea 2 (type-habitation mining) does
not address, because mining sibling idioms cannot invent `0*` inside a regex.

So the honest ledger for this row is: oracle now exists (new capability, measured), patch
still absent (Wall 2, now located to a line and a node class).

## Ledger for this session

| claim | before | now |
|---|---|---|
| P(oracle) from issue text | unmeasured | **10/45 = 22.2%**, parser, 0 model calls |
| rows with a discriminating reproducer | unmeasured | **4/45**, fail-to-pass verified |
| new capable rows (unsolved + oracle) | 0 | **2** (`77fa67aaf2`, `d05bd3858c`) |
| end-to-end new solves | 0 | **0** — control VERIFIED, patch not generated |
| rows with no oracle in parent | suspected | **43/45 = 95.6%**, benchmark requires 100% |
| generator's reach on the new row | — | fails at a module-level regex constant, outside its 44 guard sites |
