# A lesson is a substitution. An edit is a composition.

*14 November 2026. Branch `arena/98e3c624-brain`. Authority: NONE. `truth.achieved` stays `false`.*

The question: *"We solved instant learning and instant learning in new arbitrary environments. So can
we give the model the smartest actions, have it do each one once, and have it learn them all
permanently — the most advanced coding and any computer use?"*

**Short answer: no. The reason is now measured, and it isn't the one we assumed.** The problem is
not how fast the system learns or how good its lessons are. A lesson is **one substitution**. A real
edit is **several substitutions that have to be right together**. Learning faster makes each
substitution more reliable. It does nothing about how many have to land at once — that number comes
from the task, not from the learner.

---

## 1. What is real and what is not

| Claim | Status | Evidence |
|---|---|---|
| Instant learning is solved perfectly | **Not real.** The tree retracts it in its own header (`INSTANT_LEARNING_COMPLETE_SOLUTION_2026.md`) | — |
| A lesson learned once transfers to another repository | **Real but narrow.** 0.573 coverage at precision 1.000, but 537 of 562 correct changes are one kind of change | prior round |
| Doing actions once solves whole tasks | **Not real.** 8 real held-out pull requests: **0 solved**; 1 of 47 files exactly right | `ACTION_CHAIN_TO_TASK_20261114_V1.json` |
| A better selector would fix it | **Not real — measured this round.** A *perfect* selector over every lesson in all 8 repositories reaches **3 of 47 (6.4%)** | `COMPOSITION_GAP_20261114_V1.json` |
| Transfer to new *environments* (GUIs, operating systems, arbitrary apps) | **Not measured anywhere in the tree.** Repository-to-repository transfer is not environment-to-environment transfer | — |
| The same mechanism covers any computer use | **Not real yet.** Code has a free verifier (tests); a GUI doesn't. OSWorld 2.0 failures are lost constraints, incomplete state, and unverified outcomes, not missing actions | arXiv 2606.29537 |
| Sentience is the missing ingredient | **Orthogonal.** No definition of sentience changes the count of places an edit must touch | below |
| No knowledge stored in parameters | **Right — and 2026 research backs it** | §3 |

## 2. The measurement that settles it

Instrument: `canonical/tools/the_composition_gap_20261114_v1.py`. Record:
`canonical/verification/COMPOSITION_GAP_20261114_V1.json`. Tests:
`canonical/tests/test_composition_gap_v1.py` (5 tests; one of them pins the record).

Setup: 47 real changed files from 8 real pull requests, none of them used in any earlier round (the
42 excluded names are in `excluded_prior_pull_requests_20261114.json`). Each target file was offered
**every other changed file in all 8 repositories** as a demonstration, with a perfect selector — if
*any* lesson produced the developers' exact text, it counted.

| Outcome | Files |
|---|---|
| Some lesson in the pool produced the developers' exact text | **3** (6.4%) |
| A lesson produced a candidate, but not the developers' text | **30** |
| Every lesson refused | **14** |
| Edits that are a single substitution | **6** |
| Edits that need several separate changes | **41** |
| Of the 30 near-misses: organ changed **fewer places** than the developers | **29 of 30** |

Among the 30 near-misses, the developers changed a median of **5.5 separate places** per file. In
**18 of them the organ changed exactly one.** Real examples from the record: the developers updated a
type annotation, added the matching import, *and* rewrote the docstring. The organ did the annotation
and stopped.

We also checked whether the near-misses were really missing knowledge — a name the lesson had never
seen. Only **8 of 30** needed one. The other **22** needed nothing new. Every piece was already in the
file or the lesson; what failed was **putting the pieces together**.

So there are three failure modes that look the same from outside, and we ruled them out one at a time:

1. **Selection** (picking the wrong lesson): ruled out. A perfect selector reaches 6.4%.
2. **Missing knowledge** (missing names or facts): a minority, 8 of 30.
3. **Composition** (making several coordinated changes serve one goal): **the dominant failure.** The
   organ (`edit_by_example_v1.py`) has no operator for it. It applies a literal diff, once.

### The arithmetic, stated with its limits

Say one substitution lands with probability `p` and an edit needs `k` of them to be right together.
Then a file succeeds with probability about `p^k`, and a task of `F` files with about `p^(k·F)`. Doing
an action once and keeping it forever raises `p`. It can't lower `k`, because `k` is a property of the
edit. **This is why "do it once, learn it permanently" can't grow into "any task".**

Limits: this assumes the substitutions are independent and equally reliable. It's an illustration of
an upper bound, not a measured long-horizon result. The measured numbers are the table above. For
context, METR (Jan 2026) found that frontier agents' time horizons drop below one hour once 80%
reliability is required.

## 3. Weights vs. knowledge: the owner is half right, and the half that's wrong is the bottleneck

Two 2026 results split the law exactly in two.

**Facts → keep them out of weights (the owner is right).** arXiv 2607.11020 (Jul 2026): weights
"store content without creating an address for it". For facts that have to be combined or survive
later writes, context is the reliable channel: **83%** in context vs **70%** for the best
weight-writing method vs **40%** bare. The tree's instant-knowledge organs (`canonical/runtime/jit_knowledge_v1.py`,
`answer_memory_v1.py`, `associative_memory_v1.py`, `acquired_operator_memory_v1.py`) are the right
design for knowledge. The 8 name-gap cases above are exactly the kind of thing they should supply.

**The composition rule → this is the one thing that has to be a part (the law, read literally,
would drop it).** arXiv 2604.27707 (Apr 2026, *"Contextual Agentic Memory is a Memo, Not True
Memory"*) proves a generalization-gap theorem. Retrieval-based memory has a **provably lower ceiling on
compositionally novel tasks, regardless of context size and retrieval quality**, and *"only encoding
the composition rule into weights resolves the gap entirely."* In-context learning activates rules the
model already has. It doesn't create new ones. The theorem's bound also covers *learned* retrieval:
better retrieval raises the hit rate but never removes the bound.

The measurement in §2 shows the same thing at small scale, on our own organ. Retrieval with a perfect
selector reaches 6.4%. What's missing is the operator that combines, not the library it draws from.

**Why this doesn't violate "the best part is no part" or "no knowledge house":** a composition
operator is **computation, not stored content**. It holds no facts about any repository, API or
person. It holds how to make several changes serve one intention: keep the import in step with the
annotation, keep the docstring in step with the signature, keep every caller in step with the callee.
Every bit can be calculated and checked. The owner's own clarification — *"it's okay to have
parameters but every bit must be calculated; I don't want those parameters to be a knowledge house"* —
allows exactly this part and nothing more.

**The decision the owner has to make:** authorise the composition operator as the one calculated
part, with every fact supplied from instant knowledge. This document doesn't build it. It names it,
because building it unannounced would sneak in a part the owner hasn't approved.

## 4. Sentience

Making the model "a sentient creature" doesn't change any number in this document. A sentient agent
that applies one substitution where five coordinated changes are needed still gets the file wrong. If
"sentient" means *understands its intention well enough to keep every consequence consistent*, then
that is the composition operator described above — not something extra. The engineering target is
**understanding as composition under a verifier**. It's measurable. Sentience as such is not.

## 5. The single bottleneck, and the smartest next step

**The bottleneck:** a **composition operator**, meaning the ability to turn one intention into the
full, coordinated set of changes it implies, with facts pulled from instant knowledge rather than
stored. Ranked by what this round measured:

1. **Composition operator** — the cause of 29 of the 30 near-misses and the gap between 6.4% and the
   task. Calculated, not knowledge.
2. **Outcome verifier per environment** — code has tests. GUIs and arbitrary apps don't, which is why
   "any computer use" can't be claimed until each environment has a check for *what the end state
   must be*, not just for which action ran.
3. **Instant-knowledge supply** — already in the tree. It covers the minority knowledge cases (8 of 30).

What **not** to do, with reasons:

- More actions or demonstrations: measured to make things worse (36.05 → 31.35).
- A better selector: measured ceiling 6.4%.
- A bigger knowledge index: the theorem bounds retrieval regardless of quality.
- Claiming environment transfer from repository transfer: different claims; only the latter is measured.

**How to test it honestly:** the target is the record in this commit. 47 real files, 8 real pull
requests that no earlier round touched, scored on exact match against the developers' text, with
whole pull requests as the unit that counts. `test_the_committed_record_still_says_the_pool_cannot_fill_the_corpus`
is allowed to fail the day a composition operator moves these numbers. Then this document gets
rewritten to match, rather than the record being re-run until it agrees.

## Sources

- arXiv 2604.27707 — Contextual Agentic Memory is a Memo, Not True Memory (Apr 2026)
- arXiv 2607.11020 — Can a Language Model Learn Facts Continually in Its Weights? (Jul 2026)
- arXiv 2609.18842 — Infinite-Parameter LLMs (Sep 2026; weights beat prompts only on long multi-hop evidence)
- Doc2Weight, EMNLP 2026 Findings
- METR Time Horizon 1.1 (Jan 2026)
- OSWorld 2.0, arXiv 2606.29537
