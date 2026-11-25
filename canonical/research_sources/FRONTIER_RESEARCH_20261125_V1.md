# Frontier research digest — 25 November 2026

Read for the leapfrog plan. Every entry names what it says and what it means for
us. Nothing here is embedded into the model; the compiler indexes it as a
research record (path, headings, retrieval terms), and the runtime opens the file
only when a query asks for it.

## Continual learning / test-time learning

| work | finding | consequence for us |
| --- | --- | --- |
| **NeurIPS 2026 Workshop: Towards Test-Time Continual Learning Agents** (neurips.cc/virtual/2026/loc/atlanta/workshop/137567) | Names the exact problem: "frontier models are frozen at deployment… any apparent adaptation comes from prompting, retrieval, memory, or external tools rather than genuine internal learning"; agents "do not improve from repeated mistakes, and erase prior skills when updated naively." Calls for shared terminology and long-horizon benchmarks. | The problem we attack is the one the field just declared open. Our constraint (no weights) is a *design position*, not a limitation, if we can show consolidation without gradients. |
| **aTTT — Agentic Test-Time Training** (arXiv 2607.03441) | Continuous in-episode LoRA updates help only when update-text repetition is controlled; gains "preserve existing competence rather than teach new abilities"; 1.9× cost. | Weight-space TTT buys retention, not learning. Our receipts are already repetition-controlled by construction (content-addressed, deduplicated). |
| **JitRL — Just-In-Time RL** (arXiv 2601.18510) | Training-free: a non-parametric memory of trajectories yields advantage estimates that directly modulate logits; provably the closed-form solution to KL-constrained policy optimisation; beats WebRL on WebArena/Jericho at >30× lower cost. | The strongest published evidence that *memory + a principled update rule* beats fine-tuning. We have no logits, so the analogue is an ordering prior over laws/actions with a stated bound — buildable and falsifiable. |
| **Are Self-Evolving Agents Continual Learners?** (arXiv 2610.25858) | Harness-editing agents (GEPA +3.7 pp terminal, −4.3 pp stability; ReasoningBank +2.5, −1.9) gain plasticity at a stability cost; global edits interfere, and similarity retrieval returns memories that are *topically* but not *procedurally* compatible. Conclusion: "continual learning needs updates conditioned on task context." | Direct validation of our law-carries-its-condition work (V24–V27). Their failure mode is our thesis: retrieval by similarity is the bug. |
| **Continual Self-Improvement with Lightweight Experiential Latent Memories** (arXiv 2606.17803) | Distils inference-time traces into soft-prompt memories ~0.001 % of parameters, a few gradient steps, beats zero-shot and raw ICL. | Even the best "cheap" method still needs gradients. A zero-gradient store that matches it would be the headline result. |
| **CL-Bench** (arXiv 2606.05661) | Dedicated memory systems do not beat naive in-context learning; agents overfit recent observations. | The memory market's premise is unproven even for them. |

## Skill induction / instant learning

| work | finding | consequence for us |
| --- | --- | --- |
| **SkillEvolBench** (arXiv 2605.24117) | 180 tasks, 6 environments, 10 model configurations, 3 harnesses. "Current agents often adapt locally but rarely form robust reusable skills"; the core problem is **selective procedural abstraction** — keep what supports future invocation, verification, robustness and composition; filter episode-specific noise. | Our measured bottleneck (selection precision 50 %, recall 100 %, laws recur 6/6, edits 3.7 %) is this paper's open problem, measured independently. That is the strongest strategic alignment in the digest. |
| **NSI — Lifting Traces to Logic** (arXiv 2605.01293) | Induces skills as explicit control flow (CheckOp/LoopOp/DataOp) with dynamic variable binding, from one successful trajectory; WebShop 44.5 % vs 32.2 % AWM; state-aware branching is what beats compressed history. | "A skill is a program with a condition", which is what our law store already is. Their LLM does the induction; we can do it with witnesses and refusals. |
| **K²-Agent** (ICLR 2026, arXiv 2603.00676) | One demonstration per task + Summarize–Reflect–Locate–Revise loop for declarative knowledge, C-GRPO executor for procedural skill; 86.5 % Android-in-the-Wild, 91.3 % ScreenSpot-v2 zero-shot. | Declarative/procedural decoupling mirrors our law/action split; their planner is the part we can beat on auditability. |

## Computer use / world models

| work | finding | consequence for us |
| --- | --- | --- |
| **CUWM — Computer-Using World Model** (arXiv 2602.17365) | Predicts the next UI state (textual delta, then a rendered screenshot); used for test-time action search with a frozen policy; specifically fixes action loops and structural transitions (modals, panes). | Their "textual state-change description" is our effect contract. We can skip the renderer entirely. |
| **GUI-CC** (EMNLP 2026 Findings) | Benchmarks world models as multi-step environments: 500 offline + 200 online tasks; "plausible single-step generation does not guarantee reliable environment simulation"; best offline reference-action progress **16.7/100**; explicitly calls for *explicit state representations or memory modules*. | The field is asking for the thing we have: an explicit, checkable state abstraction. Rendering pixels is the part we should refuse to do. |
| **World-In-World** (ICLR 2026) | Closed-loop world-model benchmark: prediction quality and task success diverge; post-training and inference-time scaling both help. | Confirms that "looks right" and "is usable" are different axes; our claim must be on the second. |

## Verification-first synthesis

| work | finding | consequence for us |
| --- | --- | --- |
| **LeetProof — Certified Program Synthesis with a Multi-modal Verifier** (ASE 2026, arXiv 2604.16584) | Validates specifications with randomised property-based testing *before* synthesis, decomposes guided by verification conditions, delegates residual obligations to Lean provers; beats single-mode synthesis at the same budget across two frontier backends. | Independent confirmation of "verification before generation" at fixed budget — our discipline, applied to their pipeline. |
| **SWE-bench Pro V2** (Scale/Reflection, board 2026-11-06) | Claude Opus 5 99.4 %, 642 tasks; vendor-owned public set 93.0 % (Fable 5.2); independent public-set leader 61.5 %. | Three different numbers for "the same" benchmark; ours must always name the set. |
| **Terminal-Bench 4.0** (tbench/Vals, Nov 2026) | 64.8–65.7 % at the top (Opus 5.5, Kimi K3.1 Pro); TB 2.0's 82.7 % is a different vintage. | Never quote a TB number without its version. |

## Memory systems, and how the frontier actually runs agents

| work | finding | consequence for us |
| --- | --- | --- |
| **Memory shootout 2026** (agentmarketcap, benchd.ai, dev.to) | Mem0 93.4 % self-reported vs **32.4 %** independent OSS on LongMemEval; GPT-4o-mini with *no* memory layer scores 57.6 %, above Mem0 OSS and LangChain; Zep 63.8 %; Letta's file-based storage 74 % on LoCoMo. | The memory market is a measurement failure, not a technology one. "What you store and how you organise it" beats "which vector DB" — our position exactly. |
| **Anthropic context engineering** (docs + 2026 write-ups) | Compaction (`compact_20260112`, 150K trigger), tool-result clearing (`clear_tool_uses_20250919`, 100K), memory tool (`memory_20250818`, client-side `/memories`), sub-agents returning 1,000–2,000 tokens; context editing +29 %, with memory +39 %, 84 % token reduction; "context rot": recall degrades as the window fills. | They are engineering around a context window. We do not have one. That is a product-shaped difference, not a philosophical one. |
| **OpenAI Agents API / durable sessions** (o-mega, 2026) | Durable sessions, automatic compaction, sub-agents, sandboxes, spend controls; multi-agent systems use ~15× the tokens of chat. | Persistence without a window is our natural advantage; theirs costs 15× tokens. |
| **Contrarian: "compaction preserves the rot"** (agenticbrew, 2026) | A summary preserves errors as faithfully as facts; power users disable auto-compaction, isolate in sub-agents, and rewind. | Our state is explicit and re-derivable from receipts, so there is nothing to summarise and nothing to rot. |

## What this digest refuses to claim

No number here was produced by us. Vendor and independent figures disagree by
15–60 points on the same benchmark name, which is itself a finding: the
comparison discipline we already enforce is a capability, not a chore.
