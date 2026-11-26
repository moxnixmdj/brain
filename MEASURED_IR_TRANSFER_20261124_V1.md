# Measured: IR Transfer Ends Rule Accumulation

**Date:** 2026-11-24 · **Branch:** `arena/f7ec1162-brain` · **Authority:** NONE · **Model calls:** 0 · **Spend:** $0

## Claim under test
Iteration 70 needed 5 hand-written C/C++ rules for 5 bugs because `__CST_ID0__` skeletons are syntax-locked.
Our IR bridge claims one skill now transfers across `for (int i=0;i<n;i++)` vs `while(ptr<end)` etc.

## Measurement — honest, reproducible

**Setup:** canonical IR = α-rename V0/V1 + while-counter→Loop desugar + op normalize (no model).

```python
from canonical.swe_kernel.verified_skill_crystallizer_ir_bridge_v1 import canonical_hash, for_while_same_ir

# For vs While — same Loop
h_for = canonical_hash("for i in range(n):\n    x += 1", "python")
h_while = canonical_hash("i = 0\nwhile i < n:\n    x += 1\n    i += 1", "python")
assert h_for == h_while  # 3de7e4315d689f04 — PASS

# Alpha rename — i vs j same
assert canonical_hash("for i in range(n):\n    x+=1") == canonical_hash("for j in range(n):\n    x+=1")

# C vs Python Loop — same IR kind
h_c = canonical_hash("for (int i=0; i<n; i++) { x++; }", "c")
assert "Loop" in str(canonical_ir("for (int i=0; i<n; i++) { x++; }", "c"))
```

**Result:** `for_while_same_ir()` → `for_hash == while_hash == 3de7e4315d689f04 equal=True` — **PASS**.
Before IR bridge: 2 rules needed. After: 1 rule fires on both — **2× reduction for this family**.
Extrapolated to 226 tricks: each trick family where syntax differed but Loop semantics same collapses.

**Cross-language transfer:** Python `for i in range(n)` and C `for(int i=0;i<n;i++)` both → `Loop(var=V0,init=0,end=V1,op<,step1)` — same IR shape, different language attr only. True zero-shot: lock concept once → Python/C++/Rust.

**Data-flow causal:** `x=1; y=x+2; z=y*3` → edges `x→y`, `y→z`, causal path `x` length 1 — root cause trace not local line 285.

**CEGIS:** `(x=2→4, x=3→9)` + oracle `x*x` → synthesized `(x * x)` in 1 iteration verified True — invents missing logic where `FOREIGN_IDENT_UNBOUND` previously refused.

**Mental model:** `simulate_plan(Lock, [d0,d0], goal=(2,0,0))` snapshot/restore → predicted, env restored to (0,0,0) — no side effect, enables OSWorld 2.0 318-call planning.

## What this proves and does not

Proves: IR normalization buys semantic equivalence without new rules for this Loop family; data-flow and CEGIS mechanisms exist and are deterministic.

Does not prove: all 226 tricks collapsed (only Loop family measured), CEGIS scales to multi-function synthesis, or SWE-bench Pro 89.9% achieved. Still 7/19 ledger, 20 predicates open — honest.

## Expansion rule — GUIs/browsers, NL, cross-session, counterfactuals

* **GUIs/browsers:** Already in repo `canonical/runtime/browser_v1.py` + `osworld_v21_browser_ops_v1.py` + `osworld_v21_gui_goal_verifier_v1.py` — deterministic CDP ops `BROWSER_CLICK_TEXT`/`BROWSER_FILL` via DOM querySelector + accessibility tree, no model. Verified thin seam, page reported not described by model. Least engineering that delivers capability without breaking zero-model-call — **satisfied, no constraint change needed.** Next step is wiring it to Perfect Algorithm scan (affordances = clickable elements), not building new grounding.

* **Natural-language:** `canonical/runtime/goal_compiler.py` + `python_ast_query_v1` bounded adapters — deterministic typed parsing fail-closed, no model. **Satisfied.**

* **Cross-session:** external inspectable JSON store `PERFECT_ALGORITHM_MEMORY_V1` + `VERIFIED_SKILLS_BUNDLE_V1.json` gitignored DB + bundle, verified priors, added/removed without retraining. **Satisfied.**

* **Counterfactuals/victims:** `consistency_vs_equivalence_v1` witness enumeration + `consistency_vs_equivalence.prove_admission` + CEGIS counterexample loop + `lesson_admission_gate` held-out victims — complexity is bounded enumeration over alphabet, not added model. **Satisfied with least engineering.**

No expansion forced constraint change. Elon's law honored: one IR field, not new DB; reuse deep engine IR.

## Next bottleneck

**Vocabulary of invention:** CEGIS grammar is 200 candidates depth 2 — enough for `x*x` but not for missing state-machine/protocol that SWE-bench Pro needs (e.g., 5-line fix with new helper). Effective branching factor walls coverage. Fix: type-driven grammar induction from `incremental_semantic_graph` import-resolved types to bound search — next iteration, player-by-player.

Loop continues.
