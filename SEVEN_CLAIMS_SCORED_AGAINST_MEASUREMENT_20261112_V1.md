# Seven claims, scored against measurement

**2026-11-12 · branch `arena/87f2b453-brain` · base `d9318588`**

The owner states a thesis and then a "brutal truth" that contradicts it. Both are lists of claims, and
claims are the one thing this tree can settle. Each is scored below: **real**, **false**, or **real but
with a cost the thesis does not mention**. Every figure is either measured this round or already
recorded in `canonical/verification/`; nothing is argued from plausibility.

---

## 1. "We already solved instant learning and instant learning in new environments perfectly."

**False, and the tree's own record says so.** `QUIXBUGS_ONE_FIX_TRANSFER_20261111_V1` is the
tree's own measurement on 40 programs nobody here wrote (QuixBugs: one defect, one line, published
fixes, each program's own tests as oracle). Read the two halves separately, because they differ by an
order of magnitude:

| what is asked | result |
|---|---|
| the same bug again, from the stored rule | **22 of 22** |
| a *different* program, having been taught all the other fixes | **1 of 40** as taught |
| the same, with every generalisation switched on | **3 of 40** |
| the rules the tree ships with, on any of the 40 | **0 of 40** |

The first row is exact recall, and it is genuinely perfect. The second is transfer, and it is 2.5%.
Instant learning works. "Instant learning in new environments" does not, and it is not close. Any
sentence that merges those two rows is the single most expensive error available here, which is why
this memo keeps them apart everywhere.

Note also `fixes_the_organ_refused_to_store`: **18 of 40** fixes could not even be stored (14 failed
mutation verification, 1 was judged non-generalizable, 3 could not be trained on). One experience does
not reliably become one lesson.

---

## 2. "Give it the smartest actions once and it learns them permanently."

**Partially real, and the permanence is the part that breaks.** 22 of 40 did become permanent,
verified rules. The three mechanisms that break it are all already built and all already measured in
this tree:

* `settled_admission_v1` — a demonstrated `a <= hi` → `a < hi`, applied to a same-shaped target where
  `<=` is *semantically required*, silently makes the target wrong. The rule was not wrong; its
  **scope** was.
* `rule_expiry_v1` — nothing ages a rule out when the interpreter, platform or tool inventory moves.
  The store's `invalidate()` exists and is tested, but it has to be **called by someone**.
* `skill_recheck_v1` — a rule that has been taught is not a rule that has been shown to hold.

These are not hypotheticals invented for this memo. They are shipped organs with recorded
measurements, and each names a way a permanently-stored action becomes permanently wrong.

---

## 3. "Therefore we can solve anything on a computer."

**False, and this is the load-bearing error.** It assumes the only missing ingredient is knowledge —
teach the action, done. The 2026 literature is unambiguous that this is not where the failure is, and
it names the failure the thesis is missing:

* **Negative transfer is worse than no memory at all.** STRATA (arXiv 2610.19386) measures a
  production agent whose flat memory scores **−100** on a task family a *memoryless* agent solves
  outright, because a superficially similar but directionally opposite experience ("heat the
  substance" vs "cool the substance") gets recalled and its **concrete steps copied verbatim**.
  Hermes with memory scores 30.4/35.8 where the memoryless agent scores 62.8/66.9 — a memory that
  makes an agent worse than none.
* **Harm concentrates on the hard cases.** *When Continual Learning Moves to Memory* (arXiv
  2604.27003) decomposes it: under raw trajectory memory on ALFWorld A→B, ΔRR = **+4.6** (easy cases
  preserved) while ΔNL = **−26.1** (hard cases degrade sharply). The cases that need help most are the
  ones memory damages most.
* **Abstraction, not storage, is what transfers.** The same study: raw trajectories *hinder*
  adaptation; abstract insights are safer and transfer more reliably. That is the opposite of "learn
  the action".
* **Misevolution.** *Your Agent May Misevolve* (ICLR 2026, arXiv 2509.26354): self-evolution is
  pervasive along model/memory/tool/workflow pathways even on top-tier backbones, and safety-refusal
  rates drop sharply after self-training.
* **The admission number that matters**: TAME (arXiv 2602.03224) rejected 211 of 383 self-authored
  rules — **55%** — because they fixed their trigger while breaking something that had worked.

So the honest statement is not "we solved it". It is: *the tree has a working exact-recall organ, a
2.5% transfer rate, and three shipped defences against the specific ways memory makes things worse.*
That is a real asset. It is the beginning of the problem, not the end.

---

## 4. "The brutal truth: it's a limited lookup system, we need model weights, conceptual
understanding, transfer, and reasoning."

**One of the four is unsupported by the evidence, and it is the one the owner leads with.**

**Weights are not required.** ReasoningBank (ICLR 2026, arXiv 2509.25140) is *training-free* and
beats memory-free agents by up to 8.3% absolute on WebArena, cutting interaction steps by up to 1.4
(2.8 on SWE-Bench-Verified), with cross-domain transfer. Its authors' own stated limitations are the
interesting part: LLM-as-a-judge errors pollute memory; append-only merging makes the pool swell; no
forgetting strategy. All three are memory-architecture problems, not weight problems. The tree already
has organs aimed at the third (`rule_expiry_v1`).

Weights are also not free: continual fine-tuning risks catastrophic forgetting and has no reliable
rollback. "Train the weights" is not a solution that avoids negative transfer — it is a *less
reversible* version of the same risk.

**The other three are real**, and the brutal-truth list is right about them being missing:

* *conceptual understanding* — the tree's rules are syntactic. Measured this round: one demonstration
  `a <= hi` → `a < hi` stores the literal rule **`a <= hi -> a < hi`** and refuses a target that
  merely renames the variables (`x <= top`).
* *transfer* — 1 to 3 of 40, above.
* *reasoning* — no organ here models *why* a change works, only *what text changed*.

---

## 5. "It can't work on different files or different task structures."

**Half right, half measurably wrong.**

*Different files: real.* 89 files across 15 projects, and every recovered change is cross-file by
construction — that is what the corpus is.

*Different task structures: this round measured it and the answer is the opposite of the obvious one.*
I built `alpha_safe_rewrite`, which generalizes a demonstrated operator change across **alpha-renamed**
code — the one generalization that needs **no oracle**, because two statements differing only in the
names of their free variables are the same statement. On the same 607 applicable changes:

| | covered | of | coverage |
|---|---|---|---|
| as taught | 493 | 607 | **0.8122** |
| alpha-safe added | 493 | 607 | **0.8122** |

**Delta: 0.0.** And the reason is not that the weld is harmless — it is that **the organ never refuses
on this corpus**: of 330 askings, 162 are edited and 168 contain nothing the demonstration changed;
**zero** are refused at apply time. There is no refusal for a wider operator to rescue.

Why: this corpus was *selected for sameness* — pull requests found because one change repeats across
many files. Selection for sameness removes exactly the variation alpha-safety exists to bridge. And
within a file the rule is already applied by **statement text after `ast.unparse`**, i.e. after
comments and formatting are stripped, which already absorbs much of the variation one might expect.

**So: the operand-name weld is real, and fixing it buys nothing here.** Reporting it as a gain would
have been easy and false. The honest version is that this corpus cannot see the mechanism, and the
"1 of 7 structurally novel instances" figure that motivated `operator_generalization_v1` came from a
*different* corpus (single-file boundary repairs), not this one.

---

## 6. "We were trying to make our model a sentient creature."

**Not real, and the tree's own vocabulary is what makes that checkable.** The organs are named for
what they do — `rule_scope_learning_v1`, `settled_admission_v1`, `rule_expiry_v1`, `skill_recheck_v1`
— and every measurement records `producer_cognition_model_dependency_count: 0`. There is a module
named `sentient_cognitive_core_v1`; its name is a label, not a measurement, and nothing in this tree
tests for sentience because no such test exists.

The framing is also the thing most likely to produce the error in §3. A system described as a creature
that "learns permanently" invites the assumption that learning is the goal. The measurements say the
goal is **not making things worse**: 55% of self-authored rules regressed something that worked.

---

## 7. "We already solved it, with non-obvious names; use the web."

**This one is right, and it is the most useful sentence in the message.** The tree does already
contain the pieces. Found by name, all on `main`:

| the idea, by its non-obvious name | where it is | what it already knows |
|---|---|---|
| least general generalization | `concept_library_v1` (`_normalize_function_for_plotkin_lgg`), `causal_trace_to_skill_compiler_v1` (`anti_unify_workflow`), `universal_parameterized_skill_candidate_v1` | Getafix-style fix patterns |
| scope as a learned quantity | `rule_scope_learning_v1`, `operator_generalization_v1` | version-space narrowing over a finite scope space |
| negative transfer | `settled_admission_v1` | a rule may not touch a new target until its open question is settled |
| staleness | `rule_expiry_v1` | retire a rule when the world moved |
| re-verification | `skill_recheck_v1` | taught ≠ holds |

`rule_scope_learning_v1`'s own docstring states the conclusion this round re-derived:
*"the missing ingredient was never a mechanism. It was the edge between them."*

**And the edge is where the tree is blocked, for a reason that is correct and that the thesis ignores.**
The generalizing path is oracle-gated by construction:

```
OPERATOR_GENERALIZATION_REQUIRES_SCOPED_PYTHON_TEST_SUITE     verified_skill_crystallizer_v1:1428
```

Every rung above "exact statement" in this tree requires a **runnable oracle**. That gate is right —
swapping `<=` for `<` changes behaviour, so it may only ship where a test can say which is correct.
But it means the ladder is unavailable precisely where the owner wants it: **a new environment, first
try, no test suite.** That is not a bug to patch. It is the actual shape of the problem.

---

## What is real, what is not — one table

| claim | verdict | the measurement |
|---|---|---|
| instant learning works | **real** | 22 of 22 same-bug repairs from a stored rule |
| instant learning in *new* environments works | **false** | 1 of 40 as taught, 3 of 40 widest |
| give an action once, it is learned permanently | **partly** | 22 of 40 stored; 18 refused; 3 organs exist for undoing it |
| therefore anything on a computer is solvable | **false** | negative transfer: memory −100 where memoryless solves; ΔNL −26.1 on hard cases |
| it needs model weights | **false** | ReasoningBank is training-free, +8.3% abs, 1.4–2.8 fewer steps |
| it needs conceptual understanding, transfer, reasoning | **real** | rules are syntactic; the weld is measured |
| it fails on different files | **false** | all 607 changes are cross-file by construction |
| it fails on different task structures | **unmeasured by this corpus** | alpha-safety delta **0.0**, because 0 of 330 askings are refused |
| we already built the pieces under non-obvious names | **real** | five organs, table above |
| the real blocker is a missing mechanism | **false** | the blocker is a missing *edge*, and the edge is oracle-gated |

---

## What I did not do, and why

* **I did not re-run QuixBugs.** The record is hash-pinned and the organ changed since
  (`69e7b7de`-era fixes). Re-running would produce a *newer* number, which is worth doing — but the
  figure that decides the owner's claim (1 of 40) is the one on record, and re-running it would
  quietly substitute a different measurement for the one being argued about. Flagged as the next
  measurement, not skipped.
* **I did not build the operator-generalization path into the one-example organ.** It is already
  built (`operator_generalization_v1`), and it is oracle-gated on purpose. Wiring it in without an
  oracle would be exactly the negative-transfer failure STRATA measures.
* **I did not "fix" the operand-name weld as if it were a win.** It is a real weld with a measured
  cost of zero on the only corpus that can see it. Shipping it as an improvement would have been a
  false claim, and the tool that measures it is the deliverable instead.

## The fastest real route, ranked

1. **Re-run QuixBugs on today's organ.** Cheapest real number available, and it is the one the
   thesis rests on. Hash-pinned, self-contained, its own oracle.
2. **Move the alpha-safe operator into the organ** — not for a gain, but because it costs nothing,
   cannot change behaviour, and removes a refusal class that *will* appear in a corpus not selected
   for sameness. Must be measured on a corpus that contains refusals, which this one does not.
3. **Wire `settled_admission_v1` in front of every lesson that reaches a new target.** This is the
   highest-value change of the three, because it is the only one aimed at the failure the literature
   says dominates: memory that makes things worse on the hard cases.
4. **Build the oracle-free rung the ladder lacks.** The gap is not "more general operators" — it is
   *what may be applied when no test can run*. Alpha-renaming is one instance. A second is a change
   whose applicability is checked by the target's **own structure** (the name it reads, the import it
   has) rather than by a test. That is the actual research question, and it is where the tree is
   genuinely blocked.

## Receipts

```
test_what_the_operand_names_cost_v1   19 passed
corpus refetch                        15 PRs / 89 files, hash-verified against the record
alpha-safety delta                    0.0 on 607 changes (162 askings, 168 not applicable)
organ refusals in corpus              0 of 330 askings
```

Zero model calls. $0. `truth.achieved` untouched. This round makes **no capability claim**: it scores
claims and reports one measured null.
