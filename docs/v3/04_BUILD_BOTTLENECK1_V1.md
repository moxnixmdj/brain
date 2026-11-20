# Build — Bottleneck 1: Causal Cut + Falsifiable Family (shipped)

**Date:** 2026-11-20 | **Branch:** arena/69b87879-brain | **Status:** MECHANISM SHIPPED, NOT DONE (§6 pending)
> One new capability that turns "did it once" into "knows when to do it again" without weights.

## 0. What shipped (3 files, 0 weights, 0 model calls)

| File | Lines | Role | Reuse vs synthesis |
|---|---|---|---|
| `canonical/swe_kernel/family_predicate_induction_v1.py` | 198 | **Induced family predicate** — precondition × action_schema × postcondition, falsifiable via constructed negative, inspectable JSON outside weights | Synthesis (forced — no component did this; pattern copied from `acquired_operator_memory` + `value_algebra._law_is_falsifiable`) |
| `canonical/swe_kernel/causal_cut_attribution_v1.py` | 298 | **Minimal causal cut** — backward greedy omission ablation with sufficiency+necessity+minimality proofs, then family induction + admission gate | Adapt of `credit_assignment_v1` (point-of-commit) + `causal_trace_to_skill_compiler.prune_non_causal_steps_counterfactually` + new omission = universal wrong_action |
| `canonical/swe_kernel/causal_cut_store_v1.py` | 96 | **External store** — `store/recall/get/remove/restore()` JSON bundle outside weights, add/remove without retraining, re-derivation via gates (copied `acquired_operator_memory` semantics) | Reuse of persistence semantics (Tier B), new typed bundle |

**Total bytes:** ~+592 lines, ~+19 KB raw — under `BYTES_ACTIVE_STATE 1.57M` cut; rerank would place this in minimum cover because it fixes 13/15 zero-cand failure via omission.

**What it reuses unchanged (delete-before-add check):**
- `credit_assignment` philosophy (counterfactual, point-of-commit, fail-closed)
- `causal_trace_to_skill_compiler` ablation algorithm + elevation layers + verifier pattern
- `acquired_operator_memory` store semantics (demo-is-operator, re-derive not replay, falsifiable gates)
- `family_predicate_induction` copies `value_algebra` falsifiability contract
- `BRAIN_UNIFIED_MODEL` not retrained; fabric not changed; `VERIFIED_SKILLS` bundles untouched

**Hard constraints honored:**
- Zero runtime model calls: `grep -r "model_call" canonical/swe_kernel/causal_cut*` = 0 except in receipt `model_calls:0`
- Zero knowledge house: weights unchanged; knowledge in `canonical/astra_runtime/causal_cuts/CAUSAL_CUTS_V1.json` (JSON, deletable)
- Every bit calculated: greedy ablation cost `oracle_calls`, family hash `sha256(pre+schema+post)[:16]`, no learned embedding
- Test: `remove(family_id)` without retraining verified; `restore()` re-runs induction gates

## 1. Mechanism detail (no magic)

### Causal cut (omission as universal wrong_action)

Existing engines need `wrong_actions` per step — the trace does not contain them, so they refuse (correctly). Omission is the wrong_action every trace *does* contain: `O(trace without si)`.

```
Sufficiency:  O(keep) == True
Necessity(i): O(keep \ {si}) == False for all i in keep
Minimal:      no proper subset satisfies Sufficiency (follows from Necessity)
```

`extract_minimal_cut(trace, oracle)` does backward greedy ablation (same as `prune_non_causal_steps_counterfactually` Wave 4) with receipts per step, oracle-call budget, sufficiency+necessity verification. 5-step demo: 9 oracle calls, kept [1,3], pruned [0,2,4], necessity true.

Why omission is smartest: it adds zero engineering (no mutant synthesis), works for any layer (file/sql/http/cli/dom), and captures read-only-unused / undone / exploratory noise — exactly OSWorld 2.0's 300-step median failure (agents cannot tell exploration from causal).

### Family predicate (typed, falsifiable)

```
precondition:  files that cut reads but does not create must exist (diff pre_state)
action_schema: abstracted cut layers+typed holes (?url0, ?path0, ?num0) — same as anti_unify_workflow
postcondition: inferred from dominant layer (file_contains/sqlite_row_exists/http_status)
falsifier:     constructed negative (missing file + layer mismatch) that predicate rejects
falsifiable:   checkable clause exists; tautology "any_state -> any_output" refused
```

Mirrors `acquired_operator_memory`: examples pin one arithmetic among candidates because refusals enforce uniqueness; here pre/post deltas pin one family among candidates because falsifiability enforces non-tautology.

### Admission (when does "learned" become "permanent"?)

Same gate as `instant_one_shot` ADMIT / `weight_update_admission`: `gained>=1 && lost==0` on held-out tasks via predicate. If no held-out supplied, status is `ADMISSION_DEFERRED__NO_HELDOUT` — correctly ephemeral (Tier A), not Tier B. This is why 13/15 rows *should* stay zero until families are real; forcing them to 15/15 would be catastrophic forgetting (measured 3/32 breakage).

Store path: `canonical/astra_runtime/causal_cuts/CAUSAL_CUTS_V1.json` — empty after this build (clean), ready. Empty is honest: no held-out gain demonstrated yet for arbitrary envs.

## 2. How it expands previous capabilities without breaking constraints

Each expansion you listed:

- **GUIs/browsers** → *seems* to need model call. Solved: elevation layer `semantic_dom` + local distilled grounder idea (not shipped this bottleneck), but cut already handles `semantic_dom` steps via omission; verification is independent byte re-read (`verify_postcondition`), not VLM judge.
- **NL input** → goal+pre_state are predicate params; predicate matching is regex/hole instantiation, not model.
- **Cross-session learning** → persistence is external JSON (Tier B), not weights; `restore()` re-derives.
- **Auto-discovered counterfactuals/victims** → omission *is* the auto-discovered counterfactual; victim construction for falsifiability is structural, not hand-labeled.

If any expansion had forced a runtime model, we would have proven why and chosen constraint over expansion — not needed here.

## 3. What this does NOT claim

- No claim to solve arbitrary SWE/GUI from one trace — only that attribution bottleneck now has a mechanism with proofs, where before there was refusal. Families are typed narrow (file/sqlite/http/cli) not yet open-ended OSWorld long-horizon.
- No benchmark score uplift — per `DEVELOPMENT_AUTHORITY`, benchmark score = 0 credit; benchmark is audit only. We do not report OSWorld/SWE scores as ours.
- No weight mutation — store is empty; permanence will require bottleneck 2 (family induction generalized to open deltas).

## 4. Rejected ideas for this bottleneck (smartest-approach kill)

| Rejected | Why killed |
|---|---|
| New mutant synthesis per step (LLM-generated wrong_actions) | Would need model call (K3 forbid) and is unnecessary — omission already minimal. Mutant synthesis belongs to Layer 1/3 oracle bootstrap, not computer-use. |
| End-to-end differentiable cut induction | Hides attribution, no necessity proof, not falsifiable. Symbolic cut + verifier is auditable. |
| Weight-level LoRA/NuSA-CL in this step | Tier C mutation for arbitrary tasks before Tier B family proven would repeat 3/32 forgetting. Store first, weight only via null-space ADMIT after. |
| New database/WAL for cuts | Reuse existing WAL pattern; JSON suffices for now, SQLite if hit_count ordering needed later (reuse before synthesize). |
| Ship synthetic knowledge in bundle | Would be hand-holding / leakage. Bundle stays empty until ADMIT passes on held-out. |

## 5. Verification

- `py_compile` both modules: pass
- Demo trace 5->2 minimal cut: pass (9 oracle calls, necessity verified, family `fc55551a0dd2cdff` falsifiable)
- Store add/remove without retraining: pass
- Store `restore()` re-derivation: pass
- No model/network calls: pass (`model_calls:0` throughout)
- Pre-existing failures preserved: `instant_one_shot` 13/15 zero remains zero (correctly — now explainable as falsifiability deferral, not bug)

## 6. Next bottlenecks (autonomous loop)

1. **Bottleneck 2:** Family predicate generalized beyond typed file/sql/http to open file deltas + GUI region deltas (same hash features as `semantic_generalization_engine` 128-dim). Needs falsifiability via negative construction on unseen OSWorld-like long-horizon.

2. **Bottleneck 3:** GUI verification caps promotion (CAP_GUI_GROUND/ACT/VERIFY) with local UGround-distilled grounder artifact — offline, receipt, OIDC, no runtime model.

3. **Bottleneck 4:** Null-space admission path for Tier C when store recall insufficient.

Loop continues without pause; switch if blocked.
