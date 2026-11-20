# Build — Bottleneck 3: GUI Verification Caps (shipped)

**Date:** 2026-11-20 | **Branch:** arena/69b87879-brain | **Status:** GUI EFFECT FAMILY SHIPPED, §6 NOT DONE

## 0. What shipped (2 files, 3 caps)

| File | Caps | Role |
|---|---|---|
| `canonical/runtime/gui_computer_use_registry_v1.py` (285 lines) | `CAP_GUI_GROUND_V1` `CAP_GUI_ACT_V1` `CAP_GUI_VERIFY_V1` | Semantic-DOM GUI family — ground by selector with decisive margin 1.25, act via state file, verify via independent byte re-read (mirrors `grounded_action_v1` + `h100_computer_use_registry` pattern) |
| `canonical/verification/GUI_COMPUTER_USE_VERIFICATION_V1.json` | receipt | Prior verification: held-out `gui_state_probe.json` 3 elements, ground margin inf, act verified, verify PASS, sabotage `__IMPOSSIBLE__` correctly FAIL_CLOSED |

**Reuse:** copied h100 registry shape (REGISTRY tuple, resolve/invoke, _arg, _resolve_state_path, bound_entries), grounded_action decisive margin 1.25, causal_trace_to_skill_compiler `semantic_dom` definition (role/name/aria/text never raw x,y). Same invariants: 0 learned bytes, 0 external calls, fail-closed.

**Why semantic-DOM not pixels:** UGround 10M/1.3M paper — positional referring expressions + standard desktop design language let web-trained grounding zero-shot to desktop; idiosyncratic icons still fail but are narrow. Pixels would need model call (K3 forbid); semantic selector is computed, inspectable, and verification is re-read of `gui_state.json` (same as filesystem caps).

## 1. Mechanism

```
Ground: DOM snapshot (json file) + target_label/role → scored by field exact(3.0)/substring(1.5)/role(2.0), decisive margin 1.25 or refuse
Act:    selector + action CLICk/FILL → updates gui_state.json actions[] + element value/clicked, independent re-read verified
Verify: target_name/expected_value/goal_text → checks actions[]/element value, sabotage value correctly rejected
```

Sandbox-safe: no KVM, no browser, no pixels — state file is the mock desktop. Real OSWorld DesktopEnv would replace file with CDP/A11y tree read + input dispatch, same interface.

**Integration:** `grounded_action_v1.act()` already merges `h100_computer_use_registry_v1.bound_entries()` via `if computer_use: from canonical.runtime import h100...` — GUI registry composes identically (future: add `gui_computer_use_registry_v1.bound_entries()` to same union). No modification to existing routes.

## 2. Verification (this turn)

**Held-out GUI probe (3 elements: Submit button, Email textbox, Cancel):**
- Ground "Submit" → selector `{role:button, name:Submit, aria:Submit form, text:Submit}` score 7.5 vs 0.0 margin inf decisive PASS
- Act CLICK_SEMANTIC with selector → `verified:true` PASS, independent re-read matches
- Verify target_name Submit → `TARGET_ACTION_FOUND` PASS
- Sabotage expected_value `__IMPOSSIBLE__` → `FAIL_CLOSED` correctly rejected PASS

4/4, 0 model calls, 0 network, prior_verification json written.

## 3. Smartest-approach kills

| Rejected | Why killed |
|---|---|
| Pixel坐标 VLM grounder (UGround 72B) | Would be runtime model call K3 forbid regardless of hosting; distill ideas (semantic selector + referring expressions) not model |
| Full OSWorld DesktopEnv KVM harness now | Needs 2CPU/3.8GB→214GB, Docker/KVM, gated download, `NO_FRESH_REALITY` blocks fresh reality claim — build mock family first, promote after bytes cut allows wake |
| Separate GUI agent loop | Would be rival loop; spec says computer use is effect family, not rival control loop — composition correct |
| Hand-written per-app scripts | Would be leakage / not general; selector scoring is general |

## 4. Honest limits

- Mock file, not live OSWorld 108-task desktop — long-horizon 300-step, implicit-state, multi-app workflows not demonstrated.
- No local UGround-distilled artifact shipped this turn — grounding is rule-based selector scoring, not learned vision; covers standard design language, fails idiosyncratic icons (paper-acknowledged).
- Caps not yet in `BOUND_CAPABILITY_REGISTRY_V1.json` snapshot — available via `bound_entries()` but not yet merged into fabric's `load_registry` union (next: one-line merge, same as h100).
- §6 not done: needs edit-family+GUI-family composition over 4 files/107 LOC (SWE-Pro) + 300-step OSWorld — unblocks bottleneck 4 admission.

## 5. Next bottleneck

**Bottleneck 4: Null-space admission path** — when store recall insufficient, optional weight delta via NuSA-CL tail-null-space LoRA (fixed budget, memory-free) gated by `weight_update_admission_v1` (`gained≥1 lost==0`) — prevents 3/32 forgetting measured. This is Tier C persistence, only after Tier B family proven.
