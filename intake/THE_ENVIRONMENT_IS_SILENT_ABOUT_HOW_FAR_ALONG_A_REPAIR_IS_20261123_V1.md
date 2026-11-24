# The environment is silent about how far along a repair is

**Date:** 2026-11-23 · **Branch:** `arena/eac85348-brain` · **Base:** `68bf0400`
**Authority:** NONE__PRODUCER_RUN_SANDBOX_MEASUREMENT · **Model calls:** 0 · **Weights:** unchanged
**Organ:** `canonical/runtime/the_witness_carries_the_distance_v1.py`
**Tests:** `canonical/tests/test_the_witness_carries_the_distance_v1.py` (23 passed)
**Corpus:** 82 real upstream fixes materialised from the repository's own mined corpus
(`pypa/packaging` 71, `hukkin/tomli` 15, `pallets/itsdangerous` 1)

---

## 0. The requirements this answers, and the §2 boundary

Own weights, **zero model calls at runtime**, **zero knowledge house**, everything derived
rather than brute-forced, instant knowledge external, Elon's law, insanely fast, nothing
claimed that was not run.

§2 stands as recorded: forbidden is *parameters acting as a lookup of memorised world facts*
and any runtime dependency on another model; allowed is an external, inspectable, editable
store the system computes with. This round adds no weight and saves nothing: every number
below is computed at run time from the repository's own test output. The §2 test holds.

---

## 1. What the project already said, which is why this round needed no new idea

The bottleneck was already written down, twice, by instruments that had measured it:

`python_test_guided_patch_search_v1._run_tests`, in its own docstring:

> cwd at the repository root → `errors=1` (`No module named 'calc'`)
> cwd at the source directory → `failures=1` (`-1 != 5`)
> **"Both score 1, so no edit to the source can ever strictly improve the metric and the
> repair loop reports `OPEN__NO_STRICTLY_IMPROVING_CANDIDATE` for every bug."**

and `FIVE_THOUSAND_DOCUMENTS_CHANGE_NOTHING_BECAUSE_THE_SEARCH_CANNOT_SAY_CLOSER`:

> **"The search has no measure of distance to the part it is trying to reach."**

The objective is `_score`, which counts failing tests and returns an integer. Two
behaviourally unrelated programs score the same, so the space has no order, so the search
cannot step.

**The field measures this and does not descend it.** FeatureBench (ICLR 2026) reports a
*Passed Rate* beside Resolved Rate — "the average fraction of fail-to-pass tests passed per
task, serving as a soft indicator of partial correctness" — and on its hard real-world set
GPT-5.1-Codex reads **20.0% resolved against 60.2% passed**. That forty-point gap is the
gradient, used as a reporting statistic. Gradient-Based Program Repair (2026) is the honest
attempt to descend it, but it needs a differentiable program, so it needs a neural
surrogate, so it needs training — which cannot be this project's runtime. **The
differentiability was never necessary**: a test already computes both operands and prints
them.

---

## 2. What was built

`the_witness_carries_the_distance_v1` reads a pytest run as **typed witnesses** rather than
a count, and scores a candidate as `(gates_satisfied, −total_distance)` — lexicographic, so
one more gate always wins, and among equals the closer one wins.

| failure shape | read from the test's own output | distance |
|---|---|---|
| expected/observed mismatch | `assert -1 == 5` → 4 vs 5 | relative deviation |
| expectation not met | `Failed: DID NOT RAISE InvalidMetadata` | 1.0 — the guard is absent and the test names it, plus the locals that arrived |
| wrong/reachable but unparsed | a section with no recognisable assertion | 1.5 |
| escaped exception | `AttributeError` | 4.0 — never reached the assertion |
| named with no evidence | summary line only | 8.0 |

Distances are **typed rather than scalar** because real failures are not all numeric: a
`DID NOT RAISE` has no operands at all, and an escaped error has no value yet. The scale is
chosen so a whole-magnitude value error costs about the same as an entirely absent guard,
which is what makes the ordering meaningful *across* kinds instead of only within one.

---

## 3. What was measured — including where the idea failed

### 3.1 The instrument had to be repaired before it could measure anything

`source_paths()` exists because of a defect that **invalidated a whole measurement pass**:
with only the repository root on `PYTHONPATH`, a `src/` layout project imports the
**installed** copy from site-packages. `import packaging` read site-packages, not the file
under repair, so every candidate edit was invisible and every candidate scored identically.
That failure is indistinguishable from "the search has no gradient" while being an
instrument reading the wrong file. Four other parser defects were found the same way:
multi-word section titles, a section counted as a second gate, `SUBFAILED` (pytest-subtests)
unknown to the summary vocabulary, and a gate set taken from the candidate's own output —
which gave a program **that cannot import** a perfect "0 of 0" score.

### 3.2 A real fix is visible to both objectives — the hypothesis was WRONG here

| | old integer | new objective |
|---|---|---|
| can step from buggy source to the real fix | **79 / 80** | **79 / 80** |
| blind spot (old flat, new moves) | — | **0** |

At the granularity of a **whole real fix**, the integer already works. A better scorer buys
nothing there, and claiming otherwise would be the false certificate this project forbids.

### 3.3 A partial fix is where they differ — and where both are mostly blind

Applying only the **first hunk** of a real multi-hunk repair, on 50 fixes:

| | result |
|---|---|
| old metric ranks the half-fix as progress | **10 / 50** |
| new objective ranks the half-fix as progress | **12 / 50** |
| verdict flat: `[before, half, fix]` identical | **29 of 50** (patterns `[1,1,0]` ×9, `[2,2,0]` ×5, `[4,4,0]` ×4 …) |

So the new objective is **strictly more informative — it never loses a step the integer
sees, and gains two** — but it does not transform the search. Something larger is going on.

### 3.4 The finding: the test cannot see a partial repair, at all

On the **17 cases where the whole test report was flat**, I asked what else the test prints:

| signal | changed |
|---|---|
| the failing frame's locals | **0 / 17** |
| the set of source lines the traceback reached | **0 / 17** |
| *anything at all in the test's output* | **0 / 17** |

The test does not report partial progress **because there is none to report**: a
half-finished repair is still wrong, and the test says "wrong" — correctly. **The
environment is silent about how far along a repair is.** No ordering over test output can be
a gradient on this corpus, and any round that ships a cleverer scalar and claims otherwise
is lying.

### 3.5 The one signal that does move is the program's own behaviour

| observable | partial fixes it distinguishes |
|---|---|
| anything the test reports | ~8 / 50 |
| the **set of lines the program executed** | **42 / 50** |

Coverage costs one interpreter hook and one subprocess. It is not distance — **a different
path is not a nearer path**, and calling it progress would be the same lie in a new place —
but it is the one honest thing a search can act on when correctness is flat.

The module therefore separates them, permanently:

    closer(before, after)   sound progress; the ONLY thing that may gate acceptance
    novel(before, after)    a different execution path; exploration, never acceptance
    verdict(...)            PROGRESS | UNCHANGED_CORRECTNESS_NEW_BEHAVIOUR | REGRESSION | NO_CHANGE

### 3.6 Does that turn into repairs? No — measured, not assumed

Two full searches over real bugs (same mutation basis, same budget, same verifier, same
seeds; only the objective differs):

| | accepted | solved |
|---|---|---|
| old integer | 1 / 8 | 1 |
| new objective | 1 / 8 | 1 |

And per candidate over 49 real mutants:

| | count |
|---|---|
| both objectives say "not progress" | **48** |
| new says progress, old says not | **1** |
| old says progress, new says not | **0** |

Zero losses, one gain, and 48 cases where the honest label is *novel behaviour, unchanged
correctness* — the exploration signal doing exactly its job. **The objective is not the
binding constraint on this corpus.** The mutation basis is: it cannot express these fixes.

---

## 4. Verdict on the standing questions

**Q. Should the agent be goal-directed or learn everything?**
Goal-directed, broadly explored, narrowly persisted — already the project's measured answer
and unchanged by this round. The Perfect Algorithm documents state it and the replay receipts
confirm it: the scan is broad, the persisted unit is a generalisation admitted only on fresh
instances, and a raw trace is never served as knowledge. This round adds nothing to that
list, deliberately: there was nothing to add.

**Q. What exactly should be saved, and what generalised?**
The durable unit is a **refusal and a condition**, never a step sequence. This round shows
why that is not a stylistic preference: on real bugs, 48 of 49 candidates produced
behaviourally new execution paths that led nowhere. Saving them would be saving noise.

**Q. Is the "perfect algorithm that reads the web for every new environment" idea right?**
It is right about *where knowledge lives* (external, not in weights) and wrong about *what
it buys*. The local-guide and instant-knowledge tiers already exist and are completeness-gated.
What this round adds is the boundary condition: **a guide tells you how a tool works; it
cannot tell you how far you are from a correct program.** No amount of web reading supplies a
gradient over candidate edits, because the information is not in the world — it is absent
from the judgement.

**Q. What is the real bottleneck for advanced SWE?**
Not the objective. Measured: at whole-fix granularity both objectives step 79/80, and a
better objective changes 1 of 49 candidates. The bottleneck is **the candidate basis** — the
set of programs the search can even propose. 25 candidates were exhausted without a single
acceptance because none of them was close to a fix. That is where the next round goes, and it
is stated here so the next round cannot mistake a scoring improvement for a capability gain.

---

## 5. Honest limits

- **Scope: three Python repositories, 82 mined fixes, one host, one interpreter.** Not
  SWE-bench. Not SWE-bench Pro. Not Terminal-Bench. **§6 remains open.**
- **The partial-fix experiment is one construction**: "apply the first hunk". A different
  hunk order could move the 10/50 and 12/50 figures. The 17-flat / 0-locals / 0-lines result
  is the robust claim; the exact counts are not.
- **The fixed source is used as an upper-bound witness, never as an oracle.** It answers one
  question: does a real repair exist in this direction? No candidate was ever scored against
  it, and no search ever saw it. This is leakage-free but it is not a benchmark score.
- **Coverage as a novelty signal is unproven as a search heuristic.** It is measured to move
  where the test cannot; that it can be *used* to find a repair is not shown here. The two
  search arms both scored 1/8, so this round earns no capability claim.
- **`_witness` distances are hand-chosen constants** (1.0 / 1.5 / 4.0 / 8.0). They are
  justified as an ordering, not derived from a distribution, and no sensitivity analysis was
  run. A round that tunes them would be fitting this corpus, which is why this round did not.
- **The 7 unmeasured fixes are `NO_TREE`** — `prepare_corpus` sampled 82 of 87 — not
  measurement failures.

---

## 6. What I will not claim

- Not that the SWE gap is closed, or narrowed. **1 of 8 both arms.**
- Not that a better objective is the answer. Measured: 0 blind spots at fix granularity.
- Not that coverage is a gradient. It is novelty, and the module says so in its own API.
- Not that this is §6 done. It is one falsified hypothesis, one repaired instrument, and one
  precisely named next blocker.

---

## 7. Next bottleneck, named

**The candidate basis.** The search can only accept a candidate it generated, and on 25 real
bugs it generated nothing acceptable. The mutation basis flips comparisons and swaps
arithmetic; the real fixes in this corpus do not mostly look like that — they add a guard,
change a parse rule, adjust a boundary. That is the same finding
`OPERAND_INVENTION_FROM_FAILING_INPUT` and `boundary_disjunction_normalization_v1` reached
from the other direction, and it is now confirmed on the full 82-fix corpus with a fixed
measurement instrument. A scoring round must not follow this one; a **basis** round must.

---

## Reproduce

```sh
# materialise the real corpus (blobless clone of 3 repositories, no answers vendored)
python3 -c "import sys,pathlib;sys.path.insert(0,'.');\
from canonical.swe_kernel import structural_rewrite_induction_v1 as S;\
S.prepare_corpus(pathlib.Path('canonical/corpus/real_fix_commits_20261116_V1.json'),\
                 pathlib.Path('/tmp/hist'), pathlib.Path('/tmp/histwork'), limit=200)"

# the objective
python3 canonical/runtime/the_witness_carries_the_distance_v1.py
python3 -m pytest canonical/tests/test_the_witness_carries_the_distance_v1.py -q
```
