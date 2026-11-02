from __future__ import annotations

import json
import sys
import time
from pathlib import Path
from typing import Any, Mapping

_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from canonical.runtime import associative_memory_v1 as amem
from canonical.runtime import brain_unified_model_v1 as bum
from canonical.runtime import cross_document_effect_semantic_lattice_v8 as lattice_v8
from canonical.runtime import goal_compiler as gc
from canonical.runtime.bounded_semantic_relation_proof_v1 import (
    EVIDENCE_SCHEMA as BOUNDED_REL_EVIDENCE_SCHEMA,
    evidence_sha256 as bounded_rel_sha256,
)
from canonical.runtime.certified_document_effect_relation_v1 import parse_effect_relations
from canonical.runtime.effect_broker_receipt_resolver_v2 import git_blob_id
from canonical.runtime.executable_skill_program_v7 import candidate_digest as skill_v7_digest
from canonical.runtime.live_integrated_brain_v1 import load_verified_registry
from canonical.runtime.oewn_decision_sense_control_v1 import MANIFEST_SCHEMA as OEWN_MANIFEST_SCHEMA
from canonical.runtime.oewn_release_sense_universe_v1 import (
    RELEASE_ID as OEWN_RELEASE_ID,
    RELEASE_SHA256 as OEWN_RELEASE_SHA256,
    SCHEMA as OEWN_SCHEMA,
)
from canonical.runtime.universal_verified_adaptive_solver_v1 import _digest as v1_digest
from canonical.runtime.universal_verified_adaptive_solver_v2 import SUCCESS_CONDITIONS
from canonical.runtime.universal_verified_adaptive_solver_v3 import (
    BINDING_SCHEMA,
    BINDING_VERIFY_SCHEMA,
    task_contract_sha256,
)
from canonical.swe_kernel.autonomous_awake_loop_v1 import AwakeAgencyDaemon
from canonical.swe_kernel.closed_loop_autonomous_controller_v1 import solve_or_learn


def test_stage1_sub4ms_bit_identical_goal_shortlist_and_composer_graph_cache() -> None:
    reg = gc._platform_admissible_registry(dict(load_verified_registry()))
    sample_goals = [
        "Audit python functions in canonical/runtime/solve_v1.py and save report to canonical/astra_runtime/tmp/s1.json",
        "Compute SHA256 digest of canonical/runtime/solve_v1.py",
        "Create a tar.gz archive from canonical/runtime/solve_v1.py",
        "Rename the parameter text to value in canonical/runtime/solve_v1.py",
        "Unknown capability sentinel xyzqwert987",
    ]
    # 1. Prove mathematical bit-identity of inverted-index shortlist vs full linear scan
    postings, adm_map, _ = gc._get_registry_rank_index(reg)
    for g in sample_goals:
        _, _, dg, _ = gc._goal_score_features(g)
        shortlist: set[str] = set()
        for tok in dg:
            shortlist.update(postings.get(tok, ()))
        for cid, entry in reg.items():
            if not isinstance(entry, dict) or entry.get("status") != "VERIFIED_BOUND_CAPABILITY":
                continue
            if not isinstance(entry.get("action_template"), dict):
                continue
            if entry.get("requires") and not gc._placeholders(entry["action_template"]):
                continue
            sc, _, _ = gc._score(g, cid, entry)
            if sc > 0:
                assert cid in shortlist and cid in adm_map

    # 2. Prove warm `_rank_bindable_candidates` runs well below 4 ms/call
    gc._rank_bindable_candidates(sample_goals[0], reg, ".")
    t0 = time.perf_counter()
    for i in range(25):
        gc._rank_bindable_candidates(f"{sample_goals[0]} {i}", reg, ".")
    avg_ms = (time.perf_counter() - t0) * 1000.0 / 25.0
    assert avg_ms < 4.0, f"Expected sub-4ms _rank_bindable_candidates, got {avg_ms:.3f} ms"

    # 3. Prove `(mtime_ns, st_size)`-cached composer graph returns identical in-RAM object
    from canonical.runtime.live_brain_route_admission_v1 import _cached_composer_graph

    g1 = _cached_composer_graph()
    g2 = _cached_composer_graph()
    assert g1 is g2 and len(g1) > 10


def test_stage2_unfamiliar_api_tool_planning_semantic_ambiguity_polytopes_and_lattice() -> None:
    # 1. Unfamiliar 2-step REST API (`GET -> PATCH`) with automatic live observation ID grounding (`K3 = 0`)
    endpoints = [
        {
            "id": "orders.search",
            "method": "GET",
            "url": "https://opaque.invalid/objects",
            "description": "Search customer orders by name and status.",
            "response": "{records: [{id, name, status}]}",
        },
        {
            "id": "orders.modify",
            "method": "PATCH",
            "url": "https://opaque.invalid/orders/{id}",
            "description": "Update order status.",
            "parameters": {"id": {"required": True, "location": "path", "type": "string"}},
            "request": "{status?: string}",
            "response": "{id, name, status}",
        },
    ]
    calls_made: list[tuple[str, dict[str, Any]]] = []

    def _mock_api_executor(ep: Mapping[str, Any], args: dict[str, Any]) -> dict[str, Any]:
        calls_made.append((str(ep["id"]), dict(args)))
        if ep["id"] == "orders.search":
            return {"records": [{"id": "ord-77", "name": "Acme", "status": "open"}]}
        return {"id": "ord-77", "name": "Acme", "status": "closed"}

    api_res = solve_or_learn(
        {
            "task_id": "s2-api",
            "goal": "Find the Acme order, then set the order status to closed.",
            "tool_schemas": endpoints,
            "tool_executor": _mock_api_executor,
        },
        record_open_gap=False,
    )
    assert api_res["pass"] is True
    assert api_res["k3_external_llm_calls"] == 0
    assert len(calls_made) == 2
    assert calls_made[0][0] == "orders.search"
    assert calls_made[1][0] == "orders.modify"
    assert calls_made[1][1]["url"] == "https://opaque.invalid/orders/ord-77"
    assert json.loads(calls_made[1][1]["body"]) == {"status": "closed"}

    # Fail-closed when observation returns no matching record ID
    ungrounded = solve_or_learn(
        {
            "task_id": "s2-api-fail",
            "goal": "Find the Acme order, then set the order status to closed.",
            "tool_schemas": endpoints,
            "tool_executor": lambda ep, args: {"records": []} if ep["id"] == "orders.search" else {},
        },
        record_open_gap=False,
    )
    assert ungrounded["pass"] is False
    assert "REQUIRED_PARAMETER_UNGROUNDED:id" in ungrounded["status"]

    # 2. Lossless Semantic Ambiguity Control (terminal-signature invariance vs divergent worlds)
    amb_eq = solve_or_learn(
        {
            "task_id": "s2-amb-eq",
            "goal": "Send notice under harmless surface ambiguity",
            "ambiguity_problem": {
                "ambiguity_owner": "USER_INTENT",
                "hypothesis_set_complete": True,
                "worlds": [
                    {"world_id": "w1", "terminal_signature_complete": True, "terminal_signature": {"op": "NOTIFY_ALL"}},
                    {"world_id": "w2", "terminal_signature_complete": True, "terminal_signature": {"op": "NOTIFY_ALL"}},
                ],
                "observations": [],
            },
        },
        record_open_gap=False,
    )
    assert amb_eq["pass"] is True
    assert amb_eq["semantic_control"]["action"] == "CONTINUE_WITHOUT_DISAMBIGUATION"

    amb_div = solve_or_learn(
        {
            "task_id": "s2-amb-div",
            "goal": "Transfer funds to ambiguous recipient",
            "ambiguity_problem": {
                "ambiguity_owner": "USER_INTENT",
                "hypothesis_set_complete": True,
                "worlds": [
                    {"world_id": "alice", "terminal_signature_complete": True, "terminal_signature": {"to": "ALICE"}},
                    {"world_id": "sarah", "terminal_signature_complete": True, "terminal_signature": {"to": "SARAH"}},
                ],
                "observations": [],
            },
        },
        record_open_gap=False,
    )
    assert amb_div["pass"] is False
    assert amb_div["semantic_control"]["ask_user_required"] is True

    # 3. Scoped Semantic Relation Control (`semantic_relation_control_v2`) + OEWN Sense Control
    rel_ev = {
        "schema": BOUNDED_REL_EVIDENCE_SCHEMA,
        "scope_id": "finance:2026",
        "left_id": "L",
        "right_id": "R",
        "universe_complete": True,
        "left_extension_complete": True,
        "right_extension_complete": True,
        "universe": ["a", "b", "c"],
        "left_members": ["a", "b"],
        "right_members": ["a", "b"],
    }
    rel_out = solve_or_learn(
        {
            "task_id": "s2-rel",
            "goal": "Verify scoped equivalence of reserve buffer and liquidity cushion",
            "semantic_relation_problem": {
                "left_id": "L",
                "right_id": "R",
                "left_surface": "reserve buffer",
                "right_surface": "liquidity cushion",
                "scope_id": "finance:2026",
                "required_relation": "LOGICAL_EQUIVALENCE_IN_SCOPE",
                "bounded_extension_evidence": rel_ev,
                "expected_bounded_extension_sha256": bounded_rel_sha256(rel_ev),
            },
        },
        record_open_gap=False,
    )
    assert rel_out["pass"] is True
    assert rel_out["semantic_control"]["strongest_proved_relation"] == "LOGICAL_EQUIVALENCE_IN_SCOPE"

    oewn_univ = {
        "schema": OEWN_SCHEMA,
        "status": "PASS__OEWN_2025_RELEASE_RELATIVE_SENSE_UNIVERSE_ENUMERATED",
        "pass": True,
        "release_id": OEWN_RELEASE_ID,
        "archive_sha256": OEWN_RELEASE_SHA256,
        "candidate_set_complete_relative_to_release": True,
        "open_world_english_sense_completeness_claimed": False,
        "lemma": "margin",
        "requested_part_of_speech": "n",
        "senses": [
            {"sense_id": "margin-1", "synset_id": "ewn-margin-1-n", "part_of_speech": "n"},
            {"sense_id": "margin-2", "synset_id": "ewn-margin-2-n", "part_of_speech": "n"},
        ],
    }
    oewn_manifest = {
        "schema": OEWN_MANIFEST_SCHEMA,
        "scope_id": "finance-margin-v1",
        "release_id": OEWN_RELEASE_ID,
        "lemma": "margin",
        "part_of_speech": "n",
        "sense_bindings": {
            "margin-1": {"terminal_signature_complete": True, "terminal_signature": {"metric": "NET_MARGIN"}},
            "margin-2": {"terminal_signature_complete": True, "terminal_signature": {"metric": "NET_MARGIN"}},
        },
        "observations": [],
    }
    oewn_res = solve_or_learn(
        {
            "task_id": "s2-oewn",
            "goal": "Resolve OEWN sense equivalence",
            "sense_problem": {"sense_universe": oewn_univ, "decision_manifest": oewn_manifest},
        },
        record_open_gap=False,
    )
    assert oewn_res["semantic_control"]["control_organ"] == "oewn_decision_sense_control_v1"

    # 4. Exact Rational Parameter Polytope (`Fraction`-exact interval extrapolation)
    poly_res = solve_or_learn(
        {
            "task_id": "s2-poly",
            "goal": "Bound linear parameter polytope",
            "polytope_problem": {
                "feature_semantics_bound": True,
                "observation_intervals_sound": True,
                "observations": [
                    {"features": ["1", "0"], "output_interval": ["9/10", "11/10"]},
                    {"features": ["1", "1"], "output_interval": ["29/10", "31/10"]},
                ],
                "queries": [{"query_id": "q_x2", "features": ["1", "2"]}],
            },
        },
        record_open_gap=False,
    )
    assert poly_res["pass"] is True
    assert poly_res["polytope"]["query_predictions"][0]["prediction_interval"] == ["47/10", "53/10"]

    # 5. Cross-Document Effect Semantic Lattice V8 (`DEFINE` superseded by `REPLACE`)
    def _mk_doc(did: str, effect_ids: list[str], effects: list[dict[str, Any]]) -> dict[str, Any]:
        lines = [
            "Effect targets only: threshold.",
            f"Effect IDs only for threshold: {', '.join(effect_ids)}.",
        ]
        claims: list[dict[str, Any]] = [
            {"claim_id": f"{did}.scope", "kind": "CERTIFIED_EFFECT_TARGET_SCOPE", "target_ids": ["threshold"]},
            {
                "claim_id": f"{did}.inv",
                "kind": "CERTIFIED_EFFECT_ID_INVENTORY",
                "target_id": "threshold",
                "effect_ids": list(effect_ids),
            },
        ]
        for idx, eff in enumerate(effects):
            line = "Effect relation: " + json.dumps(eff, sort_keys=True, separators=(",", ":"))
            lines.append(line)
            sem = {
                k: v
                for k, v in parse_effect_relations(line, source=did)["relations"][0]["effect"].items()
                if k != "source_locator"
            }
            claims.append({"claim_id": f"{did}.rel.{idx}", "kind": "CERTIFIED_DOCUMENT_EFFECT_RELATION", "effect": sem})
        return {"document_id": did, "source_id": did, "source_text": "\n".join(lines), "claims": claims}

    e1 = {
        "conditions": {},
        "effect_class": "DEFINE",
        "effect_id": "e1",
        "supersedes": [],
        "target_id": "threshold",
        "valid_from": None,
        "valid_until": None,
        "value": 10,
    }
    e2 = {
        "conditions": {},
        "effect_class": "REPLACE",
        "effect_id": "e2",
        "supersedes": ["e1"],
        "target_id": "threshold",
        "valid_from": None,
        "valid_until": None,
        "value": 25,
    }
    xdoc_res = solve_or_learn(
        {
            "task_id": "s2-xdoc",
            "goal": "Resolve cross-document superseded threshold",
            "cross_document_problem": {
                "schema": lattice_v8.SCHEMA,
                "case_id": "threshold-amendment",
                "source_documents": [_mk_doc("D1", ["e1"], [e1]), _mk_doc("D2", ["e2"], [e2])],
                "query": {"target_id": "threshold", "as_of": "2026-11-02", "context": {}},
            },
        },
        record_open_gap=False,
    )
    assert xdoc_res["pass"] is True
    assert xdoc_res["cross_document_lattice"]["k3_external_llm_calls"] == 0


def test_stage3_associative_memory_dom_grounding_perf_hotspots_and_command_repair(tmp_path: Path) -> None:
    mem_file = tmp_path / "assoc_mem.json"
    seed_id = amem.remember(
        {"hint": "save button uses data-testid=save"},
        kind="ui_hint",
        tags=("dom", "save"),
        path=str(mem_file),
    )
    before_imp = amem.recall("click save button", k=3, path=str(mem_file))[0]["importance"]

    # 1. Exact DOM Grounding + Consensus DOM Grounding + Associative Memory reinforcement
    dom_elems = [
        {
            "id": "btn_save",
            "role": "button",
            "name": "Save Changes",
            "text": "Save Changes",
            "ocr_text": "SAVE  CHANGES",
            "attrs": {"data-testid": "save"},
            "actions": ["click"],
        },
        {
            "id": "btn_cancel",
            "role": "button",
            "name": "Cancel",
            "text": "Cancel",
            "ocr_text": "Cancel",
            "attrs": {"data-testid": "cancel"},
            "actions": ["click"],
        },
    ]
    dom_exact = solve_or_learn(
        {
            "task_id": "s3-dom-exact",
            "goal": "Click save button on https://app.example.invalid/settings",
            "dom_action": {"action": "click", "role": "button", "name": "Save Changes"},
            "dom_elements": dom_elems,
            "associative_memory_path": str(mem_file),
        },
        record_open_gap=False,
    )
    assert dom_exact["pass"] is True
    assert dom_exact["dom_grounding"]["grounding_stage"] == "exact_dom_grounding"
    assert dom_exact["dom_grounding"]["element_id"] == "btn_save"
    assert dom_exact["dom_grounding"]["urls"] == ["https://app.example.invalid/settings"]

    after_imp = [r for r in amem.recall("click save button", k=5, path=str(mem_file)) if r["id"] == seed_id][0]["importance"]
    assert after_imp > before_imp

    # Case/whitespace normalized OCR + role consensus fallback
    dom_cons = solve_or_learn(
        {
            "task_id": "s3-dom-cons",
            "goal": "Click save changes via normalized OCR consensus",
            "dom_action": {"action": "click", "role": " BUTTON ", "ocr_text": "save changes"},
            "dom_elements": dom_elems,
        },
        record_open_gap=False,
    )
    assert dom_cons["pass"] is True
    assert dom_cons["dom_grounding"]["grounding_stage"] == "consensus_dom_grounding"
    assert dom_cons["dom_grounding"]["element_id"] == "btn_save"

    # Ambiguous duplicate buttons fail closed (`ESCALATE`)
    dom_amb = solve_or_learn(
        {
            "task_id": "s3-dom-amb",
            "goal": "Click ambiguous duplicate button",
            "dom_action": {"action": "click", "role": "button", "name": "Cancel"},
            "dom_elements": dom_elems + [dict(dom_elems[1], id="btn_cancel_2")],
        },
        record_open_gap=False,
    )
    assert dom_amb["pass"] is False
    assert "ESCALATE" in dom_amb["status"]

    # 2. Hotspot Profiling & Dead-Code Diagnostics (`diagnostics_perf_and_design_engine_v1`)
    sample_mod = tmp_path / "hot_mod.py"
    sample_mod.write_text(
        "def compute_squares(n: int = 200) -> int:\n"
        "    return sum(i * i for i in range(n))\n\n"
        "def _unused_dead_helper() -> int:\n"
        "    return 99\n",
        encoding="utf-8",
    )
    perf_res = solve_or_learn(
        {
            "task_id": "s3-perf",
            "goal": "Profile hotspots in module",
            "perf_target": str(sample_mod),
        },
        record_open_gap=False,
    )
    assert perf_res["pass"] is True
    assert perf_res["diagnostics"]["diagnostic_organ"] == "profile_module_hotspots"

    dead_res = solve_or_learn(
        {
            "task_id": "s3-dead",
            "goal": "Find dead unused symbols in module",
            "perf_target": str(sample_mod),
        },
        record_open_gap=False,
    )
    assert dead_res["pass"] is True
    assert dead_res["diagnostics"]["diagnostic_organ"] == "find_dead_code_symbols"

    # 3. Stderr-driven Command Failure Diagnosis & Active Transfer Strategy (`repair_v1` + `universal_active_transfer_learner_v2`)
    cmd_res = solve_or_learn(
        {
            "task_id": "s3-cmd-repair",
            "goal": "Diagnose failing command and rank transfer strategy",
            "repair_command": "python3 -c 'import nonexistent_pkg_xyz'",
            "repair_stderr": "ModuleNotFoundError: No module named 'nonexistent_pkg_xyz'",
            "repair_exit_code": 1,
            "cwd": str(tmp_path),
        },
        record_open_gap=False,
    )
    assert cmd_res["pass"] is True
    assert cmd_res["command_repair"]["diagnosis"]["class"] == "missing_python_module"
    assert cmd_res["command_repair"]["compiled_strategy"]["preferred_action_kind"] == "run_deterministic_setup"


def test_stage4_r3_fixed_point_closure_skill_macro_and_adaptive_solver_v12(tmp_path: Path) -> None:
    # 1. AwakeAgencyDaemon drives R3 queue to a verified SHA-256 fixed point + causal architecture synthesis
    ws = tmp_path / "awake_ws"
    ws.mkdir()
    (ws / "calc.py").write_text("def clamp_hi(x, hi):\n    return x if x <= hi else hi\n", encoding="utf-8")
    (ws / "test_calc.py").write_text("from calc import clamp_hi\ndef test_ok():\n    assert clamp_hi(3, 5) == 3\n", encoding="utf-8")

    st_dir = tmp_path / "awake_state"
    st_dir.mkdir()
    daemon = AwakeAgencyDaemon(
        ws,
        ledger_path=st_dir / "ledger.json",
        skill_store_path=st_dir / "skills.db",
        workflow_db_path=st_dir / "workflows.db",
        journal_dir=st_dir / "journal",
        r3_state_path=st_dir / "r3_state.json",
    )
    pulse_snap = daemon.pulse(max_curriculum_lessons=1)
    assert pulse_snap["k3_external_llm_calls"] == 0
    assert pulse_snap["r3_fixed_point"]["fixed_point"] is True
    assert pulse_snap["r3_fixed_point"]["status"] == "VERIFIED_R3_FIXED_POINT_REACHED"

    arch = daemon.synthesize_causal_architecture(
        {
            "components": [
                {
                    "id": "parse_ast",
                    "requires": ["RAW_SOURCE"],
                    "provides": ["AST_READY"],
                    "cost": {"wall_clock": 1, "incremental_spend_usd": 0},
                    "brain_owned": True,
                    "donor_independent": True,
                    "verified": True,
                },
                {
                    "id": "verify_patch",
                    "requires": ["AST_READY"],
                    "provides": ["REPAIRED_SOURCE"],
                    "cost": {"wall_clock": 2, "incremental_spend_usd": 0},
                    "brain_owned": True,
                    "donor_independent": True,
                    "verified": True,
                },
            ],
            "initial_facts": ["RAW_SOURCE"],
            "target": {"required_effects": ["REPAIRED_SOURCE"], "forbidden_effects": []},
            "counterexamples": [],
        }
    )
    assert arch["pass"] is True
    assert arch["k3_external_llm_calls"] == 0

    # 2. UnifiedModel.act_or_learn -> `verified_skill_macro_planner_v1.plan_with_skills`
    model = bum.open_model()
    steps = [
        {"index": 0, "op": "a", "inputs": ["RAW"], "outputs": ["MID"]},
        {"index": 1, "op": "b", "inputs": ["MID"], "outputs": ["DONE"]},
    ]
    skill_doc = {
        "schema": "PROJECT_BRAIN_EXECUTABLE_SKILL_PROGRAM_V7",
        "status": "VERIFIED_EXECUTABLE_SKILL",
        "source_episode_ids": ["ep1", "ep2"],
        "steps": steps,
        "preconditions": ["RAW"],
        "postconditions": ["DONE"],
        "invalidators": [],
        "candidate_sha256": skill_v7_digest(
            source_episode_ids=["ep1", "ep2"],
            steps=steps,
            preconditions=["RAW"],
            postconditions=["DONE"],
            invalidators=[],
        ),
        "verified_skill": True,
        "reuse_authorized": True,
        "candidate_only": False,
        "scope_relation": "EXACT",
        "verification_receipt": "receipt-s4",
    }
    macro_res = model.act_or_learn(
        "Plan compound target DONE using verified macro skill",
        inputs={
            "skill_macro_problem": {
                "problem": {
                    "initial_facts": ["RAW"],
                    "target_effects": ["DONE"],
                    "capabilities": [
                        {"id": "a", "requires": ["RAW"], "provides": ["MID"], "cost": 4, "result_fields": [], "action": {"type": "x"}},
                        {"id": "b", "requires": ["MID"], "provides": ["DONE"], "cost": 4, "result_fields": [], "action": {"type": "x"}},
                        {"id": "slow", "requires": ["RAW"], "provides": ["DONE"], "cost": 25, "result_fields": [], "action": {"type": "x"}},
                    ],
                },
                "verified_skills": [skill_doc],
            }
        },
    )
    assert macro_res["pass"] is True
    assert macro_res["status"] == "PASS__VERIFIED_SKILL_MACRO_PLANNED"
    assert macro_res["skill_macro_plan"]["expanded_execution_plan"] == ["a", "b"]
    assert len(macro_res["skill_macro_plan"]["used_verified_skill_macros"]) == 1

    # 3. UnifiedModel.act_or_learn -> `universal_verified_adaptive_solver_v12.run` dynamic capability expansion (`K3 = 0`)
    v12_root = tmp_path / "v12_repo"
    v12_root.mkdir()
    prob = {"task_id": "s4-v12", "initial_facts": [], "target_effects": ["GOAL_MET"], "capabilities": []}
    action = {
        "type": "verified_policy",
        "verifier_id": "EXACT_JSON_V1",
        "verifier_payload": {"expected": {"answer": 42}},
        "effect_contract": {
            "effects": ["GOAL_MET"],
            "verifier_success_condition": SUCCESS_CONDITIONS["EXACT_JSON_V1"],
        },
    }
    expected = {
        "capability_id": "expanded-route",
        "task_contract_sha256": task_contract_sha256(prob),
        "requires": [],
        "verifier_id": "EXACT_JSON_V1",
        "verifier_payload_sha256": v1_digest(action["verifier_payload"]),
        "verifier_success_condition": SUCCESS_CONDITIONS["EXACT_JSON_V1"],
        "provided_effects": ["GOAL_MET"],
    }

    def _save_blob(rel: str, doc: Mapping[str, Any]) -> dict[str, str]:
        p = v12_root / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        raw = json.dumps(doc, sort_keys=True, separators=(",", ":")).encode("utf-8")
        p.write_bytes(raw)
        return {"path": rel, "git_blob_sha": git_blob_id(raw, object_format="sha1")}

    rr = _save_blob(
        "canonical/verification/s4-effect.json",
        {"schema": BINDING_SCHEMA, **expected, "pass": True, "claim": "BUILTIN_VERIFIER_PASS_IMPLIES_EXACT_PROVIDED_EFFECTS"},
    )
    vr = _save_blob(
        "canonical/verification/s4-effect.verify.json",
        {
            "schema": BINDING_VERIFY_SCHEMA,
            "subject_git_blob_sha": rr["git_blob_sha"],
            **expected,
            "pass": True,
            "independent_verified": True,
            "implication_semantics_verified": True,
            "independent_verifier_id": "s4-verifier",
        },
    )
    cap_row = {
        "id": "expanded-route",
        "requires": [],
        "provides": ["GOAL_MET"],
        "cost": 1,
        "result_fields": [],
        "action": action,
        "effect_semantics_binding": {"receipt": rr, "verification": vr},
    }
    v12_res = model.act_or_learn(
        "Expand capability frontier and solve GOAL_MET",
        inputs={
            "adaptive_solver_v12_problem": {
                "problem": prob,
                "repo_root": v12_root,
                "capability_expander": lambda _p, idx, _diag: {"source_id": "s4-expander", "capabilities": [cap_row]} if idx == 0 else None,
                "max_capability_expansions": 1,
                "proposal_provider": lambda _r, _i, _pr: {"candidate": {"answer": 42}},
                "proposal_provider_max_candidates": 1,
            }
        },
    )
    assert v12_res["pass"] is True
    assert v12_res["adaptive_solver_v12"]["pass"] is True
    assert v12_res["adaptive_solver_v12"]["expanded_capability_ids"] == ["expanded-route"]
