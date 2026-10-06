from __future__ import annotations

import ast
import hashlib
import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
SCHEMA = "PROJECT_BRAIN_HONESTY_LOAD_BEARING_BYPASS_VERIFIER_V1"

ASTRA = "canonical/runtime/astra_runtime.py"
ADMIN = "canonical/runtime/root3_typed_durable_admin_write_v1.py"
HONESTY = "canonical/runtime/honesty_envelope_v1.py"
CANDIDATE = "canonical/governance/HONESTY_LOAD_BEARING_PROPAGATION_BYPASS_20261006_V1.json"

EXPECTED = {
    ASTRA: "15dd59ad644c5c73a9218dba4fcc17f880d725f0",
    ADMIN: "6c488b10b8afbaf61781703775cfd9a79710de52",
    HONESTY: "1ff02d62322b76068933498e869b1ee22949b991",
}


def _blob(path: str) -> str:
    data = (ROOT / path).read_bytes()
    return hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()


def _load(path: str) -> dict[str, Any]:
    value = json.loads((ROOT / path).read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError("DOCUMENT_NOT_MAPPING:" + path)
    return value


def _function_source(source: str, name: str) -> str:
    tree = ast.parse(source)
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == name:
            lines = source.splitlines()
            end = int(getattr(node, "end_lineno", node.lineno))
            return "\n".join(lines[node.lineno - 1:end])
    raise ValueError("FUNCTION_NOT_FOUND:" + name)


def evaluate() -> dict[str, Any]:
    errors: list[str] = []
    for path, expected in EXPECTED.items():
        if _blob(path) != expected:
            errors.append("SOURCE_BLOB_DRIFT:" + path)

    astra = (ROOT / ASTRA).read_text(encoding="utf-8")
    admin = (ROOT / ADMIN).read_text(encoding="utf-8")
    candidate = _load(CANDIDATE)

    run_goal_unstamped = _function_source(astra, "_run_goal_unstamped")
    run_goal = _function_source(astra, "run_goal")
    execute_step = _function_source(astra, "execute_step")
    main = _function_source(astra, "main")
    run_shell = _function_source(astra, "run_shell")
    write_statej = _function_source(astra, "write_statej")
    typed_admin_commit = _function_source(astra, "_typed_admin_commit")
    admin_commit = _function_source(admin, "commit")

    if '"stdout":summary' not in run_goal_unstamped:
        errors.append("MODEL_SUMMARY_STDOUT_PATH_NOT_FOUND")
    if '"final_summary":summary' not in run_goal_unstamped:
        errors.append("MODEL_FINAL_SUMMARY_PATH_NOT_FOUND")

    if "honesty_envelope" in run_goal or "honesty_envelope" in execute_step:
        errors.append("HONESTY_ENVELOPE_ALREADY_PRESENT_ON_GOAL_EXECUTION_PATH")
    if "return _stamp_cognition_provenance(_run_goal_unstamped(step, mission))" not in run_goal:
        errors.append("RUN_GOAL_EXPECTED_DIRECT_PROVENANCE_ONLY_PATH_DRIFT")

    if 'return run_goal(step, mission or {})' not in execute_step:
        errors.append("EXECUTE_STEP_GOAL_RESULT_PATH_DRIFT")
    if 'state["history"].append(rec)' not in main:
        errors.append("STATE_HISTORY_RESULT_PERSISTENCE_PATH_NOT_FOUND")
    if "write_statej(state_path,state)" not in main:
        errors.append("STATE_TYPED_PERSISTENCE_PATH_NOT_FOUND")

    for marker in (
        'env[prefix+"RESULT_JSON"]',
        'env[prefix+"BODY"]',
        'env[prefix+"STDOUT"]',
    ):
        if marker not in run_shell:
            errors.append("CROSS_STEP_EXPORT_PATH_NOT_FOUND:" + marker)

    if 'admin_class="ASTRA_STATE_JSON"' not in write_statej:
        errors.append("STATE_TYPED_ADMIN_PATH_DRIFT")
    if '_load_runtime_helper("root3_typed_durable_admin_write_v1")' not in typed_admin_commit:
        errors.append("TYPED_ADMIN_HELPER_PATH_DRIFT")

    if "honesty_envelope" in admin_commit or "honesty_envelope" in admin:
        errors.append("TYPED_ADMIN_WRITE_ALREADY_PERFORMS_HONESTY_MEDIATION")

    # On the exact bound ASTRA bytes, absence is meaningful because the bypass
    # path is direct: goal result -> state history -> typed durable write and
    # declared cross-step exports. No wrapper on that path calls the envelope.
    if "honesty_envelope_v1" in astra or "compile_honesty_envelope" in astra:
        errors.append("ASTRA_NOW_REFERENCES_HONESTY_ENVELOPE__COUNTEREXAMPLE_STALE")

    if candidate.get("falsified_claim") != "HONESTY_UNIVERSAL_EMISSION_MEDIATION_TOTALITY_ON_CURRENT_ASTRA_RUNTIME":
        errors.append("FALSIFIED_CLAIM_ID_DRIFT")

    cut = candidate.get("shared_causal_cut")
    if not isinstance(cut, dict) or cut.get("effect_boundary_claim") != "C_EFFECT_BOUNDARY_CLOSURE_V2":
        errors.append("SHARED_EFFECT_BOUNDARY_BINDING_MISSING")
    if not isinstance(cut, dict) or cut.get("shared_falsifier_class") != "UNMEDIATED_EFFECT_ESCAPE":
        errors.append("SHARED_FALSIFIER_CLASS_MISSING")

    repair = candidate.get("minimum_repair")
    law = repair.get("law") if isinstance(repair, dict) else None
    if not isinstance(law, list) or len(law) < 6:
        errors.append("MINIMUM_REPAIR_LAW_INCOMPLETE")

    for key in (
        "execution_authority",
        "promotion_authority",
        "fresh_reality_authority",
    ):
        if candidate.get(key) is not False:
            errors.append("AUTHORITY_OVERCLAIM:" + key)

    ok = not errors
    return {
        "schema": SCHEMA,
        "status": (
            "PASS__CURRENT_ASTRA_LOAD_BEARING_HONESTY_BYPASS_CONSTRUCTIVELY_LOCALIZED__ZERO_CREDIT"
            if ok else "FAIL_CLOSED"
        ),
        "pass": ok,
        "errors": sorted(set(errors)),
        "current_honesty_mediation_totality_falsified": ok,
        "shared_effect_escape_localized": ok,
        "repair_implemented": False,
        "ledger_completeness_proved": False,
        "effect_boundary_closed": False,
        "acceptance_credit_delta": 0,
        "capability_credit_delta": 0,
        "ownership_credit_delta": 0,
        "execution_authority": False,
        "promotion_authority": False,
        "fresh_reality_authority": False,
    }


if __name__ == "__main__":
    out = evaluate()
    print(json.dumps(out, indent=2, sort_keys=True))
    raise SystemExit(0 if out["pass"] else 1)
