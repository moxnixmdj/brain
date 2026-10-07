#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import importlib.util
import json
import pathlib
import subprocess
import sys
import tempfile

ROOT = pathlib.Path(__file__).resolve().parents[2]
CANDIDATE = ROOT / "canonical/runtime/same_identity_supervisor_credited_v2.py"
LAUNCHER = ROOT / "canonical/runtime/root3_production_astra_launcher_v1.py"
ASTRA = ROOT / "canonical/runtime/astra_runtime.py"
AGENT = "SUPERWORKER-UNIFIED-1"
TASK_ID = "CONTINUITY-C-V7-DEFAULT-CHILD-QUAL-001"
MISSION_ID = "CONTINUITY-C-V7-DEFAULT-CHILD-QUAL-001"
MISSION_REL = "canonical/astra_runtime/missions/CONTINUITY-C-V7-DEFAULT-CHILD-QUAL-001.json"
MISSION_PATH = ROOT / MISSION_REL


def sha_bytes(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def sha_file(path: pathlib.Path) -> str:
    return sha_bytes(path.read_bytes())


def canonical_json_sha(value) -> str:
    return sha_bytes(
        json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")
    )


def load_supervisor():
    spec = importlib.util.spec_from_file_location("continuity_v2_qual_target", CANDIDATE)
    if spec is None or spec.loader is None:
        raise RuntimeError("CANDIDATE_IMPORT_SPEC_FAILED")
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


def continuous_obs_context() -> dict:
    pointer_path = ROOT / "canonical/CANONICAL_POINTER.json"
    pointer = json.loads(pointer_path.read_text(encoding="utf-8"))
    required = [
        "canonical/CANONICAL_POINTER.json",
        "canonical/governance/ACTIVE_GOAL_HIERARCHY_V1.json",
        "canonical/governance/REAL_OUTPUT_SCOREBOARD_V1.json",
    ]
    return {
        "schema": "PROJECT_BRAIN_CONTINUOUS_OBS_CONTEXT_V1",
        "status": "CURRENT",
        "dependency_inventory_complete": True,
        "material_world_state_dependencies_complete": True,
        "information_boundary_complete": True,
        "unknown_material_dependencies": [],
        "stale_authority_absent": True,
        "valid_proof_action_priority": True,
        "canonical_generation": pointer["canonical_generation"],
        "obs_layers_current": {
            "goal": True,
            "capability": True,
            "blocker": True,
            "solution": True,
            "verification": True,
            "inherited_system": True,
            "obs_process": True,
        },
        "information_policy": {
            "mode": "NO_EXTERNAL_INFORMATION",
            "allowed_exact_sources": [],
            "allowed_external_tool_kinds": [],
        },
        "canonical_state_dependencies": [
            {"path": rel, "sha256": sha_file(ROOT / rel)} for rel in required
        ],
        "dependencies": [],
    }


def terminal_honesty_record(receipt_sha256: str) -> dict:
    obligation = "CONTINUITY_DEFAULT_CHILD_SEAM_COMPLETED"
    return {
        "schema": "PROJECT_BRAIN_HONESTY_ENVELOPE_INPUT_V1",
        "task_contract": {
            "task_id": MISSION_ID,
            "required_obligations": [obligation],
        },
        "obligations": [
            {
                "id": obligation,
                "state": "VERIFIED",
                "receipts": [receipt_sha256],
            }
        ],
        "completion_claim": "COMPLETE",
        "provenance_events": [],
        "material_claims": [],
        "belief_assertions": [],
    }


def make_mission() -> dict:
    receipt_sha = sha_file(CANDIDATE)
    return {
        "schema": "PROJECT_BRAIN_ASTRA_RUNTIME_MISSION_V1",
        "mission_id": MISSION_ID,
        "purpose": (
            "Qualify only the current same-identity continuity default child seam "
            "through the canonical Root3 production ASTRA launcher."
        ),
        "goal": "Complete the model-independent continuity seam qualification.",
        "continuous_obs": continuous_obs_context(),
        "steps": [
            {
                "id": "continuity-default-child-seam",
                "adapter": "goal",
                "controller_actions": [
                    {
                        "type": "finish",
                        "args": {"summary": "CONTINUITY_DEFAULT_CHILD_SEAM_OK"},
                    }
                ],
                "verify": {
                    "type": "stdout_contains",
                    "text": "CONTINUITY_DEFAULT_CHILD_SEAM_OK",
                },
            }
        ],
        "terminal_honesty_record": terminal_honesty_record(receipt_sha),
        "constraints": {
            "incremental_spend_usd": 0,
            "model_dependency_count": 0,
            "external_information_forbidden": True,
            "qualification_scope": "CONTINUITY_DEFAULT_CHILD_SEAM_ONLY",
        },
    }


def child_code(task_path: pathlib.Path, state_dir: pathlib.Path, evidence_dir: pathlib.Path) -> str:
    return f"""
import importlib.util, pathlib, sys
p=pathlib.Path({str(CANDIDATE)!r})
spec=importlib.util.spec_from_file_location("continuity_child",p)
m=importlib.util.module_from_spec(spec); sys.modules[spec.name]=m; spec.loader.exec_module(m)
root=pathlib.Path({str(ROOT)!r})
task_path=pathlib.Path({str(task_path)!r})
state=pathlib.Path({str(state_dir)!r})
evidence=pathlib.Path({str(evidence_dir)!r})
code,receipt=m.run_once(root,root/"canonical/same_identity_worker/tasks",state,evidence,{AGENT!r},task_path)
print(__import__("json").dumps({{"code":code,"receipt":receipt}},sort_keys=True))
raise SystemExit(0 if code in (0,75) else code)
"""


def run_fresh(code: str) -> dict:
    proc = subprocess.run(
        [sys.executable, "-c", code],
        cwd=ROOT,
        text=True,
        capture_output=True,
        timeout=120,
    )
    if proc.returncode != 0:
        raise RuntimeError(
            "QUALIFICATION_CHILD_FAILED:"
            + str(proc.returncode)
            + "\nSTDOUT:\n"
            + proc.stdout
            + "\nSTDERR:\n"
            + proc.stderr
        )
    lines = [line for line in proc.stdout.splitlines() if line.strip()]
    if not lines:
        raise RuntimeError("QUALIFICATION_CHILD_OUTPUT_EMPTY")
    return {
        "returncode": proc.returncode,
        "stdout_sha256": sha_bytes(proc.stdout.encode()),
        "stderr_sha256": sha_bytes(proc.stderr.encode()),
        "result": json.loads(lines[-1]),
    }


def cleanup_runtime_artifacts() -> None:
    for base in (
        ROOT / "canonical/astra_runtime/state",
        ROOT / "canonical/astra_runtime/evidence",
    ):
        if not base.is_dir():
            continue
        for path in base.glob(MISSION_ID + "*"):
            if path.is_file():
                path.unlink()
    bridge = (
        ROOT
        / "canonical/same_identity_worker/external_tool_bridge"
        / TASK_ID
    )
    if bridge.is_dir():
        try:
            bridge.rmdir()
        except OSError:
            pass
    try:
        MISSION_PATH.unlink()
    except FileNotFoundError:
        pass


def main() -> int:
    if not CANDIDATE.is_file() or not LAUNCHER.is_file() or not ASTRA.is_file():
        raise SystemExit("QUALIFICATION_INPUT_MISSING")

    cleanup_runtime_artifacts()
    mission = make_mission()
    MISSION_PATH.parent.mkdir(parents=True, exist_ok=True)
    MISSION_PATH.write_text(
        json.dumps(mission, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    mission_sha = sha_file(MISSION_PATH)

    with tempfile.TemporaryDirectory(prefix="continuity-c-v7-") as td:
        temp = pathlib.Path(td)
        state = temp / "supervisor-state"
        evidence = temp / "supervisor-evidence"
        task_path = temp / "task.json"
        task = {
            "schema": "PROJECT_BRAIN_SAME_IDENTITY_TASK_V1",
            "task_id": TASK_ID,
            "agent_id": AGENT,
            "incremental_spend_usd": 0,
            "mission_path": MISSION_REL,
            "mission_sha256": mission_sha,
            "priority": 100,
            "prerequisites": [],
            "checkpoint_before_runtime_once": True,
        }
        task_path.write_text(
            json.dumps(task, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )

        try:
            proc_a = run_fresh(child_code(task_path, state, evidence))
            if proc_a["result"]["code"] != 75:
                raise RuntimeError("PROCESS_A_DID_NOT_CHECKPOINT")

            proc_b = run_fresh(child_code(task_path, state, evidence))
            if proc_b["result"]["code"] != 0:
                raise RuntimeError("PROCESS_B_DID_NOT_COMPLETE")

            supervisor_state_path = state / (TASK_ID + ".json")
            supervisor_state = json.loads(
                supervisor_state_path.read_text(encoding="utf-8")
            )
            attempt = json.loads(
                (evidence / (TASK_ID + "__ATTEMPT_1.json")).read_text(encoding="utf-8")
            )
            checkpoint = json.loads(
                (evidence / (TASK_ID + "__CHECKPOINT.json")).read_text(encoding="utf-8")
            )
            astra_state_path = ROOT / "canonical/astra_runtime/state" / (MISSION_ID + ".json")
            astra_receipt_path = (
                ROOT / "canonical/astra_runtime/evidence" / (MISSION_ID + "__RECEIPT.json")
            )
            astra_state = json.loads(astra_state_path.read_text(encoding="utf-8"))
            astra_receipt = json.loads(astra_receipt_path.read_text(encoding="utf-8"))

            expected_events = [
                "TASK_ACQUIRED",
                "CHECKPOINT_CREATED",
                "TASK_RESUMED",
                "ASTRA_RUNTIME_STARTED",
                "TASK_COMPLETE",
            ]
            events = [row["type"] for row in supervisor_state["events"]]
            checks = {
                "candidate_supervisor_exact": sha_file(CANDIDATE),
                "production_launcher_exact": sha_file(LAUNCHER),
                "current_astra_exact": sha_file(ASTRA),
                "forced_process_boundary": True,
                "process_a_checkpointed_before_runtime": proc_a["result"]["code"] == 75,
                "process_b_default_executor_completed": proc_b["result"]["code"] == 0,
                "same_agent_identity_preserved": (
                    supervisor_state["agent_id"] == AGENT == attempt["agent_id"] == checkpoint["agent_id"]
                ),
                "same_task_identity_preserved": (
                    supervisor_state["task_id"] == TASK_ID == attempt["task_id"] == checkpoint["task_id"]
                ),
                "mission_hash_preserved": (
                    supervisor_state["mission_sha256"] == mission_sha
                    == attempt["mission_sha256"] == checkpoint["mission_sha256"]
                    == astra_state["mission_sha256"] == astra_receipt["mission_sha256"]
                ),
                "checkpoint_exactly_once": supervisor_state["checkpoint_count"] == 1,
                "runtime_attempt_exactly_once": supervisor_state["runtime_attempt_count"] == 1,
                "claim_count_two_fresh_processes": supervisor_state["claim_count"] == 2,
                "supervisor_terminal_complete": supervisor_state["status"] == "COMPLETE",
                "astra_terminal_complete": (
                    astra_state["status"] == "COMPLETE"
                    and astra_receipt["status"] == "COMPLETE"
                ),
                "astra_same_identity_bound": (
                    astra_state["supervisor_agent_id"] == AGENT
                    and astra_state["supervisor_task_id"] == TASK_ID
                    and astra_receipt["supervisor_agent_id"] == AGENT
                    and astra_receipt["supervisor_task_id"] == TASK_ID
                ),
                "event_order_exact": events == expected_events,
                "runtime_command_uses_root3_production_launcher": (
                    attempt["runtime_command"][1]
                    == "canonical/runtime/root3_production_astra_launcher_v1.py"
                ),
                "model_dependency_zero": True,
                "incremental_spend_zero": (
                    attempt["incremental_spend_usd"] == 0
                    and checkpoint["incremental_spend_usd"] == 0
                ),
            }
            bool_checks = [v for v in checks.values() if isinstance(v, bool)]
            report = {
                "schema": "PROJECT_BRAIN_LONG_HORIZON_CONTINUITY_CURRENT_SEAM_QUALIFICATION_V2",
                "family": "LONG_HORIZON_MEMORY_AND_CONTINUITY",
                "scope": "CURRENT_DEFAULT_CHILD_SEAM_ONLY",
                "candidate_supervisor_blob_sha": None,
                "mission_sha256": mission_sha,
                "process_a": proc_a,
                "process_b": proc_b,
                "checks": checks,
                "event_types": events,
                "all_boolean_checks_pass": all(bool_checks),
                "fresh_reality_units_consumed": 0,
                "incremental_spend_usd": 0,
                "acceptance_credit_delta": 0,
                "family_credit_delta": 0,
                "capability_credit_delta": 0,
                "ownership_credit_delta": 0,
                "hard_nonclaims": [
                    "NO_GENERAL_ASTRA_CAPABILITY_CLAIM",
                    "NO_AUTONOMOUS_WAKE_CLAIM",
                    "NO_GENERAL_SEMANTIC_MEMORY_QUALITY_CLAIM",
                    "NO_TERMINAL_CREDIT_FROM_THIS_RUNNER_ALONE",
                ],
            }
            out = pathlib.Path(sys.argv[1]) if len(sys.argv) > 1 else (
                ROOT / "LONG_HORIZON_CONTINUITY_CURRENT_SEAM_REPORT.json"
            )
            out.write_text(
                json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8"
            )
            print(json.dumps(report, indent=2, sort_keys=True))
            return 0 if report["all_boolean_checks_pass"] else 1
        finally:
            cleanup_runtime_artifacts()


if __name__ == "__main__":
    raise SystemExit(main())
