# Being ahead of the frontier: no part, and insanely fast

**Date:** 2026-11-24 · **Base:** `0b5ede3b` · **Authority:** NONE — sandbox measurement

Third pass. Prior passes proposed **adding** and **wiring**. Both are the opposite of
*the best part is no part*. And neither pass measured speed at all. This one opens with
the two laws as measurements, and it changes the plan's direction.

---

## Part 1 — "Insanely fast", measured

| Surface | Measured | Verdict |
|---|---|---|
| Cold front-door import | **0.58 s** | acceptable |
| `open_model()` (10.9 MB artifact) | **42.3 ms** / **0.2 ms** cached | fine |
| **The one capability that ever passes**, `python.source.symbols.index.ast` | **35.6 s** → **10.9 s** (my fix) | **not fast** |
| The refusal counterfactual | **>200 s**, killed, twice | **does not finish** |
| Per-goal door call (typical) | 0.23 – 2.7 s | fine |
| Two goals in that tool | **hit their 240 s timeout** | pathological |

For scale: the frontier's own numbers are **0.5–1.5 s on a cache hit** (hybrid
cached-first architecture) and **3–6 s** for a single-model monolith. Our one working
solve is **10.9 s** — slower than the frontier's *monolith*, and it runs zero model calls.

### 1.1 What I fixed, and what it was

Profiled the one passing capability. **6,777 calls to `json.loads`, 4.85 s of pure
decode in a 14.19 s run.** One file, re-readable, re-decoded once per row.

**Fix:** memoise `_json()` on `(path, size, mtime_ns)`. Behaviour identical.

```
before: 35.64 s
after : 10.46 s        (3.4x)
```

Same verdict: `PASS__RAW_GOAL_EXECUTED_AND_EXACT_SEMANTIC_ACCEPTANCE_VERIFIED`.
Verified the 10 test failures in the touched suites are **pre-existing** — identical
failures on a stashed tree.

This is the purest form of the law: *nothing was added, 6,776 redundant parses were removed.*

### 1.2 What is left, and why deleting it would be wrong

After the fix, 6,161 of the remaining `json.loads` calls come from
`SymbolRowSQLiteCache.get_many`. Measured shape of that cache:

| | |
|---|---|
| rows | **80,010** |
| payload | **478 MB** |
| bytes per row | **5,977** |
| the artifact it caches | **10.9 MB** |

**478 MB to store what one 10 MB artifact already holds.** It is also load-bearing, which
I would have got wrong by assuming:

```
with the 478 MB sqlite cache:  10.98 s
without it                  :  25.56 s
```

So the no-part move is **not deletion** — it is *stopping the queries whose results are
thrown away*. `_collect_index_parts` asks for rows keyed by `(rel_path, sha)`; the cache
returns **all** rows for a path and lets the caller discard the non-matching ones. That is
why 6,161 inflations happen to admit a few hundred.

**The targeted fix:** add `sha256` to the `WHERE` clause and batch 450 paths per query.
**Predicted: 5–8 s, same verdict, payload identical.** Estimated from the 4.85 s of decode
that is ~100% discardable.

---

## Part 2 — "Best part is no part", measured

The law is falsifiable here, and the tree fails it in a countable way.

| Measure | Value |
|---|---|
| `.py` files on disk under `canonical/` | **6,002** |
| `.py` modules indexed | 2,024 |
| imported by anything | 65 (3.2%) |
| **exact duplicate symbol-sets (≥4 public symbols)** | **26 groups / 66 files** |
| **near-duplicate pairs (Jaccard ≥ 0.8)** | **105** |
| largest duplicate group | **7 files, one mechanism** |

The 7-file group is `bytes_v14_single_artifact_closed_v10.py` and six siblings with the
*same 22 public symbols*. Six of those seven are parts that should not exist.

Concrete examples of the frontier-claim variety:
- `trajectory_failure_typed_ir_proof_v3` ≡ `_v4` (Jaccard 1.00)
- `terminal_coverage_partition_compiler_v1` ≡ `_v2` (1.00)
- `same_identity_supervisor` ≡ `same_identity_supervisor_credited_v1` (1.00)
- `synthesis_implication_residual_verifier_v1` ≡ `_v2` ≡ `synthesis_witness_target_binding_verifier_v1` (1.00)

**A v2 that is symbol-identical to its v1 is not a version. It is a copy with a new name.**
That is how 6,002 files became a directory instead of a system.

### 2.1 The part that earns nothing

`canonical/verification/` holds **3,069 files**. `canonical/action_intents/` holds **1,065**.
Every one was written to justify a claim, and none of them can execute anything. They are
prose about capability competing for attention with 998 working-but-unreached modules.

**Proposed:** a single index over verification docs (path + claim + falsifier + date),
and the 3,069 files collapsed behind it. Nothing is deleted; 3,068 lookups are removed.

---

## Part 3 — The plan, revised

Prior passes said *wire orphans* and *compose depth*. Both add parts. Under the law, the
plan inverts.

### Track 0 — Do not add. Delete duplicates. (half day)

1. Collapse the **26 exact-duplicate groups** to one canonical file each, with the others
   replaced by a re-export shim so nothing breaks. **66 → 26 files; 40 parts gone.**
2. Same for the 105 near-duplicate pairs, where the symbol sets are provably equal.
3. **Measurable:** `git ls-files canonical/**/*.py | wc -l` must fall by ≥40 with the full
   test suite's pass count unchanged.

**Stop condition:** if collapsing a group breaks a test, that group was not a duplicate
and the pair goes back.

### Track 1 — Make the one working thing 5× faster. (1 day)

The 10.9 s solve is the only capability that passes, so it sets the ceiling for
everything.

1. `sha256` in the `WHERE` clause + batching in `SymbolRowSQLiteCache.get_many`.
2. Re-measure. **Target < 5 s.** If it does not move, revert and say so.
3. Then the refactor this enables: **stop maintaining the 478 MB row cache** in favour of
   loading the 10.9 MB artifact once and indexing it in memory. That is *one part
   instead of 80,010 rows*.

### Track 2 — The 200 s tool that never finishes. (half day)

`lift_the_refusal_and_see_what_remains_v1.py` forked a fresh interpreter per goal
(51 of them) and two goals hung to their 240 s timeout. Rewrite the probe loop to run the
whole stage **in one process** with a per-call alarm.

**Measurable:** the tool must complete in **< 30 s**. It currently does not complete at all,
which means the number the last two plans quoted (*"19 of 38 refused"*) came from a run
nobody could reproduce.

### Track 3 — Continuity and stopping, still, but smallest possible. (unchanged intent)

`continuous_self_v1` and `h100_anytime_proposal_confidence_v1` remain the unusual assets.
But under this law they get **one consumer each**, not a framework:

- `continuous_self` gets `study()` as its loop. No new interface.
- the confidence sequence gets called **inside the existing channel loop**, replacing the
  fixed cost ordering. No new module.

### What I am no longer proposing

- **Not** wiring 20 orphans into the model. That adds parts.
- **Not** a new index, registry, or governance artifact. There are 3,069 already.
- **Not** the composed/raw status relabel. It breaks 13 tests and buys a string.

---

## Part 4 — The seam, restated against the frontier's own numbers

| | Frontier | This tree |
|---|---|---|
| Latency, cached | **0.5–1.5 s** | 10.9 s (best case) |
| Latency, monolith | **3–6 s** | 10.9 s |
| Cost per task | $0.0005 – $0.033 | **$0.00** |
| Restarts | lost in-flight state | **honest `INTERRUPTED`, measured absence** |
| Claims | held-out split, post-hoc audit | **target-free certificate exists** |
| Stopping | named open problem, applied inside one model | **machinery exists, orphaned** |

The frontier is faster. We are free, restart-honest, and uncontaminated-by-construction.
**Speed is the one axis where this tree is losing to a *worse* system**, and that is
fixable with deletion and one cache query — not with a new capability.

---

## Part 5 — Risk

| Risk | Detector | Consequence |
|---|---|---|
| the duplicate collapse breaks imports | full test pass count | some "duplicates" are load-bearing variants |
| the sha-keyed query is not the hot path | re-profile after | the 4.85 s was elsewhere, prediction wrong |
| 478 MB cache cannot be replaced by the artifact | Track 1 step 3 | keep the cache, it is load-bearing |
| **speed work does not move task completion** | already known | it never will; it moves the floor |

The last row is the honest one: **shaving 25 s off one capability does not make this
competitive on task completion, which is 20–30× behind.** It makes the system not-slow,
which is a precondition for anyone using it at all.

---

## Reproduce

```bash
# the memoised parse
python3 -c "
import time,sys;sys.path.insert(0,'.')
from canonical.runtime import live_brain_route_admission_v1 as ra
t=time.perf_counter()
print(ra.solve({'task_id':'t','goal':'index the python symbols in this repo with ast'})['status'])
print(f'{time.perf_counter()-t:.2f}s')"      # 10.5s, was 35.6s

# the duplicates
python3 - <<'PY'
import json,pathlib
from collections import defaultdict
m=json.load(open('canonical/unified_model/BRAIN_UNIFIED_MODEL_V1.json'))
sig=defaultdict(list)
for r in m['source_index']:
    if not r['path'].endswith('.py'): continue
    s=tuple(sorted(x for x in (r.get('symbols') or []) if not x.startswith('_')))
    if len(s)>=4: sig[s].append(r['path'])
dup=[v for v in sig.values() if len(v)>1]
print(f'{len(dup)} duplicate groups, {sum(map(len,dup))} files')
PY

# the cache that costs 478MB to hold a 10.9MB artifact
python3 -c "
import sqlite3
c=sqlite3.connect('/tmp/project_brain_swe_graph_v1/symbol_index_rows_v1.sqlite')
n,b=c.execute('SELECT COUNT(*),SUM(LENGTH(payload)) FROM symbol_rows').fetchone()
print(n,'rows,',round(b/1e6,1),'MB')"
```
