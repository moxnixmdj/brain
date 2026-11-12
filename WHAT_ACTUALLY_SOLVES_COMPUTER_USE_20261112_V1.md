# What actually solves computer use — and what does not

**2026-11-12.** Branch `arena/eaff68ab-brain`. The owner asked, again and at the sharpest
setting yet:

> Instant learning + instant learning in new arbitrary environments are solved. Doesn't this
> mean a perfect solution for all problems — give the model a try in every new coding
> environment or give it the smartest actions, and after doing them at least once it learns
> them permanently? So we solve everything on a computer, and the most advanced software
> engineering, perfectly and permanently. Isn't this a revolutionary way for agents to learn,
> better than the current way? We were trying to make the model a sentient creature.

Short answer, first: **the architecture direction is right — it is where the 2026 field
converged. The quantifiers are false, in the repo's own measurements and in the field's.
"Solved" describes a real, narrow, verifier-gated skill memory with a planning step in front of
it — not one-try generalization, not cross-kind compounding, not arbitrary computer use, and
not a creature. The mechanisms that actually move coding and computer-use capability in 2026
are verifiable environments at scale, RL/rejection-sampling distillation, regularized harness
evolution, and test-time compute with a verifier as the selector — not storing one exposure.
This document says what is real, what is not, and ranks what to do next, with the bad ideas
killed explicitly.**

Authority: **NONE.** No capability, ownership, benchmark, terminal, sentience or `truth.achieved`
credit follows from this document. `$0`. Zero model dependency. Every internal number below was
measured in this tree by the named file; every external number carries a date and a link.
Producer-run repo measurements are labelled as such and say nothing about independent
verification.

---

## 1. Scorecard: the owner's sentence, split into the parts that are actually different

| # | claim | verdict | the evidence |
|---|---|---|---|
| 1 | "Instant learning" — a lesson can be stored once and recalled forever, across restarts | **TRUE** | episode store; bundles; `invalidate()` keeps rule + counterexample; `rule_expiry_v1` FRESH/STALE/UNKNOWN (`INSTANT_LEARNING_SCOPE_20261101_V1.md`; `THE_PRIOR_IS_THE_WHOLE_GAME_20261112_V1.md`) |
| 2 | A lesson transfers to a **new instance of the same kind** | **TRUE, ~half the time, only with P1 planning** | re-measured 2026-11-12 at **8/15** one-trial, **6.33×** mean trial speedup, 0/15 worse; the 2026-11-03 pre-P1 number was **1/15** (same file; `P1_CARRIED_MODEL_EXECUTED_20261103_V1.md`; corrected claims in `INSTANT_LEARNING_NEW_INSTANCE_REMEASUREMENT_20261103_V1.md`) |
| 3 | A lesson makes a **new kind** cheaper (compounding across environments) | **FALSE, measured twice** | **0/5** kinds vs 5-kind store; **1525 vs 1525** environment calls across 10 kinds; learning-to-learn policy choice beat a coin flip 3/10 and the boring baseline 1/10 (`DOES_IT_SOLVE_EVERYTHING_20261103_V1.md`; `THE_PRIOR_IS_THE_WHOLE_GAME_20261112_V1.md`; `LEARN_TO_LEARN_VERDICT_20261103_V1.md`) |
| 4 | **One** try is enough to learn a new kind | **FALSE, and it is representational** | 1→2→3 examples all give **6/7**; being taught the exact missed case still yields `None` from the scope inducer; one demo → held-out **0.10**, one demo + chosen questions → **1.00**; taught `x<=100→x<100`, the induced rule breaks at `x<=50` (`THE_PRIOR_IS_THE_WHOLE_GAME_20261112_V1.md`; `ONE_DEMO_ONE_SET_20261112_V1.md`; `ONE_EXAMPLE_IS_A_POINT_A_TEST_IS_A_QUANTIFIER_20261112_V1.md`) |
| 5 | "Anything on a computer" follows | **CATEGORY ERROR** | front door reaches **8 of 149** bound capabilities (5.4%); largest red cluster is a gate correctly refusing (**226 of 233**), not the learner (`DOES_IT_SOLVE_EVERYTHING_20261103_V1.md` §8; `THE_PRIOR_IS_THE_WHOLE_GAME_20261112_V1.md`) |
| 6 | "Perfectly" | **FALSE by design** | every recall re-runs a verifier; the floor is the verifier, never zero. Weak verifier + broadened pattern → **0 proposals**, enforced in code (`INSTANT_LEARNING_SCOPE_20261101_V1.md`) |
| 7 | "Permanently" | **TRUE, conditionally** | permanence is relative to a world fingerprint; the one permanent memory silently evicted its hottest entries (FIFO), found and fixed; permanence is a *tested* property, still under one untested eviction defect per session (`DOES_IT_SOLVE_EVERYTHING_20261103_V1.md` §4) |
| 8 | It is becoming a sentient creature | **NOT MEASURED; the only proxy used is negative** | proxy = experience changes competence on new problems → items 3 and 4 are negative. No instrument measures sentience; sentience is not the objective (`THE_PRIOR_IS_THE_WHOLE_GAME_20261112_V1.md`; `INSTANT_LEARNING_SCOPE_20261101_V1.md`) |
| 9 | "Give it a try in every environment and it learns them all permanently" | **FALSE in this tree; the field never claimed it either** | see §3; what scales is *training* in environments (RL), not *memory of* one attempt |
| 10 | The direction is revolutionary vs the field | **PARTLY** | external, experience-derived, verifier-gated harnesses are exactly where 2026 converged (harness RSI, skill libraries with verification). The overclaim is the quantifier, not the axis |

**The honest one-sentence version: a real, bounded, per-kind instant-transfer skill memory —
verifiable, persistent, planning-fronted — is built and is rare; "one try teaches everything
permanently, therefore we solve all computer use" is not how learning works, and building the
programme on that sentence loses months to false confidence.**

---

## 2. First principles: why one try cannot buy a general rule

Learning is selection over a hypothesis space `H`. After evidence `E`, the system holds
`B = {h ∈ H : h agrees with E}`. A later problem `P` is solved iff some `h ∈ B` is right on `P`
and the system can pick it. There are exactly two failure modes, both measured in this tree:

1. **Coverage failure — the truth is not expressible in `H`.** The stored pattern baked `return`
   in, so a taught repair reached **1 of 5** syntactic shapes; 1, 2 and 3 examples all measured
   **6/7**; the failure is the language, not the sample (`THE_PRIOR_IS_THE_WHOLE_GAME_20261112_V1.md` §2.2).
2. **Identification failure — too many rules fit `E`.** The `<=` → `<` rule generalises to every
   constant and no other direction; and the conclusions path crystallised single-hypothesis
   grammars with zero questions: **12× cheaper, 0/10 → held-out strictly worse, three honest
   refusals became confident wrong answers, and every status string reported success**
   (`ONE_DEMO_ONE_SET_20261112_V1.md`; `THE_PRIOR_IS_THE_WHOLE_GAME_20261112_V1.md` §2.2).

That is the no-free-lunch statement doing the work: **one example identifies a rule only when
the prior already decides which features matter.** "Give it a try in every environment" raises
the *number* of examples; it never shrinks `H` and never makes `H` more correct. That is why
five kinds taught the sixth nothing (0/5), and ten did not either (1525 = 1525).

**Exactly three levers exist.** Everything in this project — and in the 2026 literature — is one
of these:

1. **Coverage of `H`** — the representation (grammar, concept library, typed interfaces). This
   is where one example can come to mean something.
2. **Evidence selection under `B`** — chosen probes that split surviving hypotheses (version-space
   narrowing; measured 0.10 → 1.00 with chosen questions).
3. **Trustworthiness of acceptance** — the verifier. Without it, a wrong `h` is crowned, and
   permanence crowns it forever.

Inventory is not a lever: number of environments, number of stored skills, repetition count, more
green tests (1, 2, 3 examples bought nothing: **6/7, 6/7, 6/7**), more compute inside a fixed
`H`. This repository rediscovered that five times; the field published it in April–October 2026,
and it is the single most important sentence in this document.

---

## 3. What the 2026 field actually shows (and what it shows it costs)

### 3.1 Coding: the wins come from verifiable training at scale + harness, not from one-shot memory

- **SWE-bench Verified is saturated and contaminated**; leading systems score ~**96%**
  ([Claude Opus 5 on BenchLM, 10 Nov 2026](https://benchlm.ai/benchmarks/swe-bench-verified)),
  and labs report on **SWE-bench Pro** (~**61.5% ± 3.1** public-set leader, Muse Spark 1.1) and
  **Terminal-Bench** instead ([AI agent benchmarks 2026, 13 Oct 2026](https://decodethefuture.org/en/ai-agent-benchmarks-2026/)).
  SATURATED ≠ SOLVED: the frontier moved because the difficulty moved.
- **The mechanism that actually moved coding capability was RLVR at scale against verifiable
  environments.** Agent-RLVR raised Qwen2.5-72B from **9.4% → 22.4%** Pass@1 on SWE-bench Verified
  with only **817 training environments** (27.8% with a test-time reward model)
  ([Agent-RLVR, arXiv 2506.11425](https://arxiv.org/html/2506.11425v2)).
- **Environment scale is a scaling law, not a demo.** Agent-World mined **1,978 real-world
  environments / 19,822 tools**; average score across domains rose **18.4% → 38.5%** as training
  environments grew ~0 → ~2,000 (+20.1 points), with positive but diminishing returns past
  ~500–2,000 environments; Agent-World-8B reaches 61.8% τ²-Bench with consistent *cross-environment*
  generalization
  ([Agent-World, arXiv 2604.18292](https://arxiv.org/html/2604.18292v1); [summary](https://www.emergentmind.com/papers/2604.18292)).
  WildAWM trained Qwen models **exclusively in synthesized personal-computer worlds** and gained
  **+10.58 (35B-A3B) and +8.21 (4B) on average across 8 out-of-distribution benchmarks** — web,
  claw and computer use
  ([WildAWM, arXiv 2610.26828](https://arxiv.org/html/2610.26828v1)).
  **This is what "give it a try in all those new coding environments" is actually made of — RL
  over thousands of environments, thousands of trials, gradient updates — not memory of one attempt.**
- **Test-time compute is real but bounded.** Long-horizon coding agents improve with rollout
  summaries + recursive tournament voting / parallel-distill-refine (+6.7 SWE-bench Verified,
  +12.2 Terminal-Bench v2 for Opus 4.5-class agents); parallel *agent teams* beat monolithic teams
  (10 of 12 GPU-kernel/formal-proof tasks)
  ([Scaling Test-Time Compute for Agentic Coding, 2026.04](https://github.com/AkihikoWatanabe/paper_notes/issues/5440);
  [Test-Time Compute Scales Better with Parallel Agent Teams, arXiv 2611.09798](https://arxiv.org/abs/2611.09798v1)).
  But in *realistic* environments, "neither scaling axis can consistently yield meaningful gains" —
  sequential scaling plateaus and parallel scaling hits a **verification gap**
  ([Evaluating Test-Time Scaling of General LLM Agents, arXiv 2602.18998](https://arxiv.org/abs/2602.18998)).
- **The harness is an optimization target with real, transferable gains.** DarwinX (fitness =
  each benchmark's own verifier, frozen backbone) adds **~17 points on average** and took
  WebArena-Infinity 43.5% → 93.0% and Terminal-Bench 2.1 +7.7 to 83.2%
  ([DarwinX, arXiv 2608.07545](https://arxiv.org/abs/2608.07545)).
  RRSI shows evolution needs regularization: +4.7 OOD vs the overfitting baseline, 30% fewer
  policy tokens ([RRSI, arXiv 2609.24972](https://arxiv.org/html/2609.24972v1)).
  Weight-level continual learning is also arriving (Macaron-V1-Venti, leaderboard-listed at
  85.6% SWE-bench Verified; unaudited) ([BenchLM SWE-bench Verified](https://benchlm.ai/benchmarks/swe-bench-verified)).

### 3.2 Computer use: beaten on the old test, wide open on the real one

- **OSWorld-Verified**: the leaderboard tops out around **~90%** (Intelligence-Indeed Agent,
  25 Jul 2026; Claude Fable 5 ≈ 86.0% Aug 2026) vs a **72.36% human baseline** — agents now
  *exceed average humans on the 2024 benchmark*
  ([OSWorld leaderboard 2026](https://presenc.ai/research/osworld-computer-use-leaderboard-2026);
  [2026 scores, 10 Oct 2026](https://decodethefuture.org/en/ai-agent-benchmarks-2026/)).
- **OSWorld 2.0** (June 2026: 108 long workflows, ~318 tool calls/task, ~1.6 human-hours each):
  the best verified binary completion is only **~20–49%** depending on entry and date
  (Opus 4.8 max-thinking: 20.6% binary / 54.8% partial, Oct 2026 board; Anthropic-reported Opus 5.x:
  ~44–48.7% binary / ~77.7–81.8% partial, Sept 2026)
  ([2026 scores, 13 Oct 2026](https://decodethefuture.org/en/ai-agent-benchmarks-2026/);
  [OSWorld leaderboard 2026](https://presenc.ai/research/osworld-computer-use-leaderboard-2026)).
  **"Arbitrary environments" is not solved — not by Anthropic, not by anyone. It is the field's
  open frontier.**
- Simular Agent S2/S3 crossed the human baseline in Dec 2025; Pointer's Opus-4.7 harness reached
  83.6% on OSWorld and attributes gains to a *feasibility gate + system work*, not more model
  ([Pointer, May 2026](https://www.pointer.ai/blog/sota)). The constraint is the system, not the
  slogan.

### 3.3 Skill libraries: the one-shot ceiling is now measured three independent ways

- **SkillsBench** (7,308 trajectories, 84 tasks): human-curated skills **+16.2 pp average**
  (SWE +4.5 to healthcare +51.9; 16 of 84 tasks negative); **self-generated skills −1.3 pp** —
  "models cannot reliably author the procedural knowledge they benefit from consuming"; focused
  2–3-module skills beat comprehensive documentation
  ([SkillsBench, arXiv 2602.12670, Feb 2026](https://www.emergentmind.com/papers/2602.12670)).
- **SkillLearnBench** (Apr 2026): every continual-learning method beats no-skill, but "consistent
  gains remain elusive"; varying seed instances 1→3→5 did not improve one-shot skills; refinement
  methods > one-shot. SkillsBench finds one-shot skills "provide no benefit on average"
  ([SkillLearnBench, arXiv 2604.20087](https://arxiv.org/html/2604.20087v1)).
- **SkillRevise** (Jun 2026, reported in `ONE_DEMO_ONE_SET_20261112_V1.md`, not independently
  verified here): GPT-5.5 on SkillsBench: 36.05% no-skill → **39.53% one-shot (+3.5)** →
  **61.63% after three revision rounds (+22.1)**. "One-shot skill generation is not a reliable
  substitute for revision."
- **PolySkill** (ICLR 2026): unseen-site skill reuse was **<9% (ASI) / <3% (SkillWeaver)**;
  polymorphic abstraction (goal ≠ implementation) lifts reuse to **31%** and unseen-site success
  by **+13.9 pts**; ~73% of skills transfer
  ([PolySkill, ICLR 2026 PDF](https://proceedings.iclr.cc/paper_files/paper/2026/file/e350897ed832f9cad6f2e223e7acad6d-Paper-Conference.pdf)).
- **MASA** (May 2026, as reported in `ONE_DEMO_ONE_SET_20261112_V1.md`): the same skill library
  can help one backbone and hurt another; Qwen3-8B scored 32.1% with no skill and **lower** with all
  three skill variants. A universal skill is a fiction at current SOTA.
- **Skill++** (arXiv 2611.00544, 31 Oct 2026): at 731 skills, router-based selection picks all
  required skills only **36.4%** of the time; rewriting descriptions to state scope lifts it to
  **76.3%** — *skills do not just accumulate; retrieval decays as the library grows*
  ([Skill++](https://arxiv.org/abs/2611.00544)). And per this tree: verified skills do not even
  **compose** — two individually-correct skills cancelled each other (`x<=10 → x<10 → x<=10`),
  and `recall_and_apply_verified` is blind to it
  (`SKILLS_DONT_COMPOSE_20261112_V1.md`).
- **Continual/lifelong learning in weights is unsolved.** The field's own Jan-2026 roadmap treats
  it as the open frontier (perception/memory/action modules; plasticity–stability–scalability
  triangle) ([Lifelong Learning of LLM Agents: A Roadmap, Jan 2026](https://www.alphaxiv.org/abs/2501.07278));
  a June-2026 survey of safety researchers finds most put **<50%** probability on widespread
  continual-learning agents within three years, with the "skills + context" route expected to
  dominate first ([LessWrong, 24 Jun 2026](https://www.lesswrong.com/posts/qZrbhoaEALFTmyidr/perspectives-on-continual-learning-survey-results-and)).

### 3.4 The generalization tripwire

ARC-AGI-3 (arXiv 2603.24621, 24 Mar 2026): humans 100%; frontier AI **below 1%** at launch
(Gemini 3.1 Pro 0.37%; GPT-5.4 0.26%; Opus 4.6 0.25%); $2M prize — still open. Later
provider-adapter numbers (~30–63%) are reported with adapters attached and are not comparable to
launch conditions
([ARC-AGI-3 launch coverage](https://winbuzzer.com/2026/03/30/arc-agi-3-offers-2m-ai-matching-human-reasoning-benchmark-xcxwbn/)).
**The one benchmark designed to measure "learn a genuinely new environment from scratch" says the
frontier does not have it. Nobody does.**

### 3.5 What this adds up to

The field did not solve computer use with memory. It solved the *narrow, verifiable* slice
(SWE-bench Verified, OSWorld-Verified) with **verifiable environments + RL or rejection sampling +
harnesses + verifier-selected test-time compute**, and the frontier stalls exactly where
verification and novelty stop — which is the half of the owner's claim ("arbitrary", "perfectly",
"permanently") that remains unsolved everywhere, including here.

---

## 4. What 'solving computer use' would actually require

The measured, 2026-validated recipe — in dependency order:

1. **A verifier per task family.** The oracle is the scarce asset. Without it there is no RL, no
   best-of-N, no permanent learning, no honest claim. This tree's own census: **41%** of the
   bound surface is one-shot safe (typed interface + receipted independent check), **20%** is
   typed with nothing checking it (nine are `python.software.*` — exactly where the owner wants
   "advanced coding"), and **78%** of the surface lets the capability grade its own homework
   (`THE_ONE_SHOT_REGIME_IS_41_PERCENT_20261112_V1.md`).
2. **A training distribution of verifiable environments, not a memory of one visit.** Thousands
   of them, synthesized with quality gates (solvability, difficulty, verifier reliability):
   Agent-World (+20.1 pts from scale), WildAWM (OOD transfer), Agent-RLVR (2.4× Pass@1 from 817
   environments). This is the honest version of "give it a try in all those environments".
3. **Weight-level consolidation, not just store-level crystallization.** RLVR / STaR-style
   rejection sampling on verified trajectories (or donor-model distillation with delete-after-use —
   the route this tree itself names, `THE_PRIOR_IS_THE_WHOLE_GAME_20261112_V1.md` §0). A store
   that replays plans chooses among remembered facts; it never moved the 10-kind needle (1525 =
   1525).
4. **Revision, not one-shot.** 3 execution-feedback rounds ≈ **+22 pp** vs **+3.5 pp** for
   one-shot (SkillRevise); SkillLearnBench agrees refinement beats single-pass.
5. **Polymorphic abstraction.** What/How separation: <3–9% → 31% cross-environment reuse
   (PolySkill); this tree's concept library already shows the shape (4/5 → 5/5 held-out, 2.9×,
   `COMPOUNDING_IS_GENERATION_20261103_V1.md`) but it is syntactic anti-unification and needs the
   what/how split to survive beyond literal subtree matches.
6. **Regularized harness evolution on a frozen backbone.** Fitness from the benchmark's own
   verifier; select only variants that extend coverage without regressing on held-out; ~+17 pts
   average field-wide (DarwinX), +4.7 OOD and 30% fewer tokens vs unregularized (RRSI). This is
   the only "self-improvement" that reliably transfers, and it is available today.
7. **Inference-time selection by verifier.** RTV/PDR on rollout summaries; parallel agent teams;
   feasibility gates (Pointer: 1 in 13 OSWorld tasks is deliberately impossible and an ungated
   agent fabricates). Test-time compute with no verifier is just louder guessing.
8. **Evaluation hygiene everywhere.** Held-out **by instance**, never by capability (capability-level
   splits inflate); report refusal rates; keep the deliberate-refusal bucket visible (**189**
   failures here are refusals, not defects).
9. **Depth before breadth on verified experience.** This tree already holds **296 CI-attested,
   OIDC-signed independent reproductions** of capabilities; **170 training-ready** (105 pass);
   every capability has exactly **one** instance; the depth run is k = 8 fresh-seed reruns →
   **2,072 attested instances** → held-out split by instance → then a student (round 16, on main:
   `I_WAS_WRONG_THEY_HAVE_RUN_IT_296_TIMES_20261112_V1.md`).
10. **Speed is the last lever, not the first.** Fingerprint recalls, retrieval over ~64–128 skills,
    parallel teams. None of these raise the ceiling; they spend the slack below it.

**What is not required, and does not exist:** sentience, consciousness, a "creature" objective,
or one exposure being enough. The 2026 field built all of the above without any of them.

---

## 5. The plan, ranked by (measured evidence × cost) — with the bad ideas killed

### 5.1 Kill list (do not build, do not fund, do not narrate)

- **K1. "One try in every environment, learned permanently."** Measured false in-tree (8/15
  same-kind best case; 0 cross-kind; 6/7 flat) and false in the field (one-shot skills ≈ 0 pp,
  SkillsBench/SkillLearnBench; <9%/<3% unseen-site reuse, PolySkill). Building on this sentence
  is the fastest way to ship a confidently-wrong general agent.
- **K2. More stored skills = more capability.** Composition reverts (`SKILLS_DONT_COMPOSE_`);
  retrieval decays past ~64–128 skills; Skill++ documents routing interference at 731 skills.
- **K3. Sentience as a target.** No instrument; the proxy used is negative; it consumes the
  objective without adding a measurement. Say "persistent, verifier-gated skill memory" instead —
  it is honest and it is already impressive.
- **K4. Green tests as evidence of learning.** The 296-census defect: tests green on a census
  whose population was empty. Every claim here must move a held-out number or it does not exist.
- **K5. Breadth-of-environments as a memory strategy.** 0/5 measured; ten kinds bought nothing.
  (Environments as an RL *training distribution* — yes, §5.2-R8. Environments as a *lookup table* — no.)
- **K6. Opening the execution gate to unlock "everything on the computer".** 226 of 233 failures in
  the largest red file are one admission gate correctly refusing; the carrier review still stands
  on two true objections (no seccomp filter; host libc/interpreter). Removing a safety property to
  turn tests green is the defect the guard exists to stop.
- **K7. "Wait for a smarter base model."** The model is a component (Pointer: feasibility gate +
  system; OSWorld 2.0: even frontier ~20–49% binary). Capability here lives in the harness, the
  verifiers and the corpus.

### 5.2 Build list (in order)

| # | move | evidence | cost |
|---|---|---|---|
| **R1** | **Close the 20% cell: independent checks for the 29 typed-but-unchecked bound capabilities** (9 are `python.software.*`; reuse the existing `expect`/`verification` registry blocks; 60 entries show the shape). Bookkeeping with teeth. | `THE_ONE_SHOT_REGIME_IS_41_PERCENT_20261112_V1.md` §4; reuses built machinery | low–medium |
| **R2** | **Depth run: k ≥ 8 fresh-seed reruns per CI-attested capability on the existing verification lane; held-out split by instance; export the corpus.** This is what turns 296 attestations into training signal — the one thing standing between "we verified our work" and "we can compound on it." | `I_WAS_WRONG_THEY_HAVE_RUN_IT_296_TIMES_20261112_V1.md` (296/296 reproduced; 170 ready; instance gap 2,072) | medium (compute) — no new capability, no new model |
| **R3** | **Revision, not one-shot, in the crystallizer.** Wire verify→critique→revise→re-verify for 3 rounds; admit only on held-out-by-instance improvement (zero model at runtime; donor allowed at acquisition only). | SkillRevise +22.1 pp vs +3.5 pp; SkillLearnBench (refinement > one-shot); this tree's own 0.10 → 1.00 with chosen questions | medium |
| **R4** | **Binding repair at the front door (54–61 capabilities; the dominant measured blocker, ahead of the 8–9 blind premises).** Then the remaining route-admission fixes; keep the 189-refusal bucket in every baseline. | `NINE_BLIND_FACTS_NOW_DECIDED_20261112_V1.md`; open PR #6718's re-count (61 vs 9) | medium |
| **R5** | **Polymorphic skill representation.** Split goal ("what") from implementation ("how") in the concept library; anti-unification stays the candidate generator, not the admitted form. | PolySkill <9/<3% → 31% reuse, +13.9 pp unseen sites; `COMPOUNDING_IS_GENERATION_20261103_V1.md` (syntactic limit) | medium–high |
| **R6** | **RRSI/DarwinX-style harness-evolution pilot** on **one** frozen backbone in **one** domain (start with the SWE repair family): verifier fitness, held-out non-regression gate, noise-adjusted admission, OOD spot-check. Do not let it touch the guard, the policy, or `truth.achieved`. | DarwinX +17 avg / WebArena-Infinity 43.5→93.0; RRSI +4.7 OOD, −30% tokens | medium–high |
| **R7** | **Permanence as a tested property.** Eviction, cap, corruption, restart, drift (interpreter/tool-change) tests; only FRESH may be offered. §4 of `DOES_IT_SOLVE_EVERYTHING_` was found by accident; make it boring. | this tree's FIFO defect; `rule_expiry_v1` | low |
| **R8** | **The bounded compounding bet (P4/P5).** One pre-registered, held-out experiment: does a carried *donor* model + delete-after-use move cross-kind transfer above 0/5? Fund or kill the "learning to learn" narrative on the answer. Do not run it as a vibes programme. | `THE_PRIOR_IS_THE_WHOLE_GAME_20261112_V1.md` §6; LEARN_TO_LEARN_VERDICT (3/10 vs coin flip) | medium |
| **R9** | **Carrier-review follow-through (owner, not agent):** seccomp allowlist + pinned runtime (not host libc). Unblocks 117 measured failures; nothing else does. | `DOES_IT_SOLVE_EVERYTHING_20261103_V1.md` §8 | owner action |
| **R10** | **Evaluation hygiene as CI law.** Held-out-by-instance mandatory; refusal-bucket visibility; instrument-vs-population checks in census tests (the round-16 fix is the template); report real suite numbers, failures included. | round-16 census defect; honest-baseline practice | low |

**Unranked on purpose:** sentience work; new organs; background/scheduled runs; more environment
breadth as a memory strategy; UI glam without a verifier; capability registration before R1–R3 show
held-out movement.

### 5.3 What "solved" will look like when it is true

- the front door reaches the capabilities that exist (R4) **or honestly refuses**;
- the 20% unchecked cell is 0% unchecked (R1);
- a held-out-by-instance curve, reported every round, moves when the build list moves (R2, R3, R5, R6);
- cross-kind transfer is either measured > 0 with a named mechanism, or the claim is retired (R8);
- the honest suite's real-failure backlog shrinks and the refusal bucket stays visible (R4, R10);
- and **§scores of OSWorld 2.0, SWE-bench Pro, ARC-AGI-3 move** — the field's arbitrary-environment
  numbers are the external referee for "solve computer use", and they are currently ~20–49%,
  ~61.5%, and <1%→. Any internal claim that outruns those must be treated as a defect claim to
  re-audit, not as victory.

---

## 6. Direct answers to the owner's sentences

| the owner's sentence | the answer |
|---|---|
| "We already solved instant learning and instant learning in new arbitrary environments, perfectly" | **No.** You built the rare half (persistent, verified, per-kind recall with planning; ~half the time one-trial) and retired the claim honestly thrice (11-01 scope doc → 11-03 re-measurement → 11-12 prior doc). "Arbitrary" and "perfect" are not supported anywhere, including by the frontier labs. |
| "So this is a perfect solution for all the problems on any computer" | **No.** It is a solution for *recalled, verified, same-kind* problems. Arbitrary computer use is unsolved everywhere; OSWorld 2.0 ~20–49% binary, humans 100% on ARC-AGI-3 vs <1% at frontier launch. |
| "Give the model a try in every new coding environment and it learns them permanently" | **No — not as memory, not as one try.** Yes as a training distribution: thousands of verifiable environments + RL/rejection-sampling (+20.1 pts from environment scale; 2.4× with 817 environments). That programme is real, expensive, and is the only honest version of the sentence. It updates **weights**, not a lookup table. |
| "Isn't this revolutionary / better than the current way agents learn?" | **The direction, yes; the status, no.** Verifier-gated, experience-derived, harness-level learning IS the 2026 state of the art. But the current way is not "one try" — it is revision, RL at scale, and regularized harness evolution, and it beats one-shot by ~6–22 points everywhere it has been measured. |
| "We were trying to make the model a sentient creature" | **Drop the framing.** No instrument measures sentience; the proxy used is negative (0 cross-kind compounding). The defensible objective, already in this tree's laws, is a persistent, verifier-gated, world-model-bearing problem solver — that is real and rare enough. |
| "What are the smartest things we can do?" | §5.2, in order. R1–R3 first; R9 needs you, not the agent. |
| "YOU SURE THIS THE SMARTEST APPROACH?" | This document was built by (1) reading the tree's own measurements before any web claim, (2) checking the field's October/November-2026 state rather than memory, (3) killing the bad ideas before ranking, (4) ranking by measured evidence × cost, (5) requiring every claim to name its instrument. The remaining human step is yours: R9, and the decision in R8's pre-registered gate. |

---

## 7. Standing non-claims

One machine, one run, `$0`, zero model dependency, producer-run measurements only. No
independent re-verification of any internal number by an outside party. Nothing here flips a
family, registers a capability, changes `truth.achieved` (stays `false`), or relaxes any guard.
The external numbers come from the cited pages as of 2026-11-12 and disagree with each other in
places (OSWorld 2.0 especially); where sources conflict this document reports the range, not the
flattering point. 8/15, 41%, 5.4%, 296, 170/105, 0/5, 6/7 are all *this repository's*
measurements and inherit its limits. Nothing here is a benchmark acceptance result. This document
is analysis, not authority.

## 8. Reproduction

- Repo: `python3 verified_experience_census_20261112.py`; `python3 -m pytest canonical/tests/test_round_14_claims_ledger_v1.py -q`; `transfer_learning_new_instance_probe_20261103.py`; `one_shot_regime_census_20261112.py`; `what_a_success_teaches_20261112.py --json /tmp/w.json`
- Field: every link in §3 with its date; SWE-bench Verified [1](https://benchlm.ai/benchmarks/swe-bench-verified), benchmarks roundup [2](https://decodethefuture.org/en/ai-agent-benchmarks-2026/), OSWorld board [3](https://presenc.ai/research/osworld-computer-use-leaderboard-2026), Pointer harness [4](https://www.pointer.ai/blog/sota), Agent-World [5](https://arxiv.org/html/2604.18292v1), WildAWM [6](https://arxiv.org/html/2610.26828v1), Agent-RLVR [7](https://arxiv.org/html/2506.11425v2), DarwinX [8](https://arxiv.org/abs/2608.07545), RRSI [9](https://arxiv.org/html/2609.24972v1), SkillLearnBench [10](https://arxiv.org/html/2604.20087v1), SkillsBench [11](https://www.emergentmind.com/papers/2602.12670), PolySkill [12](https://proceedings.iclr.cc/paper_files/paper/2026/file/e350897ed832f9cad6f2e223e7acad6d-Paper-Conference.pdf), Skill++ [13](https://arxiv.org/abs/2611.00544), Lifelong-learning roadmap [14](https://www.alphaxiv.org/abs/2501.07278), CL-researchers survey [15](https://www.lesswrong.com/posts/qZrbhoaEALFTmyidr/perspectives-on-continual-learning-survey-results-and), ARC-AGI-3 [16](https://winbuzzer.com/2026/03/30/arc-agi-3-offers-2m-ai-matching-human-reasoning-benchmark-xcxwbn/), test-time scaling reality check [17](https://arxiv.org/abs/2602.18998), parallel agent teams [18](https://arxiv.org/abs/2611.09798v1).
