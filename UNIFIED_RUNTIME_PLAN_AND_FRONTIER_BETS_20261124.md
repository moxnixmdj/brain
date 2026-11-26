# The Unified Runtime + Six Unusual Bets

**2026-11-24 · `arena/283e85a5-brain`**

Two things: (1) I tested the premise that our capabilities are sitting hidden under
non-obvious names, and (2) I researched the Nov-2026 frontier. The premise is **half right,
and the half that's wrong is the more important half.**

---

# Part 0 — The premise, measured

## What I checked

All 100 branches, 2,648 distinct runtime module names, deduplicated by name, then a real
import-graph walk from the single front door `brain_unified_model_v1.py` →
`unified_cognitive_fabric_v1.py`.

## Result

| | count |
|---|---|
| distinct capability modules across all branches | **2,648** |
| present on `main` | **2,422 (91.5%)** |
| present only on other branches | **226** |
| **reachable from the front door** | **463 of 2,247 (20.6%)** |
| **orphaned — exists, cannot be invoked** | **1,784 (79.4%)** |

| concept | total | reachable | **orphaned** |
|---|---|---|---|
| verification | 295 | 49 | **246** |
| computer use | 199 | 29 | **170** |
| world model / simulation | 112 | 6 | **106** |
| coding / repair / synthesis | 81 | 19 | **62** |
| memory / skill | 59 | 6 | **53** |
| instant learning | 9 | 2 | **7** |
| generalisation / transfer | 18 | 7 | **11** |
| self-improvement | 7 | 1 | **6** |

Roughly **110,000 lines** of capability code is orphaned.

## The premise is right about the fact and wrong about the location

They are **not hidden on other branches under non-obvious names.** 91.5% are already on
`main`, under their own names, exactly where you'd look. The problem is not *finding* them.
**It is that the unified model cannot reach 79% of what it already shipped.**

And the sharpest example is the one that matters most:

> `canonical/runtime/harbor_swe_zero_model_agent_v1.py` — **876 lines**, unreachable.
> `canonical/runtime/swe_observational_program_synthesizer_v1.py` — **1,857 lines**, unreachable.
> `canonical/runtime/tree_sitter_swe_kernel_v1.py` — 514 lines, unreachable.

Our SWE-bench Pro run scored **0/51** through a path that never touched the 876-line zero-model
SWE agent or the 1,857-line program synthesizer sitting in the same repository. **That is not a
capability gap. That is a wiring gap** — and it is the single highest-value thing we own.

---

# Part 1 — The unification plan (this is the actual work)

Nothing else on this page matters until this is done. Five steps, in order.

## 1.1 Make the reachable set honest (1 day)

Add a census test that walks the import graph from the front door and **fails CI** if a module
declares a capability it cannot be reached from. `brain_owned_python_closure_census_v1` already
exists — point it at reachability instead of file presence. We have 1,784 orphans; we should be
able to see that number go down.

## 1.2 Declare capabilities instead of importing them (3–4 days)

The front door currently requires a static `import`. 2,247 modules cannot each be imported by
one file. Replace with a **declaration registry**: each module declares
`CAPABILITY`, `PRECONDITIONS`, `EFFECTS`, `COST`, `VERIFIER`. The runtime discovers them.

We already have the pieces and they're already on `main`: `BOUND_CAPABILITY_REGISTRY_V1.json`,
`live_capability_invoker_v1`, `live_capability_composition_v1`, `capability_first_scheduler_v1`.

This is exactly the architecture DeepSeek Harness went to 170k stars with — *"everything is a
plugin: model adapter, tool registry, session log and the agent loop itself."* We are 2,247
modules into that problem and currently solving it with `import`.

## 1.3 One capability, one operator (1 week)

There are likely duplicate implementations of the same mechanism (the 38 modules using dynamic
import, 246 verification modules). Collapse to one canonical operator per capability and archive
the rest. **Keep them in git; remove them from the search space.** A registry with 246
verifiers is not a registry, it is a pile.

## 1.4 Route by what the operator can prove (2 days)

`capability_first_scheduler_v1` exists and is reached. Feed it the typed contracts from 1.2 so
routing is *evidence-based* rather than name-based: pick the operator whose preconditions match
the observed state and whose verifier can actually check the result.

This is the same insight as **Forethought** (arXiv 2607.04096): primitives with typed output
contracts, composed by a DSL, verified *at design time*, model-agnostic. Their argument maps
directly onto ours — *"correctness is a property of the program structure rather than of the
model weights."* **That is our thesis, already validated by someone else's paper.**

## 1.5 Then — and only then — re-run the benchmark

Re-run hard51 with the same oracle/nop gates. The prediction: the number moves without a single
new law being written, because the 0/51 was measured through a path that skipped the SWE agent.

**If it does not move, step 1.2 was wasted and we learn that cheaply on 3 tasks, not 51.**

---

# Part 2 — Six unusual bets, ranked by evidence

These are what could put us *ahead*, not caught up. Each one is grounded in a specific published
result or in a number we already own. I mark the ones that are bets.

## BET 1 — Attack hidden-state inference with a computed state machine, not a longer context

**The evidence — and it is the strongest single fact in this document.** The OSWorld 2.0 authors
(arXiv 2606.29537) measured why front agents fail:

> *"The lowest-scoring phenomena are those that demand state the instruction does not provide
> directly, namely **Implicit-state Inference, Multi-item State Tracking, Conflict
> Disambiguation, and Dynamic Environment**."*

And: *"they spend almost none of their budget (**under 7%**) on detecting and repairing their own
errors."* Plus **14%** of tasks extract hidden application state, **33%** bypass user-visible
interfaces to force completion.

**Why this is our opening.** Their bottleneck list is almost exactly our asset list. We hold
computed verification with **0 false successes across 8 arms / 29 adversarial cases**, calibrated
refusal with recorded reasons, and an external removable state store. The frontier is failing at
repair and verification *because verification lives inside the same model that is wrong.*
Ours structurally does not.

**The unusual idea.** Don't build a better memory. Build a **typed task-state ledger** that is
*derived*, not narrated: every constraint in the instruction is compiled into a checkable
predicate; every observation updates it; a constraint is only "held" if a check passes. Then the
agent's context is not "what happened" but "which predicates are still unsatisfied." That is a
small, inspectable program.

**We already have this and cannot reach it:** `osworld_verified_task_ledger_v1` (808 lines, orphan).

**The test.** OSWorld 2.0's partial-reward checkpoints (~27 per task) let us score predicate
tracking *without* completing tasks. That means we can measure the mechanism on 10 tasks for
almost nothing. Not the full benchmark — the ledger only.

**Honest caveat.** "Proactive Interaction" is only **6 of 108 tasks (5.6%)** and "Streaming
Interaction" 6 more. Our calibrated-refusal strength maps to a *small slice* of this benchmark.
It is real but it is a niche, and I will not let it be sold as the main event.

---

## BET 2 — Turn the memory store into a *compounding* agent, and fix the 2.6× re-derivation cost

**The evidence.** Voyager's ablation is the cleanest in the literature: removing the skill library
causes progression to **plateau**; removing the curriculum causes **−93%**; removing
self-verification **−73%**. And — this is the part people forget — the skill library **transferred
to a new world and even helped AutoGPT**, i.e. it is a portable asset, not a trained-in
disposition.

**Our number.** Ablating our store costs **11.6 points** (38.2% → 26.6%), with **69 of 129 tasks
carried by a skill learned on a different task**. That's a real Voyager-shaped result.

**But we already know our store doesn't compound**, and I found the reason in an earlier receipt:
the cost measurement shows `cost_ratio_vs_exact_cache: 2.6207` with only 29 cache probes — a
cache miss that arrives with a *differently framed question* re-derives the whole abstraction.
**Every re-derivation is a skill that didn't compound.**

**The unusual idea.** Nobody ships this: **make the store's retrieval key the *computed
precondition signature*, not the goal text.** A skill becomes reusable when its precondition is
satisfied by the current state — regardless of how the goal is worded. That is why our
`version_space_practice` generalises 82% while `verbatim` gets 27%: abstraction helps, and the key
is the wrong place to put the abstraction.

**The test.** Re-run the MiniWoB store ablation with signature keys. Prediction: 38.2% → >50%,
and the 2.6× ratio drops below 1.0. **Falsified if the ratio stays above 1.5.**

---

## BET 3 — Steal the paradigm: *the harness is the product*

**The evidence, and it is uncomfortable.** From the 2026 harness literature: *"harness design can
rival model upgrades in impact."* Concrete: **fine-tuning the harness moved Terminal-Bench from
52.8% to 66.5%** — on the same model. And **RHO** (retrospective harness optimization via
self-preference, self-supervised, using only past trajectories) raised **SWE-Bench Pro pass rate
59% → 78%** without touching weights. Meanwhile mini-SWE-agent gets **>74% on SWE-bench Verified
in ~100 lines of Python with only bash.**

**Why this should sting.** We have 2,247 modules and scored 0/51. They have 100 lines and score
74%. **We are a harness problem that believes it is a model problem.** And the "0 model calls"
constraint does not exempt us: the harness is exactly the layer that a zero-call system *should*
be winning.

**The unusual idea.** Instead of hand-writing law #91, run **self-play harness optimization on
our own receipts**: the 3,296 verification receipts are a labeled dataset of what our operator
did and whether it worked. Compile that into a *routing policy* — which operator, in what order,
under what precondition. No model calls. The receipt archive becomes a training set.

**The test.** Hold out 20% of receipts. Does a compiled router beat the current hand-written
dispatch on held-out receipts? **Falsified if it doesn't beat it by 5 points.**

---

## BET 4 — Fix localisation with the *second organ*, and stop treating it as one ranking problem

**The evidence — and it is a direct indictment.** SOTA at file level uses **two independent
organs combined**: Agentless gets **78.7%** from prompting alone, **67.7%** from embeddings alone,
and **81.3%** combined. Combination beats either by ~3 points. Latest localisers: CuraLoc
**Func@1 59.3%** (vs LocAgent 53.8%, Agentless 39.6%), using **90.3% fewer tokens** than
iterative inspection.

**Our number: rank-1 file 42.8%.** We are **~38 points behind SOTA on the exact sub-skill that
gates everything else** — and our own decomposition says 44% of tasks die before a candidate
exists.

**The unusual idea, and it is the most defensible one here.** Our organ scores code by *what the
issue text says*. Theirs scores by *semantic similarity*. **These fail on disjoint task sets** —
that is the whole reason 81.3 > 78.7. Combine them with a rule that needs no model: when the two
organs agree, take it; when they disagree, look at the **test file's import graph** — the failing
test's import closure is a tiny candidate set that neither organ uses.

That third signal is free, computed, and zero-call. I have not seen it in the localiser literature.

**The test.** On the 500-task Django set we already have, measure rank-1 of
`organ ∪ embedding ∪ test-import-closure`. **Prediction: >65%.** Falsified below 50%.

---

## BET 5 — Zero-test verifiers: check patches without executing them

**The evidence.** **Dockerless** (2026-06-26) verifies patches by *agentic repository exploration
without execution*, and reaches **62.0 / 50.0 / 35.2%** on Verified / Multilingual / Pro — matching
environment-based results. That is a zero-execution verifier performing at environment quality.

**Why it's ours to win.** Our whole mission is zero model calls; a verifier that needs no
container removes our single biggest practical blocker (no Docker in this sandbox, 8 logged
blockers on OSWorld). We already hold `verifier_falsification_v1` (1,637 lines) and 246
verification modules — largely orphaned.

**The unusual idea.** Our **17 caught pass-and-are-wrong** repairs from HumanEval-Fix are a
ready-made adversarial set for any zero-execution verifier. **We already have the data that would
disqualify a bad verifier.** That is rare and it is free.

**The test.** Run our 17 known-wrong-but-passing repairs plus 36 known-right ones through a
zero-execution verifier. **A verifier that cannot separate those 53 is worthless** — and we'd know
in an afternoon. Falsified if separation < 0.8 AUC.

---

## BET 6 — The one genuinely unfashionable bet: **make the runtime fully symbolic and put everything learned offline**

**The evidence.** The **AT/ATA pattern** (2026): confine the LLM to offline knowledge ingestion,
compile to a symbolic KB, and *"all runtime decisions are made by the symbolic engine without
invoking the LLM"* — giving determinism and **prompt-injection immunity**. **VerIbmc** proves the
economics: a purely symbolic Phase 1 solved **75 problems with no LLM call at all**, and added
+36 solves for the weakest model.

**Why it's ours.** It is our mission statement, written by someone else, with proof that the
symbolic phase carries real weight on its own. Almost no one else is building this because it
doesn't demo well.

**The risk, stated plainly.** The same literature is honest that symbolic-only plateaus. VerIbmc's
own ablation shows Phase 2 (the LLM) still carries 144–303 solves. So a *fully* symbolic runtime
is likely to be a **strong specialist, not a generalist** — and we should decide in advance that
we're okay with that.

**The test.** Take our 5 solved SWE-bench Verified tasks and our 1 verified real-history row.
What fraction is reachable by symbolic operator composition alone with no search over free text?
We already know: **1 of 44** on real history. That number is our ceiling estimate and it is low.

---

# Part 3 — What the frontier is doing (Nov 2026 digest)

## Instant / continual learning

| Line of work | What it does | Result | Why it matters to us |
|---|---|---|---|
| **JitRL** (ICML 2026, arXiv 2601.18510) | No gradients. Memory bank of `<state,action,reward>`. Modulates **logits** in closed form (proven exact solution to KL-constrained policy optimisation) | Beats WebRL fine-tuning at **>30× lower cost** | The strongest evidence that a frozen model + external memory beats weight updates |
| **StepLearn** (*Learn Now, Use Next, Trust Later*) | Prequential test-time learning | **59.9%** WebArena-Lite, **84.0%** ALFWorld (GPT-5-mini); +2.2–12.7 over EvoTest | Ablations confirm stepwise acquisition + immediate reuse + retention — the exact loop we should copy |
| **In-Place TTT** (ICLR 2026) | MLP final projection = fast weights, drop-in | 4B model strong to 128k context | The parametric route. Not for us (violates zero-weights), but it's the pressure we're under |
| **MemoryAgentBench** (ICLR 2026) | 4 competencies incl. **selective forgetting** | — | We have no forgetting mechanism at all. That's a hole |

## Agent memory

- Consolidation (episodic → semantic) is explicitly called **"particularly underserved"** — *"crude heuristics, fragile and hard to validate."* **This is an open problem, not a solved one.**
- **AgeMem** trains store/retrieve/update/summarize/discard as tools, and discovers non-obvious tactics (preemptive summarisation; discarding near-duplicates). Suggests **memory operations should be schedulable**, which is a policy question, not a storage question.
- Nobody in the mainstream ships a **removable, inspectable, refusal-capable** store. We do. Voyager is the closest and it is 2023.

## Computer use

- Frontier's own diagnosis: hidden state, multi-item tracking, conflict disambiguation, dynamic environments. **<7% of budget on error repair.**
- Best scores: **31.4% binary / 68.3% partial** (Claude Opus 5, v2026.08.08). OSWorld 1.0 is at **83.5%** — the field considers v1 solved and has moved the goalposts.
- Unsafe behaviours: **14%** hidden-state extraction, **33%** UI bypass. **A system that can prove it did not cheat has value here that a system that scores 2 points higher does not.**

## Coding agents

- Localisation is the recognised bottleneck. SOTA file-level **81.3% combined**; Func@1 **59.3%**.
- **SWE-Adept**, **CuraLoc** (90.3% fewer tokens), **ARISE**, **LocAgent**, **RepoMem** — the field is converging on *graph + planned inspection*.
- **Dockerless** verification without execution.
- **RHO** 59→78% by harness self-optimisation. **Socratic-SWE** distils own traces into skills.
- **A²Agent** action-level RL: +8.55% localisation F1 on Pro with a **4B** model beating 8× larger.

## Tools worth adopting outright

`Harbor` (we already use it) · `mini-SWE-agent` (100 lines, 74% — read it, it will humble you) ·
`Inspect AI` (evals) · `z3`/`clingo` (we hand-roll what these do) · `Lemmalog` (Datalog agent
memory with provenance, MCP server) · `Nucleoid` (executable logic graph) · `Scallop`
(differentiable Datalog).

**The uncomfortable observation:** `Lemmalog` and `Nucleoid` are 300–800 stars and do what our
`residual_witness_retrieval_compiler_v1` is trying to do, with provenance, in Rust, and people
can install them.

---

# Part 4 — The sequence

| # | Do | Why | Cost | Kill criterion |
|---|---|---|---|---|
| 0 | Reachability census in CI | 1,784 orphans is invisible today | 1 d | — |
| 1 | Declaration registry (1.2) | unlocks 79% of the repo | 3–4 d | <2× reachable gain |
| 2 | Collapse duplicates (1.3) | 246 verifiers is a pile | 1 wk | — |
| 3 | Re-run 3 hard51 tasks | does wiring alone move 0? | hours | no change |
| 4 | Second localiser organ (BET 4) | rank1 42.8% is the gate | 1 wk | <50% rank1 |
| 5 | Signature-keyed store (BET 2) | fix the 2.6× re-derivation | 1 wk | ratio >1.5 |
| 6 | Task-state ledger on 10 OSWorld tasks (BET 1) | frontier's own bottleneck | 2 wks | — |
| 7 | Zero-execution verifier on our 17 wrong repairs (BET 5) | we already own the data | 1 wk | AUC <0.8 |
| 8 | Receipt-compiled router (BET 3) | 3,296 receipts as training data | 2 wks | <5 pts gain |

**Steps 0–3 are not optional and not a bet.** They are the difference between a repository with
2,247 modules and a system with 2,247 modules.

---

# Part 5 — What would prove me wrong

I'd rather name these now than have them found later:

1. **If the reachability walk is wrong** — if dynamic dispatch loads modules my static graph
   misses — then the 20.6% is an underestimate and step 1 is less urgent. I checked
   `importlib` in the front door: it is only `find_spec` for dependency checks, and dispatch goes
   through `unified_cognitive_fabric_v1`'s static import list. **38 modules do use dynamic import,
   though, and I did not fully resolve each one.** This is the weakest part of Part 0.
2. **If localisation is not the gate.** Our own receipt says the loss is FINDING (44% no
   candidate) and PRECISION (18/25). If PRECISION is actually the larger term on Pro-hard51, BET 4
   is aimed at the wrong target.
3. **If fully-symbolic plateaus** as VerIbmc's Phase-2 ablation suggests, BET 6 is a specialist
   strategy, not a path to general computer use, and we should say so out loud rather than let it
   become the story.

**The thesis, one line:** they are failing at repair and self-verification because those live
inside the model that is wrong; we have them outside, with zero false successes, and cannot
currently reach them. **Wire the 79% first. Then the frontier's bottleneck is our home ground.**
