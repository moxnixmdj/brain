# A goal is an effect, and the call is derived from it

**Date:** 2026-11-21 · **Authority:** NONE · `truth.achieved` stays `false` · **$0**, 0 model calls, 0 stored parameters
**Instrument:** `canonical/tools/effect_predicate_binder_v1.py` · **Tests:** `canonical/tests/test_effect_predicate_binder_v1.py` (13 passed)
**Receipt:** `intake/RECEIPT_EFFECT_PREDICATE_BINDER_20261121_V1.json`

---

## 0. The cell this closes

The repository could already say what a machine **is** (broker, world_probe), find
**documents** about it (jit_knowledge), learn **stdlib** by reading CPython's RST and
running its examples (documentation_mining), learn an **action model** by resetting and
acting (environment_learning), and instantiate a **CLI** usage line against its own
vocabulary (`an_effect_not_a_description_v1`, pygmentize).

The open cell was narrower: **a goal + an unrelated third-party library the repo has
never seen → callable paths derived from the artifact's own surface → executed → effect
verified against a predicate built from the goal → one reusable record, keyed by the
effect.**

`whitebox_introspector.rank_callables_for_goal` addressed only the first half. It ranks
names by token overlap and stops; it never runs anything, so it cannot tell `SortedList.add`
from `SortedSet.add`.

---

## 1. The law this instrument adds

> **A goal is admitted only as a predicate on observable state. The predicate is compiled
> before a candidate is chosen, it is used to derive an input on which competing effects
> disagree, and a candidate earns a record only by executing and satisfying it. What is
> stored is the effect, the evidence for it, and one binding — never the search.**

Three consequences follow, and each was forced by a measured failure:

| Failure observed while building | Consequence |
|---|---|
| `SortedList.add` accepted for "sorted and unique" — a sorted list keeps the duplicate | the goal's predicate, not a plausible output, decides |
| a hash set accepted for "sorted" — for small ints, hash order equals sort order | the battery must contain a member where they disagree |
| `PSet([3,1,2])` constructed fine and `.add()` failed on its internals | a constructor is accepted only if the object it yields is *usable* |
| `SortedSet.add` and `.update` looked like two effects | dominance over the battery, not equality of verdicts, resolves a tie |

---

## 2. What was measured

Acquisition is content-addressed: the wheel's published sha256 is checked before anything
is extracted, and **22/22 acquisitions verified**. No pip, no site-packages write, no
install. Runtime dependencies are resolved one level by pure wheel and reported; that is
what makes `sortedcollections` (needs `sortedcontainers`) runnable at all.

The battery is derived from the goal's own domain, not curated, and each member is labelled
with the impersonation it exists to kill: `SMALL_INTS` (where a hash set impersonates a
sorted set), `WIDE_INTS`, `STRINGS`, `LIST_VS_SET`. The instrument reports
`can_tell_hash_set_from_sorted_set` so a battery too weak to decide the goal is visible
rather than implied.

### The discriminating result

Same artifact, same surface, **inverted goal, opposite verified answer**:

| goal | binding | proof |
|---|---|---|
| sorted **and unique** | `SortedSet.add` | `SortedList.add` → NO_EFFECT (keeps the duplicate) |
| sorted **keeping duplicates** | `SortedKeyList.add` | `SortedSet.add` → NO_EFFECT (drops the duplicate) |

### Precision on packages that look right and are not

| artifact | class | effect the name promises | verdict | executed counter-evidence |
|---|---|---|---|---|
| `pyrsistent` | `PSet` | a set | **NO_EFFECT** | passes `[3,1,2]→[1,2,3]`, fails `[8,3,100]→[8,3,100]` and `['b','a','c']` — hash-ordered, not sorted |
| `pyrsistent` | `PBag` | a bag | **NO_EFFECT** | keeps duplicates on all four members |
| `boltons` | `IndexedSet` | a set | **NO_EFFECT** | insertion-ordered |
| `sortedcollections` | `OrderedSet` | a sorted set | **NO_EFFECT** | insertion-ordered, killed by the battery |
| `sortedcollections` | inherited `SortedSet` | a sorted set | **BOUND** | passes every member |

The `PSet` row is the important one. Under the first, single-input probe it **passed** and
would have been recorded as a sorted set. The battery replaced a coincidence with
counter-evidence. This is the difference between binding and guessing, and it is the only
reason the stored record is worth anything.

### Honest coverage

| | |
|---|---|
| packages tried | 11 |
| reached an effect test | 4 |
| unique records minted | 2 (`sortedcontainers`, `sortedcollections`) |
| correct refusals | 9 |
| median wall time, goal → stored binding | **0.709 s** (max 4.158 s, network included) |

Nine refusals were correct: `more-itertools`, `toolz`, `funcy`, `bidict`, `textdistance`,
`attrs`, `six` have no sorted-container effect; `boltons` and `pyrsistent` have names that
promise one and do not deliver it, which is exactly what the battery is for.

---

## 3. The amnesiac control

A plan is only interesting if it was *derived*. A fresh process was given the parsed
surface and the goal text — no record, no prior run, no candidate list, no store — and it
narrowed the space itself:

```
amnesiac plan from surface alone: 10 candidates
executed binder chose           : SortedSet.add
present in amnesiac plan        : True
```

That is the honest division of labour: **the surface narrows 10 candidates, execution picks
1.** Neither half is sufficient alone, and neither is a lookup table.

---

## 4. The store, and why replay is falsifiable

A record lives as a JSON file in a directory. It can be added, read, removed, and re-added
with no retraining, because nothing about it is in any parameter. It carries the effect,
the battery, an observations digest, one binding, the artifact's surface digest, and a
scope line — not the search that produced it.

Replay reconstructs the call from the record alone and re-runs the battery on a fresh
artifact directory:

| action | result |
|---|---|
| replay stored record | `ok=True`, 4/4 PASS, `derived=False`, `source=store` |
| tamper binding to `append` | `ok=False`, 4/4 ERROR |
| remove record, re-add, replay | `ok=True` |

The tampered-record row matters more than the passing one: a store that can only say yes
is a log, not a skill.

---

## 5. What this does not prove

- **Two records is not a capability.** Coverage is 4/11 reached and 2/11 minted, on one
  effect family. It is an instrument, and its numbers are small enough to be honest.
- **Goals must be compilable.** `bind` refuses an unknown goal by name
  (`UNCOMPILABLE_GOAL`). Compiling arbitrary natural language into a predicate on state is
  *not* solved here, and this receipt does not claim it.
- **One effect family only.** Sorted containers. Nothing here shows transfer to files,
  processes, network protocols, or GUIs.
- **Relations are not derived.** `confusable_with` and the footprint names were written by
  hand for two goals. Deriving them from the goal text is open.
- **`truth.achieved` remains `false`.** §6 is not met and nothing here shortens it to a
  number.

---

## 6. The one-line claim

Given an unseen artifact and a goal stated as an effect on state, a bound method is chosen
by executing candidates until one satisfies the effect on inputs deliberately built to
separate it from its lookalikes — and the record that survives is falsifiable by replay.
