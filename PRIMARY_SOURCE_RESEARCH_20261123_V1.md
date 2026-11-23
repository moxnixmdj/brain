# Primary-source research ledger — fetched 2026-11-23

**Purpose:** replace search-snippet-only research with primary pages opened through `fetch_page`. These are inputs to design/falsification, never runtime dependencies and never capability credit. The project remains authority `NONE__PRODUCER_RUN_SANDBOX`; **no benchmark was run**.

**Method:** fetched the primary paper/leaderboard/repository pages below (first chunk for long pages; where a page had more chunks, the ledger records `hasMore=true` and does not pretend the entire page was read). Key verbatim passages are preserved so later turns can verify the claims without trusting snippets. Search snippets from earlier in the session are superseded for any fact that appears here. Twenty-one unique pages were opened; two additional calls fetched second chunks of the Scale leaderboard and one HTML paper.

---

## 1. Hardest computer use — OSWorld 2.1 / 2.0

- **Primary paper:** [OSWorld 2.0, arXiv:2606.29537](https://arxiv.org/abs/2606.29537), submitted 2026-06-28, revised 2026-07-13. `hasMore=true` on chunk 0; abstract and metadata fetched.
- **Release page:** [Snorkel AI, OSWorld 2.1](https://snorkel.ai/osworld-2-1-long-horizon-computer-use-evaluation/), dated 2026-09-16. `hasMore=true` on chunk 0; release, task design, metrics and running instructions fetched.
- **Official leaderboard:** [Snorkel AI OSWorld 2.0 leaderboard](https://snorkel.ai/leaderboard/os-world-2-0/). `hasMore=true` on chunk 0; leaderboard and methodology fetched.
- **Project repository:** [xlang-ai/OSWorld-V2](https://github.com/xlang-ai/OSWorld-V2). `hasMore=true` on chunk 0; top-level tree and latest commit fetched (Nov 13, 2026).
- **Original OSWorld:** [OSWorld 1.0 project page](https://osworld-v1.xlang.ai/). `hasMore=true` on chunk 0; abstract and environment infrastructure fetched.

Verbatim from OSWorld 2.0 paper abstract:

> "We introduce OSWorld 2.0, a benchmark of 108 long-horizon computer-use workflows across everyday and professional tasks ... Each task represents a realistic end-to-end workflow that takes human users a median of about 1.6 hours to complete and requires an average of 318 tool calls with Claude Opus 4.7 using maximum thinking, compared with about 30 in OSWorld 1.0."

> "Under our primary binary-completion metric at 500 steps, Claude Opus 4.8 with maximum thinking and batched tool calls scores best but still completes only 20.6% of tasks at a 54.8% partial score; GPT-5.5 is far more token-efficient yet plateaus near 13%. These results show that current agents are still far from professional-level computer use: rather than stumbling on basic GUI control or coding, they lose track of constraints, miss information that arrives mid-task, guess rather than ask the user, and skip verification, struggling most when a task hinges on hidden state they must recover."

Verbatim from OSWorld 2.1 release page:

> "OSWorld 2.1, released on September 16, 2026, is the recommended version for running the benchmark. It is a bug-fix release with updated agents, evaluation workflows, and pinned references for the task files, assets, mocked websites, and provider images, so results from different teams can be compared on the same footing."

> "The harness supports Docker, for Linux servers with KVM, and AWS, for large parallel runs. Task classes and full assets are distributed through gated Hugging Face datasets, which keeps answers and evaluator details out of reach of agents being evaluated."

Leaderboard facts (first chunk): 108 tasks, 31 self-hosted websites, 69.6% take humans over 1 hour, >250 average agent steps, 27.25 average scoring checkpoints; rank 1 Claude Opus 5 (max, batch tool) **44.33% binary / 77.67% partial**; Claude Opus 4.8 release row **20.6% / 54.8%**. Methodology: binary completion and partial credit vs deterministic graders, with **11.53%** of score from validated model-based checks; step budgets 150/300/500; separate 8-check safety audit.

Original OSWorld abstract: 369 real computer tasks; humans >**72.36%** vs best model at publication **12.24%**; execution-based evaluation scripts; headless operation supported.

**Implication for §6:** current hardest computer-use test is OSWorld 2.1 (bug-fixed 2.0), not a synthetic grid. A zero-model system that has not run its Docker/KVM or AWS harness, gated assets and evaluator has **no OSWorld score**. This sandbox has no guest VM/display and no such harness execution.

---

## 2. Hardest software engineering — SWE-bench Pro / Pro V2

- **Primary paper:** [SWE-Bench Pro, arXiv:2509.16941](https://arxiv.org/abs/2509.16941), submitted 2025-09-21, revised 2025-11-14. `hasMore=true` on chunk 0; abstract fetched.
- **Official benchmark page and public leaderboard:** [Scale Labs SWE-Bench Pro](https://labs.scale.com/leaderboard/swe_bench_pro_public) (resolved to `https://labs.scale.com/leaderboard/swe_bench_pro`). Chunks 0 and 1 fetched; chunk 1 `hasMore=false`.
- **Official open-source repository:** [scaleapi/SWE-bench_Pro-os](https://github.com/scaleapi/SWE-bench_Pro-os). `hasMore=true` on chunk 0; top-level tree and latest commit fetched.
- **Secondary November 2026 leaderboard digest:** [Morph, SWE-bench Pro Leaderboard November 2026](https://morphllm.com/terminal-bench-2) (resolved to `https://www.morphllm.com/swe-bench-pro`). `hasMore=true` on chunk 0; used only for split/version caveats, not as primary score authority.

Verbatim from SWE-bench Pro paper abstract:

> "SWE-BENCH PRO contains 1,865 problems sourced from a diverse set of 41 actively maintained repositories spanning business applications, B2B services, and developer tools. The benchmark is partitioned into a public set with open access to problems sourced from 11 repositories, a held-out set of 12 repositories and a commercial set of 18 proprietary repositories ... Problems in the held-out and the commercial set are not publicly accessible ... often involving patches across multiple files and substantial code modifications. All tasks are human-verified and augmented with sufficient context to ensure resolvability."

Official Scale page facts: public set **731** instances, private set **276**, held-out set **858**; reference solutions average **107.4 lines across 4.1 files**; primary metric Resolve Rate requires fail-to-pass tests pass **and** pass-to-pass tests continue to pass; four-stage workflow of sourcing, Docker environment creation, commit harvesting, human augmentation with three human-in-the-loop checkpoints. The page's older chart text says top models around **23%** on the public set, while its live leaderboard table lists **Muse Spark 1.1 61.50 ±3.10**, `gpt-5.4 (xHigh) 59.10 ±3.56`, and `claude-opus-4-6 (thinking) 51.90 ±3.61`; these are different evaluation eras/harnesses on the same page and must not be merged into one number. The Morph digest reports the same Scale standardized public top **61.5%** and commercial **51.5%**, plus a vendor aggregate **89.9%** (Opus 5.5); the spread is explicitly attributed to scaffolding and data splits. No single "SWE-bench Pro score" is meaningful without the split and harness.

Official repo top-level tree fetched: `v2/` commit message says **SWE-bench Pro V2 (v2.0.0): 642 Harbor tasks, HARD-51 subset, locked-protocol tooling**, with `v2/tasks` 642 validated task directories, `v2/hard51_ids.txt`, `v2/tooling`, `v2/GATE.md` release gate (reference patch 642/642, empty patch 0/642). Latest visible commit `66f9276` (Sep 22, 2026). This is a newer, harder target than the 2025 paper's public set.

**Implication for §6:** current hardest open coding target includes SWE-bench Pro V2 / HARD-51, not just the 2025 Pro page. Running it requires Harbor-format task images and a locked grader; no such run happened here. The local `single_line_fix` corpus is not SWE-bench Pro.

---

## 3. Hardest terminal work — Terminal-Bench 2.1 / 4.1

- **Official site:** [tbench.ai](https://www.tbench.ai/). `hasMore=true` on chunk 0; current leaderboard first page fetched. The rendered heading showed `TERMINAL-BENCH4.09876543210` with a `4.1` tab; the top row is **Copilot Fusion (max) / GitHub Copilot, 71.2% ±2.9%, Nov 17, 2026**; Opus 5.5 / Claude Code and Fable 5.2 / Claude Code both **65.8%**. (These are current-site rows; no independent re-verification.)
- **2.0 release explainer:** [Snorkel, Terminal-Bench 2.0](https://snorkel.ai/blog/terminal-bench-2-0-raising-the-bar-for-ai-agent-evaluation/), dated 2025-11-07. `hasMore=true` on chunk 0; release rationale and Harbor link fetched.
- **Archived 2.1 leaderboard:** [Snorkel, Terminal-Bench 2.1](https://snorkel.ai/leaderboard/terminal-bench-2-1/). `hasMore=true` on chunk 0; leaderboard and 2.0→2.1 comparison fetched.
- **Harbor repository:** [laude-institute/harbor](https://github.com/laude-institute/harbor) linked from the 2.0 explainer; not separately fetched in this round.

Verbatim from the 2.0 explainer:

> "Terminal-Bench 2.0 delivers on this vision with 89 carefully curated tasks that push the boundaries of what AI agents can accomplish in terminal environments. Each task underwent rigorous verification, with the development team meticulously reviewing every challenge to ensure it meets the highest standards."

> "Every task is now reproducible, properly specified, and genuinely solvable, with the team confident that near-100% performance is attainable for sufficiently capable agents."

2.1 leaderboard facts: 2.1 fixes **28 of 89** tasks (9 external dependencies, 8 resource mismatches, remaining misspecification); top archived 2.1 row **GPT-6 Astra / Codex CLI 87.4% ±1.8 (2026-09-03)**; 14 representative pairs average mostly improved from 2.0 to 2.1. The current official site now shows a 4.1-era table with lower top resolution (71.2%), which is a different task/harness generation and must not be averaged with 2.1.

**Implication for §6:** "Terminal-Bench 2.0" is no longer the frontier name on the official site. The hardest terminal target as of Nov 2026 is at least the current 4.1 table, with 2.1 archived. Neither was run here; running requires containerized Harbor tasks and graders.

---

## 4. Continual / instant learning and clarification

- **Primary paper:** [When Continual Learning Moves to Memory, arXiv:2604.27003](https://arxiv.org/abs/2604.27003), submitted 2026-04-29. Abstract page `hasMore=false`; full HTML [2604.27003v1](https://arxiv.org/html/2604.27003v1) chunk 0 fetched, `hasMore=true` (11 chunks).
- **Clarification paper:** [Ask or Assume?, arXiv:2603.26233](https://arxiv.org/pdf/2603.26233), chunk 0 fetched, `hasMore=true` (9 chunks).
- **Environment adaptation:** [ACuRL, arXiv:2602.10356v1](https://arxiv.org/abs/2602.10356v1), submitted 2026-02-10, revised 2026-05-11. Abstract page `hasMore=false`.

Verbatim from memory paper abstract:

> "Memory-augmented LLM agents offer an appealing shortcut to continual learning: rather than updating model parameters, they accumulate experience in external memory, seemingly sidestepping the stability-plasticity dilemma of parametric learning. We show that this challenge does not disappear but resurfaces at the memory level."

> "Across sequential-task experiments in ALFWorld and BabyAI, we find that abstract procedural memories transfer more reliably than detailed trajectories, while negative transfer disproportionately harms the hard cases. Moreover, finer-grained memory organization is not universally beneficial: designs that yield strong forward transfer can simultaneously induce severe forgetting."

Verbatim from the memory HTML introduction:

> "irrelevant memories may be recalled, introducing retrieval pollution; useful experiences may be displaced by other retrieved items under a finite context window, creating context competition; and as the memory store grows across tasks, relevant experience may become harder to identify, resulting in memory dilution."

Verbatim from Ask or Assume? abstract:

> "we systematically evaluate the clarification-seeking abilities of LLM agents on an underspecified variant of SWE-bench Verified. We propose an uncertainty-aware multi-agent scaffold that decouples underspecification detection from code execution. Across both proprietary and open-weight frontier LLMs, our scaffold achieves a 69.40% task resolve rate ..."

The paper's contributions state it uses frontier LLMs (Claude Sonnet 4.5 and Kimi K2.6) and simulated user interaction. That is an input about *when* clarification helps; it is forbidden as a runtime dependency here.

Verbatim from ACuRL abstract:

> "we introduce ACuRL, an Autonomous Curriculum Reinforcement Learning framework that continually adapts agents to specific environments with zero human data. The agent first explores target environments to acquire initial experiences. During subsequent iterative training, a curriculum task generator leverages these experiences together with feedback from the previous iteration to synthesize new tasks tailored for the agent's current capabilities."

> "our method effectively enables both intra-environment and cross-environment continual learning, yielding 4-22% performance gains without catastrophic forgetting on existing environments. Further analyses show highly sparse updates (e.g., 20% parameters) ..."

ACuRL updates parameters and uses a CUAJudge; it is evidence that adaptation is hard, not an allowed runtime component.

**Implication for design:** external store alone does not solve learning; raw trajectories harm hard cases; abstract relations are safer; clarification works in model-based scaffolds but cannot be borrowed. This supports the §2 boundary refinement: store relation *texts*, recompute predicates from the new machine's own runs, refuse when recomputation fails, and never count guides/web as capability.

---

## 5. Relation algebra / deictic representation — fetched for iteration 5

- **Primary 2026 predicate-invention paper:** [Continual learning and refinement of causal models through dynamic predicate invention, arXiv:2602.17217](https://arxiv.org/abs/2602.17217), submitted 2026-02-19. Abstract page `hasMore=false`; full [HTML v1](https://arxiv.org/html/2602.17217v1) chunk 0 fetched (`hasMore=true`, 6 chunks). Verbatim abstract: "We propose a framework for constructing symbolic causal world models entirely online by integrating continuous model learning and repair into the agent's decision loop, by leveraging the power of Meta-Interpretive Learning and predicate invention to find semantically meaningful and reusable abstractions..." The HTML states "We assume lifted dynamics, meaning rules depend on object relations rather than identities" and describes a "Predict–Verify–Refine" cycle. This is an input: its lifted, object-relational representation supports the direction of iteration 5, but the system uses MIL and world-model learning; none of it is a runtime dependency here.
- **ExoPredicator:** [arXiv:2509.26255](https://arxiv.org/abs/2509.26255), v3 2026-03-15, ICLR 2026. Abstract page `hasMore=false`. Verbatim: "We learn these world models from limited data via variational Bayesian inference combined with LLM proposals." It invents predicates from 1–2 demonstrations but uses an LLM/VLM proposer. That is forbidden at runtime here and is useful only as evidence that predicate invention is a frontier bottleneck.
- **Canonical labelling:** [Canonical Labelling of Random Regular Graphs, ICALP 2026](https://drops.dagstuhl.de/entities/document/10.4230/LIPIcs.ICALP.2026.114), published 2026-07-01. Metadata page `hasMore=true` on chunk 0; abstract fetched. It proves canonical labellings for random regular graphs via colour refinement. This is an input for the killed full-isomorphism-table design: canonicalising whole traces is a real operation, but exact canonical cells turned out too fine for transfer (43/69 abstentions measured in iteration 5), so the shipped relation uses a coarser deictic holder-shape projection instead.
- **Deictic object-oriented transfer:** [Zero-Shot Transfer with Deictic Object-Oriented Representation in RL, NeurIPS 2018](https://papers.nips.cc/paper_files/paper/2018/hash/df0aab058ce179e4f7ab135ed4e641a9-Abstract.html). Abstract page `hasMore=false`. Verbatim: "we introduce a novel deictic object-oriented framework that has provably efficient learning bounds and can solve a broader range of tasks... zero-shot transfer of transition dynamics across tasks." Older than Nov 2026, but it names the mechanism iteration 5 computed: refer to objects by their relation to the current transition, not by absolute names.
- **Project prior art:** `THE_GOAL_IS_A_QUOTIENT_OF_THE_TRACE_20261128_V1.md` already computed projections of `(identity, content)` readings and measured that `holders_by_step[probe_seed_content]` is a single sufficient statistic for `moved_judge`; `THE_VOCABULARY_IS_THE_ARTIFACT_20261125_V1.md` measured that `mv` and `sort` are invisible to a fixed `{CARD, MULTISET}` vocabulary because the needed relation is `PAIRING`/`ORDER`; `A_SITE_IS_NOT_A_PRODUCTION_20261124_V1.md` rejected hand-built row-per-form vocabularies. Iteration 5 reuses those findings instead of rebuilding them.

**Implication for iteration 5:** use a computed deictic holder-shape term family, not a hand-written `holder_changed` predicate, not a full canonical-trace table, and not a model-proposed predicate. The relation is a conjunction of computed Boolean invariants, selected by version space and one real judgment on a delayed-content run.

## 6. Conflicts and honesty notes

- **OSWorld:** 2.1 is a bug-fix release of 2.0; the paper's 20.6% is the release binary score, while the live 2.0 leaderboard shows 44.33%; both are true at different times. Original OSWorld 1.0's 12.24% is not a 2.x score.
- **SWE-bench Pro:** the paper (2025), Scale page (older chart + live table), Morph digest (Nov 2026), and Pro V2 repo (Sep 2026) describe different splits/harnesses/versions. Do not quote a single score without split and harness; do not claim our system has one.
- **Terminal-Bench:** 2.0 (89 tasks), archived 2.1 (28 fixes, 87.4% top), and current 4.1-era site (71.2% top) are different generations. "Terminal-Bench 2.0" is not the current frontier name.
- All fetched pages are build-time research. No web page, model, paper, leaderboard, adapter, or external agent became a runtime dependency or supplied producer cognition. No full PDF was downloaded into the repo; no benchmark task, answer, evaluator, or trajectory was imported.
- This ledger itself is **not** independent verification and does **not** satisfy §6.

**Saved deliverables:** this file, plus `THE_ENVIRONMENT_ANSWERS_THE_QUESTION_20261123_V1.md` (consolidated report) and the six receipts under `canonical/verification/` named in that report.
