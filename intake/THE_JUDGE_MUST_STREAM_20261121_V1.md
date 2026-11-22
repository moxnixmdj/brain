# The judge must stream — and batching it was worth −12 items

**Date:** 2026-11-21 · **Authority:** NONE · `truth.achieved` stays `false` · **$0**, 0 model calls
**Instruments:** `batched_oracle_v1.py` (`judge_stream`), `body_grammar_v1.py`, `shape_and_synonym_v1.py`
**Tests:** `canonical/tests/test_batched_oracle_v1.py` (8 passing)

---

## 0. A self-inflicted regression, and what it proved

After the composition grammar took the cohort to **15/32**, I introduced a chunked judge to
deal with one pathological item. The next full run scored **3/32**.

The cause was not the grammar. It was that `shape_and_synonym_v1` still called the *batched*
judge, and the batched judge had gained a rule derived from the budget:

```python
allowance = max(1, int(timeout / max(len(bodies), 1)) - 1)
per_body_seconds = max(1, min(int(per_body_seconds), allowance))
```

With 60 candidates and a 40 s budget the allowance collapses, the worker is killed, and
**every** verdict comes back false — including the correct one. A judge that fails closed on
*correct* answers is worse than no judge.

Wiring the **streaming** judge in restored 15/32 and cut the cohort from 220 s to **163 s**.

## 1. Why streaming is the right shape, not a patch

The judged object is tiny and the candidate list is long. Under batching, the outcome of a
600-candidate list is one value: all-verdicts or none. Three separate failures came from that:

| failure | consequence |
|---|---|
| one hanging candidate | the whole item's verdicts are lost |
| budget ÷ candidates | allowance collapses; correct answers scored false |
| a pass early in the list | still waits for every later candidate |

Streaming fixes all three at once: the worker prints one line per verdict and **flushes**, the
caller stops at the first pass, and the process is killed either way. A pass that occurred
before a hang survives the hang.

`judge_stream` also reads on a daemon thread, because a blocking `readline` cannot be
interrupted by a deadline — the first implementation honoured neither its timeout nor its
early exit and hung the whole run.

## 2. Measured effect

| configuration | full sympy cohort | wall time |
|---|---|---|
| batched judge, 60 candidates | **3/32** | 233 s |
| streaming judge, 60 candidates | **15/32** | **163 s** |

Per item, the trials actually spent are small once ordering is right: `use` 1, `totient` 3,
`isprime` 4, `is_square` 4, `jacobi_symbol` 15.

## 3. Tests that pin the failures

Eight tests, each written from a real failure:

- `test_stream_finds_the_pass_at_the_right_index` — a pass at index 2 is reported as index 2;
- `test_a_hanging_candidate_does_not_cost_the_item` — `sympy.prime(10**9)` never returns, and
  the good candidate after it is still found;
- `test_allowance_never_exceeds_the_budget` — the budget derivation still exists;
- empty candidate lists, and positive/negative agreement with the hidden test.

## 4. Also fixed in this pass, all mechanical

- **stdlib lookalikes.** `index.args` is a tuple, so `index.args.index` is Python's tuple
  search and hangs a symbolic object. Paths whose head is a stdlib container are not generated.
- **`stated_symbols` was junk.** Tokenising the prose and keeping every word that matched a
  module member produced **`two`** and **`second`** for item 192. Stated symbols now come from
  the stub's own imports and annotations, where `Matrix` is actually named.
- **Cheap-first reordering was rejected by measurement.** Moving property reads ahead of the
  combinatorial block pushed `eq.lhs - eq.rhs` from 169 to 514 and removed
  `Matrix([first, second])` from the space entirely. Reverted, with the reason recorded in the
  code so it is not tried again.

## 5. Status

15/32 on the full no-dependency sympy cohort, 163 s, zero model calls.

Still unsolved and classified: 5 vocabulary (194, 183, 184, 185, 188), 3 shapes the grammar
does not admit (176, 177, 180), 4 object construction with nested cross-parameter reads
(181, 182, 189, 190), 1 relative-import path (186), 1 throughput limit (191 — passes alone in
0.4 s, never inside a batch), 1 benchmark defect (203).

`truth.achieved` remains `false`. 15/32 = 47% of a 32-item no-dependency sympy cohort is not a
benchmark score and is not comparable to the 51–59% frontier figures on the full 328.
