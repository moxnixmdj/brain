# §3 Verdict — Is "one experience → permanent learning + strongest coding = computer use solved" true?

**Date:** 2026-11-20 | **Branch:** arena/69b87879-brain | **Status:** FAIL-CLOSED, zero benchmark runs this turn
> Verdict required: true / false / unproven / missing, with evidence. Plus first-principles limiting factors and why one advanced-coding exposure does not yet yield permanence.

---

## Verdict: FALSE as stated, UNPROVEN in its charitable reading, with 3 real blockers and 1 structural category error

**Precise hypothesis under test (H):**
> Your agent already possesses (A) *instant learning* and (B) *instant learning in new arbitrary envs* in the sense "does something once in any new coding env/computer task and learns permanently"; together with (C) strongest coding capability this *would* solve arbitrary computer use inc most advanced SWE fastest-optimally.

**My verdict on H literal:** **FALSE**.

**My verdict on H charitable** ("could one-experience learning *in principle* unlock computer use if we had it fully"): **UNPROVEN — missing a falsifiable demonstration, and we have positive evidence of the opposite (3 failures where one experience did not yield permanence).**

I do not say "true with more scale" and I do not say "impossible in principle." I say: the repo contains *mechanisms* for A/B, not *capabilities* that satisfy the quantifiers "anything," "arbitrary," "permanently," "fastest." The gap is architectural, not scale.

### Why literal FALSE — project-internal evidence

| Claimed quantifier | What project actually has (verified) | Contradiction with claim |
|---|---|---|
| **"anything person can do on computer"** | 4 verified computer-use caps: FS_LIST/READ/WRITE + PROGRAM_RUN (confined). No verified GUI_CLICK, BROWSER_AUTOMATE, WINDOW_MANAGE, FILE_PICKER, AUTH_FLOW in live registry. 89 OSWorld modules are ORPHAN (addressable not executable). OSWorld-V2.1 326 tests /108 tasks have not been taken; frontier on that board is 20–44% binary. | "Anything" is not in registry; broad GUI claim is unproven. |
| **"arbitrary new envs — does something once and learns permanently"** | Three co-existing persistence semantics, none satisfies "once → permanent for arbitrary env": (1) `instant_one_shot` REMEMBER always 0 bytes — explicitly ephemeral; ADMIT requires ≥1 held-out repair + ≥1 preserve with zero breakage (13/15 rows had zero admissible cands). (2) `semantic_generalization_engine` has 24 experiences (8 unique descs, all *success-only*), 8 embeddings, GENERALIZATION_POLICY_V1.json **absent** — zero permanent weight. Past naive weight updates broke 3/32 held-out predictions while self-loss improved (the very failure ADMIT was built to prevent). (3) `verified_skill_crystallizer` 5 skills/11 workflows, verified but scoped to **bug-class repair** (Python/CPP/Rust/Go/TS), not arbitrary GUI/browser — re-verified on recall, scoped. (4) `acquired_operator_memory` — only durable success: `spreadish sum-max` via re-derivation `acquire_from_examples` + falsifiable law gate; typed arithmetic family, not SWE/GUI. | No family claims arbitrary; where family is arbitrary, permanence is 0; where permanence is real, family is typed narrow. |
| **"strongest coding capability"** | `BRAIN_UNIFIED_MODEL_V1` 447 caps, but model file is index+router not weightful net (README: `NOT_A_TRAINED_NEURAL_NETWORK__CONTAINS_NO_WEIGHTS`). Strongest *verified* coding is `CODING_GENERAL_SOFTWARE_REPAIR_LOOP_V9_PLUS_CURRENT_BYTES_RESOURCE_PARETO_CUT` — bounded source-grounded acceptance without oracle leakage, not "strongest frontier coding." Terminal V3 3352/3352 green but `5/19 FROZEN_OPUS55` still red; V22 has 30 open obligations; bytes frontier NEXT87 frozen unspent. | Strongest-coding premise is not established. |
| **"learns permanently"** | Durable stores exist (`COMPOSITION_MEMORY_*`, `H100_ZERO_LEARNED_EVENT_MEMORY_PRECOMMIT`, `VERIFIED_SKILLS_BUNDLE`, `COMPILED_WORKFLOWS_BUNDLE`) but second-carrier verification for general computer-use is FROZEN/ORPHAN, not green. `GENERALIZATION_EXPERIENCES_V1` 24 rows succeed-only → no rung proof. `TERMINAL_FALSE`, `NO_FRESH_REALITY_FROM_THIS_CUT`. | Permanent learning for computer-use has no fresh reality. |
| **"fastest optimal smartest mechanisms"** | Bytes law active: 1,577,081 raw bytes, cut `BYTES_ACTIVE_STATE_20261010_V1` verified, `NEXT86 NO_ADAPTATION` proven; next step is *rerank exact V81 using already-spent evidence* (no rebuild). 1,452 ORPHAN modules already excluded to avoid claim inflation — actual bytes law enforcement. | Speed/optimality is resource-bounded, not asserted. |

**One-experience counterexample already in repo:** `GENERALIZATION_RUNG_GRADIENT` report — 24 success-only experiences were *insufficient* to prove rung; admission blocked weight commit; 13/15 independent eval rows zero demand-matching cands. Literal hypothesis predicts all 15 should pin from one trace; they didn't. The report is titled `A_SINGLE_TRACE_DOES_NOT_PIN_THE_RULE_20261120_V1` for a reason.

So: **H as written is FALSE** on project evidence.

### Charitable reading: why not declare "impossible" — what *is* proven

The repo proves a *narrower* claim:

> **Proven:** For typed narrow families (arithmetic operator laws, bug-class repair workflows, unary H100 chains, certain chart tasks), a single *demonstrated* episode can be re-derived in a fresh process without weight change and applied to held-out instances of the *same family* (acquired-operator `restore()` + verified-skill recall with re-verification).

This is non-trivial and distinguishes this project from frontier "frozen + RAG" stacks that *assert* learning. But it does not generalize to "arbitrary new envs" because families were hand-typed, not discovered.

Hence charitable H = **UNPROVEN** — missing is an *automatic* family-discovery + admission mechanism that works for open-ended GUI/browser/SWE without human-typed family.

---

## First-Principles Limiting Factors (in causal order)

I identify limiting factor *before* solution, per law.

### 1. Attribution — *the* bottleneck (not perception, not coding)

**What it is:** Given a trajectory (obs → think → act → obs … → outcome), which subsequence *caused* success, and under which precondition, so the extracted rule transfers?

**Why it dominates:** UGround shows grounding (where to click) is solved at 86–89% ScreenSpot-V2 from web synthetic data alone; frontier coding is strong on single-file fixes. OSWorld 2.0 still 20–44% binary because agents cannot *attribute* failure/success across 300+ steps with hidden state (inbox unread count, calendar conflict, unsaved doc). The paper's lowest-scoring phenomena are exactly attribution failures: implicit-state inference, multi-item tracking, conflict disambiguation, dynamic env.

**Project symptom:** `causal_trace_to_skill_compiler` exists but operates on already-sliced traces with human-typed bug classes; `semantic_generalization` synthesizes plans for typed families; `instant_one_shot` phases IDENTIFY→CONTRACT→APPLICABILITY require a clean causal unit but have 0/90 real-commit rows and 0/5 structural rows — attribution not yet general.

**Killer question:** If you experience advanced coding once, why can't you learn it? Because the trace contains ~10²–10³ actions, only ~3–7 mattered, interleaved with exploration/noops, conditioned on latent repo state the trace doesn't surface. Without correct attribution, you memorize the episode, not the rule; replay breaks on the next instance.

### 2. Admission — the gate that prevents false learning (currently too strict *and* too narrow)

**What it is:** Which candidate rule earns durable persistence (weight or store) — measured by held-out gain + zero regression, not self-loss.

**Why it blocks:** Project correctly built `weight_update_admission_v1` after naive updates broke 3/32 held-out predictions while self-loss improved. Gate demands `gained≥1 && lost==0`. On OSWorld/SWE, a single episode rarely yields a held-out gain without a family; gate correctly rejects → no permanence. Loosening gate = catastrophic forgetting (Frontier 2026: LRM fine-tunes *increase* forgetting); keeping it = no learning.

**Project symptom:** 13/15 rows zero cands; `GENERALIZATION_POLICY_V1` absent after 24 successes (all success-only, no failure contrast).

### 3. Applicability / Recall — when to fire what you learned

**What it is:** Given new task, retrieve right memory/skill/operator among thousands, with calibrated abstention.

**Why it blocks:** `COMPOSITION_MEMORY_OWNED_FAMILY_BRIDGE` shows retrieval works for owned families; open retrieval across arbitrary OSWorld tasks has no verified policy (ORPHAN modules, V21 workflow policy not promoted). Frontier symptom: OSWorld agents guess instead of asking user — applicability misfires.

**Project symptom:** `recall_and_apply_verified` re-verifies before fire (good) but scopes to bug-class; `UNKNOWN_DOMAIN_DIRECT` V1-V6 has abstention theorems but no general computer-use policy.

### 4. Grounding + actuation with verification (not generation)

**What it is:** Translate attributed rule into grounded action (coordinate, key sequence, file edit) and verify effect via independent byte re-read before credit.

**Why it blocks less than assumed:** Grounded action (`grounded_action_v1`) + decisive-margin bind is solved for FS/program; for GUI, UGround module existence means we can distill a local grounder without runtime model call (see Plan). But verification loop (`verify_gui_goal`, `CAPABILITY_VERIFICATION_KERNEL`) is still ORPHAN for broad GUI — agents skip verification and hallucinate success (OSWorld paper).

### 5. Persistence / forgetting separation (architectural, not scale)

**What it is:** Where learned things live: ephemeral calculation vs external store vs weight. Project's three-tier split (Tier A ephemeral, Tier B external store, Tier C tiny mechanism) is correct but incomplete: no automatic *family* formation → Tier B stays human-scoped, Tier C never fires for arbitrary tasks.

**Why it answers "why not learn coding once?":** Advanced coding tasks require composing ~4.1 files /107 LOC cross-file edits (SWE-bench Pro). One episode yields a *workflow* (ordered edits + checks), not a weight. Turning that workflow into a reusable family (e.g., "null-check family") without a human label is the missing step: you need to infer the family predicate from one example, with falsifiable contrast — exactly what `acquired_operator_memory` does for arithmetic but no one has for SWE/GUI.

---

## Why "experience advanced coding once → learn permanently" fails today (direct answer)

1. **Episode ≠ rule.** One advanced SWE episode (e.g., fix cross-file null deref) contains ~hundreds of LOC touched, test runs, reverts, file reads — only the *causal cut* (e.g., "guard deref at dominance frontier in 3 files") is reusable. Without causal attribution, you store the episode, not the cut; next repo breaks replay.

2. **No automatic family.** Permanence needs a family to generalize *to*. `value_algebra` recovers laws because arithmetic families are typed and falsifiable (`laws_induce` + `indistinguishable_from` + `law_is_falsifiable`). SWE/GUI families (e.g., "calendar conflict disambiguation") have no such typed spec — `semantic_generalization_engine` only handles `Count/List` families.

3. **Admission demands held-out gain.** You cannot test generalization from one episode without a held-out instance of the *same* family. With no automatic family, you cannot construct held-out; gate correctly rejects; no permanence.

4. **Even strongest coding ≠ transfer.** Frontier coding is strong *within* a given task (Opus 5.5 64.8% TB4), weak *across* tasks without attribution — OSWorld 2.0 binary 20–44% vs Verified 90% shows long-horizon transfer, not single-task coding, is the gap.

5. **Forgetting vs not-learning tradeoff.** If you loosened admission to force permanence from one success, you'd get catastrophic forgetting (proven in this repo: 3/32 breakage). So current system is *correctly* fail-closed; unblocking needs better attribution, not weaker gates.

**In one line:** One experience is sufficient *iff* you can extract the causal cut and its family predicate; we can do that for typed laws, not yet for arbitrary SWE/GUI — so the blocker is attribution+family, not memory size.

---

## Honest accounting (what is proven / not / failed)

| Claim | Status | Evidence |
|---|---|---|
| Single trace pins chart-axis rule 7/7 | **Proven** (public recomputed) | `CHART_AXIS_TITLE_UNIT_BINDING`, `UNIVERSAL_ESCAPE_RESOLVER` 112M variants |
| Operator law re-derived across process | **Proven** | `acquired_operator_memory` spreadish demo (`teach→restore` re-derivation, `_usable`+falsifiable gates) |
| Bug-class workflow re-verified on recall | **Proven** (scoped) | `VERIFIED_SKILLS 5 + WORKFLOWS 11`, `skill_recheck`, merge admission-preserving, second-carrier for H100 family (20261005) |
| One trace → any SWE/GUI rule permanent | **Failed** (expected) | `A_SINGLE_TRACE_DOES_NOT_PIN 13/15 zero`, `REAL_COMMIT 0/90`, `STRUCTURAL 0/5`, `GENERALIZATION_POLICY_V1` absent |
| Strongest coding alone solves OSWorld2.0 | **Failed** (frontier) | Best binary 20.6→44.3% despite 86-89% grounding; TB4 64.8% ≠ OSWorld long-horizon |

## The 3 blockers to remove (ranked)

1. **Causal attribution for open trajectories** — produce minimal causal cut + falsifiable family predicate from one episode without human type.
2. **Admission that admits without forgetting** — held-out construction from inferred family, with null-space / memory-free update (NuSA-CL style) when weight change needed.
3. **Verified actuation loop for GUI** — grounded action + independent re-read verification as first-class cap, not ORPHAN; local UGround-distilled grounder, zero runtime model.

Remove #1 and #2 moves; #3 is then assembly of existing parts.

Next: `03_ULTIMATE_PLAN_V1.md` turns these into one minimal build (reusing what exists, refusing what doesn't justify).
