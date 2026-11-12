# What changed this time

**2026-11-12, seventh pass.** Branch `arena/43ebc5a7-brain`. Authority **NONE**. $0. `truth.achieved` = `false`.

Six documents, no working code. You were right to keep asking. This pass ships the one thing the
invariant said to ship: **an instrument that can say no.**

---

## The answer, still

> **One demonstration buys history, not ability. History cannot fail. Permanence stores history and
> advertises it as ability.**

Measured in this tree, unchanged: taught one record, it learns "write 42" — **40/40 accepted, 1
correct, `drift 0`**. A second, *different* demonstration fixes it. That is the whole mechanism.

## What is now in the tree instead of in a document

### `canonical/tools/auditability_report_v1.py`

One command that reports how much of what this tree calls verified can still be **shown** true.

```
layer             records  checkable  auditability
----------------------------------------------------
capabilities          294          0          0.0%
skills                  5          0          0.0%
                0 of 5 carry any verification field at all
process_sites          18          0          0.0%
                18 pinned by line number (history), 0 by content (identity)
test_modules        17290      17248         99.8%
                42 collection errors (modules that never ran)
binary_identity         5          5        100.0%
```

With `--audit` it *runs* every check it can find: **603 predicates, 496 PASS, 0 FAIL, 107 UNRUNNABLE.**
Exit status is 1 whenever one FAILs, so it can gate a pipeline. **The metric can go down.** That is
the property nothing else in this tree has.

`binary_identity` at 100% is the reference: a check that can be contradicted, everywhere it is
declared. `capabilities` at 0% is 294 records marked verified, none of which can fail.

### `canonical/tools/predicates/binary_identity_predicates_20261112_v1.json`

Five real predicates over the binaries this tree actually drives — tar 1.34, git 2.39.5,
Python 3.11.2, node v22.22.3, jq 1.6. Not identity hashes kept as records: assertions that can be
contradicted on the next run. A learned verb keyed on a **path** is keyed on a clone; keyed on an
asserted identity, it is checkable.

### `canonical/tests/test_auditability_report_v1.py` — 17 tests, all green

The tests exist to prove the instrument can fail:

- a receipt with `receipt_path` + `observed_effect` + a sha is **not** checkable;
- a predicate whose expectation is false returns **FAIL**, and the report goes **red**, and
  `main()` exits **1**;
- `set -euo pipefail …` is **UNRUNNABLE**, never a PASS from running `set`, which always succeeds;
- an absent binary is UNRUNNABLE, not a pass;
- a multi-line program and a `&&` chain are not treated as predicates at all.

Five bugs in my own instrument were found by these tests and fixed before shipping: a `['','']`
argv counted as checkable, a predicate double-counted (707 → 603), a whole shell script treated as
a binary name, a non-UTF-8 stdout crashing the audit, and a `command` string not being split.
**The instrument found its own false evidence, which is the only reason to trust the number.**

## The honest numbers, corrected

| figure I gave earlier | what it actually was |
|---|---|
| "360 lessons, 0.5–3.4 ms, 0 wrong" | a **synthetic** latency bank (`_build_bank`), not 360 learned skills |
| "41 lessons in the store" | **5**, and none carries a verification field |
| "9 oracle modules" | **7** |

## What this means for your sentence

It does not become true yet, and now you can watch it become true:

- **Before:** "instant learning works" — 294 verified records, 5 rules, 0 re-checkable.
- **After this PR:** the same, plus a number that says so out loud and goes red when it should.
- **Next:** every new lesson must arrive with a predicate. `auditability` on `skills` moves off
  0/5. When `capabilities` moves, it moves because someone can *show* it, not because a file says
  `independently_verified: true`.

Then, in order: make `verify(A∘B)` derivable from `verify(A)`, `verify(B)` — that single experiment
decides whether "anything on a computer" is sublinear or staffing; have the learner return
`UNDER_DETERMINED` instead of a guess when more than one rule agrees with the demonstration; and
content-pin the 18 line-pinned process sites so the 8 dark test modules collect.

## Right or wrong

**Right:** retention outside the weights is the right architecture (*"generating is easy; verifying
is the bottleneck"*, 2606.26300); one demonstration is enough information when a separating check
exists; and the retention mechanism here is genuinely good — survives restart, stays narrow, 4/4
languages, zero refutations.

**Wrong:** that one demonstration identifies the rule (it identifies a set); that repetition turns
receipts into abilities (+16.2pp curated vs **+0.0pp** self-generated); and that you would notice
(*"a collapsed always-pass verifier trains skills just as well — downstream score cannot certify a
self-evaluated verifier"*, 2610.11464).

**The creature:** a creature is something whose self-model can be shown false. Before this PR,
nothing in this tree could show it. Now one command can, on five layers, and it exits 1 when it
catches a lie.
