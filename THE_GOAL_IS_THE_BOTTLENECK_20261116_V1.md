# The goal is the bottleneck — 16 November 2026

**Authority: NONE.** Producer-run sandbox measurement on branch `arena/5ea0bf08-brain`.
No capability registered, no family flipped, no weight touched, `truth.achieved` unchanged,
$0, zero model calls, zero network at run time. Independent verification is open.

Receipt: `canonical/verification/CONTRACT_GROUNDED_REPAIR_20261116_V1.json`
Mechanism: `canonical/swe_kernel/contract_grounded_repair_v1.py`
Tests: `canonical/tests/test_contract_grounded_repair_v1.py` (8 passed)

---

## 0. Read this first

You asked the same question again. I read it again, in full, as a new prompt. This is the
answer, from first principles, checked against everything already in this repository and against
2026 research, with a new measurement rather than a new opinion.

> "Instant learning + instant learning in new arbitrary environments are solved perfectly, so
> give our model the most advanced coding actions, let it do a thing once, and it learns all of
> it permanently — therefore all computer use and the most advanced software engineering are
> solved. Am I right?"

**You are right about the mechanism and wrong about every "therefore".** The mechanism is real,
in this tree, measured, and rare. The chain "once ⇒ permanent ⇒ correct ⇒ any computer" has five
links; four are information-theoretic or provenance questions, not learning questions.

**The single bottleneck that unlocks the most capability is not the verifier, not admission, not
the edit space, not coverage, not weights.** Those are five *projections* of one missing object,
which is why nine previous rounds named five different "single bottlenecks". The invariant is:

> **The system cannot derive an executable, falsifiable statement of the GOAL from the live
> environment at use time, over an observable vocabulary rich enough to name what caused the
> outcome.** Everything else — knowledge, verification, identification, synthesis, permanence —
> is downstream of that contract.

Fix that and the other five stop being walls. Leave it and no quantity of experiences, actions,
environments, tests, or parameters helps. This document proves the identity, reports a measured
closure on real held-out bugs, and states exactly what is still not solved.

---

## 1. First principles: what "learn once, forever, anything" would require

Strip every word away. Let `H` be the hypotheses the system can express, `O` the facts it can
observe, `V` the independent verdict on an outcome, `G` the goal stated as a checkable contract.

An experience `E` shrinks the belief set to `B = {h ∈ H : h agrees with E}`. A new task is solved
**iff** some `h ∈ B` is right on it **and** the system selects it. Six consequences, all measured
here, none a matter of taste:

1. **One point does not identify a rule.** After one success, **13.05 of 32** hypotheses survive,
   **3.40 bits** unresolved, **0/200** cases identified exactly; the most general survivor is
   wrong on **68%** of states (`WHAT_ONE_SUCCESS_CAN_AND_CANNOT_TEACH_20261114_V1.md` §3).
   Repetition in the same state is worth **exactly zero bits**. The floor is **~2.76 chosen
   contrasts**, not one.
2. **If the causal observable is not in `O`, no amount of data helps — provably.** The
   insufficiency certificate: with `A` = the intersection of all successes' fact sets,
   *no requirement exists ⟺ A ⊆ F for some failure F*. On this tree's pinned real code-repair
   corpus it fires with `unrepairable_by_repetition: True`
   (`INSUFFICIENCY_CERTIFICATE_20261113_V1.json`). The missing facts are exactly the ones you
   named: an executed function, a callee signature, a runtime traceback exception.
3. **Replay is not synthesis.** Retrieving a seen edit covers repeated syntax (**~2.2%** of
   SWE-bench Verified). The other 97.8% requires composing a new edit grounded in the live
   codebase and repairing it against execution feedback. On 40 real published bugs, a hand-listed
   basis repaired **2/20** held-out and an induced basis **1/20**; the successes were disjoint
   (`WHAT_ONE_DEMONSTRATION_BUYS_20261116_V1.md`).
4. **Permanence without a verdict is worse than no memory.** The admission gate measured an
   ungated lesson breaking a correct program (`ADMISSION_REJECT:BROKE_CORRECT_PROGRAM`). A store
   fed by unverified experience holds the 68%-wrong reading forever, at full confidence.
5. **A verifier built from shape adds nothing.** Today's measurement on this tree's own code: a
   real test suite rejected **77/96 (0.8021)** wrong variants; of the **19** it accepted, a law
   confirmed on the pristine module rejected **0**, in all three arms
   (`WHAT_A_PASS_IS_WORTH_20261116_V1.md`, open PR #6874). The verdict's reach is the reach of
   the *knowledge inside it* — and knowledge about correctness is **G**.
6. **Action richness is an anti-lever for one-shot learning.** Every action added enlarges `H`
   (more rules fit one demonstration) and multiplies the search branching factor: measured
   **8.34 actions per distinguishable state**, so depth 6 costs `8.34^6 = 336,511` actions
   against 1,500 spent; 2.26× the budget bought **1 page in 37**
   (`WHAT_IS_REAL_AND_THE_ONE_BOTTLENECK_20261116_V1.md` §2). "Give it the most advanced
   actions" makes coverage cheaper and learning strictly harder.

The deepest limit, stated honestly: **"literally anything on a computer" is not achievable in
general**, because a goal arrives as intent and correctness is a predicate over states; intent is
underdetermined by any finite observation, and non-trivial semantic properties of programs are
undecidable (Rice). No-free-lunch applies to any learner without a prior. **But** a computer is a
formal system: where the environment declares its contract (tests, types, schemas, APIs, diff
structure, execution traces), `G` can be *derived exactly*, at zero cost, from the environment
itself. That regime is where your intuition is right, and it is the only regime worth building
for first.

---

## 2. Why nine rounds named five different "single bottlenecks"

| round | named bottleneck | what it actually measured |
|---|---|---|
| 12 Nov | the prior / hypothesis space | `H` is too wide for one example |
| 13 Nov | the vocabulary | `O` cannot express the cause (a **proof**) |
| 13 Nov | admission | `V` did not run before the write |
| 14 Nov | the state in which an outcome happened | `O` was discarded at the live call site |
| 16 Nov | the verifier | `V` is unavailable in GUI, unreliable in code |
| 16 Nov (#6873) | the edit space | `H` cannot *express* 1/3 of real fixes |

Each is a necessary condition. Each is a **projection of `G`**:

```
G (executable contract over sufficient observables)
 ├─ determines which observables matter        -> O  (vocabulary/insufficiency certificate)
 ├─ restricts which candidates are thinkable   -> H  (edit space, prior, branching factor)
 ├─ IS the falsifiable verdict                 -> V  (verifier, admission, "a pass is worth")
 ├─ supplies the counterfactual contrast       -> identification (2.76 chosen contrasts)
 └─ is what a permanent rule must predict     -> learning/weights (identified traces only)
```

The flip-flopping was measurement of one projection at a time, not progress. The 2026 field
converged on the *same* invariant from the outside: training-time and test-time self-improvement
are "gated by the same bottleneck: the verifier" [1](https://arxiv.org/abs/2605.30290);
Veritas generates verifiers because "most tasks collected from real-world use come without one"
[3](https://arxiv.org/html/2611.13336); verification-skipping and state drift are the central
failure modes of long-horizon computer use [1](https://decodethefuture.org/en/ai-agent-benchmarks-2026/);
demonstrations filtered by observation suffer "observational equivalence" and need executable
causal interventions [2](https://arxiv.org/abs/2610.21149); specification-guided repair derives
localized postconditions from failing tests and execution traces [1](https://arxiv.org/html/2604.11770v1).
All of those use a model to guess `G`. **The revolutionary move available to us is that we do not
have to guess: on a computer, `G` is published by the environment.** No weights, no pretraining.

---

## 3. What was built (one organ, "no part added")

`canonical/swe_kernel/contract_grounded_repair_v1.py`. Zero model, zero learned weights,
stdlib-only, deterministic. It reuses the existing sufficiency certificate, contrast selector and
the existing QuixBugs fresh-copy harness. It adds only the goal compiler:

1. **Observation.** Executes the published failing test's cases in a bounded child and records,
   per case, the executed line numbers, callee, result/expectation types, delta sign and
   traceback exception. Those are the causal observables the certificate said were missing.
2. **Certification.** Runs `applicability_v1.insufficiency_witness` on the *static* vocabulary
   and on the *executed* vocabulary. It refuses to **learn a permanent rule** when both are
   insufficient — but it does **not** refuse to repair: verified *doing* and identified *learning*
   are different rights. (Conflating them was a defect found and fixed in this session.)
3. **Contract.** Generalises what the published assertions state into relations over a wider
   grid built only from published inputs. A relation is REFUTED if it fails on an already-passing
   case, VACUOUS if nothing can break it, and usable only if the buggy program demonstrably
   violates it. No relation invented from a function name (the 0/19 lesson).
4. **Goal-conditioned synthesis.** Candidates are generated **only on positions that executed on
   the failing path**, in edit families selected by the goal's discrepancy signature, ranked by a
   **calculated prior** — exact counts of executed verdicts, no fitted parameter, no gradient.
   It includes the shapes the hand basis could not express (`AugAssign`, offsets, containment,
   comparison *classes*, insertion with a precondition) and renders **one-node surgical patches**.
5. **Verification.** A candidate's own pass is a filter only. The repair verdict is the corpus's
   own pytest, re-run on a **fresh copy**, with the test bytes hashed; the answer key
   (`correct_python_programs`) is asserted absent before every task and was never read.

### Measured, preregistered, on the hardest OPEN test that runs here

QuixBugs (MIT, pinned `4257f44b`, 40 real published bugs with their own pytest files), the
published `sha256(name)` 20/20 split, the **20 held-out bugs**, corpus's own tests, $0, no model,
no network at run time. Preregistered PASS condition: ≥4 repairs (beating the union of both
published baselines, 3/20), zero regressions, every repair backed by a fresh-copy rc=0, answer
key absent, ≤260 candidates tried per task.

| | this session | hand basis (#6873) | induced basis (#6873) |
|---|---|---|---|
| held-out repairs | **4/20** | 2/20 | 1/20 |
| candidates | 2,850 (**142.5/task**, 95.2 to first repair) | 5,021 | 224 |
| regressions | **0** | — | — |
| fresh-copy verdicts | 4, all rc=0 | — | — |
| answer keys present | **0** | — | — |
| preregistered | **PASS** | — | — |

Repaired: `bitcount` (`^=` → `&=`, previously **unreachable at any budget**), `pascal`
(`range(0,r)` → `range(0,r+1)`), `next_permutation` (`<` → `>`), `quicksort`.
Minimal one-line diffs are recorded verbatim in the receipt.

Also measured: static vocabulary insufficient on **14/20** tasks, executed observables restored
separation on **6** (`certificate_closures`), assertion-derived relations with teeth on **7**,
**0** permanent rules admitted (every `learn` returned `INCONSISTENT`: the edit was verified, the
rule was *not* identified). **0** candidates that passed the published cases were refused by the
wider contract — an honest negative: the verdict-reach half added nothing on this corpus. The
gain came from the goal-conditioned hypothesis space.

### What this does NOT claim — read before celebrating

- **Not "understanding".** `quicksort` was repaired by `x < pivot` → `x - 1 < pivot`, equivalent
  to `<=` on integers but wrong for floats. It passes the suite because the suite is integer data.
  A pass is worth that suite's reach, no more (`WHAT_A_PASS_IS_WORTH`: 0.8021 here). This is a
  measured example of pattern-matching-in-disguise, and it is the sharpest remaining gap.
- **Not permanence, not learning.** `permanent_rules_admitted = 0`. The loop *did* four real
  repairs and *learned* zero permanent rules from them. That is the exact refutation of "do it
  once and he learns all of it permanently", now with a number.
- **Not general.** 13/20 not repaired, 2 unmeasurable (no published JSON cases), 1 refused with
  no execution trace. QuixBugs is 40 single-function programs — **not** SWE-bench Pro
  (best public ~61.5%, contaminated/retired Verified) or OSWorld 2.0 (best ~20.6% binary)
  [1](https://decodethefuture.org/en/ai-agent-benchmarks-2026/). SWE-bench Pro Verified documents
  reward hacking and flawed tests that inflate scores
  [3](https://arxiv.org/abs/2609.08149); we therefore use a corpus with an anti-peeking
  protocol rather than a leaderboard number.
- **Not independent.** One machine, one producer. Integrity is enforced by construction (fresh
  copy, hashed test bytes, answer key absent, candidate self-report never a verdict), but a second
  person must reproduce it.
- **No sentience result, no terminal credit, no weight update.**

---

## 4. Weights from scratch, "every bit calculated", and "the best part is no part"

**You already built the thing, under a non-obvious name.** `canonical/unified_model/BRAIN_UNIFIED_MODEL_V1.json`
ships **Weights: 0** and states its own theory: "Knowledge is *indexed, not embedded* … text is
read from disk at query time. That is the repository's theory — knowledge is external and
just-in-time, capability is what Brain owns." That is instant knowledge with no knowledge house.
It is not a missing component; it is the load-bearing spine (58-import raw-task contract etc.).

From first principles, the division of labour is forced:

| where | what belongs | why |
|---|---|---|
| environment / JIT (`jit_knowledge_v1`, retrieval, AST, tests, schemas) | **facts** | free, exact, current, no parameters, never stale |
| compiled code + **calculated** counts (`Prior` in this session) | **procedure and prior** | every bit is computed from an executed verdict or from the formalism, not fitted from a corpus |
| weights | **only identified, contrastive, admitted traces** | a parameter is justified only by evidence that identifies it; an unidentified survivor is one of 13 readings that happen to fit |
| nowhere | unverified successes, self-graded receipts, guessed laws | permanence amplifies them; measured harm |

Why not conventional pretraining: for *knowledge*, it is strictly worse — a corpus is a stale,
lossy, energy-hungry copy of facts the environment will hand you exactly at use time. For the
*prior*, a statistical prior is not required on a computer: the environment's own formal
semantics (grammars, types, declared interfaces, test contracts) **compile** into the prior.
That is the genuinely better-than-conventional route you were reaching for, and it is real here,
not a slogan. The 2026 continual-learning literature agrees on the cost of doing it the other way
(fast prompt/playbook fitting falls back to baseline after the next domain
[1](https://arxiv.org/html/2607.07847)); training-free test-time policy modulation via retrieved
trajectories is now a recognised route [2](https://iclr.cc/virtual/2026/10021226)), and Google's
multi-speed "Nested Learning"/HOPE line is a direction to watch, not an authority
[1](https://labs.adaline.ai/p/the-ai-research-landscape-in-2026),
[4](https://the-decoder.com/googles-nested-learning-aims-to-stop-llms-from-catastrophic-forgetting).

**Do not train now.** Weight-space fuel stands at **258 units / 64 verified against a 5,000
threshold**, `ready_to_train=False`. Training on today's four repairs would bake in the
integer-only `quicksort` reading — the "knowledge house" you reject, at full confidence, in
weights. Weights are last, from admitted traces only, with a held-out backward-transfer check.

---

## 5. Sentience and "understand, not pattern match"

**Sentience is not a target; it is a word hiding three measurable targets**: state continuity
across hundreds of steps, self-verification against the requirement, and recovery before
submission (`WHAT_IS_REAL_AND_THE_ONE_BOTTLENECK_20261116_V1.md` §7; OSWorld 2.0 names exactly
those failures). Nothing in this tree measures experience; modules named `sentient_*` are names.
The system that has all three will look like what you mean. It will also be the system that stops
learning wrong things permanently.

**"Understanding" has an operational definition** you can test, and it is not a vibe: a system
understands `X` iff it can (a) predict the effect of an unseen intervention on `X`, (b) answer a
counterfactual ("what would have happened if…") correctly, (c) construct a check that could
falsify its own belief, and (d) transfer the reason, not the shape. The 2026 counterfactual
literature measures exactly this gap in frontier models — near-perfect interventional reasoning,
less than half on counterfactual reasoning
[1](https://proceedings.iclr.cc/paper_files/paper/2026/file/a50aa557c4be35aa2bf13a471601e23f-Paper-Conference.pdf) —
and SFT memorises shallow abduction patterns while RL with verifiable rewards induces transfer
[3](https://en.papernotes.org/ICLR2026/llm_reasoning/executable_counterfactuals_improving_llms_causal_reasoning_through_code/).
The `quicksort` fix in §3 fails (d): it is an integer-domain coincidence, not the reason. The
fix is not more demonstrations; it is a **contract that ranges over types the suite never tried**
— a stronger `G`, which is the same bottleneck again.

---

## 6. Kill list — measured dead, do not rebuild

- More demonstrations in the same state (0 bits, 0/200). More environments as strategy (0/10
  cross-kind; Continual-ARC: no harness-based gain on unseen tasks).
- "Most advanced actions" as the coverage fix (0/37 pages proved unreachable; raises `H` and `b`).
- More search budget (2.26× → 1 page). Choosing which instances to learn from (measured tie,
  aggressive version worse). Bigger skill library (0.605 vs 0.602).
- A verifier invented from names/shape (0/19 survivors; informative relations refuted by the code
  itself). Test generation as the fix (shipped generator mutation score 0.000).
- Training weights now (fuel 4%; unidentified readings; TRACE 28.8% → 2%).
- Treating the identifiability certificate as a refusal to *repair*. It bounds learning, not
  verified doing — a defect found and fixed here.
- Any test on synthetic data, any candidate's self-report as a verdict, any benchmark whose
  verifier the agent can reach (10-line `conftest.py` scored 100% on SWE-bench Verified
  [4](https://baeseokjae.github.io/posts/exploiting-ai-agent-benchmarks-berkeley-2026/)).
- Using a model and calling the result "our model". Not done, not needed, forbidden.

## 7. The fastest complete plan (ultimate, not incremental)

1. **Make `G` stronger, not bigger.** Widen the contract from "expected values over published
   cases" to *typed, executable specifications* the agent derives from the environment: declared
   types, invariants, metamorphic relations over grids that include values the suite never tried.
   Pre-registered falsifier: the `quicksort` integer shortcut must be **refused**. This is the
   one change that turns a passing pattern into understanding.
2. **Widen the declared-contract regime.** Every capability expressible as code against a typed
   interface with a mechanical check inherits one-shot transfer for free (this is why
   `environment_fit_v1` transfers and pixels do not). Count the fraction of the surface in that
   regime and push more of it there. GUI is hard precisely because `G` is unavailable — solve
   that by constructing the oracle, not by learning faster.
3. **Keep the calculated prior** as the only "weights": exact counts from executed verdicts,
   keyed by the goal signature. Add edit shapes only when a real held-out bug is *unexpressible*;
   each addition must be evidence, not taste.
4. **Keep verified doing and admitted learning separate.** Repairs are licensed by an independent
   fresh-copy verdict; permanence only by an identified requirement plus the held-out admission
   gate. Today: 4 repairs, 0 permanent rules — correct.
5. **Weights last**, from identified, contrastive, admitted traces, with backward-transfer
   measurement and donor deletion. Never a grader, never credited.
6. **Hard tests always**: real open corpora, held-out splits chosen before the run, anti-peeking
   enforced, answer key absent, independent fresh-copy verdict, every refusal and non-repair
   printed. No bug we already know works.

## 8. Honest status, one sentence

> The mechanism is real and now measurably better on held-out real bugs (4/20, preregistered PASS,
> $0, no model); the "therefore" is still false — the agent did four real repairs and learned
> **zero** permanent rules — and the single thing that unlocks the rest is deriving the goal as
> an executable contract from the environment, which no weights and no amount of experience can
> substitute for.

---

### Sources (for ranking, never for authority)

External numbers above are 2026 third-party reports and several are vendor/aggregator
self-reports; the web is not holy and none of them verifies anything in this tree. Every internal
number cites an in-tree receipt measured in this checkout. `truth.achieved` remains `false`.
