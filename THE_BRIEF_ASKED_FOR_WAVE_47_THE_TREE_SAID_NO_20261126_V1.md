# The brief asked for Wave 47. The repository's own evidence said do not.

**2026-11-26 · branch `arena/9e357806-brain` from `main@3e652cf2` · authority NONE · $0 · 0 model calls · 0 stored parameters**

This round did not awaken twenty "titan" modules. It re-measured the front door
with a working interpreter and found three defects in the **instrument** before
it found one in the system. That ordering is the result.

---

## 1. What I was handed, and what the tree actually says

The brief's claims, checked against `main@3e652cf2`:

| claim | status | evidence |
|---|---|---|
| Localized third-party code at `stirrup/`, `mini_swe_agent_2_4_6/` with `litellm`/`openai` imports | **verified** — and a §2 runtime-constraint risk | `canonical/capabilities/internalized/**` |
| Commits `209bbc6c`, `de2f51cf`, `983130c2` etc. solve the failures | **failed** — none exist | `git cat-file -t 209bbc6c` → *Not a valid object name* |
| 756 open PRs / **8 open PRs** | **failed** — count is 8 | `gh pr list` |
| `03f69853` is on `main` | **failed** — `main` is `3e652cf2` | `git log -1` |
| The repo already solved the hard problems, just unplugged | **failed** — measured below, four ways | §3–§4 |

## 2. The instrument was lying, and it was my own first measurement

Two separate ways to get a false "the system fails everything":

**A missing pytest is indistinguishable from a failing test.** Every harness in
this project runs `python -m pytest`. Without pytest the process exits `1`, and
exit `1` is precisely the signal the honest baseline reads as *this test fails
on the parent*. Measured: `/usr/bin/python3` has no pytest, and the run reported
**12/12 `NO_PROPOSAL`** with the identical shape of a real result. My first
ground-truth run — "0/40 candidates fix the node" — was made the same way and is
**void**.

**The tests were importing the installed copy.** `pytest` depends on
`packaging`, so `from packaging.dependency_groups import …` resolved to
site-packages `packaging 26.4`, not the checkout. With that, six of twelve tasks
looked like `GOLD_DOES_NOT_PASS` — the benchmark's own gold patch appearing not
to work. It worked; it had been applied to a tree nobody imported.

**Repaired and enforced** (`canonical/tools/honest_baseline_wellposed_v1.py`):
refuses to emit a number unless a trivial test collects and passes; asserts the
package resolves inside the checkout; applies the full gold diff as a validity
audit before any task is counted.

## 3. The tasks themselves: 2 of 12 are unsolvable by construction

`9f5249fb` and `e83801f4` need `tests/metadata/everything.metadata` changed
(`Metadata-Version: 2.5 → 2.6`). The harness applies the gold diff for the
**test file only**, and the engine is forbidden from editing oracle files
(`_is_test_or_oracle_file`). The new test asserts `== "2.6"` while the fixture
still says `2.5`. No honest source change passes it.

This is the small-scale shape of the verifier error the repo already cites from
the 2026 SWE-bench audits: *a check that cannot be satisfied by any correct
answer is not a check.*

**Honest denominator: 10 well posed, 2 ill posed.** The published `12` was not
defensible.

## 4. The capability result, unchanged and now properly measured

Both generator families were run on the well-posed tasks with a working
interpreter and correct import provenance.

**In-portfolio generator** (`unified_epistemic_portfolio_v1`), task `959bb79c`:

```
synthesized_total: 96   cow_fork_survivors: 0   angelic_guards: 0
```

Ground truth applied for real in a fresh copy per candidate: **0/30 fix the
node.** The screener is not the problem; the generator is.

**Titan kernel** (`angelic_cegis_repair_v1` — the brief's "awaken the titans"
thesis) across all twelve:

```
NO_VERIFIED_PATCH_FOUND : 8
NO_EXECUTED_REPO_LINES  : 4
verified                : 0
```

### Why, exactly

The gold fix for `959bb79c` **adds a parameter and a guard** and threads it
through recursion:

```python
def _resolve(self, group, requested_group, errors, seen_error_groups):
    if group in seen_error_groups:
        return ()
```

Every one of the 96 synthesized candidates is a **value substitution on an
existing return**:

```python
-    return normalized_groups
+    return group_name == normed_name
```

Not one is a structural addition, and none is semantically coherent. This is
the ceiling the repository already measured (V42/V43): a substitution family
cannot add a statement, and the answer is outside the family.

## 5. Why Wave 47 was not implemented

V43 tested the brief's central premise on four independent axes and it failed on
all four: presence (9 of 9 named commits absent), reach (64% of `canonical/`
never reached by the runtime), effect (0 candidates on 26 of 27 tasks), content
(the repo's own history supplies at most 33% of the added lines its bugs need).
Wiring twenty more unplugged modules feeds more *proposers* into a pipeline
whose measured wall is the *proposal space*, not the number of proposers. Doing
it because the brief asked would have been the dishonest move.

The brief also asked for `#7144` to be merged as step one. **Not merged:**
`gh pr view 7144` → mergeable `UNKNOWN`, merge state `UNKNOWN`. It is not "22/22
CI green, clean", and merging on that claim would be acting on an unverified
premise.

## 6. What is actually real, and the one bottleneck

**Real** — reproduced on this machine today:

- the front door refuses instead of answering wrongly (9 probes, 0 false
  PASSes; the 2026-11-25 wrong-answer defect does not reproduce);
- differential tracing works and is informative when the repo is importable
  (147 ranked lines, 181 passing-spectrum lines on `959bb79c`);
- the whole-slice screener is honest: every candidate it rejects genuinely does
  not fix the node (0/30 verified by direct application);

**The bottleneck is the proposal space, and it is a *representation* problem,
not a search-budget problem.** Synthesizers that edit *values at existing sites*
cannot express the fixes that dominate real commits, which *add structure*. The
repo's own taxonomy agrees: 482 of 667 changed sites are additions.

The one bottleneck, stated so it can be attacked:

> **A fix generator whose unit is the statement—with parameters, guards and
> free names abstracted from the failing run's own demand—rather than the
> value substituted at an existing node.**

## 7. Files

- `canonical/tools/honest_baseline_wellposed_v1.py` — new. The preflight, the
  ill-posedness audit, the import-provenance assertion, two denominators.
- Commit `37a21cb2`.

## 8. Limits, stated plainly

- One machine, producer-run, `authority: NONE`. Not independent verification.
- The full suite does not run here: 42 collection errors in `test_root3_*`
  modules, unrelated to this change and present without it. No whole-suite claim
  is made.
- Ten tasks, two repositories. Nothing here says anything about SWE-bench Pro,
  Terminal-Bench or OSWorld. §6 **DONE is not met** and this round does not
  move it.
