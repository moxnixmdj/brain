# Frontier Plan V3 — where a $0 deterministic system can actually get ahead

**Date:** 2026-11-26 · **Branch base:** `main@ac5c1015` · **Status:** plan, not a claim

---

## 0. The answer in one paragraph

Stop trying to beat the frontier on the benchmarks where it is strong and expensive (SWE-bench Pro
HARD-51: 90–98%; Terminal-Bench 4.0: ~58–65% at $1.5k–$6.5k per run). Beat it on the axis where it
is **structurally** broken and where money does not help: **dependency-correct memory** — the six
MEME operations, where six production memory systems average **3% on Cascade and 1% on Absence**,
and where the best configuration known (a file-based agent behind Claude Opus 4.7) reaches
**0.32 / 0.59 at ~70× the cost** [1]. Brain closed the *structured* version of exactly that gap last
wave: **36/36 against a from-scratch oracle, $0, 0 model calls** [repo]. The plan is to convert that
one proven asympmetry into a measured product surface — cost-per-correct-answer on dependency-evolving
tasks — and then use it as the armour behind which a frontier model is *demoted* to a Rung-3 proposer.

Everything else in the brief is either already true, already built, or not defensible. This document
separates those three.

---

## 1. What actually changed by November 2026 (verified, with caveats)

The brief you gave me contains a mix of real papers and claims that the sources do not support. Both
matter for the plan.

### 1.1 Verified — and load-bearing

| Claim | What the source actually says | Why it matters here |
|---|---|---|
| MEME: memory systems collapse on dependency reasoning | Six systems (BM25, text-emb-3-small, Mem0, Graphiti, MD-flat, Karpathy Wiki) on 100 controlled episodes: **Cascade 0.03, Absence 0.01** average. Prompt optimisation, deeper retrieval, less filler and stronger LLMs do **not** close it. Best config = file-based agent + Opus 4.7, 20-episode subset: **Cas 0.32, Abs 0.59 at $3.87 ingest + $0.66/ep inference** (~70× baseline) [1] | The gap is *architectural*, not a model-quality problem. This is the axis Brain can own. |
| "Dependency evidence is usually stored and retained but **lost at retrieval**" | MEME §4.3 (per the paper's own diagnosis) | A memory that keeps dependencies as first-class edges does not have a retrieval problem to lose them in. That is the whole thesis, and it is now a *published* diagnosis. |
| JitRL: test-time policy improvement without gradients | Trajectory memory → advantage estimate → **logit shift `z' = z + β·Â`**, proved to be the exact closed-form solution of the KL-constrained objective; beats fine-tuning (WebRL) at **>30× lower cost** [2]. Explicit limitation: it **cannot summon an action the base model gives zero probability** | The $0-compatible half is the *advantage-weighted re-ranking of candidates*. The logit half needs model access we do not have and a proposer bill we do not pay. |
| TTT-Discover: RL on a single test problem | Entropic objective (`log E[e^{βR}]`) + PUCT reuse; beats the best human on TriMul kernels (1161 µs vs 1371 µs), Erdos minimum overlap; **a few hundred dollars per problem**, `gpt-oss-120b` [3] | Works on **sparse-reward discovery**, not on dense-reward verifiable tasks. |
| …but TTT loses to plain search under matched compute | Equal-budget study (2602.07670): Best-of-N K=64 reaches **90%** task success on KernelBench L1 vs TTT's **30.6%**; TTT's "equivalent K" is **< 1** [4] | **Search + verifier beats fine-tuning when the reward is dense and checkable.** That is Brain's native mode. It is the strongest external argument for the architecture. |
| Nested Learning / CMS / Hope | Continuum memory = spectrum of modules at different update frequencies; self-modifying Titans; catastrophic forgetting "not solved" [5] | Confirms the *multi-timescale* framing is real; the paper is about weights, so the $0 analogue is multi-timescale **skill** memory, not multi-timescale gradients. |
| WebMCP moved to `document.modelContext` | Chrome 154 with `--enable-features=WebMCP` exposes `document.modelContext` on HTTPS origins; moved from `navigator` in the July 2026 build; `provideContext`/`clearContext` gone [6] | A real, checkable API change. Any computer-use code using `navigator.modelContext` is already stale. |
| Hybrid Computer Use (HCU) | 3 channels (programmatic / semantic AX / visual) over MCP; **OSWorld 2.0: 68.82%**, above the best single-model entry (68.31%) [7] | Channel 0/1 first, pixels last — and it measurably wins. |
| OSWorld-MCP | MCP tools roughly double success (o3 8.3%→17.6%), but **tool-invocation rate is only 33.3%** even for the best model [8] | The bottleneck is *deciding to use the tool*, i.e. routing — a deterministic-router problem, not a perception problem. |

### 1.2 Contradicted — do not put these in a PR

| Brief claim | What the sources show | Consequence |
|---|---|---|
| "Frontier still only 29.6–31.6% on SlopCodeBench / SWE-bench Pro" | SWE-bench Pro **V2 HARD-51**: Opus 5 (Claude Code, xhigh) **98.0%**, Fable 5.1 and Gemini 4 Argon 92.2%, GPT-6 Astra 90.2% [9]. Terminal-Bench 4.1 top: **71.2%**; 4.0: 58.2%–64.8% depending on harness [9][10] | A `0/51`-style claim is not a gap to close; it is a different task. Do not frame Brain's SWE numbers as competitive. |
| "Terminal-Bench costs $1.7k–$6.5k" | Run cost $1,557–$6,244, and **effort** drives both score and cost (GPT-6 Astra 50.6%→58.2%, $1,557→$3,267) [10] | The real, under-exploited axis is **cost at fixed verified-correctness**, not peak score. |
| "SWE-bench Verified is the reference" | Saturated 95–97%; OpenAI no longer reports it [11] | Never quote it. |
| Implied: benchmark numbers are stable | The same benchmark is reported at 58.2% (official board), 64.8% (Terminal-Bench 4.0 board), and 66.4% (Anthropic, unreproduced) for near-identical models [9][10] | Harness and running-party variance is larger than most gaps. Any cross-system comparison Brain makes must be *self-run, same harness, same judge* or it is noise. |
| "MEME >90% is achievable by wiring DBSP" | Best published-known result is 0.59 Absence (70× cost). A self-reported vendor claims 40%/43%, unreplicated [12] | **Frame the target as: match the paper's protocol, report structured and end-to-end separately, and never claim a number on their task unless we run their episodes.** |

**Discipline that follows:** every claim Brain makes about itself must be (a) self-run, (b) judged by
an oracle we can inspect, (c) accompanied by the ablation that would fail if the capability were
removed. The Wave 41/42 pattern (honest / liar / stub controls, from-scratch oracle, "1/3 when the
capability is stubbed") is the only kind of claim worth making.

---

## 2. Where the frontier is structurally weak (and why money doesn't fix it)

Three failures, in order of how much they are worth to Brain:

1. **Dependency reasoning (MEME Cas/Abs).** Not a scale problem: the paper tried stronger models,
   deeper retrieval, prompt optimisation and less noise; the only thing that helped was handing the
   model a *file system* and letting a frontier model do the closure by hand — at 70× cost and still
   0.32/0.59. Vector and graph memories lose the dependency edge at write or at read.
2. **Cost at fixed correctness.** Terminal-Bench effort curves are strictly monotic in dollars; the
   best-known configuration pays 2× for +7.6 points. Nothing in the 2026 literature shows a system
   that *gets cheaper as it runs* — no compile-away, no skill consolidation, no amortisation.
3. **The "no" problem.** Absence is 1%; tool-invocation routing is 33%; half of agent failures in
   OSWorld 2.0 traces are "premature stop / false done" and "final-state exactness"
   [7]. Systems are bad at *knowing when they do not know*, and worse at saying it in a way a
   checker can verify.

Brain already has, measured: a cascade/absence engine that distinguishes four kinds of "no" with
named witnesses (Wave 42), a refusal-as-specification acquisition loop (Wave 41), and a bench that
scores abstention honestly. That is a real head start on failure 1 and 3. Failure 2 is unclaimed
territory: **nobody has published a monotone "cost per verified task falls as the system runs"
curve**, and it is the one curve a $0 deterministic system can produce that a frontier API cannot.

---

## 3. The three asymmetries worth betting on

**A. Dependency memory as a product surface, not a module.**
Nobody can buy their way past MEME's Cascade because the failure is in the data model. Brain's
engine answers it by construction. The work is not more engine — it is (i) a faithful episode harness
with the paper's protocol, (ii) a deterministic extractor so the memory can be filled from
*sessions* rather than from structured triples, and (iii) honest separate reporting of engine-only
vs end-to-end. **The extractor is the whole risk**, and it is where a frontier model would normally
be spent.

**B. Cost-per-verified-answer as the headline metric.**
Frontier runs are $1.5k–$6.5k and effort-monotone. Brain's Wave 41/42 numbers are $0.00 with 0 model
calls on tasks where the frontier's own harness costs real money. Publish the *curve*: on a stream of
N dependency-evolving tasks, verified-correct answers per dollar, and the neural-call rate as it
decays to zero as compiled skills absorb each task family. This is the compounding claim, and it is
falsifiable: if the rate does not decay, the claim is dead.

**C. The "no" surface — verification-gated abstention with named witnesses.**
Every abstention carries a machine-checkable reason (`UNKNOWN__UPSTREAM_SUPERSEDED` + the rule id +
the missing body; `ABSENCE__SUPPORT_PREMISE_INVALIDATED` + the premise). A downstream checker can
audit a refusal, which no frontier model's "I'm not sure" can survive. That is a differentiated
product surface for any agent that must be *trustworthy* rather than impressive.

---

## 4. Where Brain must not compete

* **SWE-bench Pro HARD-51 / Terminal-Bench head-to-head.** 90–98% / ~58–71% with hidden tests and
  real repos, at four figures per run. A $0 engine that scores 0 there is not "behind"; it is
  playing a different game. Measure it once, honestly, as a *baseline we do not claim*, then stop.
* **OSWorld 2.0 numbers.** Requires a real desktop VM and a harness we cannot run in this sandbox.
  Any number we produced would be a simulation, and a simulated OSWorld number is a lie with extra
  steps.
* **Weight-level continual learning.** Hope/CMS/TTT all live in the weights. Brain can implement the
  *policy* of consolidation (what to keep, merge, expire, compile away) without the gradients, and
  should say exactly that.
* **"We already have it somewhere" as an argument.** See §5.

---

## 5. Repo audit: the dark matter is a liability until adjudicated

Measured on `main@ac5c1015`, today:

| Fact | Number |
|---|---|
| Python modules under `canonical/` | **6,369** |
| Modules with **no importer** (by module name) | **3,549** — see correction below; the first count, 6,114, was wrong |
| Modules with no importer, ≥140 lines, non-test | **227** (the substantial bank; first counted as 1,996) |
| Koan-named modules (`the_*`, `a_*`, `what_*`, `why_*`, `how_*`) | 102 — **58 of them unreachable** |
| Model source index | 2,264 modules (of 6,369) |
| Promotion candidates → callable | **849 → 31 (3.7%)** |
| Model capabilities / harvested capabilities / federation engines | 462 / 659 / 54 |
| `brain_unified_model_v1.py` | **7,533 lines** (hard cap `< 7,534`) |

**Correction (measured after this document was written, Wave 43 / PR #7146).** The 6,114 and 1,996
above came from a candidate rule that compared a bare filename stem against fully dotted import
names, so every module reached as `from canonical.<pkg>.<mod> import X` counted as dark. Corrected,
the tree has 3,549 unimported modules, 227 of them substantial. The adjudicator then ran on all
2,174 substantial modules: **6 can prove they run** on the day it merged, **8** after Wave 44
(futamura_leapfrog_kernel_v1 and egraph_and_deductive_synthesizer_v1 adopted the contract), 2,080 import and prove nothing, 79 need substrate this sandbox does not ship, 7 are broken.
The 227-module no-importer census proves **nothing at all**. The numbers that follow in this section
are still worth reading for their shape, but every count of "hidden organs" must be read as 227,
not 1,996.

Some of those 3,549 are legitimate CLI entry points with no importer. Many are not. Here is the
uncomfortable part: **a module nobody imports is not a capability, it is a claim.** The brief's
"we already solved this somewhere" is true in the sense that a library you never open "has" the book
you need. Three consequences:

1. Every unreachable module **inflates the model** (compile time, digest churn) and **dilutes the
   capability count** — the same 96% that makes "tremendous hidden capabilities" sound true makes
   every capability number in the repo uninterpretable.
2. The interesting ones are real, and they are big: `semantic_causal_engine_v1.py` (4,637 L),
   `causal_cegis_inventor_v1.py` (3,299 L), `declared_input_derivation_v1.py` (2,705 L),
   `causal_trace_to_skill_compiler_v1.py` (2,579 L), `history_template_repair_v1.py` (499 L),
   `abstain_gated_skill_induction_v1.py` (539 L), `history_induced_edit_grammar_v1.py` (386 L).
   **None of these is verified wired**, and none should be promoted on the strength of its name.
3. The model's line budget is **1 line**. Any plan that says "wire 15 more organs into
   `UnifiedModel`" is already dead on arrival unless the organs land as separate modules reached
   through the federation registry, or the model is split into mixins first.

**So the first wave is not a capability wave. It is the wave that makes every later claim checkable.**

---

## 6. The plan — four waves, each with an oracle and an ablation

Ordering rule: a wave may not start until the previous wave's ablation exists, because the ablation
is the only thing that distinguishes "capability" from "wiring".

### Wave 43 — Dark-Matter Adjudicator (the meta-capability)

**Why first:** it converts the repo's central ambiguity ("96% unreachable, therefore boundless") into
a ranked, evidence-bearing queue, and it gates every "we already have it" claim in the plan.

**What:** `canonical/tools/dark_matter_adjudicator_v1.py`

*(As built: four verdicts, not three — `PROVEN`, `IMPORTS_ONLY`, `MISSING_SUBSTRATE`, `BROKEN` —
over 2,174 substantial modules with `--all-modules` and 227 without it.)*

For each candidate module (start: the no-importer list, which is 227 substantial modules, not
6,114), emit a verdict, fail-closed:

* `PROVEN` — imported, its declared entrypoint/self-check executed on synthesised inputs at $0, and
  a receipt written naming the exact call and result;
* `BROKEN` — imports but the probe raises or returns a fail-closed status (quarantine list);
* `DARK_UNPROVEN` — cannot be exercised without a substrate we do not have (network, VM, GPU).

**Oracle:** the module's own contract (docstring entrypoint, or `self_check()`/`__main__`), plus the
existing `repo_integrity_guard`. **Ablation:** run the adjudicator with the probe step disabled —
the verdict distribution must collapse to `DARK_UNPROVEN`, or the instrument is not measuring
execution.

**Acceptance:** a receipt for every candidate; a ranked top-20 of PROVEN modules; `repo_integrity_guard`
clean; **no capability is added to the model in this wave** (that is the point — it measures before it
promotes). Falsified if <5% of the largest 200 are PROVEN *and* the plan still assumes the rest are.

### Wave 44 — MEME-faithful episode harness (the frontier-facing claim)

**What:** `canonical/evaluation/meme_episode_harness_v1.py` implementing the paper's *protocol shape*
from the public description: multi-session episodes, gold facts introduced in evidence sessions,
**probe-before and probe-after** questions, **trivial-pass filtering** (score only episodes where the
pre-probe was answerable), and the six task types.

Three named arms, reported separately and never blended:

| arm | memory | extractor | what it proves |
|---|---|---|---|
| **S** structured | Wave-42 dependency memory | given triples + rules | engine correctness (expect ~1.000, as already measured) |
| **E** end-to-end | same engine | deterministic session→facts extractor | the real product claim; the extractor's miss rate is the honest ceiling |
| **B** baseline | flat last-write-wins store | same extractor | the 1%/3% shape, in our own hands |

**Oracle:** for each probe, the answer is derived from the episode's own gold facts and dependency
rules by `reference_fixpoint` (no shared bookkeeping with the arms). **Ablation:** arm S with the
dependency edges stripped must fall to arm B's level — that is what makes "edges cause the score"
a measurement rather than an assertion.

**Acceptance:** arm S ≥ 0.99 on all six; arm B ≤ 0.15 on Cas+Abs; arm E's extraction recall reported
per task type with its failure modes named; `model_calls = 0`, `spend = $0.00`. **Not claimed:** any
comparison to the paper's LLM-judged numbers.

### Wave 45 — the demotion, measured (proposer behind the armour)

**What:** a *pluggable, off-by-default* Rung-3 proposer adapter with the JitRL-compatible half that
needs no logits: candidate generation, then **advantage-weighted re-ranking** from episodic
`(state, action, outcome)` memory, then the verifier gate from Wave 41/42. Off by default → the
default path stays `K3 = 0`, $0.

**Oracle:** the task's own verifier (the only thing allowed to admit a candidate). **Ablation:** the
same proposer with the advantage memory disabled (uniform re-ranking) — the delta is the value of
the memory, and if it is zero, the wave is dead and should be reported as dead.

**Acceptance:** the measured **neural-call rate curve** over a stream of N tasks, plus cost per
verified answer for both arms. Falsified if the rate does not decay with the store growing, or if the
advantage memory adds nothing over uniform sampling.

### Wave 46 — the cost curve, published as the headline

**What:** a single scoreboard that runs W44 arm E + W45 on a stream of tasks and plots two curves:
verified-correct per dollar, and neural-call rate vs tasks seen. One receipt, one digest, reproduced
in CI.

**Acceptance:** monotone decay of neural-call rate over ≥100 tasks, with the anchor set (previously
solved tasks) reproved at every step so that "cheaper" cannot mean "forgot". This is the claim no
frontier API can make, and it is the only one worth a headline.

---

## 7. The scoreboard: one number

> **Verified-correct answers per dollar on dependency-evolving tasks, with the neural-call rate and
> the abstention precision beside it.**

Reference points to beat, self-run and cited: 0.24 overall / Cas 0.03 / Abs 0.01 at the paper's
default cost; 0.32 / 0.59 at $3.87 + $0.66/ep [1]. Brain's current measured position: **1.000 on the
structured protocol at $0.00 and 0 model calls** (Wave 42), which is *not yet comparable* — arm E is
what makes it comparable, and arm E is unbuilt.

---

## 8. Anti-self-deception rules (non-negotiable, from this repo's own history)

1. **No claim without an ablation.** If removing the capability does not move the number, the number
   is not about the capability.
2. **No cross-system comparison without the same harness.** 58.2% / 64.8% / 66.4% for near-identical
   models proves harness variance swamps most gaps.
3. **Never quote a number we did not run.** No Inherited Benchmark Numbers.
4. **`truth.achieved` stays `false`.** Every PR carries `what_is_not`.
5. **Names are not evidence.** A module called `causal_cegis_inventor_v1` is a *hypothesis* until
   Wave 43 says PROVEN.
6. **The line cap is a design constraint.** One line of headroom in `UnifiedModel` means new organs
   land as federation-reached modules or the model gets split — not as more lines.
7. **Publish the dead waves.** If Wave 45's advantage memory adds nothing, that goes in the PR body,
   not in a drawer.

---

## 9. What I would cut from the brief, and why

| Cut | Reason |
|---|---|
| "Wire 15 dark modules into `UnifiedModel` in one wave" | 1 line of headroom; and none of the 15 is verified. Adjudicate first (W43), promote only PROVEN. |
| "Beat the frontier on SWE-bench Pro HARD-51 / SlopCodeBench" | Frontier is at 90–98% there. Reframe as cost-at-fixed-correctness on tasks we can actually run. |
| "MEME >90%" | The best known result is 0.59. Target the protocol faithfully; let the number be whatever it is. |
| "TTT/LoRA weight consolidation" | No GPU, no budget, and the equal-budget study says search wins where our tasks live. Keep the *policy* of consolidation; drop the gradients. |
| "OSWorld 2.1 execution" | No VM. Simulated desktop scores are fabricated numbers with good manners. |
| "Unify 7 unmerged PRs" | Merge ordering is a queue, not a capability. Rebase, measure, land one at a time. |

---

## 10. If you want one thing next

**Wave 43.** It is $0, it needs no external benchmark, it takes the repo's biggest ambiguity and
turns it into a ranked queue, and it makes every subsequent "we already have it" claim *checkable* —
including the ones in this document. Everything else in this plan is downstream of knowing which of
those modules are real — and it turned out to be 6 of 2,174, not 5% of 6,114.

---

### Sources

1. Jung, Rubinstein, Uselis, Yun, Oh. *MEME: Multi-entity & Evolving Memory Evaluation.* arXiv:2605.12477 (v2, 11 Nov 2026); project page with per-system table (`Cas 0.03 / Abs 0.01`; MD-flat×Opus 4.7 `0.32 / 0.59` at `$3.87` ingest).
2. *Just-In-Time Reinforcement Learning: Continual Learning in LLM Agents Without Gradient Updates.* arXiv:2601.18510 (code: `liushiliushi/JitRL`); >30× cost reduction vs WebRL; cannot summon zero-probability actions.
3. Yuksekgonul et al. *Learning to Discover at Test Time (TTT-Discover).* arXiv:2601.16175; entropic objective + PUCT; a few hundred dollars per problem.
4. *Equal-budget test-time strategies* (KernelBench L1): Best-of-N K=64 90% vs TTT 30.6%, TTT equivalent K<1. arXiv:2602.07670.
5. Behrouz et al. *Nested Learning: The Illusion of Deep Learning Architectures* (CMS, self-modifying Titans, Hope). arXiv:2512.24695.
6. WebMCP: `document.modelContext` (moved from `navigator` in the July 2026 build; Chrome 154 + `--enable-features=WebMCP`); 79% fewer bytes / 42% fewer tokens vs DOM scraping on a 150-product benchmark.
7. *Hybrid Computer Use: A Unified Programmatic, Semantic, and Visual interface.* arXiv:2610.41432; OSWorld 2.0 68.82%.
8. *OSWorld-MCP.* ICLR 2026; tool-invocation rate 33.3%; MCP doubles some models' success.
9. Coding-agent leaderboards, Oct–Nov 2026: SWE-bench Pro V2 HARD-51 (Opus 5 98.0%, Fable 5.1 92.2%, Gemini 4 Argon 92.2%, GPT-6 Astra 90.2%); Terminal-Bench 4.1 top 71.2%.
10. Terminal-Bench 4.0: 58.2% (GPT-6 Astra, Codex, max effort) vs 57.9% (Fable 5.1, Claude Code); run cost $1,557–$6,244; effort-monotone.
11. SWE-bench Verified saturated at 95–97%; OpenAI no longer reports it.
12. Vendor self-report (Sentra): MEME Cascade 40% / Absence 43%, unreplicated — cited only as a competitor's claim, not as a fact.

*Repo numbers in §5 are measured on `main@ac5c1015` this session. Benchmark numbers in §1 are the
sources' own; where sources disagree, both are shown. Nothing here is an independent verification.*
