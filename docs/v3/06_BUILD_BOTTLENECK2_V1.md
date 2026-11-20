# Build — Bottleneck 2: Open-Delta Family Generalization (shipped)

**Date:** 2026-11-20 | **Branch:** arena/69b87879-brain | **Status:** MECHANISM UPGRADED, §6 NOT DONE

## 0. What changed (reuse > add)

**Single file upgraded:** `canonical/swe_kernel/family_predicate_induction_v1.py` (198 → 425 lines, +17 holes logic)

**What was added:**
- Literal extraction now `url | path | num | ?str (quoted) | ?ident | semantic_dom selector` — same vocabulary as `causal_trace_to_skill_compiler_v1._extract_goal_literals` (Plotkin anti-unification). Previously only url/path/num.
- `_extract_postcondition` now detects **file edit** vs overwrite via pre/post snapshot diff, emitting `edit_of` + `edit_preserves_outside: True` — mirrors `file_edit_claim` + `content_a_generalized_write_would_destroy` guard that prevents "replace whole file with taught file" bug (measured 2026-11-11).
- `_LAYER_RE` now includes `confined_python_exec` (taught programs run sandboxed, not host).
- Precondition still `requires_files` from pre_state delta; now also handles `confined_python_exec` code field.

**What reused unchanged:** falsifiability gate (`_is_falsifiable` tautology check), falsifier construction, hash family_id, store semantics, cut extraction.

**Bytes:** +227 lines ≈ +7 KB raw — still under 1.57M cut; minimal cover because it unlocks file-edit families that bottleneck 1 could not generalize (creation-only).

## 1. Why this is the next non-dominated bottleneck

Bottleneck 1 solved attribution (5→2 cut, necessity proven) but families were typed `url/path/num` only. Real SWE is **edits**: rename symbol, fix null deref across 4 files, preserve surrounding code. Those are `?str` holes in file content, not path holes. Without `?str/?ident`, a rename `old_name→new_name` memorizes concrete names; next file `old_foo→new_foo` fails to match. Frontier's SWE-bench Pro average 107 LOC / 4.1 files is exactly this.

OSWorld 2.0 failure: "replace geom.py with shapes.py" passes `file_contains` but fails `edit_preserves_outside` — new predicate catches it.

## 2. Smartest-approach kill test

| Rejected | Why killed |
|---|---|
| New AST diff engine for file edits | Would be rebuild of `file_edit_claim` already in `causal_trace_to_skill_compiler`; we emit same signal (`edit_preserves_outside`) via snapshot diff — reuse, not rebuild. |
| Learn embedding for file content holes | Would be weights-as-lookup (violates zero house, every bit calculated). Typed holes are calculated from literals, no training. |
| Capture every identifier as hole | Would over-generalize (`def`, `return` as holes → tautology). Filtered: only quoted strings length≥2, semantic_dom selector fields, and ident with `_`/`-` length≥3 — same as compiler's `_IDENT_RE` + stop-words. |
| Separate GUI family module | Premature; `semantic_dom` selector fields already handled as `?str` holes — one predicate covers both code and GUI. |

## 3. Verification (this turn)

**Test A — creation (bottleneck1 regression):**
- Trace 5 steps [noise, write output.txt, noise, write result.txt, noise] → kept [1,3], pruned 3, family `bd8fb4362fd29a94` with `?path+?str` holes, falsifiable PASS — unchanged behavior plus extra str holes harmless.

**Test B — edit (new capability):**
- Pre `geom.py: def old_name(): ... helper`, Post `def new_name(): ... helper`, Trace [read, confined_python_exec edit, noise]
- Oracle = contains new_name && layer confined_python_exec
- Result: kept [1] alone (pruned read+noise), minimal 3→1, **postcondition** `file_contains geom.py: def new_name(): edit_of: geom.py edit_preserves_outside: True` — correctly distinguishes edit from overwrite
- Holes: 17 (path+str+ident+num) — includes `old_name`/`new_name` as `?str`/`?ident`
- Store add/recall/restore PASS, then cleaned (0 cuts — honest empty until ADMIT)

**Governance:** No benchmark score claimed; no model call; knowledge outside weights verified via `remove()` without retraining.

## 4. Honest limits (not done)

- Over-capture: `?path` regex matches `pathlib.Path` as path (code dotted name) — inflates holes 17 vs ideal ~4. Tolerable (still falsifiable) but will be tightened next iteration via slash/dot-extension filter (reuse `PATH_TOKEN_RE` strictly).
- GUI `semantic_dom` not end-to-end tested with real DOM snapshot — selector hole logic ships but no live OSWorld DOM trace taken (needs KVM).
- Admission still deferred (no held-out gain demo for edit family) — Tier A ephemeral correctly, not Tier B. Next bottleneck must produce held-out gain with `file_edit_claim` verifier.

## 5. Next bottleneck

**Bottleneck 3: GUI verification caps** — promote `CAP_GUI_GROUND/ACT/VERIFY` to verified-bound with offline UGround-distilled grounder artifact (no runtime model), binding via `grounded_action_v1` decisive margin + independent byte re-read. Unblocks OSWorld 2.0 long-horizon where 300 steps are GUI.
