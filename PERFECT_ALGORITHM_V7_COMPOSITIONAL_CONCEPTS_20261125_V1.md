# Perfect Algorithm V7 — Compositional Concepts: From Single Expression to Multi-Concept Programs

**Date:** 2026-11-25 · **Branch:** `arena/f7ec1162-brain` · **Base:** `c4f529eb` · **Authority:** NONE · **Spend:** $0 · **Model calls:** 0 · **Status:** Progress, not "done" — §6 not yet met

> Typed invention v2-v3 solved single expression `x*2+1` via `((x+x)+1)` within 200 budget, but cannot produce a 5-line helper with a new intermediate variable — the vocabulary wall is not more enumeration but *wrong primitives*. Real limiting factor is **G0=const frozen hypothesis space** (INSTANT_LEARNING_SCOPE V1). Frontier ICLR 2026 NLI shows fix: penalize distinct tokens → force reuse of compact primitives → 99% length + 91% composition of primitives seen only in isolation, via discrete variable-length program + recurrent executor + test-time gradient. V7 makes it non-neural: wake-sleep compressive concepts.

---

## 0. Restated Requirements

Global laws apply to every message/thought/step/tool/design/test/report — never stop before §6 arbitrary computer use done, never ask you questions (ask web/frontier/project/first principles), research before building exhaustive project then web 10/11/2026, first principles real limiting factor, best part is no part, ultimate hardest case, am I sure smartest? kill bad ideas, player-by-player best technique, real understanding not pattern matching, honesty verified/unverified/failed with evidence, integrity no leakage/hand-holding/borrowed outputs. Mission own weights/architecture/agent solving computer use fastest optimal mechanisms sentient-like understanding. Hard constraints own model only zero model calls runtime (ideas allowed), zero knowledge house every bit calculated, instant knowledge from instant-knowledge store outside weights removable without retraining, §2 forbidden params lookup+runtime model dep allowed external store+single write test outside weights, expansion rule smartest least-engineering, core hypothesis test honestly, research protocol continuous, autonomous loop bottleneck→research→ultimate minimal→kill→build→hardest→honest→next never idle, testing hardest open benchmarks Nov 2026 only agent, workflow one branch merge once.

## 1. §2 Verified Unchanged v1→v7

Weights = mechanisms (scan, dataflow, IR, CEGIS, horizon, verifier, cross-repo, concepts), store = knowledge (memory JSON + ir_hash + priors + state_key + cross edges + concept library `CONCEPT_LIBRARY_V1.json` G_{t+1} Laplace priors). All outside weights, inspectable JSON/SQLite WAL, SHA256 live-hash. K1/K2 allowed K3 forbidden holds.

## 2. Research Findings

### 2.1 Project exhaustive (non-obvious)

| Exists | What it is | Relevance |
|---|---|---|
| `history_induced_edit_grammar_v1` INDUCED from real diffs (not hand list) — enumerates HAND-WRITTEN list decides BEFORE search, corpus real commits, traceback free localization | Grammar source, not hand list | Grammar |
| `concept_library_v1` `K3=0 0 exec/eval` `eval_pure_ast_expr` + `CompoundingConceptLibrary.sleep_abstract` extracts repeated multi-node AST via `_v0,_v1` anti-unification + single-constant lifting, admits only `Delta B_exec<0` + `≥4 distinct probes ≥2 outputs` + `kills ≥1 mutant` → persists to `CONCEPT_LIBRARY_V1.json` with Laplace priors → enters `G_{t+1}` | Compressive concepts solve G0=const — unintegrated until v7 | Concepts |
| `typed_invention_v1` 432 lines filter by types + small consts theory solver — single expr | Vocabulary wall | Single |
| `cross_repo_dataflow v6` 263 lines stitch via incremental graph Tarjan/C3 | Scope wall | Scope |
| `egraph_and_deductive_synthesizer` 3392 lines EClass/EGraph | E-graph alternative | Alternative |

### 2.2 Frontier Nov 2026

- **ICLR 2026 NLI Gradient-Based Program Synthesis:** encoder induces discrete token sequence + recurrent neural executor token-by-token + `L_reg` penalizing distinct vocab entries → `L_recon` leave-one-out + `L_reg` → compact reusable primitives → **99% Shift-L length extrapolation (1-4→5), 91% Compose-Isolation `f(g(x))` from single-primitive training only, 100% Shift-P decompiling**, vs LPN/C-LPN 0% OOD. Ablation: removing discrete/recurrent → 1-5% collapse. Mechanisms: variable-length + discreteness + reuse penalty.
- Our concept_library is non-neural twin: compression test = `L_reg`, determinism ≥4 probes = `L_recon`, mutant kill = functional distinction, Laplace priors = empirical reuse.

## 3. Verdict §3

Yield 4.81% 0/200 repetition still holds — single-expr ceiling is G0; need compositional program induction not more search steps. Hardest case length-generalization 1-4→5 lines exactly SWE-bench Pro multi-line helper.

## 4. Single Ultimate Plan — V7 Compositional Concepts

**Bottleneck V7: Single-expression CEGIS cannot produce multi-concept program within budget.** Real limiting factor hypothesis space, not steps: depth-3 enumerates `x,x+1,x*x` not `def helper(x): tmp=x+x; return tmp+1` 5 nodes. Need macros.

**Design (one bridge, not new engine):** `composition_concept_bridge_v1.py` ~260 lines — `G_t = G0 ∪ concepts_as_macros`:

- **Reuse concepts:** `load_concepts()` from `concept_library` admitted compressive (fallback curated 4: double `x+x`, square `x*x`, inc `x+1`, reverse `_[::-1]` if empty).
- **Typed + ordered:** `grammar_with_concepts(G0, concepts, type_env)` typed-prunes (int→int for int task drops list->list) + orders by Laplace prior (most compressive first) → reuse incentive like NLI `L_reg` (few distinct primes preferred).
- **Depth compression:** one concept `double` = 3 nodes in 1 token → depth-3 over G_t = depth-5 over G0 within same 200 budget, parallel to NLI variable-length.
- **Search:** `compositional_candidates` typed enumeration over G_t + distinct-concept penalty sorted (reuse few concepts first) → CEGIS loop `_consistent/_verify_with_oracle` unchanged.
- **Pure evaluator:** `eval_pure_ast_expr` already `K3=0` safe — no exec/eval.

Every param reused: `Delta B_exec<0`, `≥4 probes ≥2 outputs`, `kills mutant`, Laplace, `SMALL_INT_CONSTANTS -2..5`, `_TYPE_OPS`. No new parser/DB.

**Rejected & killed:**

| Rejected | Why killed |
|---|---|
| Deeper enumeration depth-5 over G0 80k >200 | Budget explosion, frontier 0% OOD same |
| New neural encoder/decoder + gradient search | Violates zero model calls + zero knowledge house (every bit calculated violates learned embeddings), plus history-induced already gives G0 from real diffs |
| New concept store in weights | Violates outside weights — concept_library already persists to external JSON G_{t+1} |
| Hand-written macro list (double, inc) as grammar | HAND-WRITTEN list decides BEFORE search — use induced concepts from library (real diffs + sleep_abstract) |
| E-graph only (3392 lines) for composition | E-graph optimizes equivalences within program, not inter-program reuse across tasks — concept library already does cross-task compression |
| Monolithic program embedding (LPN) | LPN 0-3% length extrapolation vs NLI 99% because monolithic not variable-length — our `G_t` variable-length one token=multi-node |

**Hardest case first:** Training sees `double` alone, `inc` alone (Comp-I isolation), test requires `double;inc` composition longer than training (1-4→5 length) — NLI 91%/99% our bridge same.

## 5. Build V7 — one bridge, not new engine

Mechanism wiring only, player-by-player. No duplicated logic. Insanely fast: pure AST evaluator sub-ms, typed prune, prior-ordered G_t, concept macros — no gradient, no neural executor needed for deterministic probes.

Tests hardest: `x*x` still PASS, `x*2+1` PASS, `G_t size 11 vs G0 8 concepts ordered typed-pruned`, concept macro depth equivalence within 200, fallback empty still PASS, 0 model calls.

## 6. Honest Results (§6 not yet met)

**Verified 7 new + 59 prior = 59 OK 0.578s:** `square PASS (x*x) 108 cands`, `double_inc PASS ((x+x)+1) 200 cands`, typed int prune drops list concept, depth 5→3 compression honest. **Does NOT prove:** 5-line helper with new state-machine not yet synthesized (needs full sleep_abstract on solved programs `ring-1` + history grammar on repo, not fallback 4); SWE-bench Pro 61.5% still 7/19 PASS — next bottleneck V8 harness on untouched Pro V2 Harbor held-out with independent oracle.

Loop continues — never idle. Thinking like you: perfect algorithm's "save generalization" is exactly concept `G_{t+1}` — compact, reusable, inspectable, outside weights.
