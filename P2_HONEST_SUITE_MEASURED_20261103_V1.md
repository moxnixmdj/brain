# P2 executed: the denominator, measured — and split into what it is actually made of

**2026-11-03.** `OPTIMAL_PLAN_20261103_V1.md` §2 P2, done. This replaces a baseline from
**2026-10-17** that `AGENTS.md` was still citing as "the real backlog", and it splits that
backlog into three different kinds of thing that need three different kinds of work.

Authority: **NONE**. One machine, one run. Not independent verification, not a receipt. It
records what the suite did; it proves nothing about capability. Spend $0.

---

## 1. The headline

| | 2026-10-17 baseline | 2026-11-03 (this) |
|---|---|---|
| cases | 11,754 | **16,361** |
| passed | 11,360 (96.6%) | **15,255 (93.2%)** |
| failed | 380 | **984** |
| error | 0 | 42 |
| skipped | 14 | 80 |
| files observed | 1,929 | **2,279** |
| files with failures | 223 | **344** |

**The suite grew 39% in cases and 18% in files. The absolute failure count grew 2.6× and the
pass *rate* fell 3.4 points.** Both numbers are true and only one of them can be summarised in a
sentence, which is why the baseline records the whole table.

Reproduce:

```
python3 execution_guard/honest_suite_baseline_v1.py --junit <merged.xml> --out <path>
python3 execution_guard/suite_backlog_split_v1.py --junit <merged.xml> --baseline <prior> --substrate-check <verdict>
```

## 2. Why a per-file sweep, and what that costs

A single-process run of the whole suite was attempted first and **killed at 8%**. A live-route
test hung past `--timeout=120` and the run emitted **no junit at all** — so one hang loses the
entire measurement. That is itself a finding about the instrument.

The sweep runs one pytest process per test file: 2,371 files, 2 workers, `--timeout=90
--timeout-method=thread`, `--continue-on-collection-errors`. A hanging file costs one file.

**What this costs, stated up front:** fixtures that rely on being in the same session are not
shared across processes here, which can only make failures *more* likely, never fewer. So these
numbers are a lower bound on passing and are **not** comparable one-to-one with a single-session
run. The direction of the bias is known and it is against me, which is the only reason this is
usable at all.

## 3. The split — 984 failures are not 984 backlog items

`execution_guard/suite_backlog_split_v1.py` (new, with the fixture-level behaviour demonstrated
below) separates failures that describe **the machine** from failures that describe **the tree**.

| | count |
|---|---|
| environment failures (missing module / network) | **48** |
| real failures | **978** |
| of which **regressions** vs the 17 Oct baseline (file was clean then) | **642** |
| of which **standing debt** (file also failed in the 17 Oct baseline) | **336** |

Failure buckets: `ASSERTION` 793, `OTHER` 113, `CURRENTNESS_GUARD__DRIFT` 53,
`IMPORT_ERROR` 43, `CURRENTNESS_GUARD__SOURCE_BLOB_DRIFT` 16, `MISSING_FILE` 5, `NETWORK` 3.

**There are 642 regressions, not 344.** That is the number that should worry the owner: on the
2026-10-17 tree those files were clean. `test_an_ordinary_sentence_runs_the_command_it_states_v1.py`
alone contributes **233** of them.

## 4. The machine was also wrong, and the tree said so

The repository already had the instrument:

```
$ python3 scripts/restore_substrate_v1.py --check
SUBSTRATE  modules_present=1/10  binaries_missing=none
  verdict: SUBSTRATE_INCOMPLETE -- lanes that need these measure an ENVIRONMENT gap,
           not a capability gap, and the matrix reports them as unmeasurable.
```

**1 of 10 declared substrate modules were present.** `AGENTS.md` says the honest failure count
"is the real backlog — reduce it by fixing runtime code or by correcting governance documents",
which conflates an uninstalled `cv2` with a broken invariant. Both print `F`.

So: substrate restored **1/10 → 9/10** (`pillow, opencv-python-headless, numpy, python-docx,
langdetect, pydantic, openpyxl, hypothesis, tree-sitter, tree-sitter-languages, coverage, mypy,
ruff, bandit, z3-solver`; `crosshair-tool` still absent), then the **10 files whose failures were
a missing module were re-run**. Result: **25 failures that were pure machine gap disappeared**
(1,010 → 984 failed, 15,229 → 15,255 passed) and three files went fully green that had been
counted as broken.

The environment split is now a first-class record, `SUITE_BACKLOG_SPLIT_20261103_V1.json`, with
`install_to_measure` naming the pip package for each absent module — so "this lane is red"
becomes "install `opencv-python-headless` to measure this lane".

## 5. What the largest failure cluster actually is — and it is not a missing capability

`test_an_ordinary_sentence_runs_the_command_it_states_v1.py`, 233 failures of 345 cases, left at
240 characters. I checked whether the *capability* was missing before believing the red:

```
>>> composer_route_v1.extract_argv("the first word of each line in the file /…/probe.txt")
['cut', '-d', ' ', '-f', '1', '/…/probe.txt']
>>> composer_route_v1.extract_argv("sort the lines of the file /…/probe.txt")
['sort', '/…/probe.txt']
>>> composer_route_v1.extract_argv("compress the file /…/probe.txt")
['gzip', '/…/probe.txt']
```

**The front compiler produces exactly the right argv from ordinary prose.** The tests fail on
`_verified(r)` — the solver did not select and verify that plan. So the single largest red cluster
in the tree is the **same defect P3 names**: the capability exists and the door does not reach it.
That is not a coincidence and it is not a capability gap; it is a routing gap with a count
attached, and it is now the best-measured argument for doing P3 next.

## 6. What to do with this, concretely

1. **`AGENTS.md`'s "the 344-failure baseline is the real backlog" is superseded.** Not deleted —
   the framing it got wrong is worth keeping visible — but it now points here, because the number
   is 984, the machine contributed some of it, and 642 of the 978 real ones are regressions rather
   than standing debt.
2. **Do not triage 978 failures.** Triage in this order: (a) the 48 environment ones, which are
   `pip install` lines; (b) the biggest regression cluster, which is one door defect worth 233
   cases — P3; (c) the 53 + 16 currentness-guard drifts, which are pinned-blob mismatches and are
   a distinct, mechanical repair.
3. **Fix the instrument too.** A suite that emits no junit when one test hangs cannot be measured
   in one process. The per-file sweep is a workaround, not a design; a proper answer is per-test
   timeouts enforced below the junit writer.
4. **Keep the direction of bias visible.** Every future baseline should say whether it was a
   single session or a sweep, because the numbers are not interchangeable.

---

## 7. Standing non-claims

Nothing here moves `0/112`, flips a family, registers a capability, or claims sentience. The
baseline is a measurement of a tree at `407cc3c` with a dirty working tree (my P1 edits were in
it, and P1 is already committed separately — the head recorded in the document is the commit the
sweep started from). 16,361 cases is not a quality score and 93.2% is not a grade. `truth.achieved`
remains `false`.

---

## 8. Addendum — a defect found in the accounting tool itself

While pinning the split with tests, the tool reported 2 regressions where there was 1. Cause:
the 2026-10-17 baseline keys files as `canonical/tests/test_old_debt.py`, while a classname that
does not resolve to an existing file stays dotted (`canonical.tests.test_old_debt`) — so **every
standing-debt file was reclassified as a new regression.**

It is a small bug with a large effect on the number the document is about, and it is worth
naming the direction: it inflated regressions. A tool that flatters the tree would be worse, but
a tool that exaggerates breakage is still wrong, and 642 is only trustworthy because the test
caught the normalisation. Both spellings now normalise to one key, and
`canonical/tests/test_suite_backlog_split_v1.py` (5 tests) pins the three-way classification, that
a missing module names its pip package, that environment-blocked files are *named* rather than
dropped, and that a real failure is never excused as an environment gap.

## 9. The protected-path proposal

`AGENTS.md` is a protected path (`AGENTS.md` rule 8): an agent that changes it cannot merge its
own PR, and the honest response is to say why and stop rather than work around it. The text I
believe it should carry is therefore **not applied**; it is staged verbatim at
`canonical/verification/proposed/AGENTS_MD_HONEST_BASELINE_PROPOSAL_20261103.md` for the owner.

Why it matters rather than being housekeeping: `AGENTS.md` currently instructs every future agent
to treat "344 failures" as "the real backlog". Following that instruction today means triaging a
number that is (a) 984, (b) 48 of it is the machine, and (c) 642 of the remainder are regressions
against a tree that was clean four weeks ago. An agent that trusts the old sentence will work on
the wrong thing first — which is precisely the failure mode `README.md` says this repository was
built to prevent.
