# Tightening + Integration — Non-Blocked Bottlenecks (shipped)

**Date:** 2026-11-20 | **Branch:** arena/69b87879-brain | **Status:** PATH REGEX TIGHTENED + GUI REGISTRY MERGED, §6 NOT DONE

## 0. What shipped (2 minimal edits, no new primitive)

| Edit | File | Why this was next non-blocked bottleneck |
|---|---|---|
| Path regex strict | `canonical/swe_kernel/family_predicate_induction_v1.py:76` | Old `_PATH_LIKE_RE` matched code dotted names `pathlib.Path` as path (28 holes for 6-step trace, over-general) → inflated family_id, reduced transfer. New regex requires `/` or known file extension `(py/pyi/js/.../php)` — `pathlib.Path` now false, `src/auth.py` true. |
| GUI registry merged | `canonical/runtime/grounded_action_v1.py:514-530` | `h100_computer_use_registry` was merged but `gui_computer_use_registry` (3 caps) was isolated — planner could not propose GUI caps despite being verified. Added same union pattern as h100, so `bound_entries()` now exposes 7 caps (4 FS/program + 3 GUI) to grounding/binding. |

**Bytes:** 2 lines changed, 0 new files — best-part-is-no-part (remove before adding). Verifies `BYTES` law: rerank would keep these as dominated improvements.

## 1. Verification (this turn)

- `py_compile` both files PASS
- Path regex: `pathlib.Path` false (was true), `src/auth.py` true, `/tmp/foo` true, `geom.py` true, `data.json` true, `pathlib` false
- Long-horizon composition still PASS (9→6 cut, composite family `d823...` now with fewer holes — still admitted)
- Composite admission still PASS `gained 1 lost 0 stored 1` — twin distinctness preserved
- Grounded action now merges 7 caps (checked via `from canonical.runtime.grounded_action_v1 import load_registry` loads 4+3)

## 2. Why these were next

Real OSWorld twin blocked by infra (KVM/214GB), SWE-Pro twin blocked by Harbor — per §5, switch to next-best bottleneck when blocked. Tightening and integration are non-blocked, unlock most capability per byte: over-capture was measurable (28 holes) and integration was why `CAP_GUI_*` never appeared in survivors despite being verified.

## 3. Honest limits

- `geom.py` still matches as path (bare filename with extension) — correct for FS caps, but for code content `geom.py` as string literal could still be over-captured — next tightening is context-aware (path hole only when `path` field, not `content` field)
- GUI caps in registry but not in `BOUND_CAPABILITY_REGISTRY_SNAPSHOT_V1.json` — still via runtime union, not compiled snapshot (snapshot update requires compiler + OIDC, next)
- §6 not done: still synthetic twin, not external harness twin with model-judge 11.53%

Loop continues — next blocked twin needs infra not present; next non-blocked is composite family negative generation for falsifiability (sabotage via `content_a_generalized_write_would_destroy` check already in store, but not yet exercised in admission).
