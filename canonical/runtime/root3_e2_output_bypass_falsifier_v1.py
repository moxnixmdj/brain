from __future__ import annotations

import ast
import hashlib
import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
SCHEMA = "PROJECT_BRAIN_ROOT3_E2_OUTPUT_BYPASS_FALSIFIER_V1"

THEOREM = "canonical/governance/ROOT3_ZERO_VIOLATION_COMPLETE_MEDIATION_BREAKTHROUGH_20261005_V1.json"
MONITOR = "canonical/runtime/material_effect_reference_monitor_v1.py"
ASTRA = "canonical/runtime/astra_runtime.py"
HONESTY_GOV = "canonical/governance/HONESTY_EXTERNAL_EMISSION_GATEWAY_V3.json"
HONESTY_RUNTIME = "canonical/runtime/honesty_emission_gateway_v3.py"

EXPECTED = {
    THEOREM: "f1b84e39bb7e4caff9e1b25e02bdfd3beaf31a03",
    MONITOR: "5abf7d4ee927c9b8084eaee08b9e86e28d88aa54",
    ASTRA: "cc389282974e892e323fadd782042ef7f7e9467a",
    HONESTY_GOV: "8dc80de8a8312133f46d8a415c6764d734e3ac30",
    HONESTY_RUNTIME: "39d32d4e73a1542253c541d63d88dc7e4f9193ce",
}


def git_blob_sha(raw: bytes) -> str:
    return hashlib.sha1(
        b"blob " + str(len(raw)).encode("ascii") + b"\0" + raw
    ).hexdigest()


def load_json(rel: str) -> dict[str, Any]:
    obj = json.loads((ROOT / rel).read_text(encoding="utf-8"))
    if not isinstance(obj, dict):
        raise ValueError(rel + ":OBJECT_REQUIRED")
    return obj


def literal_string_set(tree: ast.AST, name: str) -> set[str]:
    for node in getattr(tree, "body", []):
        if isinstance(node, ast.Assign):
            if any(isinstance(t, ast.Name) and t.id == name for t in node.targets):
                value = node.value
                if isinstance(value, (ast.Set, ast.List, ast.Tuple)):
                    out = set()
                    for item in value.elts:
                        if not isinstance(item, ast.Constant) or not isinstance(item.value, str):
                            return set()
                        out.add(item.value)
                    return out
    return set()


def direct_print_sites(tree: ast.AST) -> list[int]:
    out = []
    for node in ast.walk(tree):
        if (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Name)
            and node.func.id == "print"
        ):
            out.append(int(node.lineno))
    return sorted(out)


def evaluate(root: Path = ROOT) -> dict[str, Any]:
    root = Path(root).resolve()
    errors = []
    observed = {}
    for rel, expected in EXPECTED.items():
        actual = git_blob_sha((root / rel).read_bytes())
        observed[rel] = actual
        if actual != expected:
            errors.append("BLOB_DRIFT:" + rel + ":" + actual)

    theorem = load_json(THEOREM)
    honesty = load_json(HONESTY_GOV)
    monitor_text = (root / MONITOR).read_text(encoding="utf-8")
    astra_text = (root / ASTRA).read_text(encoding="utf-8")
    monitor_tree = ast.parse(monitor_text, filename=MONITOR)
    astra_tree = ast.parse(astra_text, filename=ASTRA)

    e_def = str(
        ((theorem.get("theorem") or {}).get("definitions") or {}).get("E") or ""
    )
    if "EXTERNALLY_OBSERVABLE_OR_DURABLE" not in e_def:
        errors.append("THEOREM_EXTERNAL_EFFECT_DEFINITION_DRIFT")

    m1 = next(
        (
            row
            for row in theorem.get("minimum_architectural_cut") or []
            if isinstance(row, dict) and row.get("id") == "M1_EFFECT_BOUNDARY"
        ),
        None,
    )
    if not isinstance(m1, dict) or "USER_VISIBLE_FINAL_OUTPUTS" not in str(
        m1.get("action") or ""
    ):
        errors.append("THEOREM_USER_VISIBLE_OUTPUT_SCOPE_DRIFT")

    sinks = literal_string_set(monitor_tree, "EXPECTED_SINKS")
    if not sinks:
        errors.append("MONITOR_SINK_SET_UNREADABLE")
    if any(
        token in sink
        for sink in sinks
        for token in ("stdout", "stderr", "emission", "user_output")
    ):
        errors.append("MONITOR_NOW_HAS_OUTPUT_SINK__COUNTEREXAMPLE_STALE")

    prints = direct_print_sites(astra_tree)
    if len(prints) != 7:
        errors.append("DIRECT_PRINT_SITE_COUNT_DRIFT:" + str(len(prints)))

    if "honesty_emission_gateway" in astra_text or "honesty_emission_client" in astra_text:
        errors.append("ASTRA_NOW_REFERENCES_HONESTY_EMISSION_GATEWAY")

    remaining = set(str(x) for x in (honesty.get("remaining") or []))
    if "CREDITED_RUNTIME_ENTRY_DOMINANCE" not in remaining:
        errors.append("HONESTY_ENTRY_DOMINANCE_STATE_CHANGED")

    ok = not errors
    return {
        "schema": SCHEMA,
        "status": (
            "PASS__E2_EFFECT_TOTALITY_FALSIFIED_BY_DIRECT_USER_VISIBLE_OUTPUT_BYPASS__ZERO_CREDIT"
            if ok
            else "FAIL_CLOSED"
        ),
        "pass": ok,
        "errors": errors,
        "observed_blobs": observed,
        "direct_print_sites": prints if ok else [],
        "declared_monitor_sinks": sorted(sinks) if ok else [],
        "falsified_root": "E2_EFFECT_TOTALITY" if ok else None,
        "repair_cut": (
            "BIND_ALL_CREDITED_EXTERNAL_OUTPUT_TO_ONE_PRECOMMIT_GATEWAY_OR_ADD_A_COMPLETE_OUTPUT_SINK_TO_THE_SHARED_EFFECT_MEMBRANE"
            if ok
            else None
        ),
        "acceptance_credit_delta": 0,
        "family_credit_delta": 0,
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
