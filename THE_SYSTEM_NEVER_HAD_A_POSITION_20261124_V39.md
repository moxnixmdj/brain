# THE SYSTEM NEVER HAD A POSITION

**Round V39 · 2026-11-24 · branch `arena/50c05c04-brain`**

---

## 1. What V38 actually proved

V38's blind edit search solved nothing, and its own explanation was that the correct edit sat at an unknown
**offset** inside a large file. That explanation was a hypothesis. Nothing in eight rounds had ever measured
whether the system can say *where in a file* an edit belongs — only *which file*.

So this round measured it, against the parent-side lines the real commits touched.

## 2. The measurement

```
tasks                                        28
file identified at rank 1                    17
line identified at rank 1                     1
line within 5                                 6
line within 10                                9
line within 25                               12
never reached within 25                      16
```

And the number that explains eight rounds:

| | |
|---|---|
| right file at rank 1 | **16** |
| of those, correct line within 25 | **5** |
| of those, correct line within 10 | **2** |
| of those, correct line first | **0** |

**Even when the file is right, the line is reached in 5 of 16 cases.** The system was never failing to *write*
the fix; it never had a position to write into. V38's token search was searching a region it could not name.

## 3. Three rankers tried and deleted

A number is worthless without the alternatives that lost to it. All three were mine, and all three were
removed on measurement rather than argument.

| ranker | what it did | measured | outcome |
|---|---|---|---|
| `EXCEPTION` | lines near `raise`/`except` for the named type | generic types (`TypeError`, `NotImplementedError`, `ExceptionGroup`) sit on hundreds of lines and it was pure noise | restricted to non-generic types only |
| `SHAPE` | statements whose shape repeats across sibling functions | line top-1 1 → **0**; within-25 12 → **8** | **deleted** |
| file ordering by fusion strength | rank files by mean reciprocal rank of each ranker's first line | file top-1 17 → **11** | **reverted** |

The one ranker that helped, and only a little:

| ranker | measured |
|---|---|
| `NAMED` — lines in a function or class the **commit message** names | within-5 5 → 6, within-10 7 → 9 |

That is a genuine signal and it is small. It is also the only ranker fed by the repository's own description
of its change rather than by the failure text.

## 4. The one near-miss worth recording

`2aada00b` — a regex quantifier flipped from `*` to `+` — had its answer at **line 251, ranked second**. With
a 2-line tolerance the scorer's top-1 is false and a "within 2" would be true. Honest labels: top-1 is
top-1, and `within 5` covers it.

## 5. What this changes

Every generation mechanism built in rounds V33–V38 — keyword threading, attribute binding, collection
extension, message dequoting, exception wrapping, blind minimal edits — was applied to a *file*. None of them
was ever given a line. Their failure was over-determined, and the largest single cause was upstream of
generation.

That reframes the next step: the useful object is not a better operator, it is a **position**. Generation
should be attempted only where a ranker has support, and the honest target is not 28 tasks but the 5–6 where
the line is reachable at all.

## 6. What this does not establish

Not that no ranker could do better — three were tried and deleted on measurement, others may exist. Not that
line localisation is the only wall; it is the one that is now measured and it is upstream of everything else
tried so far.

**No SWE-bench, Terminal-Bench or OSWorld task has been attempted by this system. No benchmark row exists or
is claimed.**
