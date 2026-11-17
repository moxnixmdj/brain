# Why one experience is not enough

**The claim.** *"Instant learning and instant learning in a new environment are solved perfectly. So give the
model the smartest actions, let it experience each once, and it has them permanently — therefore every problem
on a computer follows, including frontier software engineering."*

**The answer: two of the three terms are solved, and the third is the whole ceiling.** Measured, not argued.

```
P(correct action)  =  REACH  ×  SEARCH  ×  VERIFICATION
                      ^         ^          ^
                      |         |          +— solved, exact: run it and compare. 53/100 on real bugs, 0 model calls.
                      |         +———— solved, bounded: AST search, CEGIS, Z3, 100k-program inducers.
                      +———————— NOT moved by experience. This is what everything below measures.
```

`REACH` is the fraction of correct answers a method can even **name**. Experience adds instances of actions that
are already nameable. It does not add names. So *"is one experience per action enough?"* is exactly the question
*"does reach saturate?"* — and that is a number.

## 1. Reach is an asymptote, measured on 500 real tasks

500 real SWE-bench Verified tasks, 2,178 fix pieces cut from the real merged pull requests that closed them.
Each piece records the operator that rebuilds it and whether **any other task's** fixes ever produced that
operator.

| measure | value |
|---|---|
| fix pieces rebuilt by no operator any other task produced | **75.2%** (1,638 / 2,178) |
| coverage with *every other task* as experience (the asymptote) | **18.7%** (407 / 2,178) |
| coverage while streaming the tasks in order | 16.7% (364 / 2,178) |
| distinct operators needed for everything reachable | **43** |
| largest expressible real edit | `delete`, **348 pieces** (16%) — a structural removal |
| does the mutation grammar have a `delete` family? | **no** (`can_delete_a_node = False`) |

The asymptote is a measurement, not an assumption: an independent leave-one-out count gives 407 pieces against
the recording's own 437, and the 30-piece difference is exactly the operators that exist only inside their own
task — which a leave-one-out view cannot hand you.

**And it does not grow.** Coverage by experience quartile: **0.151 · 0.178 · 0.157 · 0.183**. A quarter of the
corpus of experience is worth as much as none of it. That is what "reach saturates" looks like when you plot it,
and it is the direct refutation of "let it experience each once and it learns them permanently" — permanent or
not, *most of what real fixes need was never in the vocabulary to begin with.*

## 2. The same wall, from the other side, on 100 real bugs with real outcomes

HumanEvalFix's six bug types, each classified by **which edit shape the fix requires** — with "in the grammar"
read out of the mutation search's own source, not typed in by me:

| bug type | required shape | in grammar | repaired |
|---|---|---|---|
| value misuse | `VALUE` | **yes** | **22/30 = 0.73** |
| operator misuse | `OPERATOR` | **yes** | **10/14 = 0.71** |
| function misuse | `CALL_FUNC_SWAP` | **yes** | **5/6 = 0.83** |
| variable misuse | `RENAME` | no | 4/12 = 0.33 |
| missing logic | `INSERT` | no | 6/19 = 0.32 |
| excess logic | `DELETE` | no | 6/19 = 0.32 |

**Perfect separation: every in-grammar type ≥ 0.71, every out-of-grammar type ≤ 0.33. Separation 0.42. Zero
anomalies.** In-grammar pooled 74%, out-of-grammar pooled 32%.

The search does not *fail* on out-of-grammar defects — it exhausts and correctly reports `OPEN`. The ceiling is
the space, and the tree already said so in its own record:

> *"…`i.price_cents` → `i.price_cents * i.qty` is outside the grammar, so three escalated engines burned 105 s
> and every one of them was right to report OPEN — **the search space, not the search, was the ceiling.**"*

## 3. A new environment changes the currency, not the ceiling

Four real machines (filesystem, git, tarball, sqlite), opaque atoms, effects learned only by execution:

- adaptation costs **29 trials** per environment;
- it pays back only after **25.78 requests** in that same environment;
- it is strictly worse for the first request, always.

Total cost is `O(machines × adaptation) + O(requests)` with unboundedly many machines. So instant learning in a
new environment is **real and is a law** — a change of currency from requests to environments, not a free lunch,
and it does nothing at all about reach: the atoms are still *given*.

## What is true, and what is false

**True.** One execution plus a computed sufficiency verdict is enough to know an action's consequence, where the
survivors agree. Instant learning in a new environment is real, as a cost law. Verification by execution is
exact, cheap, and the reason any of this can be trusted. Search over a fixed grammar is effective precisely on
the defects inside that grammar. Instant knowledge (induced operators recalled, never trained into weights) is
real and already exists here.

**False.** That experience is the limiting term — *reach* is, and experience does not move it. That competence
follows from consequence knowledge: knowing what an action does is silent about which action to take when the
needed action has no name. That more experience makes it permanent — permanence holds only where survivors
agree. That a benchmark is a frontier measure: **SWE-bench Verified was retired in February 2026 because
frontier models reproduce its gold patches from memory.** That contamination touches nothing in this round
because nothing here proposes or generates a patch at all.

**Not answerable, and declined.** Whether any of this constitutes a sentient creature. It is not measurable by
anything in this tree, and every claim about it would be a claim without evidence. What *is* measurable is that
the system's behaviour is now predicted by a law with three terms and no free parameters about its inner life.

## The single bottleneck, and the one build that moves it

**REACH — the set of edits the proposer can name.** Not search (bounded and measured), not verification (solved),
not memory (measured, 4.8% exact replay), not environment adaptation (a cost law).

The *wrong* next move is the tempting one: hand-add `INSERT`, `DELETE`, `RENAME` families to the grammar. That
buys exactly the three defect types you named and nothing else, and it is **the same defect as the index rebuilt
once more** — this tree already measured that mistake at 6,261 wrong transitions out of 19,648. A `delete`
family does not know *which* node to delete.

The right move follows from what a failure actually gives you, for free:

> A failing test is a **witness**: a concrete input, and the value the answer must have. A traceback **localises**
> the site. Between them they specify a function at one node — *this input must produce that output* — and a
> function on concrete values can be **inverted by evaluation**, not by enumeration. The alphabet for the
> inversion is read from the world (the repository's own identifiers, attributes, calls and literals), never
> from a corpus and never from a model.

That is derivation from the failure instead of enumeration over a hand-written list, and it is the same law this
tree has been climbing for four rounds: observation → determinacy → repair → sufficiency → vocabulary growth →
**reach**. Each round turned a fixed vocabulary into one derived from the failure; this round measures that the
fixed one is the ceiling, and says exactly what must be derived next.

## Law block

```
canonical/verification/CAPABILITY_LAW_20261116_V1.json, `reach` block, sha-pinned
  real_tasks = 500   real_fix_pieces = 2178
  coverage_with_every_other_task_as_experience = 0.1869
  never_rebuilt_by_any_other_task             = 0.752
  repair_in_grammar = 0.74   repair_out_of_grammar = 0.32
  grammar_can_insert_a_node = False   grammar_can_delete_a_node = False
```

`p_correct` unchanged at **0.2978**. This round does not move it; it says why it is where it is, and which single
term would move it.

## Reproduce

```
python3 canonical/swe_kernel/reach_of_the_grammar_v1.py \
  --json canonical/verification/REACH_OF_THE_GRAMMAR_20261116_V1.json
python3 -m pytest canonical/tests/test_reach_of_the_grammar_v1.py -q      # 11 tests
python3 -m pytest canonical/tests/test_capability_law_v1.py -q            # 8 tests, re-pinned
python3 canonical/swe_kernel/capability_law_v1.py --pinned                 # refuses if a receipt moved
```

The eleven tests are built to catch this file congratulating itself. One proves the classification is driven by
the grammar's **source**: delete the `CALL_FUNC_SWAP` family from a copy and `function misuse` must fall out of
grammar. One asserts that coverage is **flat** across experience quartiles — if it grew, the law would be refuted
by its own receipt. One holds the recomputation to the independent recording (437 vs 407, and the 30 explained).
One asserts **zero anomalies** in the separation, because a law with an unexplained exception would have to be
stated as one.
