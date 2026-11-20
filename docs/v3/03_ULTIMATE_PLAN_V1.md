# Ultimate Minimal Plan — Computer Use from One Experience (no waste, no pretense)

**Date:** 2026-11-20 | **Branch:** arena/69b87879-brain | **Status:** PLAN (no code shipped this turn, zero benchmark runs)
> One plan, not incremental. Every component justified then killed via "smartest approach?" Rejected ideas with reasons. Reuse→Adapt→Compose before synthesis.

---

## 0. One-sentence plan

**Ship a single new capability — `COMPUTER_USE_ONE_SHOT_CAUSAL_CUT_V1` — that turns any OSWorld2.0/SWE episode into a verified, family-scoped, re-derivable skill via causal-cut attribution + falsifiable family predicate, admitted only on held-out gain, actuated by local grounded verification loop; all else is reuse of what you already have.**

No new model training. No runtime API. No "world facts in weights." One typed mechanism + one store extension + one verification cap.

## 1. Why this is the *only* non-dominated next action

Per `ACTIVE_GOAL_HIERARCHY_V1` + `CURRENT_LIVE_WORK_FRONTIER` exact-next:
- Runnable benchmark rows: 0. Wake-gated 12, parked 1. Benchmark-as-parent is forbidden.
- Standing exact-next: `CODING_GENERAL_SOFTWARE_REPAIR_LOOP_V9_PLUS_CURRENT_BYTES_RESOURCE_PARETO_CUT…PROFESSIONAL_WAKES_ONLY_ON_ZERO_SPEND_CARRIER_STATE_CHANGE`
- Allowed credit: verified reusable gain / reliability+resource gain without regression / live integration / independent falsification. Benchmark score alone = 0.
- Route order forces: DELETE > BYPASS > REUSE > ADAPT > SUBSTITUTE > COMPOSE > CONFIGURE > INTEGRATE > SYNTHESIZE_NEW_PRIMITIVE (new primitive requires falsification proof).

The plan obeys all:
- **Reuse** the typed attribution+admission successes (acquired-operator re-derivation, verified-skill recall, bytes law).
- **Adapt** their family predicate machinery from arithmetic to open trajectories (the one synthesis).
- **Compose** with existing grounded action + bytes cut + fabric routing.
- **Zero** new primitive that isn't forced: causal-cut engine is forced because no existing component extracts falsifiable family from open trajectories (proven by 0/90 real-commit, 0/5 structural, 24 success-only rows).
- Benchmarks are **audit/probe only** (OSWorld2.0 20–44% gap localizes attribution; TB4/SWE-Pro calibrate generality) — not parent objective.

## 2. Architecture — 5 existing + 1 new (each justified or it dies)

### 2.1 What we reuse unchanged (delete-before-add check passed)

| Reused component | Why it stays | "Smartest approach?" kill test |
|---|---|---|
| **BRAIN_UNIFIED_MODEL_V1 (11.2 MB, 447 caps, 1383 sources)** + live registry adapter | Router+mechanism index; not retrained; SHA verified. Computer use today 4 FS/program caps stay; new GUI caps are *bindings*, not model. | Kill: rebuild model? No — bytes frontier says rerank V81, not rebuild. Reuse. |
| **unified_cognitive_fabric_v1** + engine descriptors | Already routes P3/H100/MYSTERY/CERTIFIED_ROUTE/LIVE through `observe_runtime_outcome`. New cap is `BOUND_CAPABILITY` route. | Kill: new fabric? No — descriptor table is the integration point. |
| **verified_skill_crystallizer + causal_trace_to_skill_compiler + VERIFIED_SKILLS/WORKFLOWS bundles** | Proven durable skill store with re-verification on recall. New causal cuts land here, same WAL. | Kill: new store? No — store semantics correct; only producer changes. |
| **acquired_operator_memory teach/recall/restore** | Only component that proves fresh-process re-derivation via gate re-check (`_usable`, `induce_laws`, `law_is_falsifiable`, `indistinguishable_from`). Pattern copied, not replaced. | Kill: keep arithmetic demo? Yes — it is the correctness proof we copy. |
| **Bytes Pareto cut (BYTES_ACTIVE_STATE 1,577,081 raw) + minimum-proof-cover optimizer** | Resource law: exact minimum cut is the cheapest falsifier. `NEXT86 NO_ADAPTATION` means next cut is pure rerank — aligns with plan's "no waste." | Kill: ignore bytes? No — violates `RESOURCE_BOUNDED_CAPABILITY_BYTES_LAW`. |

### 2.2 What we adapt (one small change, not rebuild)

| Adapted | Change | Justification |
|---|---|---|
| **weight_update_admission_v1 + semantic_generalization_engine** | Keep 3-head mechanism (op/concept/domain) and parser-judge. Add *null-space / LoRA-memory-free* update path (NuSA-CL style: null-space of past tasks > top, merge-to-base fixed budget) as *optional* weight path when store recall + re-derive insufficient. Gated same ADMIT. | Prevents forgetting (3/32 breakage) without dossier bloat. Frontier: NuSA-CL ICLR26 is memory-free continual; TTT shows hidden-state-as-model works ≤1.3B. Adapt, not invent. |
| **h100_computer_use_registry** | Promote from 4 caps to **7 caps** by adding `CAP_GUI_GROUND_V1`, `CAP_GUI_ACT_V1`, `CAP_GUI_VERIFY_V1` as verified-bound caps (grounded_action_v1 pattern: bind-first + decisive margin + independent byte re-read). Grounding distilled from open UGround (10M/1.3M recipe) into local artifact — no runtime model. | Kill: call hosted VLM? Forbidden (K3). Kill: skip verification? OSWorld paper: lowest scores are unverified implicit-state — verification is load-bearing. |

### 2.3 The single synthesis — CAUSAL_CUT engine (forced, falsifiable)

**Component:** `canonical/swe_kernel/causal_cut_attribution_v1.py` + `family_predicate_induction_v1.py` (two files, one capability)

**What it does:** Input: one full episode trace (obs/act/outcome). Output: triple `(cut, family_predicate, verifier)` where:
- `cut` = minimal subsequence that is *necessary and sufficient* for outcome (counterfactual test: removing any element breaks success; replaying cut alone succeeds — bounded `≤7` edits / `≤5` GUI actions, same bound that made H100 chains provable).
- `family_predicate` = falsifiable predicate over tasks (like `value_algebra.laws` but for trajectories): typed as `precondition (file set / UI region / state predicate) × action schema × postcondition check`. Must pass `law_is_falsifiable` equivalent: there exists a constructible negative that predicate distinguishes.
- `verifier` = independent byte re-read check (file content / screenshot crop / DOM subset) that decides success without LLM judge.

**Why this is the right synthesis (first principles):**
- Bottleneck is attribution, not perception/coding. One trace encodes causal cut + family; extracting both is exactly `acquired_operator_memory` for arithmetic, lifted to trajectories.
- Minimal cut + falsifiable predicate gives held-out construction for free: synthesize negative/positive tasks by predicate mutation (same trick `UNIVERSAL_ESCAPE_RESOLVER` used for 112M variants; same trick Terminal-Bench uses per-task verifiers).
- ADMIT stays strict: `gained≥1 && lost==0` on predicate-generated holdouts; no forgetting.

**Mechanism details (no magic):**
- Search cut via A* over trace subsequences with verifier as goal test (cost = cut length + predicate complexity; frontier `BYTES` law weighted in — shorter cut preferred).
- Induction via `induce_laws` analog but over trajectory features: `pre-state delta`, `action type`, `post-state delta` hashed features (reuse semantic engine 128-dim hash). Laws are counted via `indistinguishable_from` on execution outcomes, not token match.
- Re-derivation guarantee: stored triple re-derives in fresh process by re-running `induce_laws` on cut+predicate — if gate fails, skill *not* admitted (same semantics as `acquired_operator_memory.restore`).

**Why this is ultimately minimal (best-part-is-no-part):**
- No new perception model shipped — grounding distilled offline, verified as cap with receipt (like Qwen smoke workflow pattern).
- No new persistence tier — writes to existing VerifiedSkillStore WAL via crystallizer (same ADMIT).
- No weight change by default — Tier B store; Tier C null-space update only when store recall insufficient and gate passes.

## 3. Design decisions killed by "smartest approach?" (rejected with reason)

| Rejected idea | Why it seemed attractive | Why killed (smartest approach) |
|---|---|---|
| **Train new vision-language model for computer use** | Frontier: UGround 72B 89.4% ScreenSpot; every vendor does it | Violates zero-model + zero-warehouse + every-bit-justified. K3 forbidden regardless of hosting. Assembly: distill grounder module (planner-less) as inspected artifact, don't ship model. |
| **Runtime call to frontier VLM (GPT-4o/Claude) as tool** | Would instantly boost OSWorld binary | K3 forbids runtime external cognition regardless of label/cost; `RUNTIME_COGNITION_PROVIDER_FORBIDDEN`. Build-time distillation of ideas allowed, runtime call not. |
| **New large parametric memory (vector DB for everything)** | Frontier "only frozen+RAG ships" (2026 map) | Conflates retrieval with learning; `A_SINGLE_TRACE` shows retrieval without causal cut doesn't transfer (13/15 zero). Verified store + re-derivation already correct; enlarge predicate, not DB. |
| **Loose admission to "learn faster" (gained≥1 only, drop lost==0)** | Would admit more one-shot skills quickly | Proven breakage 3/32 when self-loss used; LRM fine-tunes increase forgetting (2601.18699). Gate is load-bearing; add null-space path instead. |
| **New benchmark-specific OSWorld harness fork** | Quick score bump on 2.1 | Violates `CURRENT_ZERO_REALITY_MINIMUM_CUT` (`NO_FRESH_REALITY_FROM_THIS_CUT`, `NO_NEW_SAME_INFORMATION…SECOND_CARRIER`, `FORBIDDEN HELDOUT_003_REPLAY`). Policy: benchmark as audit only, no patch without transfer. Next cut is professional wakes only. |
| **Replay Verified 369 as parent to claim OSWorld win** | 90% saturated, easy win | Verified is *narrow single/short tasks* by design; 2.0 paper: long-horizon multi-app is different phenomenon (implicit-state etc.). Chasing saturated board = `BENCHMARK_AS_PARENT_OBJECTIVE` forbidden. |
| **End-to-end differentiable skill induction** | Elegant | Hides attribution; no falsifiable predicate → no held-out auditing; violates FAIL_CLOSED_TRUTH. Symbolic cut + verifier is auditable. |
| **Immediate weight mutation from one episode** | Feels like "real learning" | NuSA-CL lesson: only tail-null-space preserves zero-shot; naive LoRA forgetting. Default to store; weight only via null-space ADMIT. |

## 4. Smartest-approach stress test on the plan itself

- *Am I rebuilding what exists?* No — 6/7 reuse/adapt; one synthesis forced by 3 independent failures (0/90, 0/5, 24-success-only).
- *Am I adding waste?* No — bytes law enforced: cut length penalized, predicate complexity penalized, shortest verified cut wins (exact minimum proof cover).
- *Is it ultimate or incremental?* Ultimate-hard: causal cut bounded ≤7 but *family* is open-ended; verifier is independent byte re-read, not LLM judge (OSWorld's 11.53% model-judge weight is why it can be gamed — we don't).
- *Player-by-player?* Yes — UGround grounding recipe + NuSA-CL null-space + our acquired-operator re-derivation + our verifier pattern; best whole, not bought team.
- *Integrity?* All proofs are trajectory+recomputation, not scores; trajectory required, Trojan-hackable boards (Berkeley audit) not trusted without independent verifier.

## 5. Build order (autonomous loop §5 — single bottleneck at a time)

1. **Bottleneck 1: Causal cut on verified narrow family (typed).** Build `causal_cut_attribution_v1` on `CHART_AXIS_TITLE_UNIT_BINDING`-class tasks where verifier already exists. Prove 7/7 with cut length ≤3 and predicate that generates held-out that ADMIT passes. Ship as `COMPUTER_USE_ONE_SHOT_CAUSAL_CUT_V1` with bundle `CAUSAL_CUT_BUNDLE_V1.json`. No benchmark chase.
2. **Bottleneck 2: Family predicate induction generalized.** Extend `family_predicate_induction_v1` from typed families to open file/GUI deltas (same hash features as semantic engine). Gate via falsifiability (constructible negative). If blocked, switch bottleneck — do not idle.
3. **Bottleneck 3: GUI verification caps.** Promote `CAP_GUI_GROUND/ACT/VERIFY` to verified-bound with local UGround-distilled grounder (offline inspection, receipt, OIDC). Bind-first + decisive margin + byte re-read. No runtime model.
4. **Bottleneck 4: Null-space admission path.** Add NuSA-CL tail-null-space LoRA path to `weight_update_admission` only after store path proven; gain with zero loss or no merge.

Each bottleneck ends with: `build → test against hardest open + unseen (held-out via predicate) → honest record → next bottleneck` ( §5 loop). No pause for approval. Switch if blocked.

## 6. What "done" looks like (§6) — not a score, a property

System on own weights+store, zero runtime model, with `COMPUTER_USE_ONE_SHOT_CAUSAL_CUT_V1`, when given a never-seen OSWorld2.0-class long-horizon env (research/admin/engineering domains) and one successful demonstration (human or agent), extracts cut+predicate, passes ADMIT on predicate-generated held-out, and replays on unseen variant with independent verification — **for harder 2.0-class tasks, not just Verified narrow**.

Until that property holds and is independently recomputed, we are not done — any "done" claim without it is pretense.

## 7. Risks and fail-closed behavior

- If attribution induction fails to produce falsifiable predicate, **do not admit** — stay ephemeral (REMEMBER=0) as `instant_one_shot` already does. Fail-closed > false learning.
- If GUI grounder distillation violates ownership receipt rules, block promotion (like `LOCAL_QWEN…_FALSIFICATION` did) — credit is verified gain only.
- If governance `30_OPEN / TERMINAL_FALSE / NO_FRESH_REALITY` blocks terminal claim, loop stays in §5 non-terminal general-cap work — no hand-waving promotion.

---

**Next action after this file:** begin §5 loop at Bottleneck 1 — read full causal compiler + acquired-operator + verifier sources before any code write (research-before-build law).
