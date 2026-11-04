# Noticing Without Being Told

**2026-11-04 · branch `arena/e55485af-brain` · authority NONE · `truth.achieved` false · $0 spent**

For four rounds the creature could revise, attribute and retire — but only when an outsider said
*that was wrong*. That was the last missing piece of the loop, and it is now measured. The result is
better than I expected in one direction and worse in a more important one.

---

## 1. What it can notice, and why that isn't cheating

The synthesizer hands back a body. The creature can look at what it produced:

- **partiality** — the body raises or returns non-finite somewhere in its own domain
- **dead branch** — an arm that never fires across the whole grid
- **branch imbalance** — an arm that fires on a sliver of the domain, which is a special case
  dressed as a rule
- **ignores a parameter** — the body cannot explain variation it was given

None of these reads an expected value. The audit sees the body, the parameter names, and a grid built
from the arity. **The answer being audited is invisible to the audit**, and the report says so
explicitly (`saw_expected_values: False`) rather than leaving it as a claim in prose.

That distinction is the whole point of the round. Being told "this is wrong" and noticing "this is
suspect" are different capabilities, and only the second one scales.

---

## 2. What it actually looks like when the search is desperate

Real bodies, produced by the real synthesizer:

```python
if not (min(v, l)):          # fires on 1 of 30 probes
    return ((v / h) + 0.5)   # <- this is the actual computation
return abs((l - 0.5))        # <- and this is what runs
```

The entire real computation sits in a branch that executes almost never, and the branch that runs
ignores both `v` and `h`. The audit reads the coverage — `{0: 0, 1: 29}` — and flags it.

Pre-registered in `PREREG_SELF_AUDIT_20261104_V1.md`; **4/4 as predicted**:

| finding | measured |
|---|---|
| flag predicts wrongness | recall **0.90**, precision **1.00** |
| no false alarm on correct answers | **0 of 10** |
| misses exist | **1 in 10**, plus two constructed cases |
| never reads expected values | `saw_expected_values: False` |

Zero false alarms matters more than high recall here. A false alarm triggers attribution against an
*innocent* concept — the exact failure the previous round was built to prevent. So the audit is
deliberately conservative, and it pays for that in misses.

---

## 3. The miss is the interesting part

The one body that escaped:

```python
if v <= 0:
    return 0.5
return (concept_bad0001(v, 1, h) * 2)
```

Coverage is balanced (13/17), nothing raises, every parameter is used. It is wrong — and there is
**no visible defect**. And the constructed case is starker still:

| body | actually | verdict | audit |
|---|---|---|---|
| `return (x * x)` | wrong — fits `2x` on three points | OVERFIT | **clean** |
| `return (x + 2)` | wrong — fits `x+1` on three points | OVERFIT | **clean** |
| `return (x + x)` | correct | SOLVED | clean |

The audit cannot tell the first two from the third. Every signal here is a **symptom of desperation**:
a search that cannot find the real structure produces special cases, crashes, or ignores its inputs.
A search that finds a well-formed, total, balanced, confident wrong answer — and the search finds
that often, because three examples are cheap to satisfy — produces nothing visible at all.

This is asserted in the tests, not merely noted: `test_a_structurally_perfect_wrong_answer_is_invisible`
requires the audit to stay silent on `x * x`, and the verdict string itself says *"NOT a clean bill
of health"* so nobody can misread a quiet audit as a correct answer.

---

## 4. What this changes about the creature

The loop is now closed end to end:

```
invent a concept from examples            ->  library grows
use it as a building block                ->  answers reach further
produce a wrong answer                    ->  AUDIT FLAGS IT (9 times in 10, no labels read)
attribute which concept misled the search ->  library revises
retry the same problem                    ->  different answer
```

Nothing in that chain is now invoked by a human who already knows the answer. That is the first time
this is true, and it is the closest thing to the property the user keeps asking for that I can
honestly demonstrate: **the creature's history, its own output, and its own self-check now determine
what it does next.**

And the limit is equally clear, which is why I trust the positive part. The creature notices when its
answer is *degenerate*. It does not notice when its answer is merely *false*. Those are different
failures and only one is detectable without evidence it does not have.

A human can be wrong in the second way too — which suggests the next mechanism is not a better
audit. It is a **demand for evidence**: noticing that three examples cannot distinguish `x * x` from
`2x`, and refusing to commit. That is what a careful creature does, and it requires no oracle. It is
also what I have been failing to do all session — every instrument error I made was a
well-formed, unbalanced-by-my-own-noticing answer accepted because it fit.

---

## 5. On "the smartest approach"

Six rounds in, the honest accounting:

| round | what it added | measured |
|---|---|---|
| concept invention | reuse a named sub-idea | 4/5 → 5/5, 2.9× |
| semantic unification | see two spellings as one idea | 81/81 probes, 3 traps silent |
| lifecycle | be wrong about yourself | priors fall, junk cannot crowd out |
| attribution | find which part failed | guilty charged, innocent spared |
| totality | certify only what is defined | 2/2 partial → 0/n |
| **self-audit** | **notice without being told** | **recall 0.90, 0 false alarms** |

What has *not* changed is the underlying method: search a fixed space, score against observations I
supply. Six rounds have improved the **error structure** of that method — what it may build on, what
it may keep, what it may trust, and now when it should distrust itself. The intelligence of the search
has not grown since round one.

Whether that is the smartest approach is a question I can now answer from data rather than opinion:
**the search itself is the bottleneck, and it is unchanged.** Every wrong answer this round came from
the same source — a three-example fit accepted without knowing whether it was distinguishable. The
audit caught the degenerates. The next mechanism has to attack the fit, not the symptom.

**Non-claims.** No sentience. Pure Python over small numeric tuples; no I/O, no host execution, no
GUI; nothing here bears on reaching a shell or browser, which remain gated. The audit detects
*defects*, not wrongness — 9 of 10 wrong answers had one in this sample, and a clean verdict means
only that nothing was visibly wrong. `truth.achieved` stays false. $0 spent.

---

## 6. Ranked next moves

1. **Demand for evidence.** Refuse to commit when the examples cannot distinguish candidate bodies.
   Three points cannot separate `x*x` from `2x`; the creature does not notice this and should. This
   attacks the actual bottleneck — the fit — and needs no oracle.
2. **Domain tracking instead of rejection** (carried over): let a concept declare where it is total
   and have the synthesizer respect it, instead of discarding partial concepts.
3. **Repair rather than discard** a refuted concept, using the semantic machinery in reverse.
4. Composition of invented concepts; the front door; backlog.
