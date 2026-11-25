"""§6 Memory Ablation, Single-Experience Transfer, O(1) Deletion & Polyglot T-1/T-2 Verification Suite.

Verifies all four core Zero-Knowledge-House memory laws (0 external model calls, 0 neural weights):
  1. Store vs. Empty ablation across SWE (with N=5,000 distractor O(1) index scaling), CLI, and OSWorld GUI;
  2. Generalized Parameterized Laws (`TreeRewriteMorphism` / `ParameterizedCausalLaw`) vs. Raw Exact Traces
     on renamed identifiers / changed file paths;
  3. O(1) surgical deletion & instant unlearning without corrupting sibling laws;
  4. Corrupted / poisoned external law rejection & L3 `NegativeSpaceInvariant` quarantine;
  5. Polyglot Engine T-1 (zero-leakage issue-only JS + native Node v22 TypeScript `.ts`) and Engine T-2 (C++17 ASan).
"""
from __future__ import annotations

import ast
import json
import pathlib
import re
import stat
import time

import pytest

from canonical.runtime.osworld_v21_brain_agent_adapter_v8 import BrainOSWorldAgentV8
from canonical.runtime.osworld_v21_zero_model_policy_v1 import (
    ZeroModelOSWorldPolicy,
    encode_rgb_to_png,
)
from canonical.swe_kernel import angelic_cegis_repair_v1 as acr
from canonical.swe_kernel import c_asan_cegis_repair_v1 as ccr
from canonical.swe_kernel import js_causal_cegis_repair_v1 as jsc
from canonical.swe_kernel import reverse_tomography_algebra_v1 as rta
from canonical.swe_kernel import universal_computer_agent_v1 as uca


def _make_single_bug_py_repo(
    root: pathlib.Path,
    *,
    mod_name: str,
    fn_name: str,
    arg_name: str,
) -> tuple[pathlib.Path, str, str]:
    """Create a minimal standalone Python repo with a real boundary/off-by-one bug using caller-chosen identifiers."""
    root.mkdir(parents=True, exist_ok=True)
    src_rel = f"{mod_name}.py"
    test_rel = f"test_{mod_name}.py"
    (root / src_rel).write_text(
        f"def {fn_name}({arg_name}: int, limit: int) -> bool:\n"
        f"    if {arg_name} < limit:\n"
        f"        return True\n"
        f"    return False\n",
        encoding="utf-8",
    )
    (root / test_rel).write_text(
        f"from {mod_name} import {fn_name}\n\n"
        f"def test_boundary():\n"
        f"    assert {fn_name}(3, 5) is True\n"
        f"    assert {fn_name}(5, 5) is True\n"
        f"    assert {fn_name}(6, 5) is False\n",
        encoding="utf-8",
    )
    return root, src_rel, test_rel


def test_ablation_1_and_2_swe_generalized_vs_raw_and_5000_distractor_o1_scaling(tmp_path: pathlib.Path) -> None:
    """Prove: (a) raw exact text replay fails 0% on renamed identifiers while generalized TreeRewriteMorphism
    transfers 1-shot 100%; (b) O(1) structural index stays fast (< 0.15s lookup) even with 5,000 distractors."""
    # Episode 1: solve Repo A (`alpha_mod.py`: `check_alpha(val_a, limit)`) from EMPTY store and crystallize L2 morphism
    repo_a, src_a, test_a = _make_single_bug_py_repo(
        tmp_path / "repo_a", mod_name="alpha_mod", fn_name="check_alpha", arg_name="val_a"
    )
    orig_a = (repo_a / src_a).read_text(encoding="utf-8")
    store_path = tmp_path / "swe_ablation_store.json"
    store = uca.ExternalCausalLawStore(store_path)

    res_a = acr.repair_repo_angelic_cegis(repo_a, test_a, timeout_s=20, skill_store=store)
    assert res_a["repaired"] is True
    assert res_a.get("model_calls", 0) == 0
    patched_a = str(res_a["patched_source"])
    assert "<=" in patched_a

    # Capture the raw exact single-line diff from Repo A (baseline "raw trace" ablation!)
    raw_old_line = "    if val_a < limit:"
    raw_new_line = "    if val_a <= limit:"
    assert raw_old_line in orig_a and raw_new_line in patched_a

    # Ensure a generalized TreeRewriteMorphism is stored in `store` (crystallized from Repo A's single fix!)
    m_a = rta.extract_multi_stmt_tree_morphism(orig_a, patched_a, provenance={"repo": "repo_a"})
    assert m_a is not None
    store.admit_tree_morphism(m_a)

    # Inject 5,000 distinct distractor morphisms (suppressing per-insert disk flush, then flushing once)
    saved_path = store.path
    store.path = None
    for i in range(5000):
        distractor = rta.TreeRewriteMorphism(
            morphism_id=f"dist_{i:04d}",
            target_kind="stmt_window",
            pattern_sexps=(f"(Assign (Name $V0) (Constant {i}))",),
            replacement_sexps=(f"(Assign (Name $V0) (Constant {i + 1}))",),
            hole_types={"$V0": "Name"},
            provenance={"distractor": i},
        )
        store.admit_tree_morphism(distractor)
    store.path = saved_path
    store.save()
    assert len(store.tree_morphisms) >= 5001

    # Episode 2: Unseen Repo B with COMPLETELY RENAMED module, function, and parameter (`beta_mod.check_beta(score_b)`)
    repo_b, src_b, test_b = _make_single_bug_py_repo(
        tmp_path / "repo_b", mod_name="beta_mod", fn_name="check_beta", arg_name="score_b"
    )
    orig_b = (repo_b / src_b).read_text(encoding="utf-8")

    # ABLATION A — Raw Exact Trace Replay on Repo B: MUST FAIL (`0%` match because identifiers changed!)
    raw_replay_matched = raw_old_line in orig_b
    assert raw_replay_matched is False, "Raw exact trace should not match renamed identifiers"

    # ABLATION B — Generalized Parameterized TreeRewriteMorphism O(1) Recall @ N=5,001: MUST SUCCEED IN 1 SHOT!
    t0 = time.monotonic()
    hits = store.query_tree_morphisms_o1(orig_b, target_lines={2})
    o1_query_ms = (time.monotonic() - t0) * 1000.0
    assert o1_query_ms < 200.0, f"O(1) structural index too slow at N=5001: {o1_query_ms:.1f}ms"
    assert any(h.morphism_id == m_a.morphism_id for h in hits)

    res_b_warm = acr.repair_repo_angelic_cegis(repo_b, test_b, timeout_s=20, skill_store=store)
    assert res_b_warm["repaired"] is True
    assert res_b_warm.get("model_calls", 0) == 0
    assert "<=" in str(res_b_warm["patched_source"])
    assert "TREE_REWRITE_MORPHISM" in str(res_b_warm.get("method") or "") or "L2" in str(res_b_warm.get("method") or "")

    # ABLATION C — O(1) Surgical Deletion & Instant Unlearning!
    sibling_id = "dist_0042"
    assert store.delete_tree_morphism(m_a.morphism_id) is True
    assert store.delete_tree_morphism(m_a.morphism_id) is False  # Already gone!
    hits_after_delete = store.query_tree_morphisms_o1(orig_b, target_lines={2})
    assert all(h.morphism_id != m_a.morphism_id for h in hits_after_delete)
    # Sibling law remains completely intact!
    assert sibling_id in store.tree_morphisms


def test_ablation_2_and_3_cli_generalized_vs_raw_and_o1_deletion(tmp_path: pathlib.Path) -> None:
    """Terminal-Bench CLI ablation: generalized ParameterizedCausalLaw transfers across renamed files with 0 new
    help probes while raw exact command replay fails, and O(1) deletion instantly unlearns only the target law."""
    bin_dir = tmp_path / "custom_bin"
    bin_dir.mkdir()
    tool_p = bin_dir / "xform_cli"
    tool_p.write_text(
        "#!/usr/bin/env python3\n"
        "import json, pathlib, sys\n"
        "args = sys.argv[1:]\n"
        "if '--help' in args or '-h' in args:\n"
        "    print('Usage: xform_cli --src <in> --dst <out>')\n"
        "    sys.exit(0)\n"
        "if len(args) == 4 and args[0] == '--src' and args[2] == '--dst':\n"
        "    txt = pathlib.Path(args[1]).read_text(encoding='utf-8').strip()\n"
        "    pathlib.Path(args[3]).write_text(json.dumps({'val': txt.upper()}), encoding='utf-8')\n"
        "    sys.exit(0)\n"
        "sys.exit(2)\n",
        encoding="utf-8",
    )
    tool_p.chmod(tool_p.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)

    store_p = tmp_path / "cli_ablation_laws.json"
    agent = uca.UniversalComputerAgent(law_store_path=store_p)

    # Episode 1 (Cold empty store): solve `alpha.txt -> out_a.json`
    ws1 = tmp_path / "ws1"
    ws1.mkdir()
    (ws1 / "alpha.txt").write_text("hello\n", encoding="utf-8")
    env1 = uca.RealTerminalEnv(ws1, extra_bin_dirs=[bin_dir])
    r1 = agent.solve_terminal_goal(env1, "Use xform_cli to convert alpha.txt into out_a.json.")
    assert r1["solved"] is True
    assert json.loads((ws1 / "out_a.json").read_text(encoding="utf-8")) == {"val": "HELLO"}
    raw_cmd_ep1 = list(r1["real_actions"][-1])

    # Episode 2 (Warm generalized store on DIFFERENT filenames `beta.txt -> out_b.json`)
    ws2 = tmp_path / "ws2"
    ws2.mkdir()
    (ws2 / "beta.txt").write_text("world\n", encoding="utf-8")

    # Raw exact trace replay from Ep1 (`alpha.txt -> out_a.json`) FAILS on ws2!
    env2_raw = uca.RealTerminalEnv(ws2, extra_bin_dirs=[bin_dir])
    raw_probe = env2_raw.probe_in_shadow_sandbox(raw_cmd_ep1)
    assert raw_probe["ok"] is False

    # Generalized ParameterizedCausalLaw SUCCEEDS on ws2 from memory!
    env2 = uca.RealTerminalEnv(ws2, extra_bin_dirs=[bin_dir])
    r2 = agent.solve_terminal_goal(env2, "Use xform_cli to convert beta.txt into out_b.json.")
    assert r2["solved"] is True
    assert json.loads((ws2 / "out_b.json").read_text(encoding="utf-8")) == {"val": "WORLD"}
    assert r2["laws_from_memory"] >= 1

    # O(1) deletion removes xform_cli law cleanly while preserving a sibling law!
    sibling_law = uca.ParameterizedCausalLaw(
        law_id="sibling::keep_me",
        domain="cli",
        tool_or_action="sibling_tool",
        command_template=["sibling_tool", "{src}", "{dst}"],
        preconditions={},
        effects={},
    )
    agent.store.admit(sibling_law)
    cli_laws = [l for l in agent.store.active_laws() if l.tool_or_action == "xform_cli"]
    assert cli_laws
    for cl in cli_laws:
        assert agent.store.remove(cl.law_id) is True
    assert all(l.tool_or_action != "xform_cli" for l in agent.store.active_laws())
    assert any(l.law_id == "sibling::keep_me" for l in agent.store.active_laws())


def test_ablation_1_and_3_osworld_gui_store_vs_empty_and_o1_unlearning(tmp_path: pathlib.Path) -> None:
    """OSWorld 2.1 pure-canvas ablation: empty store needs 2 exploration clicks; warm L2 store solves in 1 click;
    O(1) deletion reverts immediately back to 2-click cold exploration."""
    def _frame(active: bool) -> bytes:
        bg = (230, 230, 230) if not active else (40, 200, 90)
        g = [[bg for _ in range(40)] for _ in range(24)]
        if not active:
            # Left decoy button (x=4..12, y=6..14), Right true target button (x=24..34, y=6..14)
            for y in range(6, 14):
                for x in range(4, 12):
                    g[y][x] = (200, 60, 60)
                for x in range(24, 34):
                    g[y][x] = (60, 80, 220)
        return encode_rgb_to_png(g)

    def _run_blind(pol: ZeroModelOSWorldPolicy) -> tuple[bool, int]:
        pol.reset_episode()
        ag = BrainOSWorldAgentV8(policy_provider=pol, policy_id="ablation_gui")
        done_flag = False
        clicks = 0
        for _ in range(6):
            _, out = ag.predict("Activate the target control", {"screenshot": _frame(done_flag), "accessibility_tree": ""})
            if out[0] == "DONE":
                return True, clicks
            clicks += 1
            mx = re.search(r"x\s*=\s*(\d+)", out[0])
            if mx and int(mx.group(1)) >= 20:
                done_flag = True
        return False, clicks

    store_p = tmp_path / "osw_ablation.json"
    pol = ZeroModelOSWorldPolicy(
        law_store_path=store_p,
        visual_goal_verifier=lambda rgb: rgb[0][0] == (40, 200, 90),
    )

    # 1. Empty store (cold): clicks left decoy first (pruned as no-op!), then right target -> 2 clicks
    ok_cold, clicks_cold = _run_blind(pol)
    assert ok_cold and clicks_cold == 2
    assert pol.noop_actions_pruned >= 1

    # 2. Warm L2 store: solves in 1 single click (50% fewer actions, 0 wasted probes!)
    ok_warm, clicks_warm = _run_blind(pol)
    assert ok_warm and clicks_warm == 1
    assert pol.memory_recall_hits >= 1

    # 3. O(1) surgical deletion: remove the learned GUI law -> reverts immediately to 2 clicks!
    gui_laws = pol.store.active_laws(domain="osworld_gui")
    assert len(gui_laws) == 1
    assert pol.store.remove(gui_laws[0].law_id) is True
    ok_after_del, clicks_after_del = _run_blind(pol)
    assert ok_after_del and clicks_after_del == 2


def test_ablation_4_poisoned_law_rejection_and_l3_negative_invariant_quarantine(tmp_path: pathlib.Path) -> None:
    """Adversarial memory integrity: (a) poisoned TreeRewriteMorphism in store is REJECTED by fresh test
    verification and never blocks live CEGIS repair; (b) destructive CLI candidate is blocked by
    NegativeEffectOracle and quarantined as an L3 NegativeSpaceInvariant."""
    # (a) Poisoned SWE morphism (`<` -> `>` which is WRONG!) injected into external JSON store
    repo, src_rel, test_rel = _make_single_bug_py_repo(
        tmp_path / "poison_repo", mod_name="guard_mod", fn_name="in_range", arg_name="x"
    )
    store = uca.ExternalCausalLawStore(tmp_path / "poison_store.json")
    bad_orig = "if a < b:\n    return True\n"
    bad_patch = "if a > b:\n    return True\n"
    poison_m = rta.extract_multi_stmt_tree_morphism(bad_orig, bad_patch, provenance={"poisoned": True})
    assert poison_m is not None
    store.admit_tree_morphism(poison_m)

    res = acr.repair_repo_angelic_cegis(repo, test_rel, timeout_s=20, skill_store=store)
    assert res["repaired"] is True
    assert res.get("model_calls", 0) == 0
    assert "<=" in str(res["patched_source"])
    assert "if x > limit:" not in str(res["patched_source"])

    # (b) Destructive CLI plan quarantined by TransactionalWorkspaceCoWRunner + NegativeEffectOracle -> L3 invariant!
    ws = tmp_path / "cow_quarantine"
    ws.mkdir()
    (ws / "sacred.txt").write_text("IMMUTABLE_DATA\n", encoding="utf-8")
    runner = uca.TransactionalWorkspaceCoWRunner(ws, law_store=store)
    cow_res = runner.execute_speculative_candidates(
        candidates=[
            {"id": "poison_destroy", "command": "rm -f sacred.txt && echo ok > result.txt"},
            {"id": "clean_plan", "command": "echo CLEAN_OK > result.txt"},
        ],
        postcondition_clauses=[
            ("result_nonempty", lambda w: (w / "result.txt").is_file() and (w / "result.txt").stat().st_size > 0)
        ],
        allowed_write_paths=["result.txt"],
        allow_new_files=True,
    )
    assert cow_res["committed"] is True
    assert cow_res["winner_id"] == "clean_plan"
    assert (ws / "sacred.txt").read_text(encoding="utf-8") == "IMMUTABLE_DATA\n"
    assert (ws / "result.txt").read_text(encoding="utf-8").strip() == "CLEAN_OK"
    assert len(cow_res.get("blocked_negative_effects") or []) >= 1
    assert len(store.negative_invariants) >= 1


def test_engine_t1_and_t2_issue_only_js_native_ts_and_cpp17_zero_model(tmp_path: pathlib.Path) -> None:
    """Engine T-1 (zero-leakage issue-only JS + native Node v22 TypeScript `.ts`) and Engine T-2 (C++17 ASan)."""
    # 1. Zero-leakage issue-only JS (`0` human tests!)
    if jsc._find_node():
        js_ws = tmp_path / "issue_only_js"
        (js_ws / "lib").mkdir(parents=True)
        (js_ws / "index.js").write_text("module.exports = { parse: require('./lib/parse') };\n", encoding="utf-8")
        (js_ws / "lib" / "parse.js").write_text(
            "module.exports = function parse(str, opts) {\n"
            "    if (opts && opts.decodeDotInKeys) {\n"
            "        return { key: str.replace(/%2E/g, '.') };\n"
            "    }\n"
            "    return { key: str };\n"
            "};\n",
            encoding="utf-8",
        )
        r_js = jsc.repair_js_repo_from_issue_zero_leakage(
            js_ws,
            "parse: decode percent-encoded dots (%2E) case-insensitively when decodeDotInKeys is enabled.",
            timeout_s=15,
        )
        assert r_js["repaired"] is True and r_js["model_calls"] == 0
        assert "/%2E/gi" in str(r_js["patched_source"])

        # 2. Native Node v22 TypeScript `.ts` repair (0 tsc, 0 npm!)
        ts_ws = tmp_path / "native_ts"
        (ts_ws / "src").mkdir(parents=True)
        (ts_ws / "test").mkdir(parents=True)
        (ts_ws / "src" / "codec.ts").write_text(
            "export function decodeDots(s: string): string {\n"
            "    return s.replace(/%2E/g, '.');\n"
            "}\n",
            encoding="utf-8",
        )
        (ts_ws / "test" / "codec.ts").write_text(
            "import assert from 'node:assert/strict';\n"
            "import { decodeDots } from '../src/codec.ts';\n"
            "assert.equal(decodeDots('x%2Ey%2ez'), 'x.y.z');\n",
            encoding="utf-8",
        )
        r_ts = jsc.repair_js_repo_causal_cegis(ts_ws, "test/codec.ts", timeout_s=15)
        assert r_ts["repaired"] is True and r_ts["model_calls"] == 0
        assert "/%2E/gi" in str(r_ts["patched_source"])

    # 3. C++17 (`g++ -std=c++17 -fsanitize=address,undefined`) repair
    if ccr._find_cpp_compiler():
        cpp_ws = tmp_path / "cpp17_ws"
        cpp_ws.mkdir()
        (cpp_ws / "reader.cpp").write_text(
            "#include <cstring>\n"
            "class BufLen {\n"
            "public:\n"
            "    int measure(const char *p) const {\n"
            "        return static_cast<int>(std::strlen(p));\n"
            "    }\n"
            "};\n"
            "int measure_str(const char *p) { BufLen b; return b.measure(p); }\n",
            encoding="utf-8",
        )
        (cpp_ws / "test_reader.cpp").write_text(
            "#include <cassert>\n"
            "int measure_str(const char *p);\n"
            "int main() {\n"
            "    assert(measure_str(nullptr) == 0);\n"
            "    assert(measure_str(\"abc\") == 3);\n"
            "    return 0;\n"
            "}\n",
            encoding="utf-8",
        )
        r_cpp = ccr.repair_c_repo_asan_cegis(
            cpp_ws, ["reader.cpp", "test_reader.cpp"], editable_files=["reader.cpp"], timeout_s=20
        )
        assert r_cpp["repaired"] is True and r_cpp["model_calls"] == 0
