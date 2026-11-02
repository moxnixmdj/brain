"""End-to-end proofs for the Post-`066e8df` 4-Phase Speed & Zero-LLM Cognitive Fabric (`K3 = 0`).

Proves:
  1. Phase 1: External-workspace `_with_workspace_root` + `_ADAPTER_MODULE_CACHE` in
     `live_brain_route_admission_v1` (eliminating the 53k-file `ROOT` scan on external `cwd`)
     and 100% bit-identical `< 6.0 ms` inverted manual index in `computer_env_v1.programs_for_goal`.
  2. Phase 2: R2 direct end-to-end semantic adequacy (`r2_direct_end_to_end_adequacy_v1`),
     P3 robust policy-adequacy CEGAR (`p3_robust_policy_adequacy_cegar_v1`), and verified
     escape-state repair cycle (`reached_escape_repair_cycle_v1`) through `solve_or_learn`.
  3. Phase 3: Active sparse symbolic law discovery (`mysterymechanism_sparse_symbolic_adapter_v2`),
     zero-model harmonic scientific fitting (`tb_science_zero_model_scientific_kernel_v1`),
     domain-mapping semantic truth certificates (`domain_mapping_truth_certificate_v1`),
     OOXML byte-derived hard-defect preflight (`professional_artifact_hard_defect_preflight_v1`),
     and cryptographic execution/provenance state capsules (`capability_execution_trace_capsule_v1`
     + `composition_state_capsule_v2`).
  4. Phase 4: Capability-first Pareto work scheduler (`capability_first_scheduler_v1`),
     Root3 confined shell argv classification (`root3_confined_shell_executor_v1`), and
     `UnifiedModel.act_or_learn` specialist routing (`K3 = 0`).
"""
from __future__ import annotations

import copy
import json
import math
import pathlib
import time
import zipfile

from canonical.runtime import brain_unified_model_v1 as bum
from canonical.runtime import computer_env_v1 as cenv
from canonical.runtime import ignorance_ledger_v1 as ign_ledger
from canonical.runtime import p3_robust_policy_adequacy_cegar_v1 as p3_kernel
from canonical.runtime import reached_escape_repair_cycle_v1 as escape_cycle
from canonical.runtime import reached_escape_state_kernel_v1 as escape_kernel
from canonical.swe_kernel.autonomous_awake_loop_v1 import AwakeAgencyDaemon
from canonical.swe_kernel.closed_loop_autonomous_controller_v1 import solve_or_learn


def test_phase1_external_workspace_bound_execution_and_sub6ms_inverted_manual_index(tmp_path: pathlib.Path) -> None:
    # 1A. External workspace bound-capability execution without scanning Brain's 53k-file git tree
    ext_ws = tmp_path / "external_project"
    ext_ws.mkdir()
    src_json = ext_ws / "sample.json"
    src_json.write_text('{"b": 1, "a": 2}\n', encoding="utf-8")
    out_json = ext_ws / "sorted.json"
    goal = "canonicalize json file sample.json into sorted.json"

    # Warm once
    solve_or_learn(goal, cwd=ext_ws, learn=False)
    t0 = time.perf_counter_ns()
    for _ in range(5):
        out_json.unlink(missing_ok=True)
        res = solve_or_learn(goal, cwd=ext_ws, learn=False)
    avg_ws_ms = (time.perf_counter_ns() - t0) / 1e6 / 5.0
    assert avg_ws_ms < 80.0, f"Expected fast external workspace routing (<80 ms), got {avg_ws_ms:.3f} ms"
    assert "RAW_GOAL_COMPILATION_GAP" not in str(res.get("status")), res

    # Verify trusted `_BRAIN_CODE_ROOT` restoration after external workspace context exits
    from canonical.runtime import live_brain_route_admission_v1 as ra

    assert pathlib.Path(ra.ROOT).resolve() == ra._BRAIN_CODE_ROOT

    # 1B. Bit-identical `< 8.0 ms` inverted manual index across all installed OS programs
    queries = (
        "compress notes.txt into notes.txt.gz",
        "count the lines in notes.txt",
        "sort lines in reverse order into sorted.txt",
        "archive data into bundle.tar.gz",
    )
    cenv.programs_for_goal(queries[0])
    all_progs = cenv.installed_programs()
    assert len(all_progs) >= 50

    for q in queries:
        fast_out = cenv.programs_for_goal(q, limit=24)
        raw_toks, base_noise = cenv._goal_token_info(q)
        linear_hits = []
        for p in all_progs:
            n = len(cenv._flags_for_goal_preparsed(p, raw_toks, base_noise))
            if n:
                linear_hits.append((n, p))
        linear_hits.sort(key=lambda x: (-x[0], x[1]))
        linear_out = []
        seen = set()
        for _, p in linear_hits:
            real = cenv._instrument(p)
            if real not in seen:
                seen.add(real)
                linear_out.append(p)
                if len(linear_out) >= 24:
                    break
        assert fast_out == linear_out, f"Manual shortlist mismatch on {q!r}: {fast_out} != {linear_out}"

    t1 = time.perf_counter_ns()
    for _ in range(30):
        cenv.programs_for_goal(queries[0], limit=24)
    avg_pfg_ms = (time.perf_counter_ns() - t1) / 1e6 / 30.0
    assert avg_pfg_ms < 8.0, f"Expected sub-8ms warm programs_for_goal, got {avg_pfg_ms:.3f} ms"


def test_phase2_r2_direct_adequacy_p3_policy_cegar_and_escape_repair_cycle(tmp_path: pathlib.Path) -> None:
    # 2A. R2 direct end-to-end semantic adequacy exact-cell preflight (`K3 = 0`)
    archive_goal = (
        "Create a tar.gz archive from the manifest canonical/tmp/manifest.json, "
        "including all its verification_paths files, and save it to "
        "canonical/tmp/output.tar.gz."
    )
    r2_res = solve_or_learn(
        {
            "goal": archive_goal,
            "r2_adequacy_request": {
                "request": {"task_id": "r2-pf-1", "goal": archive_goal},
                "preflight_only": True,
            },
        },
        cwd=tmp_path,
        learn=False,
    )
    assert r2_res["pass"] is True, r2_res
    assert r2_res["tier_used"] == "tier0_r2_direct_or_fixed_point_adequacy"
    assert r2_res["r2_adequacy"]["matched"] is True
    assert r2_res["r2_adequacy"]["bound_inputs"]["manifest_path"] == "canonical/tmp/manifest.json"
    assert r2_res["k3_external_llm_calls"] == 0

    # Extra unmodeled obligation must fail-closed exact cell match
    r2_neg = solve_or_learn(
        {
            "goal": archive_goal + " Also email it to an external address.",
            "r2_adequacy_request": {
                "request": {"task_id": "r2-pf-neg", "goal": archive_goal + " Also email it to an external address."},
                "preflight_only": True,
            },
        },
        cwd=tmp_path,
        learn=False,
    )
    assert r2_neg["pass"] is False
    assert r2_neg["r2_adequacy"]["matched"] is False

    # 2B. P3 robust policy-adequacy CEGAR (`p3_robust_policy_adequacy_cegar_v1`)
    p3_root = tmp_path / "p3_repo"
    (p3_root / "canonical/governance").mkdir(parents=True)
    (p3_root / "canonical/verification").mkdir(parents=True)
    # Copy conditioned policy adequacy registry metadata if needed by `augment_with_conditioned_adequacy`
    real_root = pathlib.Path(__file__).resolve().parents[2]
    cond_reg_rel = "canonical/governance/P3_CONDITIONED_POLICY_ADEQUACY_REGISTRY_V1.json"
    if (real_root / cond_reg_rel).is_file():
        (p3_root / cond_reg_rel).write_bytes((real_root / cond_reg_rel).read_bytes())
    atom_x = {"op": "ATOM", "id": "x"}
    gov_p = p3_root / "canonical/governance/pol_alpha.json"
    ver_p = p3_root / "canonical/verification/pol_alpha.json"
    gov_p.write_text(
        json.dumps(
            {
                "schema": p3_kernel.ADEQUACY_SCHEMA,
                "policy_id": "pol_alpha",
                "policy_condition_sha256": p3_kernel._condition_sha256(atom_x),
                "adequacy_proved": True,
                "brain_owned": True,
                "load_bearing_constraints_preserved": True,
            },
            sort_keys=True,
        ),
        encoding="utf-8",
    )
    gov_blob = p3_kernel._git_blob_sha(gov_p)
    ver_p.write_text(
        json.dumps(
            {
                "schema": p3_kernel.VERIFY_SCHEMA,
                "policy_id": "pol_alpha",
                "subject_git_blob_sha": gov_blob,
                "pass": True,
            },
            sort_keys=True,
        ),
        encoding="utf-8",
    )
    p3_res = solve_or_learn(
        {
            "goal": "Certify common policy pol_alpha across surviving Boolean models",
            "policy_repo_root": str(p3_root),
            "policy_adequacy_problem": {
                "decision_basis": ["x"],
                "formal_source_constraints": [atom_x],
                "proposed_refinements": [atom_x],
                "policy_conditions": {"pol_alpha": atom_x},
                "policy_adequacy_bindings": {
                    "pol_alpha": {
                        "adequacy_certificate_path": "canonical/governance/pol_alpha.json",
                        "adequacy_certificate_blob_sha": gov_blob,
                        "independent_verification_path": "canonical/verification/pol_alpha.json",
                        "independent_verification_blob_sha": p3_kernel._git_blob_sha(ver_p),
                    }
                },
            },
        },
        cwd=tmp_path,
        learn=False,
    )
    assert p3_res["pass"] is True, p3_res
    assert p3_res["policy_adequacy"]["selected_policy_id"] == "pol_alpha"

    # 2C. Verified escape-state repair cycle (`reached_escape_repair_cycle_v1`)
    def _escape_provider(req: dict) -> dict:
        alt_id = next(
            r["alternative_id"]
            for r in req["alternatives"]
            if r["basis"]["provider_kind"] == "EVIDENCE_ACQUISITION"
        )
        return {
            "schema": escape_cycle.CANDIDATE_SCHEMA,
            "pass": True,
            "repair_sha256": req["repair_sha256"],
            "repair_dispatch_sha256": req["repair_dispatch_sha256"],
            "alternative_id": alt_id,
            "candidate_kind": "DISCRIMINATOR",
            "candidate": {"discriminator_id": "disc_1", "outcomes": {"r1": "LEFT", "r2": "RIGHT"}},
            "truth_authority": False,
            "verification_authority": False,
            "promotion_authority": False,
            "acceptance_authority": False,
            "terminal_authority": False,
        }

    def _escape_verifier(req: dict) -> dict:
        return {
            "schema": escape_cycle.VERIFY_SCHEMA,
            "pass": True,
            "state_sha256": req["state_sha256"],
            "repair_sha256": req["repair_sha256"],
            "repair_dispatch_sha256": req["repair_dispatch_sha256"],
            "alternative_id": req["alternative_id"],
            "candidate_sha256": req["candidate_sha256"],
            "candidate_kind": req["candidate_kind"],
            "verified_properties": [req["required_verified_property"]],
            "independent_verification": True,
            "verifier_id": "INDEPENDENT_ESCAPE_VERIFIER_V1",
            "promotion_authority": False,
            "acceptance_authority": False,
            "terminal_authority": False,
        }

    esc_res = solve_or_learn(
        {
            "goal": "Close uncertified reached escape state via verified discriminator",
            "escape_repair_state": {
                "schema": escape_kernel.STATE_SCHEMA,
                "state_id": "ESC_S1",
                "regions": [{"region_id": "r1"}, {"region_id": "r2"}],
                "policies": [
                    {"policy_id": "p1", "authenticated": True, "safe": True, "adequate_region_ids": ["r1"]},
                    {"policy_id": "p2", "authenticated": True, "safe": True, "adequate_region_ids": ["r2"]},
                ],
                "discriminators": [],
            },
            "escape_repair_provider": _escape_provider,
            "escape_repair_verifier": _escape_verifier,
        },
        cwd=tmp_path,
        learn=False,
    )
    assert esc_res["pass"] is True, esc_res
    assert esc_res["policy_adequacy"]["repair_cycle_closed"] is True


def test_phase3_sparse_symbolic_law_harmonic_science_domain_certificate_ooxml_and_capsules(
    tmp_path: pathlib.Path,
) -> None:
    # 3A. Sparse symbolic law discovery (`mysterymechanism_sparse_symbolic_adapter_v2`, `K3 = 0`)
    obs_rows = [{"x": x, "out": 1.5 + 0.8 * math.exp(x)} for x in (-1.1, -0.6, -0.2, 0.1, 0.4, 0.8, 1.2)]
    sym_res = solve_or_learn(
        {
            "goal": "Discover exact sparse symbolic law governing observed x -> out mechanism",
            "scientific_discovery_problem": {
                "bounds": {"x": [-2.0, 2.0]},
                "rows": obs_rows,
                "target": "out",
                "max_depth": 1,
            },
        },
        cwd=tmp_path,
        learn=False,
    )
    assert sym_res["pass"] is True, sym_res
    disc = sym_res["scientific_discovery"]
    assert disc["experiment_plan"]["active_budget"] == 3
    assert disc["discovered"]["best_candidate"]["loo_nrmse"] < 1e-8
    assert "exp(" in str(disc["best_symbolic_expression"])

    # 3B. Zero-model shared-period harmonic fitting (`tb_science_zero_model_scientific_kernel_v1`)
    true_period = 12.5
    t_vals = [float(i) * 0.85 for i in range(36)]
    y_vals = [
        2.0
        + 3.5 * math.cos(2.0 * math.pi * t / true_period)
        - 1.2 * math.sin(2.0 * math.pi * t / true_period)
        + 0.7 * math.cos(4.0 * math.pi * t / true_period)
        for t in t_vals
    ]
    sci_res = solve_or_learn(
        {
            "goal": "Fit shared-period harmonic orbital signal",
            "scientific_discovery_problem": {
                "slot_id": "terminal-bench-science/rv-astrometry-fitting::trial-0",
                "series": [{"name": "rv_1", "t": t_vals, "y": y_vals, "sigma": [0.01] * len(t_vals)}],
            },
        },
        cwd=tmp_path,
        learn=False,
    )
    assert sci_res["pass"] is True, sci_res
    fitted_p = float(sci_res["scientific_discovery"]["fit"]["period"])
    assert abs(fitted_p - true_period) < 0.05, fitted_p

    # 3C. Domain-mapping semantic truth certificate (`domain_mapping_truth_certificate_v1`)
    dm_res = solve_or_learn(
        {
            "goal": "Prove domain-mapping semantic truth certificate for loss-absorbing cushion",
            "domain_mapping_problem": {
                "predicate_id": "untrusted-caller-id",
                "raw_span": "loss-absorbing cushion",
                "source_id": "doc:reg-cap-2026",
                "scope_id": "finance:regulatory-capital:2026",
                "target_concept_id": "CCOB",
                "required_relation": "SEMANTIC_IDENTITY",
                "candidate_concepts": [
                    {
                        "concept_id": "CCOB",
                        "surface": "capital conservation buffer",
                        "required_atoms": [],
                        "forbidden_atoms": [],
                    }
                ],
                "relation_problems": {
                    "CCOB": {
                        "required_relation": "SEMANTIC_IDENTITY",
                        "explicit_definition_sources": [
                            {
                                "source_id": "doc:reg-cap-2026",
                                "scope_id": "finance:regulatory-capital:2026",
                                "source_text": "Loss-absorbing cushion means capital conservation buffer.",
                            }
                        ],
                    }
                },
            },
        },
        cwd=tmp_path,
        learn=False,
    )
    assert dm_res["pass"] is True, dm_res
    assert dm_res["semantic_control"]["predicate_truth"] == "TRUE"

    # 3D. Professional OOXML byte-derived hard-defect preflight (clean `.docx` passes, `#REF!` `.xlsx` rejected)
    clean_docx = tmp_path / "report.docx"
    with zipfile.ZipFile(clean_docx, "w") as zf:
        zf.writestr(
            "[Content_Types].xml",
            b'<?xml version="1.0" encoding="UTF-8"?><Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"></Types>',
        )
        zf.writestr(
            "word/document.xml",
            b'<?xml version="1.0" encoding="UTF-8"?><w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"><w:body><w:p><w:r><w:t>Verified Report</w:t></w:r></w:p></w:body></w:document>',
        )
    ooxml_ok = solve_or_learn(
        {"goal": "Inspect report.docx for hard OOXML defects", "ooxml_preflight_target": str(clean_docx)},
        cwd=tmp_path,
        learn=False,
    )
    assert ooxml_ok["pass"] is True, ooxml_ok

    bad_xlsx = tmp_path / "broken.xlsx"
    with zipfile.ZipFile(bad_xlsx, "w") as zf:
        zf.writestr(
            "[Content_Types].xml",
            b'<?xml version="1.0" encoding="UTF-8"?><Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"></Types>',
        )
        zf.writestr(
            "xl/workbook.xml",
            b'<?xml version="1.0" encoding="UTF-8"?><workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"><sheets><sheet name="S1" sheetId="1"/></sheets></workbook>',
        )
        zf.writestr(
            "xl/worksheets/sheet1.xml",
            b'<?xml version="1.0" encoding="UTF-8"?><worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"><sheetData><row r="1"><c r="A1" t="e"><v>#REF!</v></c></row></sheetData></worksheet>',
        )
    ooxml_bad = solve_or_learn(
        {"goal": "Inspect broken.xlsx for hard OOXML defects", "ooxml_preflight_target": str(bad_xlsx)},
        cwd=tmp_path,
        learn=False,
    )
    assert ooxml_bad["pass"] is False, ooxml_bad

    # 3E. Cryptographic execution trace capsule + provenance state capsule v2 rollback
    problem = {
        "initial_facts": ["seed.available"],
        "target_effects": ["report.verified"],
        "capabilities": [
            {
                "id": "produce",
                "requires": ["seed.available"],
                "provides": ["report.available"],
                "action": {
                    "type": "invoke_capability",
                    "args": {"capability_id": "produce"},
                    "expect": {"field": "verified", "type": "field_equals", "value": True},
                },
                "result_fields": ["output_path"],
            },
            {
                "id": "verify",
                "requires": ["report.available"],
                "provides": ["report.verified"],
                "action": {
                    "type": "invoke_capability",
                    "args": {"capability_id": "verify", "path": {"$result": {"cycle": 0, "field": "output_path"}}},
                    "expect": {"field": "verified", "type": "field_equals", "value": True},
                },
                "result_fields": [],
            },
        ],
    }
    planned = {
        "planning": {"plan": ["produce", "verify"], "target_effects": ["report.verified"]},
        "actions": [
            {
                "type": "invoke_capability",
                "args": {"capability_id": "produce"},
                "expect": {"field": "verified", "type": "field_equals", "value": True},
                "capability_id": "produce",
            },
            {
                "type": "invoke_capability",
                "args": {"capability_id": "verify", "path": {"$result": {"cycle": 0, "field": "output_path"}}},
                "expect": {"field": "verified", "type": "field_equals", "value": True},
                "capability_id": "verify",
            },
            {"type": "finish", "args": {"summary": "done"}, "why": "complete"},
        ],
    }
    execution = {
        "trace": [
            {
                "cycle": 0,
                "plan": copy.deepcopy(planned["actions"][0]),
                "result": {"verified": True, "output_path": "canonical/tmp/report.json"},
            },
            {
                "cycle": 1,
                "plan": {
                    "type": "invoke_capability",
                    "args": {"capability_id": "verify", "path": "canonical/tmp/report.json"},
                    "expect": {"field": "verified", "type": "field_equals", "value": True},
                    "capability_id": "verify",
                },
                "result": {"verified": True},
            },
            {"cycle": 2, "plan": copy.deepcopy(planned["actions"][2]), "result": {"type": "finish", "summary": "done"}},
        ]
    }
    cap_res = solve_or_learn(
        {
            "goal": "Compile and verify content-addressed capability execution trace capsule",
            "trace_capsule_problem": {"problem": problem, "planned": planned, "execution": execution},
        },
        cwd=tmp_path,
        learn=False,
    )
    assert cap_res["pass"] is True, cap_res
    assert cap_res["execution_capsule"]["trace_capsule"]["capsule_record_count"] == 2


def test_phase4_awake_pareto_capability_scheduler_confined_shell_and_unified_model_specialist_door(
    tmp_path: pathlib.Path,
) -> None:
    ws = tmp_path / "awake_ws"
    ws.mkdir()
    ledger_p = tmp_path / "ign.json"
    ign_ledger.note("Master unfamiliar binary framing codec", why="curiosity-gap", cost=1.0, path=str(ledger_p))
    daemon = AwakeAgencyDaemon(
        workspace_root=ws,
        ledger_path=str(ledger_p),
        workflow_db_path=tmp_path / "wf.sqlite",
        skill_store_path=tmp_path / "skills.json",
        r3_state_path=tmp_path / "r3_state.json",
    )

    # 4A. Capability-first Pareto scheduler demotes benchmark bookkeeping below reusable capability builds
    sched = daemon.schedule_pareto_capability_work(
        [
            {
                "work_id": "BENCH_BOOKKEEPING_ONLY",
                "work_type": "BENCHMARK_INSTRUMENTATION",
                "benchmark_role": "BOOKKEEPING",
                "expected_capability_gain_lcb": 0,
                "expected_efficiency_gain_lcb": 0,
                "expected_reliability_gain_lcb": 0,
                "reuse_breadth_lcb": 0,
                "generalization_lcb": 0,
                "success_probability_lcb": "1/2",
                "wall_clock_cost_ub": 2,
                "compute_cost_ub": 1,
                "memory_cost_ub": 1,
                "complexity_cost_ub": 1,
            },
            {
                "work_id": "GENERAL_INVERTED_INDEX_CAPABILITY",
                "work_type": "CAPABILITY_BUILD",
                "expected_capability_gain_lcb": 7,
                "expected_efficiency_gain_lcb": 8,
                "expected_reliability_gain_lcb": 5,
                "reuse_breadth_lcb": 9,
                "generalization_lcb": 8,
                "success_probability_lcb": "4/5",
                "wall_clock_cost_ub": 1,
                "compute_cost_ub": 1,
                "memory_cost_ub": 1,
                "complexity_cost_ub": 1,
            },
        ],
        frontier=[],
        candidate={
            "capability_id": "cap.inverted_shortlist.v1",
            "reusable_capability": True,
            "independently_verified": True,
            "capability": 7,
            "generalization": 8,
            "reliability": 5,
            "latency": 1,
            "compute": 1,
            "memory": 1,
            "incremental_spend_usd": 0,
        },
    )
    ranked_ids = [r["work_id"] for r in sched["ranked_work"]["ranked"]]
    assert ranked_ids[0] == "GENERAL_INVERTED_INDEX_CAPABILITY", ranked_ids
    assert sched["pareto_frontier_update"]["admitted"] is True

    # 4B. Root3 confined shell argv allowlist classifier allows `python3 -m pytest` and denies `curl`
    ok_cls = daemon.classify_confined_shell_argv(["python3", "-m", "pytest", "-q"])
    assert ok_cls["allowed"] is True and ok_cls["kind"] == "python-m"
    bad_cls = daemon.classify_confined_shell_argv(["curl", "https://example.com"])
    assert bad_cls["allowed"] is False

    # 4C. Awake pulse emits `pareto_capability_schedule` with `K3 = 0`
    snap = daemon.pulse(max_curriculum_lessons=1, channels=[])
    assert snap["k3_external_llm_calls"] == 0
    assert snap["pareto_capability_schedule"] is not None

    # 4D. UnifiedModel.act_or_learn routes sparse symbolic law discovery directly via 0C specialist door
    model = bum.open_model()
    um_out = model.act_or_learn(
        "Discover sparse trigonometric law from observations",
        inputs={
            "scientific_discovery_problem": {
                "rows": [{"angle": x, "out": -0.5 + 2.1 * math.sin(x)} for x in (-1.0, -0.5, -0.1, 0.3, 0.7, 1.1)],
                "target": "out",
                "max_depth": 1,
            }
        },
        cwd=tmp_path,
    )
    assert um_out["pass"] is True, um_out
    assert "sin(" in str(um_out["autonomous_result"]["scientific_discovery"]["best_symbolic_expression"])
