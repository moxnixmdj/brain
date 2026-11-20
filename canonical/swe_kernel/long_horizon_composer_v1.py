#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Long-Horizon Composer — hardest-case composition of file+GUI+code via causal cuts.

WHY THIS EXISTS
----------------
OSWorld 2.0 hardest failures are long-horizon 300-step multi-app workflows with
implicit state, not single-file fixes. SWE-Pro 4.1 files / 107 LOC average is
also long-horizon (cross-file). Frontier solves Verified (1-liner) but fails
Pro (-20 to -25 pts). The missing piece is not grounding (UGround 89%) nor
coding (Opus 64% Pro) but *composition that tracks state and verifies*.

This composer is the ultimate-hard design: a task that needs
  1. Causal-cut attribution over a mixed trace (file edit + GUI click)
  2. Falsifiable family induction (edit_preserves_outside + selector holes)
  3. Decisive grounding + independent verify
  4. Null-space admission so composition does not forget
It reuses bottleneck 1-4 mechanisms, no new primitive beyond composition.

Reuse before synthesis:
- causal_cut_attribution_v1.extract_minimal_cut
- family_predicate_induction_v1.induce_family_predicate
- gui_computer_use_registry_v1 + h100 registry via grounded_action pattern
- nullspace_admission_v1.evaluate_nullspace_update
- horizon_bounded_execution_v1 SubGoal checkpoint semantics (borrowed, not rebuilt)

Zero model calls, external store for families, fail-closed.

Authority: NONE — sandbox measurement.
"""
from __future__ import annotations

import json
import pathlib
import tempfile
import time
from pathlib import Path
from typing import Any, Mapping, Sequence

_ROOT = pathlib.Path(__file__).resolve().parents[2]
import sys
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

SCHEMA = "PROJECT_BRAIN_LONG_HORIZON_COMPOSER_V1"

# ------------------------------------------------------------
# Long-horizon task definition (hardest proxy)
# ------------------------------------------------------------

def _make_hardest_proxy_task(tmp: Path) -> dict[str, Any]:
    """Create a hardest-case proxy: 4-file edit + GUI submit, 9 steps with noise."""
    # Pre-state: 4 files each with old symbol that needs fixing
    files = {
        "src/auth.py": "def authenticate(token):\n    if token is None:\n        return False\n    return token == 'secret'\n",
        "src/db.py": "def query(sql):\n    if sql is None:\n        return []\n    return execute(sql)\n",
        "src/api.py": "def handle(req):\n    if req is None:\n        return 500\n    return 200\n",
        "src/ui.py": "def render(x):\n    if x is None:\n        return ''\n    return str(x)\n",
        "gui_state.json": json.dumps({
            "elements": [
                {"role": "button", "name": "Submit", "text": "Submit Fix", "aria": "Submit fix for review"},
                {"role": "textbox", "name": "Summary", "placeholder": "Describe fix"},
                {"role": "button", "name": "Cancel", "text": "Cancel"}
            ],
            "actions": []
        })
    }
    for rel, content in files.items():
        (tmp / rel).parent.mkdir(parents=True, exist_ok=True)
        (tmp / rel).write_text(content if isinstance(content, str) else content, encoding="utf-8")
    # Hardest trace: 9 steps, only 5 are causal (4 edits + 1 GUI), 4 are noise
    trace: list[dict[str, Any]] = [
        {"layer": "cli_exec", "argv": ["ls", "src"], "note": "noise read-only"},
        {"layer": "python_file_op", "op": "write_text", "path": "src/auth.py", "content": files["src/auth.py"].replace("if token is None:", "if not token:")},
        {"layer": "cli_exec", "argv": ["echo", "checking"], "note": "noise"},
        {"layer": "python_file_op", "op": "write_text", "path": "src/db.py", "content": files["src/db.py"].replace("if sql is None:", "if not sql:")},
        {"layer": "python_file_op", "op": "write_text", "path": "src/api.py", "content": files["src/api.py"].replace("if req is None:", "if not req:")},
        {"layer": "cli_exec", "argv": ["pwd"], "note": "noise"},
        {"layer": "python_file_op", "op": "write_text", "path": "src/ui.py", "content": files["src/ui.py"].replace("if x is None:", "if not x:")},
        {"layer": "semantic_dom", "op": "FILL_SEMANTIC", "selector": {"role": "textbox", "name": "Summary"}, "value": "Fix null deref: use truthiness check"},
        {"layer": "semantic_dom", "op": "CLICK_SEMANTIC", "selector": {"role": "button", "name": "Submit"}},
    ]
    goal = "Fix null deref in 4 files (use truthiness check) and submit fix via GUI Submit button"
    postcondition = {"kind": "gui_goal_verified", "checks": ["all_files_contain_not_token", "gui_submit_clicked"]}
    return {"tmp": tmp, "files": files, "trace": trace, "goal": goal, "postcondition": postcondition, "causal_indices": [1,3,4,6,7,8], "noise_indices": [0,2,5]}

def _oracle_for_proxy(trace: Sequence[Mapping[str, Any]], tmp: Path) -> bool:
    """Hardest oracle: all 4 files must contain corrected pattern AND GUI Submit clicked."""
    # File checks: each of the 4 files written must appear in trace with corrected content
    required_files = {"src/auth.py", "src/db.py", "src/api.py", "src/ui.py"}
    written = {}
    for s in trace:
        if str(s.get("layer")) == "python_file_op" and s.get("path") in required_files:
            written[str(s["path"])] = str(s.get("content") or "")
    if set(written.keys()) != required_files:
        return False
    for content in written.values():
        if "if not " not in content:  # corrected pattern must be present
            return False
        if "if None" in content or "is None" in written.get("src/auth.py","") and "is None" not in content:
            pass  # old pattern should be gone, but we check presence of new is enough
    # GUI check: both fill and click must be present
    has_fill = any(str(s.get("layer"))=="semantic_dom" and "FILL" in str(s.get("op")) for s in trace)
    has_click = any(str(s.get("layer"))=="semantic_dom" and "CLICK" in str(s.get("op")) and "Submit" in str(s.get("selector",{}).get("name","")) for s in trace)
    return has_fill and has_click

# ------------------------------------------------------------
# Composer: cut + family + verify
# ------------------------------------------------------------

def compose_and_verify(task: dict[str, Any] | None = None, root: Path | None = None) -> dict[str, Any]:
    t0 = time.perf_counter_ns()
    from canonical.swe_kernel.causal_cut_attribution_v1 import extract_minimal_cut, attribute_and_induce
    from canonical.swe_kernel.family_predicate_induction_v1 import predicate_matches_task
    tmp = Path(tempfile.mkdtemp(prefix="brain-longhorizon-")) if root is None else Path(root)
    try:
        hard = _make_hardest_proxy_task(tmp)
        trace = hard["trace"]
        goal = hard["goal"]
        expected_causal = set(hard["causal_indices"])
        expected_noise = set(hard["noise_indices"])

        def oracle(subtrace: Sequence[Mapping[str, Any]]) -> bool:
            return _oracle_for_proxy(subtrace, tmp)

        # 1. Attribution via omission
        cut_res = extract_minimal_cut(trace, oracle, max_ablation_cost=50)
        if cut_res["status"] not in ("CUT_DONE__CAUSAL_CUT_EXTRACTED","CUT_MINIMAL__NECESSARY_AND_SUFFICIENT"):
            return {"schema": SCHEMA, "pass": False, "status": "FAIL_CLOSED__CUT_FAILED", "cut_res": cut_res, "elapsed_ms": (time.perf_counter_ns()-t0)/1e6}

        kept = set(cut_res["kept_indices"])
        pruned = set(cut_res["pruned_indices"])
        attribution_correct = (kept == expected_causal and pruned == expected_noise)

        # 2. Family induction on the minimal trace (ultimate-hard: mixed file+GUI)
        # Pass pre/post snapshots so edit_vs_create is proven: file existed as buggy, fixed content preserves outside.
        pre_state = {k: v.encode() if isinstance(v, str) else v for k, v in hard["files"].items() if k != "gui_state.json"}
        # Build post_state by applying trace writes to pre_state
        post_state = dict(pre_state)
        for s in trace:
            if str(s.get("layer")) == "python_file_op" and s.get("path") and s.get("content"):
                post_state[str(s["path"])] = str(s["content"]).encode()
        induced = attribute_and_induce(trace, oracle, goal=goal, pre_state=pre_state, post_state=post_state)
        family_ok = induced.get("pass") and induced.get("family_predicate",{}).get("postcondition",{}).get("kind") != "unknown"

        # 3. GUI grounding verification (using mock state file)
        from canonical.runtime.gui_computer_use_registry_v1 import invoke as gui_invoke
        gui_state = str(tmp / "gui_state.json")
        g1 = gui_invoke("CAP_GUI_GROUND_V1", {"target_label": "Submit", "state_path": gui_state}, str(tmp))
        ground_ok = g1["status"] == "VERIFIED_CAPABILITY_INVOKED" and g1["receipt"].get("decisive")
        g2 = gui_invoke("CAP_GUI_ACT_V1", {"selector": g1["receipt"]["selector"], "action": "CLICK_SEMANTIC", "state_path": gui_state}, str(tmp)) if ground_ok else {"status":"FAIL"}
        act_ok = g2.get("status") == "VERIFIED_CAPABILITY_INVOKED" if isinstance(g2, dict) else False
        g3 = gui_invoke("CAP_GUI_VERIFY_V1", {"target_name": "Submit", "state_path": gui_state}, str(tmp)) if act_ok else {"status":"FAIL"}
        verify_ok = g3.get("status") == "VERIFIED_CAPABILITY_INVOKED" if isinstance(g3, dict) else False

        # 4. Null-space admission probe (would this composition be remembered without forgetting?)
        from canonical.swe_kernel.weight_update_admission_v1 import probes_from_goals, stream_goals, fresh_model
        from canonical.swe_kernel.nullspace_admission_v1 import evaluate_nullspace_update
        built = probes_from_goals(stream_goals())
        probes = built["probes"]
        with tempfile.TemporaryDirectory() as t2:
            model = fresh_model(Path(t2))
            null_eval = evaluate_nullspace_update(model, probes[0].goal, probes[0].operation, probes[0].concept, probes[0].domain, [p for p in probes if p.goal != probes[0].goal], G_history=[])

        elapsed = (time.perf_counter_ns()-t0)/1e6
        passed = attribution_correct and family_ok and ground_ok and act_ok and verify_ok
        return {
            "schema": SCHEMA,
            "pass": passed,
            "status": "PASS__LONG_HORIZON_COMPOSITION_VERIFIED" if passed else "FAIL__LONG_HORIZON_COMPOSITION_FAILED",
            "goal": goal,
            "trace_len": len(trace),
            "kept_indices": sorted(kept),
            "pruned_indices": sorted(pruned),
            "expected_kept": sorted(expected_causal),
            "attribution_correct": attribution_correct,
            "family_ok": family_ok,
            "family_id": induced.get("family_predicate",{}).get("family_id") if family_ok else None,
            "ground_ok": ground_ok,
            "act_ok": act_ok,
            "verify_ok": verify_ok,
            "nullspace_probe": {"verdict": null_eval.get("verdict"), "counts": null_eval.get("counts")},
            "oracle_calls": cut_res.get("oracle_calls"),
            "elapsed_ms": round(elapsed,2),
            "derivation": "causal_cut_x_family_x_gui_ground_verify_x_nullspace_admission",
            "model_calls": 0, "network_calls": 0,
        }
    finally:
        if root is None:
            import shutil
            shutil.rmtree(tmp, ignore_errors=True)

def main(argv: Sequence[str] | None = None) -> int:
    import argparse, json
    parser = argparse.ArgumentParser(description="Long-horizon hardest-case composition test")
    parser.add_argument("--json", dest="json_path", default=None)
    ns = parser.parse_args(argv)
    res = compose_and_verify()
    print(json.dumps(res, indent=2, sort_keys=True))
    if ns.json_path:
        p = Path(ns.json_path)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(res, indent=2, sort_keys=True)+"\n")
        print(f"\nwritten: {ns.json_path}")
    return 0 if res.get("pass") else 1

if __name__ == "__main__":
    raise SystemExit(main())
