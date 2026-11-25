# The corpus is one line wide, and every result inherits that

**2026-11-24.** Measured from the 45 commits' own diffs. No new tool.

## The number

| | mean source files | mean source lines | multi-file source fixes |
|---|---|---|---|
| **this corpus** | **1.00** | **1.00** | **0 / 45** |
| SWE-bench Verified | 1.7 | 32.8 | — |
| SWE-bench Pro | 4.1 | 107.4 | — |

The 107.4 / 4.1 figure is now **verified**, not an input: the SWE-bench Pro paper states
reference solutions "average 107.4 lines of code across 4.1 files", against SWE-bench
Verified's 32.8 lines across 1.7 files (arXiv:2509.16941). A separate audit of 266 Python
Pro tasks reports gold patches averaging "145.5 changed lines across 3.42 files and 9.84
hunks", and that "the Pro tasks change a mean of nine functions across three files".

So the honest position is not merely that my corpus is smaller. It is that my corpus sits
**below SWE-bench Verified**, the benchmark generally described as saturated, by 33× in
lines — and I have been reporting results against Pro.

Counted by `git show --numstat`, excluding test files. All 45 rows touch **exactly one
source file** and change **exactly one line**, because that is the filter the corpus was
mined with: `single_line_fix_commits_20261123_V1`.

This is not a discovery about software. It is a discovery about **my evidence**: every
capability claim in this repository — 19/45 union, 22/45 with this session's three, the
guard-rule engine, the callee rule, the literal refinements — was measured on fixes that
are **107× smaller in lines** than the benchmark the plan wants to compete on.

## Why this matters more than any single solve

It reorders the whole plan. Wall 3 in the plan is "multi-file coupling", and I have
been treating it as a downstream concern to reach after Walls 1 and 2. It is not
downstream. **I have never attempted it.** The corpus cannot express the question:

- `d05bd3858c` passed `context` to one call in one file. A real SWE-bench Pro task
  changes a representation at one site and repairs every caller across 4 files.
- `ba17fcea23` rewrote one regex in one file. The Pro version of the same class of bug
  would also update the call sites, the type stubs, the docs and the changelog.
- My "0/45 multi-file source fixes" means the propagation machinery the plan's Idea 3
  proposes (def-use zipper) has **zero rows on which it could even run here**.

The one genuinely multi-file thing in the corpus is the *test* file, and the engines
never had to write it — they were handed it.

## What the earlier numbers actually mean

The right way to read 22/45 is therefore:

> 22 of 45 **single-line, single-file** OSS fixes solved, given an oracle derived from
> prose.

That is a real result and it is the strongest evidence in this repository, because each
of the three new rows was verified end to end with a byte-identical patch against a real
fixed tree. But it is a *floor* on a deliberately easy class of task, not a forecast for
SWE-bench Pro, and I should not have let it sit next to 107.4 without this measurement.

## Why I could not simply measure the real distribution here

Two attempts to mine 250–400 commits per repo timed out at 300 s and 900 s. Cause: the
clones are `--filter=blob:none` partial clones, so a history walk fetches blobs lazily.
`/tmp/m2.py` (single-pass `--numstat` over 250 commits) and `/tmp/mine_multi.py`
(3 subprocess calls per commit) both failed for this reason, not because the mining is
hard.

That is an environment limit with a known fix — a full clone of one repo — and it is
logged once here rather than retried. It does not block the next step, because the next
step does not need a distribution: it needs **one** multi-file row solved end to end.

## The single next target this implies

Pick **one** real fix that touches ≥3 source files, with an issue that carries an
executable excerpt, and attempt it with the machinery that exists:

1. oracle from the issue prose (measured 22.2% of issues carry one);
2. root repair by the callee rule or a literal refinement (both measured, both produce
   byte-identical patches);
3. **propagate**: after the root edit, treat each new `TypeError`/`AttributeError` at a
   caller as the next sub-goal and re-apply the same two rules one hop at a time.

Step 3 is the only untested part, and the two rules it would apply are the two rules
that already work. So the experiment is cheap and the failure mode is informative: if the
zip does not converge, that is a real Wall 3 measurement on a single case, which is more
than the plan's 107.4 figure has behind it here.

`flask` and `werkzeug 285af2c465` looked like candidates and are not. Checked:

```
werkzeug 285af2c465  "4 files" = CHANGES.rst + src/werkzeug/utils.py + 2 test files
                     the source change is `code: int = 302` -> `code: int = 303`
urllib3  644124ecd0  "5 files" = CHANGES + docs + src/urllib3/util/retry.py + 2 tests
werkzeug 3a408edffd  "3 files" = CHANGES + src/werkzeug/routing/rules.py + 1 test
```

Every apparent multi-file fix in the corpus is **one source line** plus changelog, docs
and tests. Confirmed mechanically: **0 of 45 commits touch more than one source file.**
The propagation machinery the plan's Idea 3 proposes has no row here on which it could
run, and that is a fact about my evidence rather than about the method.

A genuine multi-file task therefore cannot be manufactured from this corpus. It has to
be taken from a source that contains one: either a full clone of a repo with multi-file
fixes in its history (blocked here only by the partial clone, fixable with one full
clone), or the public SWE-bench Pro set itself, which would also supply the container
environment and remove the 100% of test-patch dependency for FAIL_TO_PASS parsing.
