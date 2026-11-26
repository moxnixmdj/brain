# Frontier research, 2026-11-26 (V2) — instant learning, memory, routing, computer use, coding agents, abstention

**Schema:** `BRAIN_FRONTIER_RESEARCH_V2` · **Harvested by:** web search, this session ·
**Model calls:** 0 · **Runtime use:** research only — nothing here is cited by the solver at runtime.

Written to answer one question before any plan is written: *what does the frontier's own
literature say is still broken, under the names its authors use?* Provenance marks follow the
house rule — **V** = figure read on the source this session, **U** = vendor self-report,
**B** = reported by another source about a third party (not independently checked).

---

## 1. Continual learning: plasticity bought with stability, and nothing shipped

- **Are Self-Evolving Agents Continual Learners?** (arXiv 2610.25858, Oct 2026) **V**. Four
  drifting streams built from BIRD, BFCL, ScienceWorld; three nonparametric methods
  (ReasoningBank, GEPA, Meta-Harness). Finding: self-evolution improves aggregate scores but
  *higher plasticity consistently costs stability*; self-modifying methods overwrite earlier
  knowledge, and similarity retrieval "injects foreign memories" and suffers **retrieval
  collision** when similar queries need conflicting workflows. Their closing line: "current
  self-evolving agents remain incomplete continual learners", and their ask is mechanisms
  that isolate updates and condition retrieval beyond surface similarity.
- **Survey of continual learning / self-iteration** (2026) **B**: three axes — what is learnt
  (knowledge, skills, alignment), how (external supervision, self-generated, architectural),
  when (offline, online, test-time); claims parameter isolation escapes forgetting but grows
  linearly; LoRA forgetting is formally analysed; "the ceiling of improvement is bounded by
  verifier accuracy".
- **Learning on the Job** (arXiv 2607.22157) **V**: frozen model + external memory of
  natural-language rules distilled from outcome verdicts; gains 1.6×–2.6× baseline on 84
  tasks, converting 22 the baseline never solved; store retains value when a different model
  reads it.
- **Memory-Centric Continual Learning** (arXiv 2610.29357) **V**: the sharpest framing in the
  literature — memory "should be judged by whether it improves future actions, not merely
  what it retrieves". Also: sequential ROME degrades after ~100–1,000 edits; MEMIT enters
  forgetting after ~1,400 edits on GPT-J 6B.
- **Position: modular memory** (ICML 2026 workshop) **B**: pure in-weight learning forgets,
  pure in-context learning explodes; the missing piece is a modular memory with sleep-like
  offline consolidation.
- Practitioner map (mid-2026) **B**: "Solved with public access: nothing. Shipping in
  production: only the dossier stack, all frozen models."

**What this means for us.** The field's live failure is *interference between updates* —
exactly what an explicit, scoped, expiring store with a refusal vocabulary can address, and
exactly what no frontier lab ships.

## 2. Memory: the measurement crisis is bigger than the capability

- LongMemEval independent scoreboard **B**: Mem0 OSS ≈ **32.4–49.0 %** where the vendor
  platform self-reports **93.4 %** (U); Zep/Graphiti **63.8 %**; Supermemory 85.4 % (U);
  Hindsight 91.4 % (B); full-context baseline varies. Same benchmark, different reader models
  and judges — "the four-point spread on LongMemEval is not a measurement of anything".
- **ForgetEval / ForgetEval-Adv** (DeepLethe, Jun 2026) **B**: the control plane nobody tests:
  supersession, decay, purge, drift. Graphiti scores **4.4–7.0 %**, Letta **52.7 %**. Systems
  with near-perfect recall have near-zero intent-aware deletion.
- **FAMA / Memora** (Apr 2026) **B**: first metric that *subtracts* points for relying on
  obsolete memories.
- **AMB** (2026) **B**: neutral aggregation gym, 100k–10M-token splits.

**What this means.** Retention is measured; *deletion, supersession and staleness are not*.
We already model rule scope and expiry (`rule_scope_learning_v1`, `rule_expiry_v1`) — an
asset that maps onto the one capability the memory vendors score worst at.

## 3. Routing and tool retrieval: the solved-shaped problem we fail

This is the literature that speaks directly to our measured weakness (route recall 0.33).

- **Switchcraft** (arXiv 2605.07112) **V**: model router for agentic tool calling; DistilBERT
  66M, **82.9 %** accuracy at 84 % lower cost; oracle upper bound 89.4 %; heuristic routers
  (turns, length, tool count) top out at 80.4 %.
- **MCP Gateway at cloud scale** (arXiv 2607.15593) **V/U**: hybrid dense + BM25 retrieval,
  **98.2 % Recall@15** over 3,616 tools at 202–243 ms, dense-only falls to 83.1 %; tool
  selection time 55.7 s → 6.2 s, tokens 505.9k → 21.2k. A published referee report notes the
  ground truth may be partly self-referential (agents could only invoke recommended tools).
- **HYSET — Tools Are Not Islands** (arXiv 2607.25718) **V**: set-level, query-conditioned
  hyperedge retrieval; +11.6 % COMP@5 over strongest baselines; zero-shot to held-out tools;
  93.2 % of fully-supervised performance with 5 labels per category.
- **Tool-to-Agent Retrieval** (arXiv 2511.01854) **V**: joint tool+agent index; +19.4 %
  Recall@5, +17.7 % nDCG@5 on LiveMCPBench across eight embedding families.
- **OATS** (arXiv 2603.13426) **V**: interpolate tool embeddings toward the centroid of queries
  where they historically succeeded — zero serving-time cost, learns from outcomes.
- **BoundaryRouter** (arXiv 2605.07180) **V**: cold-start routing from early experience;
  RouteBench; +28.6 % over direct inference, +37.9 % over prompt-based routing.

**What this means.** Retrieval over a large tool catalog is a *known* problem with published
bars (98 % R@15 at 3.6k tools). Our index reaches 2,242 modules and our router reaches the
right function one third of the time. The gap is fixable with published technique, and the
published technique still needs a *label*: where does "the right tool" come from? We have
receipts — the outcome of the call — which is OATS's signal, obtained without a model.

## 4. Computer use: short tasks solved, long horizons not

- **OSWorld** leaderboard **B**: best entry **90.2 %** (agentic framework, Jul 2026); best
  general model 86.0 % (Aug 2026) against a human baseline of 72.4 %.
- **OSWorld 2.0** (Jun 2026) **B/V**: 108 long-horizon workflows across 7 professional domains;
  humans need a median **1.6 h** per task; best agents **20.6 % binary / 54.8 % partial**;
  Opus 4.7 at max thinking averaged **318 tool calls** per task (vs ~30 in 1.0). One
  independent write-up states that past ~163 minutes of human time *every* model's strict
  completion was zero (**B**).
- **Qwen-UI-Agent** (arXiv 2607.28227) **V**: 79.5 % OSWorld-Verified; **40.0 % partial** on
  OSWorld-v2 (vs Opus 4.8 54.8 %); 73.6 % WebArena; 81.5 % ScreenSpot-Pro with zoom. Notable
  behaviour: **CLI actions are 40.7–55.1 % of all actions** and batched actions 39.6–41.6 %.
- **CUWM** (arXiv 2602.17365) **V**: two-stage UI world model — textual state-delta first, then
  visual realisation; used for test-time action search with a frozen policy. Key insight:
  agent performance correlates with **structural** information ("a dropdown appeared") more
  than pixel fidelity.
- **Latent World-Action Model** (arXiv 2610.14228) **V**: predict action-induced future in
  latent space instead of rendering screens; drops the render-and-re-perceive pipeline.
- **Self-Improving Agents with World Model Predictive Paths** (arXiv 2610.28945) **V**:
  MPPI-style multi-branch imagination + dual-branch experience memory.
- **AdaJEPA** (arXiv 2606.32026) **B**: test-time adaptation inside the MPC loop, one gradient
  step per replan, five-transition buffer — and explicitly *within-episode*, not continual.

**What this means.** The frontier's long-horizon failure is a *planning under uncertainty*
failure, and every serious fix is a world model. Ours is cheap and unusual: we can predict
the consequence of an action on a program by executing laws, not by rendering pixels.

## 5. Coding agents: harness-dominated scores, and a confession about abstention

- **SWE-bench Pro** **B**: 1,865 tasks (731 public / 858 held-out / 276 commercial) across 41
  repos; published scores span **23 %–61.5 %** for the same era of models, and the spread is
  driven by scaffold: same model, SWE-agent 45.89 % vs other harnesses 49.75–51.80 %; "sub-25 %
  under SWE-Agent, 64 % under optimized scaffolds".
- **Terminal-Bench 4.0** **B**: 66 hard terminal tasks; leader 64.8 % (Claude Code + Opus 5.5,
  Sep 2026); 4.1 updated verifiers for reward-hack resistance.
- **DeepSWE** (arXiv 2607.07946) **V**: original long-horizon engineering tasks; mean reference
  solution ~7.4 lines; agents author their own tests far less under SWE-bench Pro's prompt.
- **FixedBench — "Coding Agents Don't Know When to Act"** (arXiv 2605.07769) **V**: 200
  human-verified tasks where *no code change is required*; state-of-the-art models propose
  undesirable changes in **35–65 %** of cases; explicit "verify-then-abstain" prompting lifts
  correct abstention to **80.5 % / 88.5 %** but introduces over-abstention when a prior patch
  was wrong; agents that pause to gather evidence recognise correctness 90.8 % vs 25.7 %.

**What this means.** On our own territory — deciding *not* to patch — the frontier is at
35–65 % error. Our refusal vocabulary and fail-closed gates are the exact instrument this
benchmark measures, and we have never scored ourselves on a paired act/abstain set.

## 6. Abstention: the newest benchmark, and its ceiling

- **AgentAbstain** (arXiv 2607.10059, NeurIPS 2026 oral) **V**: 263 paired tasks, 42 executable
  MCP sandboxes, 8 abstention scenarios (missing parameter, ambiguous action, conflicting
  constraints, high-stakes action, insufficient tools, critical tool failure, conflicting
  evidence, newly discovered risk). Best of 17 frontier models: **59.5 % paired accuracy**
  (Gemini 3.1 Pro); mean act accuracy 80.6 % vs abstain 59.1 %; abstention ability is
  **largely independent of task-solving ability**; "post-hoc abstention" — acting
  irreversibly before recognising the trigger — is a named failure mode.
- **The Missing "I Don't Know"** (2026) **B**: argues leaderboards assign zero reward to
  decline, so the gradient that would select calibrated abstention does not exist; proposes
  triple-scoring (correct / incorrect / abstain), abstention-rate reporting, stratified
  evaluation, mandatory calibration metrics.
- **UA-Bench** (ACL 2026) **V**: distinguishes *data uncertainty* (input ambiguity) from
  *model uncertainty* (capability limit); binary refusal benchmarks conflate them.

**What this means.** A public, paired, act/abstain benchmark now exists with a 59.5 % ceiling
and a *published* independence claim. If our abstentions are mechanically checkable — and the
refusal ledger says 40 % of our reasons are typed today — this is the one board where the
incumbent number is low and our instrument is already built.

## 7. Skill formation: library learning, rediscovered

- **DreamCoder** (2021) **V**: wake/sleep — search, then compress solutions into a library;
  text editing 3.7 % → 79.6 %; ~20 new routines including higher-order functions; learns from
  5–10 examples per concept.
- **Stitch** (2023) **V**: top-down corpus-guided abstraction; libraries comparable or better
  than DreamCoder at **1,000–10,000×** less compute; single CPU, tens of milliseconds per
  abstraction.
- **LILO** (ICLR 2024) **V**: LLM-guided search + compression + **AutoDoc** — inferred names
  and docstrings for learned abstractions improve both readability and synthesis.

**What this means.** The mechanism that turns episodes into reusable procedures is
compression with documentation, and it does not need gradients. Our tree already carries
`compress_by_anti_unification` and a docstring discipline; the missing piece is running
compression over *our own* solved episodes and measuring reuse.

---

## 8. What none of them has, and this repository does

| property | frontier 2026 | here |
|---|---|---|
| Every claim carries a receipt that a *different identity* re-runs (OIDC) | no | `capability-receipt-verification.yml`, 296 receipt-backed capabilities |
| A single deterministic, digest-addressed compiled model of everything owned | no | `BRAIN_UNIFIED_MODEL_V1.json`, 38/38 verifier checks |
| Abstention reasons that name a missing artifact | 59.5 % paired ceiling; post-hoc abstention | 991 refusals in 4,674 receipts, 40 % typed (measured 2026-11-25) |
| Laws that *fire* on a program (metamorphic oracle), not just tests that pass | rare | `metamorphic_oracle_v1` 9 laws, mutation probe landed |
| Zero model calls at runtime | no (all are model-centric) | enforced |

The literal asymmetry: the frontier measures capability with benchmarks whose labels are
model-generated or human-generated; we can manufacture labels by *executing our own laws*.

## 9. Non-claims for this digest

- Vendor scores are marked **U**; independent scores are marked **V/B** with the caveat that
  most "independent" numbers are one blog's run, not a replication.
- No benchmark in this document was run by us this session.
- Some 2026 model names appearing in secondary sources (Opus 5.5, GPT-6 Astra, Muse Spark,
  Claude Fable) are **reported**, not verified here; they are used only to date a claim, never
  as a target we claim to beat.
