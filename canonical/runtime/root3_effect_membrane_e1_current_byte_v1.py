from __future__ import annotations

import ast
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ASTRA = "canonical/runtime/astra_runtime.py"
WRAPPER = "canonical/runtime/astra_mediated_runtime_v1.py"
MONITOR = "canonical/runtime/material_effect_reference_monitor_v1.py"

EXPECTED_BLOBS = {
    # 2026-11-01: astra_runtime.py rebound to the current blob
    # aa91d571a881d4ff97d30d2c1386fa10439434d9 (already pinned as current by the
    # 2026-10-06/2026-10-11 verification receipts). Signatures, channels and
    # sinks re-measured unchanged on the same date.
    ASTRA: "aa91d571a881d4ff97d30d2c1386fa10439434d9",
    WRAPPER: "eec2aaf7076e3bd2374ee581e498554d08a8dcce",
    MONITOR: "5abf7d4ee927c9b8084eaee08b9e86e28d88aa54",
}

EXPECTED_SIGNATURES = {
    "run_shell": (["step", "prior_results"], 1),
    "run_http": (["step"], 0),
    "run_goal": (["step", "mission"], 0),
    "_goal_action": (["action"], 0),
    "_invoke_bound_capability": (["args"], 0),
}

EXPECTED_CHANNELS = {
    "run_shell": "shell",
    "run_http": "http",
    "run_goal": "goal_step",
    "_goal_action": "goal_action",
    "_invoke_bound_capability": "bound_capability",
}

EXPECTED_SINKS = {
    "file.open_write",
    "file.remove",
    "file.rename",
    "file.directory_mutation",
    "file.metadata_or_link_mutation",
    "process.spawn",
    "network.connect",
    "network.bind",
    "native.escape",
}


def git_blob_sha(data: bytes) -> str:
    return hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()


def _defs(tree: ast.AST) -> dict[str, ast.FunctionDef | ast.AsyncFunctionDef]:
    out = {}
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            out.setdefault(node.name, node)
    return out


def _signature(node: ast.FunctionDef | ast.AsyncFunctionDef):
    args = [a.arg for a in node.args.args]
    defaults = len(node.args.defaults)
    return args, defaults


def _wrapper_bindings(tree: ast.AST) -> dict[str, str]:
    out = {}
    defs = _defs(tree)
    fn = defs.get("install_complete_mediation")
    if fn is None:
        return out
    for node in ast.walk(fn):
        if not isinstance(node, ast.Call):
            continue
        if not isinstance(node.func, ast.Name) or node.func.id != "_wrap":
            continue
        if len(node.args) < 3:
            continue
        name_node, channel_node = node.args[1], node.args[2]
        if isinstance(name_node, ast.Constant) and isinstance(name_node.value, str) and isinstance(channel_node, ast.Constant) and isinstance(channel_node.value, str):
            out[name_node.value] = channel_node.value
    return out


def _sink_literals(tree: ast.AST) -> set[str]:
    return {
        node.value
        for node in ast.walk(tree)
        if isinstance(node, ast.Constant)
        and isinstance(node.value, str)
        and node.value in EXPECTED_SINKS
    }


def evaluate(root: Path = ROOT) -> dict:
    errors = []
    observed_blobs = {}
    for rel, expected in EXPECTED_BLOBS.items():
        path = root / rel
        actual = git_blob_sha(path.read_bytes())
        observed_blobs[rel] = actual
        if actual != expected:
            errors.append(f"BLOB_DRIFT:{rel}:{actual}")

    astra_tree = ast.parse((root / ASTRA).read_text(encoding="utf-8"), filename=ASTRA)
    wrapper_tree = ast.parse((root / WRAPPER).read_text(encoding="utf-8"), filename=WRAPPER)
    monitor_tree = ast.parse((root / MONITOR).read_text(encoding="utf-8"), filename=MONITOR)

    defs = _defs(astra_tree)
    observed_signatures = {}
    for name, expected in EXPECTED_SIGNATURES.items():
        node = defs.get(name)
        if node is None:
            errors.append("MISSING_SYMBOL:" + name)
            continue
        sig = _signature(node)
        observed_signatures[name] = {"args": sig[0], "default_count": sig[1]}
        if sig != expected:
            errors.append(f"SIGNATURE_DRIFT:{name}:{sig}")

    bindings = _wrapper_bindings(wrapper_tree)
    if bindings != EXPECTED_CHANNELS:
        errors.append("WRAPPER_CHANNEL_BINDING_DRIFT:" + json.dumps(bindings, sort_keys=True))

    sinks = _sink_literals(monitor_tree)
    if sinks != EXPECTED_SINKS:
        errors.append("MONITOR_SINK_CLASS_DRIFT:" + ",".join(sorted(sinks)))

    ok = not errors
    return {
        "schema": "PROJECT_BRAIN_ROOT3_EFFECT_MEMBRANE_E1_CURRENT_BYTE_OUTPUT_V1",
        "status": "PASS__E1_CURRENT_BYTE_COMPATIBILITY" if ok else "FAIL_CLOSED",
        "pass": ok,
        "errors": errors,
        "observed_blobs": observed_blobs,
        "observed_signatures": observed_signatures,
        "wrapper_channels": bindings,
        "sink_classes": sorted(sinks),
        "e1_closed_for_bound_bytes": ok,
        "effect_totality_closed": False,
        "child_process_semantics_closed": False,
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
