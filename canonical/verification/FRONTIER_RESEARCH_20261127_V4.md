# Frontier research V4 — the delta since V3, and the one law that explains this repo's own numbers

Delta document. V3 (`FRONTIER_RESEARCH_20261127_V3.md`) covers In-Place TTT, JitRL, OSWorld 2.0,
TF-TTCL, Skill-V, EvoSkills, Mem0/Zep vendor spread, CPO/CMP/SLoRA/FIT, Latent2World and the
October board. This file records only what changed the plan, plus one law that reconciles this
repo's measurements with the literature instead of contradicting it.

Legend: **V** = page read, **U** = vendor claim, **B** = aggregator or blog (numbers kept only when
the underlying paper or table is quoted inline).

---

## 1. The law: a selection stage pays only when it can select

Three 2026 sources measure the same boundary from different sides.

| source | what it varies | result |
|---|---|---|
| Reranking ablations (V, arXiv:2604.01733 §IV-C) | candidate depth | **20 candidates: reranking ineffective, Recall@5 0.458; 50: 0.826; 100: 0.888** |
| Same (V) | component removal | cross-encoder is the single most impactful component, **+17.2 pp MRR@3** over unreranked hybrid |
| SkillCorpus (V, arXiv:2607.15557 §4.5) | retrieval stack and corpus quality, 821k-file crawl | fine-tuned retrieval **22.6 %** pass@1; off-the-shelf Qwen3 embeddings **13.8 %**; raw unfiltered crawl **14.9 %** |
| Practitioners' rule (B, three independent posts) | when a reranker cannot help | when **recall** is the bottleneck: "a reranker can only reorder what retrieval found" |

The rule that survives all three: **a second stage earns its cost only when the pool it sees is
much larger than what it keeps *and* the answer is already in that pool often enough to reorder.**
Where the pool is small or recall is low, the stage is dead weight and "best part is no part"
applies literally.

**This repo measured exactly the dead case and did not have the vocabulary for it.**
`EXACT_TARGET_SCOREBOARD_20261127_V1.json`: pool 849, keep 5 — a 170× ratio, which by pool size
alone looks ideal for a reranker — but `find_source` recall@5 on clean targets is **0.064**, and the
contract gate reaches **0.128** while the same scorer with the gate removed reaches **0.181**.
Recall-limited, therefore every precision stage is negative-value. SkillCorpus's retrieval stack
looked valuable for the opposite reason: 821k candidates, low-baseline tasks, and the winner often
present. Same law, opposite conclusion — and it says where a gate *would* be worth building: a
corpus an order of magnitude larger than what the router keeps, with measured recall@k above 0.5.

**Consequence for the plan.** Do not revisit routing on this corpus. The 641 uncallable modules
are a callability problem, and no arrangement of a 5-item shortlist from 849 can fix it.

---

## 2. Speed: where the frontier's milliseconds actually go

**GUI-Decisions (V, Oct 2026).** Stop decoding coordinates; read the answer out of a reserved slot.

| how a computer-use step is decided | ms / step | vs slot |
|---|---:|---:|
| slot read | **146** | — |
| coarse-to-fine slot read | 159–163 | +15 ms |
| vanilla JSON `[y, x]` (~20 tokens decoded) | 472–546 | **~3.5×** |
| pixel JSON (~30 tokens) | 704 | 4.8× |
| vanilla + thinking (130–230 tokens) | 2600–3100 | **~20×** (up to 7 s) |

Same accuracy (GUI-Owl-2B 0.626 either way; ScreenSpot 0.770 with slots vs 0.645 vanilla), at 30 %
of the latency. The cost of *deciding* was the cost of *emitting tokens that restated a decision
already made*.

**Harness vs model (V, arXiv:2609.11987).** A neutral harness has no capability premium (−1.25 pp
Opus 4.8, +1.25 pp GPT-5.5, intervals crossing zero) but costs **1.2–1.6× per solved task**. And
the number that should be framed on a wall: **22 of 81 runs cancelled at the wall-clock ceiling had
already produced a passing patch** — the time limit destroyed 27 % of completed work.

**Scaffold Effect (V, arXiv:2607.22585).** 300 trials: harness changes tokens per solved task by
**40×** (28,142 Goose → 1,546,977 OpenCode) while paired pass-rate moves 0–8 pp. Upgrading the
model moves tokens 1.0–1.3×.

Together: **latency is dominated by re-deriving decisions that were already determined, and by
scaffolding, not by the model.** The correct response is not a faster loop; it is fewer loop
iterations over decisions that could have been read from a slot.

---

## 3. Instant learning: fast weights are a reuse decision

**In-Place TTT (V, ICLR 2026)** commandeers the MLP down-projection `W_down` already present in
every block as the fast weight; `W_up`/`W_gate` stay frozen. No new layers, no retraining — the
architectural answer to "how do I add learning" is **"do not add anything, repurpose what is
there."** Fast weights are reset at document boundaries (V, secondary). **IP-TTCD**
(arXiv:2608.01672, V) makes the update a teacher–student residual and beats DeltaNet, Gated
DeltaNet, SWA and TTT when pre-trained from scratch. **End-to-End TTT** (Dec 2025, V via secondary)
reports **2.7× faster inference at 128K** than full attention — learning that *reduces* per-token
cost.

Repurposing is the same move in this repo: `UnifiedModel.promotion` is a compiled projection of
real executions, refreshed at compile time by `promotion_ledger_v1.py`, and it costs **zero** at
query time (measured: 0.6 µs per lookup in `RUNTIME_ANSWER_RECEIPT_20261127_V1.json`). The lesson
generalises into a rule for the plan: **a "learner" that is not a recompile of evidence is a new
part, and a new part must beat its own removal.**

---

## 4. Skill libraries: verification pays, generation does not

| system | ablation | result |
|---|---|---|
| CoEvoSkills (V, arXiv:2604.01687) | remove the surrogate verifier, keep 5 evolution rounds | **71.1 % → 41.1 %** |
| SkillRevise (V, arXiv:2606.01139) | remove diagnosis; remove the preserved ledger | **53/86 → 28/86 (−29.1 %)**; 53 → 42 (−12.8 %) |
| SkillOpt (V, arXiv:2605.23904) | how many edits survive | huge gains from **1–4 accepted edits**, artifacts **<2,000 tokens**, best/tied on 52/52 cells |
| SkillCorpus (V) | same skills, two harnesses | Raven +13.4 pp vs OpenClaw +5.7 pp on the same model |

Generation adds ~1–3 pp (30.6 → 32.0 % one-shot); verification and repair add tens of points.
This repo's two-run admission gate is that verifier, and last round it killed 96.3 % of candidates
(15 of 406). The gate is the cheap part and it is doing all the work — keep the receipt, delete the
prose.

---

## 5. Memory: the graph is often the part that should not exist

| system | LoCoMo | LongMemEval | architecture |
|---|---:|---:|---|
| Letta filesystem (V, quoted) | 74.0 % | — | files, no vector store |
| Mem0 graph (V, quoted) | 66.9–68.4 % | 49–68.5 % | hybrid graph + vector |
| Memanto (V, arXiv:2604.22085) | **87.1 %** | **89.8 %** | **vector only, single query, no LLM per write** |
| ByteRover context tree (B) | 96.1 % | — | filesystem, ~80 ms p50 |

Mem0's own reported ablation (V, via Memanto's comparison table): the graph-augmented variant
yields "only marginal improvements over the base vector configuration." Files beat graphs below a
size threshold; a single retrieval query beats parallel multi-query; zero ingestion LLM calls beats
extraction pipelines. This repo is already a filesystem plus a compiled index — **do not add a
vector store, and do not add a memory graph.** The gap is not the store, it is that 641 modules
have no adapter and therefore no retrievable effect.

---

## 6. Computer use: grounding is solved, horizon is not

ScreenSpot-Pro grounding: 18.9 % at launch (early 2025) → **92.7 %** (GPT-6 Astra, Sep 2026, V).
OSWorld-Verified: **90.19 %**; OSWorld 2.0 binary: **20.6 %** (V3). WinDeskGround (V, ICML 2026):
>80 % single-window → **7–11 % at 10+ windows with occlusion** for all five models tested.
UI-TARS 7B edge (B): 0.4–0.8 s/turn, 31.8 % on a 100-step task, $0.35/compute — vs Claude 3.7
Sonnet 2.8–4.2 s, 44.2 %, $18.50–28.

The pattern is the plan's: per-step perception is cheap and solved; **the failures are constraints,
hidden state and skipped verification across dozens of steps** — which is a *bookkeeping* problem,
exactly the kind a compiled receipt layer solves without a model.

---

## 7. What V4 adds to the plan and what it deletes

**Adds**
1. The selection law, with the two-sided evidence (§1), and a precondition for ever rebuilding a
   gate: pool ≥10× the kept set **and** recall@k ≥ 0.5.
2. A latency gate as an admission rule, not a metric: a capability that needs a model call to be
   found is not in the compiled model (enforced by `runtime_answer_receipt_v1.py`).
3. Slot-read discipline: if a decision is determined by compiled evidence, the runtime reads it,
   and no tokens are emitted to restate it.

**Deletes**
1. Any further work on routing on the 849-module corpus.
2. Any proposal to add a memory store, a graph, or a vector index (marginal-to-negative by §5).
3. Any "learner" that is not a recompile of evidence (§3).
4. Any skill/prompt generation step without a verifier behind it (§4).
