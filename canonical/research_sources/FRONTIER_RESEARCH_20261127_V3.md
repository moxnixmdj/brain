# Frontier research sweep V3 — 2026-11-27

Breadth-first, one rule: every item is marked with what kind of claim it is.

- **V** — the page was read in this session and the number appears on it.
- **B** — reported by an aggregator or a second-hand write-up of a page not read directly.
- **U** — vendor self-report; not independently reproduced.

Numbers are copied, not paraphrased. Where a vendor and an independent run disagree, both are listed.

---

## 1. Instant learning: adaptation without gradient updates

| Item | Claim | Mark |
|---|---|---|
| **In-Place Test-Time Training** (ICLR 2026) | The MLP down-projection is used as the fast weight; `W_up`/`W_gate` stay frozen; a chunked, strictly causal "apply-then-update" loop; NTP-aligned objective instead of reconstruction. Drop-in on a pretrained LLM, no retrain, context-parallel. | V |
| **TTCD / IP-TTCD** (arXiv 2608.01672) | A long-window teacher supervises a short-window student's fast weights; the teacher–student residual is what gets written. Beats DeltaNet, Gated DeltaNet, sliding-window attention and TTT on long-context LM. The learned item survives after the evidence leaves the window. | V |
| **JitRL** (2601.18510, ICML 2026) | Trajectories `<state, action, reward>` in a non-parametric store; retrieved neighbours give an advantage estimate that is added to the logits in closed form. No gradients, no value network; reported >30× cheaper than weight-update baselines. | V (paper), U (30× is the authors' figure) |
| **Where Should LLM Agents Adapt at Test Time?** (2611.19700) | 14 adaptation mechanisms, 109 tasks, 4 environments (SWE-bench Verified, AppWorld, ScienceWorld, BIRD-Critic-SQLite), Qwen3.5-9B. **ICL gives the largest standalone gain: mean success 28.8 % → 49.4 %.** ICL, GRPO with verifiable rewards and SDPO are compared alone and combined. | V |
| **TF-TTCL** (2604.13552) | Training-free test-time *contrastive* learning: an expert/amateur logit difference distilled into explicit positive and negative rules at the context level; no weights, no logits at inference. | V |

**What this says about us.** The frontier's own comparison says in-context adaptation is the biggest single lever, and the weight-side work (TTT, TTCD) is about making the *fast* state persist after the window closes. Both are "the fast state is the learning". We have no model, so our fast state is the trace store and the promoted code — but the mechanism they are formalising (write the residual, not the reconstruction) is exactly the playback rule we need for Play 4 and Play 5.

## 2. Computer use: the number that matters is 20.6 %, not 90 %

| Item | Claim | Mark |
|---|---|---|
| **OSWorld 2.0** (2606.29537) | 108 multi-application workflows; median human time ~1.6 h; ~318 tool calls per task (vs ~30 in OSWorld 1.0); 27.25 checkpoints per task. Best 500-step result: **Claude Opus 4.8, 20.6 % binary completion, 54.8 % partial**; GPT-5.5 13.0 % / 49.5 %. Completion falls below 10 % in the 137–163 min bin and reaches **zero above 163 minutes for every model**. Failures are attributed to constraint loss, missed mid-task information, guessing instead of asking, skipped verification, and **hidden or evolving state** — not to clicking. | V (paper page + two read-outs) |
| **Qwen-UI-Agent** (2607.28227) | 79.5 % OSWorld-Verified, 13.9 % binary / 40.0 % partial on OSWorld 2.0; 82.1 % MobileWorld; 92.2 % MobileWorld-Real; 97.5 % AndroidDaily. | V (write-up), U (vendor) |
| **Agent S4** | An open 27B model goes from 5.6 % to **21.3 % binary on OSWorld 2.0** at $1.10/task because the agent **evolves its own repository of interfaces** — 3.8× the same model with fixed interfaces. | B |
| **CUAWright** | A minimal unified interface for digital agents: **+33.2 % relative partial reward, −37.5 % estimated cost** against the published GPT-5.5 baseline. | B |
| **Latent2World** (2610.14228) | Predict the *action-induced change in latent space*, not the next screenshot. Two heads (action, transition) on shared representations, action-aware InfoNCE. **+31.9 % / +40.6 % relative success** over pixel-space world models, **−98.9 % inference latency**. Identity shortcut on strong transitions: 98 % (diffusion), 66 % (Code2World), 41 % (latent). | V |
| **CUWM** (2602.17365) | Two-stage: textual transition description, then visual realisation; trained on offline Office transitions; used for test-time action search with a frozen agent. | V |
| Vendor partial scores on OSWorld 2.0 | Fable 5.1 77.9 % (41.7 % strict), Simular Sai 73.0 % (28.25 % binary), GPT-6 Astra 72.6 %, Opus 5 70.6 %, GPT-6.1 Sol 70.5 %, Gemini 4 Argon 69.2 %, Muse Spark 1.3 66.9 %. Each was produced by its own vendor on its own subset/grader; none is comparable to the 20.6 % binary row. | U |

**What this says about us.** OSWorld 2.0's failure list is a list of *state* failures, and the fixes that worked (Agent S4's evolved interfaces, CUAWright's minimal interface) are *interface* fixes, not perception fixes. Latent2World's own ablation says the shortcut is in the prediction target, not the model. Every one of those is cheaper for us than for them: we pay nothing per step, so verification and expectation-checking are free at our margin and expensive at theirs.

## 3. Coding agents: the scaffold is the model

| Item | Claim | Mark |
|---|---|---|
| **The Scaffold Effect** (2607.22585) | 300 trials, 3 harnesses × 2 models × 50 Terminal-Bench Pro tasks. Harness choice induces **up to a 40× difference in tokens per solved task** while paired within-model pass-rate differences stay **0–8 pp**. Terminal-Bench 2.0 reports Opus 4.5 at 52.1 % vs 57.8 % with 256.9M vs 3.9M input tokens — a 65× token difference for 5.7 points. | V |
| **Harness design study** (2609.20804) | Predefined tool set vs bash-only: +15.0 % SWE-Bench and +10.1 % Terminal-Bench for a 30B model; for a 550B model bash-only is **+3.6 % / +5.6 % and 53 % / 30 % cheaper**. Planning: +11.6 pp for the 30B, **−2.0 pp** for the 550B. 66 % of bash-only trajectories for the small model die on out-of-interface emission. | V |
| Harness vs model variance | A controlled factorial reports harness-induced variance **7.8× the model-induced variance** on a SWE-bench subset, with **6 of 9 model-pair rankings reversing** under a different scaffold; OpenClaw adapter swap 19.1 % → 73.4 % Pass@1 with weights frozen; GLM-5.2 23 % → 52 % by harness alone. Anthropic: differences below 3 pp are noise, resource configuration alone moves ~6 pp. | B |
| Benchmark board, 13 Oct 2026 | SWE-bench Pro 61.5 % (Muse Spark 1.1, mini-swe-agent), Terminal-Bench 4.0 64.85 % (Claude Code + Opus 5.5), SWE-bench Verified 79.2 % (**contaminated**), OSWorld-Verified 90.19 %, τ²-bench 87.9 % pass^1. | B |

**What this says about us.** A harness we own is a harness we can measure, and the measured effect of the harness is larger than the measured effect of the model at the frontier. It is also free. The plan's Play 3 deletes harness knobs instead of adding them, because the 40× token spread is an indictment of unmeasured parts.

## 4. Memory: the accuracy argument is over and it was never an argument

| Item | Claim | Mark |
|---|---|---|
| Mem0 (platform) | 94.4 % LongMemEval, 92.5 % LoCoMo at ~6.8K–7.0K tokens/query, top-200 depth, GPT-5 as answerer *and* judge. | U |
| Zep | 90.2 % LongMemEval, 94.7 % LoCoMo, 104 ms p50 retrieval, GPT-5.4 reader/judge. | U |
| Independent runs | **Mem0 open-source edition 32.4 % LongMemEval against the vendor's 93.4 %**; Zep 63.8 % with GPT-4o; Letta ~83 % LoCoMo; Hindsight 91.4 %; Supermemory 85.4 % under 300 ms. | B |
| Method critique | The quoted Mem0-vs-Zep spread comes from different readers, judges and retrieval depths: *"the four-point spread is not a measurement of anything."* Mem0's own committed run moves 93.4 % → 90.4 % by changing retrieval depth from 200 to 50. | V |
| **PATH-Bench** (2608.01149) | Path-dependent lifelong evaluation: probe-centred sequences with controlled helpful/interfering histories, scoring average performance plus forward transfer, backward transfer and forgetting. Experience utility depends jointly on representation and task structure; **strong transfer does not ensure retention**; later experience reshapes earlier gains. Selective Experience Use (SEU) cuts forgetting across agents. | V |
| Forgetting under supersession | Graphiti 4.4–7.0 %, Letta 52.7 % on supersession/decay/purge suites (retained from V1). | B |

**What this says about us.** Memory is the one place where the public numbers are demonstrably not measurements, and where the honest metric (does the item change a decision; what does removing it cost) is cheap. Play 4 makes deletion the test.

## 5. Continual learning: everything still forgets

| Item | Claim | Mark |
|---|---|---|
| **RL Forgets / CPO** (2607.04364) | Continual RL still forgets badly on MRCL. CPO (replay-free, prior-task behavioural KL relaxed to a parameter-movement surrogate): **−13.7 % forgetting and +7.0 % pretrained capability on Qwen3-VL-8B**. Full SFT collapses to 43.99 % mean final accuracy. | V |
| **CMP** (2607.26523) | Local-learning architecture, no backprop and no replay: BWT +0.1482 vs +2.7897 naive and +2.2457 online-EWC, i.e. **94.7 % / 93.4 % less forgetting** on 15-domain byte-level LM. Also reports a null result on Split-MNIST. | V |
| **SLoRA** (ACL 2026) | The noise inside low-rank updates is a cause of forgetting; filtering it by subspace similarity to the frozen base gives **+12 % accuracy and −29 % forgetting** on TRACE while removing 30 %+ of LoRA parameters. | V |
| **FIT** (2601.21682) | Continual unlearning to 300 sequential requests; Forget Degree / Retain Utility as symmetric metrics. | V |

**What this says about us.** Our learning is code, so forgetting is observable as a test that stops passing — a cheaper and stricter signal than any of these. Play 5 uses that: backward transfer over a frozen probe set, with rollback.

## 6. Skill libraries and self-evolution: verification is the whole gain

| Item | Claim | Mark |
|---|---|---|
| **EvoSkills** (2604.01687) | SkillsBench: **71.1 %** vs 30.6 % no-skill and 53.5 % human-curated. One-shot self-generated skills: 30.7 % — **no better than no skills**. Gains appear only once iterative verification starts (44 % at round 2, 63 % at round 3, 75 % by round 5). Skills transfer to six other models at +36 to +44 pp. | V |
| **Skill-V** (2610.11781) | ALFWorld 95.3 % vs GRPO 77.6 %. Acquisition-only 68.8 %, failure-revision-only 67.2 %, full 95.3 %: **the revision of boundaries is the mechanism**, and the library stays smaller. | V |
| **Scaffold** (2609.05511) | Recursive parametric skill abstraction: WebArena 42.7 % (+11.1 over SkillRL), VWA 36.3 %, OM2W-X 43.5 %. In-context distillation instead of parametric: 34.7 % — **parametric beats prompting**; MDL compaction keeps the library bounded. | V |
| **MUSE-Autoskill** (2605.27366) | Self-created skills 60.35 % vs 68.40 % human skills vs 53.19 % baseline; generated skills transfer across agents. | V |
| **SkillSmith** (2606.01314) | OfficeQA 80.1 % at 397B (+18.3). **Locking the tool layer costs 6.8 points** — the largest single ablation. Removing anti-pattern memory triples the regression rate. | V |
| **OpenSkill** (2606.06741) | 43.6 % (Opus 4.6) / 42.1 % (GPT-5.2) against a human upper bound of 44.5 / 44.8, with no target-task supervision; its self-built verifier covers 88.9 % of ground-truth test intents. | V |
| **SkillX** (2604.04804) | A pre-built plug-and-play library lifts Qwen3-32B by ~10 points across AppWorld/BFCL-v3/τ²-Bench. | V |
| **SkillFoundry** (2604.03964) | Mines a domain into executable skill packages: 71.1 % of mined skills are novel against existing libraries; Repo-Acc 61.19 → 66.73 %, Paper-Acc 43.85 → 53.05 %. | V |

**What this says about us.** Every one of these results says the same thing: **a skill that is not verified is not a skill**, and a tool layer that is locked cannot improve. Our 641 adapterless modules are the open end of exactly that result; our receipts are the verification machinery already in place.

## 7. Speed: the cost that compounds

| Item | Claim | Mark |
|---|---|---|
| Small-model economics | 10–30× lower inference cost per token; local SLM 100–300 ms vs 2–5 s cloud round trip; the metric that matters is **cost per successful task**, not per call. | B |
| Agent loops | A 4× faster step is a 4× throughput gain in a loop; a 43× token difference on a perception step is a 43× cost difference per run. | B |
| OSWorld 2.0 cost | $3.87K per full run for one frontier configuration at 500 steps. | V |

**What this says about us.** Step latency compounds, and our step is a function call. The plan makes latency a gate rather than a metric: a change that slows a step must buy capability in the same measurement, or it is reverted.

---

## What changes in our plan because of this sweep

1. **Interface over intelligence.** The three strongest 2026 effects on agents (Agent S4's interfaces, Scaffold's parametric skills, the harness-vs-model factorial) are all interface effects, and all of them are free at our margin. Our ledger says 641 of 849 frontier-function modules have no adapter: that is the largest interface deficit we can measure, and it needs no new capability.
2. **Verification is not optional and it is our comparative advantage.** EvoSkills' one-shot condition shows self-generated skill without verification is worthless; OSWorld 2.0's failure list is verification failures. We pay zero tokens per step, so we can afford a check on every step where the frontier cannot.
3. **The public memory numbers are not measurements.** Independent and vendor runs differ by up to 61 points. Our memory claims must be cost-of-removal claims, not recall claims.
4. **Latent prediction is the wrong target and the right lesson.** Latent2World's 98 % identity shortcut is what happens when you predict appearance. We should predict the *change in observable facts*, and we already own the readers that can check it.
5. **ICL is the frontier's own best adaptation lever**, and we have no ICL — because we have no model. Our equivalent is the promoted library: an item that is callable and verified is the only kind of "in-context" we can have, and it is stronger because it is executed, not prompted.
