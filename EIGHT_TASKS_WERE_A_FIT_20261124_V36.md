# EIGHT TASKS WERE A FIT, NOT A CAPABILITY

**Round V36 · 2026-11-24 · branch `arena/50c05c04-brain`**

---

## 1. The problem with the last four rounds

V35 reported **3 solved of 8**. Every conclusion since V32 rested on 8 tasks in 2 repositories. Picking the
next operator from 8 tasks is guessing, and V35 ended by naming the next wall from a single example
(`67ec7d10` needed a helper). That is building from anecdotes.

So this round did the least glamorous thing available: **it made the task set 3.5× bigger before building
anything else.**

## 2. A miner with the rules learned by being wrong

`canonical/tools/mine_fail_to_pass_v1.py` mines the two repositories' own history: a commit must change both a
test file and a source file, and the **added test must fail on the parent as a genuine test failure**
(pytest `rc=1`) with the checkout on `PYTHONPATH`.

| repo | mined | rejected: no test+source pair | rc=2 | no added test fn | rc=0 |
|---|---|---|---|---|---|
| pypa/packaging | 23 | 60 | 19 | 11 | 7 |
| hukkin/tomli | 5 | 102 | 0 | 10 | 3 |

**28 genuine fail-to-pass tasks**, 23 already known, **5 never examined**. Reproducible, zero model calls.

Three defects in the miner itself, all found by running it:

1. It ran pytest with `sys.executable`, which has no pytest. Every task was rejected as `No module named
   pytest` and the run reported **0 fail-to-pass**. Had I trusted that number I would have concluded the
   repositories contain no testable commits.
2. It read `git log` from a detached checkout left on an old commit, mining **7 instead of 28**.
3. Failed node ids were split on spaces, truncating class-based nodes to `TestMarker` and **losing the test
   name entirely** — every task would have run the wrong node.

## 3. Localisation survives the wider set

| localiser | top-1 | within 5 | blind |
|---|---|---|---|
| traceback frames | 3/28 | 4/28 | 24 |
| assertion symbols | 5/28 | 5/28 | 22 |
| **combined, ranked** | **17/28** | **27/28** | 0 |

17/28 top-1 on tasks never used to build the localiser, against 8/10 on the set that was. V35's localisation
result generalises. **That is the one component in four rounds that has.**

## 4. And generation collapses

```
                           v35 (8 tasks)      v36 (28 tasks)
solved                     3                  0
of which change behaviour  2                  0
denominator                8                  28
with localisation seed     —                  0
with empty store           —                  0
```

**Zero solved in 28.** The 8-task set was the set the operators were designed against; two of its three solves
came from watching those exact tasks fail and adding an operator for them. On 20 tasks never used for design,
the same operators solve nothing.

**V35's 3/8 was a fit, not a capability estimate.** The shrinkage is the most important number this round
produced, and it is recorded as such.

## 5. Why — 27 of 28 produced no candidate at all

Reading the change each task actually needs:

| kind of change | count |
|---|---|
| invents a function that does not exist in the file | **11** |
| edit of 5–20 lines | 8 |
| edit of at most 4 lines | 6 |
| edit of more than 20 lines | 3 |

39% of the set requires writing code that is nowhere in the file. The operators **substitute, extend, wrap or
rebind what is already present**. They are aimed at 6 of 28, and on a first pass they reached 0.

## 6. The one operator I added, and why it still failed

`WRAP_EXCEPTION`: when the test demands `assertRaises(X)` and the code either silently succeeds or raises the
wrong type, pytest **states the required type**. No guessing is involved. So I wrapped each single-line
statement in the localised file in a handler that converts the failure to the demanded type.

It ran on 12 candidates on `794c8e50` and solved nothing. The real fix does not touch the call site; it
installs a decorator that validates the *callable's return type* before the call happens. The mechanism was
expressible; the semantics were not. Recorded as a failed operator, not a pending one.

## 7. What this establishes

**Established, with execution:**
- A reproducible 28-task fail-to-pass set exists, mined by rule, with the rejection counts published.
- Assertion-based localisation generalises: 17/28 top-1, 27/28 within five, 0 blind, no model calls.
- The current operator set solves **0 of 28**. It was fitted to 8.

**Not established:** anything about hard benchmarks. Two pure-Python repositories with small, recent
histories; the mined tasks are the easy end of open-source practice because they are commits a maintainer
rotated a test alongside a small source change. **No SWE-bench, Terminal-Bench or OSWorld task has been
attempted by this system, and no benchmark row exists or is claimed.**

**Next bottleneck, named by the distribution rather than by an anecdote:** 11 of 28 need a function that does
not exist anywhere in the file, and the remaining 11 need multi-line restructuring. Every operator built in
four rounds recombines what is present. That is the wall, and it is now measured across 28 tasks instead of
guessed from one.
