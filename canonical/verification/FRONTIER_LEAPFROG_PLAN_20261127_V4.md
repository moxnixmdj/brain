# Frontier leapfrog plan V4 — fewer parts, faster answers, receipts instead of claims

Supersedes V3 and the V3 amendment. V4 is shorter on purpose: three plays, each with a number that
kills it, and a delete list that is longer than the build list. "Best part is no part" applies to
plans first.

## The claim, in one paragraph

A frontier system answers "can you do X, and where is the code" by spending seconds and tens of
thousands of tokens re-deriving a fact it already has. This repo already *contains* the fact: 462
capabilities, 849 promotion candidates, every one compiled into a single 13 Mb artifact. Measured
today: the compiled model answers in **1.4 ms p95 with zero tokens and zero network calls**
(`RUNTIME_ANSWER_RECEIPT_20261127_V1.json`), against **28,142 tokens per solved task** for the
cheapest harness measured in the literature (Goose, 300 trials). The advantage is not a better
model. It is that the answer was compiled by execution, and the runtime reads a slot instead of
decoding prose. The only thing standing between this repo and that advantage is that **818 of 849
candidates are not callable** — a callability problem, not a reasoning problem.

## Three laws this plan obeys

1. **Selection law.** A second stage pays only if its pool is ≥10× what it keeps *and* the answer is
   already in the pool often enough (rerankers: useless at 20 candidates, on at 50 — arXiv:2604.01733).
   This repo: 170× pool ratio but recall@5 = 0.064 clean, and the gate (0.128) loses to its own
   removal (0.181). **Verdict: delete the gate, do not tune it.**
2. **Verification law.** Generation adds 1–3 pp; verification and repair add tens (CoEvoSkills
   71.1 → 41.1 without the verifier; SkillRevise −29.1 pp without diagnosis; SkillOpt's whole gain
   from 1–4 accepted edits). This repo already owns the verifier: two agreeing runs. Keep the
   verifier, delete the prose around it.
3. **Slot law.** If compiled evidence determines the decision, read it; never emit tokens to restate
   it (GUI grounding: 146 ms slot read vs 472–546 ms for ~20 decoded tokens, same accuracy;
   2.6–3.1 s with thinking).

## The plays, in order

### Play A — delete the gate (1 PR, no new module)

Remove the contract-first routing stage from the runtime decision path. `find_source` stays as the
fallback. No replacement, no weights, no tuning.

- **Kill criterion:** clean exact-target recall@5 falls by more than 5 pp (i.e. below 0.014) on the
  94 clean rows. If it does, restore — the gate would have been load-bearing after all.
- **Expected:** 0.064 → ≥0.064, since the ablation already scored 0.181 with the gate absent.
- **Speed:** deletes work; the route path becomes one index lookup.
- **Why first:** it is the only play that removes code, and it removes the third-most expensive
  thing in the runtime path.

### Play B — callable by execution, not by source reading (1 PR)

Record the call frame during each module's own test (arguments, types, return), replay it twice,
admit at a **40 % floor**, and write the surviving adapters into the ledger. This replaces the
literal-call rule that died at 3.7 % (15 of 406) — same admission test, different evidence source.

- **Kill criterion:** fewer than 40 % of the 406 attempted modules admit. Partial credit is not
  admission: 15 receipts changed no number last round.
- **Expected:** the 406 become ≥160 callable, taking the ledger from 31 to ≥190 of 849 (22 %).
- **Speed:** 5 s timeout per call, two runs, entire census under 10 minutes, 0 model calls.
- **Why second:** it is the only play that moves the number that matters (3.7 % → 22 %).

### Play C — a latency gate on every new capability (standing rule, enforced by artifact)

`runtime_answer_receipt_v1.py` runs in CI-adjacent form: load p95 ≤ 2 s, query p95 ≤ 5 ms, total
≤ 60 s, 0 model calls, 0 network calls. Any capability that cannot answer inside those budgets is
not in the compiled model — it is a script, and scripts do not claim to be runtime capability.

- **Kill criterion:** if a *legitimate* capability cannot meet the budget, the budget is wrong and
  gets raised once, in a PR that says so; if a capability meets the budget but answers nothing, it
  is deleted (that is the empty-answer column).
- **Current reading:** load 292 ms, query p95 1.44 ms, composite p95 1.46 ms, promotion lookup
  0.6 µs, total 1.04 s → **FAST**.
- **Why third:** it is the guard that keeps every future play honest, and it is already passing.

## The delete list (things this plan will not build)

| not building | because |
|---|---|
| a router, reranker, or gate of any kind | selection law; two independent corpora already say no |
| a vector store, embedding index, or memory graph | filesystem 74.0 % LoCoMo vs Mem0 graph 66.9 %; Mem0's own ablation calls the graph marginal; Memanto gets 89.8 % vector-only with no LLM per write |
| a "learner" separate from compile | fast weights are a *reuse* decision (In-Place TTT commandeers `W_down`); this repo's learner is the recompile |
| a bigger skill library | one-shot generation is 30.6 → 32.0 %; only verification moves the number |
| an agent loop for questions the artifact answers | 1.4 ms vs 28,142 tokens; the loop is the anti-pattern |
| per-module hand-written wrappers | 641 hand-written adapters is what the 3.7 % failure rate already priced |

## The hidden capabilities this plan promotes (found under non-obvious names)

These already exist in the tree and are what the unified runtime must expose. None is new code.

| capability | where it lives under an unlikely name | what it is in front of a model |
|---|---|---|
| compiled capability index | `canonical/unified_model/BRAIN_UNIFIED_MODEL_V1.json` | 462 capabilities, 1.4 ms lookup |
| promotion ledger | `canonical/tools/promotion_ledger_v1.py` → `UnifiedModel.model["promotion"]` | answers "why can't you call your own code" with counts |
| two-run admission gate | `canonical/tools/ast_adapter_derivation_v1.py` (`run_once`, digest compare) | a verifier that killed 96.3 % of candidates at 5.5 s |
| determinism as evidence | `verify_brain_unified_model_v1.py` 38/38 | a model that can prove it is itself |
| gate-free ablation | `contract_first_routing_v1.py` `require_contract=False` | the control that has now beaten the treatment twice |
| drift guard | `enforce_goal_hierarchy.py` | refuses stale-base receipts, 0 model calls |
| load-bearing admission | `execution_guard/enforce_load_bearing_primary_pr.py` | refuses work that does not move the obligation count |

## What "ahead" means operationally, this quarter

Three numbers, all local, all reproducible, none requiring a model API:

1. **Callable share of the 849** — currently 3.7 % (31). Play B target: ≥22 %.
2. **Answer latency at p95 with zero tokens** — currently 1.44 ms. Gate: never exceeds 5 ms.
3. **Parts removed per part added** — currently 1 removed (gate) to 0 added. Any PR that adds a part
   must show its own removal ablation in the same PR or it does not land.

A frontier lab cannot copy this by training a bigger model: the artifact is a projection of *this*
tree's executions, and the receipts are the moat — they are the difference between "the model says
it can" and "the model ran it twice and the digests matched."
