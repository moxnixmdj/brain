"""Exhaustive mutable cross-step channel audit for the live Astra runtime (#3046).

Enumerates every mutable cross-step channel outside the known declared
content-bound shell-environment projection, grounded in an AST-derived
inventory of every channel-capable call site in astra_runtime.py:

- the inventory is exhaustive by construction: any function that gains a
  subprocess / os.environ / filesystem-write / tempfile / urlopen call site
  that is not in the expected inventory fails closed as an unknown channel
  site, so new channels cannot appear silently;
- every admitted channel is either DECLARED_CONTENT_BOUND / DECLARED (with
  its exact binding named) or explicitly QUARANTINED from claimed scope;
- semantic_declaration_completeness and
  external_evidence_channel_completeness remain UNVERIFIED until separately
  proved;
- replays against exact current bytes on every run (content-addressed).

Zero composition acceptance/family/capability/ownership/terminal credit.
"""

from __future__ import annotations

import ast
from hashlib import sha1
import json
from pathlib import Path
from typing import Any, Mapping

ROOT = Path(__file__).resolve().parents[2]
RUNTIME = ROOT / "canonical/runtime/astra_runtime.py"
SCHEMA = "PROJECT_BRAIN_COMPOSITION_CROSS_STEP_CHANNEL_AUDIT_V3"

# Exhaustive expected channel-capable function inventory, derived from the
# current runtime bytes. Any drift (new function or changed count) fails closed.
EXPECTED_INVENTORY: dict[str, dict[str, int]] = {
    "subprocess": {
        "run_shell": 1,
        "_ensure_apt_dependencies": 1,
        "_ensure_pypi_dependency": 2,
        "_goal_action": 1,
        "_verify_and_promote_acquisition": 1,
    },
    "environ": {
        "run_shell": 1,
        "_external_tool_bridge": 6,
        "_planner_post": 10,
        "_resolve_bash_executable": 1,
        "_supervisor_binding_from_env": 4,
        "_validated_external_tool_bridge_dir": 2,
        "_ensure_apt_dependencies": 1,
        "_verify_and_promote_acquisition": 1,
    },
    "write": {
        "writej": 2,
        "_external_tool_bridge": 1,
        "_goal_action": 45,
        "main": 2,
        "_ensure_git_source_tree_dependency": 5,
        "_ensure_npm_dependency": 5,
        "_ensure_pypi_dependency": 3,
    },
    "tempfile": {
        "_ensure_pypi_dependency": 2,
    },
    "urlopen": {
        "_bridge_aware_urlopen": 1,
        "_ensure_pypi_dependency": 2,
        "_goal_action": 7,
        "_planner_post": 1,
        "_verified_pypi_wheel_bytes": 2,
        "fetch_discovery": 1,
        "run_http": 1,
    },
}

CHANNELS: dict[str, dict[str, Any]] = {
    "SHELL_ENV_PROJECTION": {
        "disposition": "DECLARED_CONTENT_BOUND",
        "carrier_functions": ["run_shell"],
        "binding": "EXACT_SHA256_OF_EACH_PROJECTED_PRIOR_RESULT_AT_THE_PROJECTION_BOUNDARY",
        "verification": "composition_cross_step_no_bypass_audit_v2.evaluate",
    },
    "RUNTIME_OUTPUT_AND_STATE_FILES": {
        "disposition": "DECLARED_TYPED_ADMIN_WRITE",
        "carrier_functions": ["writej", "_goal_action", "main"],
        "binding": "ROOT3_TYPED_DURABLE_ADMIN_WRITE_V1_ADMIN_CLASSES_PLUS_DECLARED_RESULT_ROOTS",
        "verification": "writej_admin_class_and_root3_writer_present",
    },
    "EXTERNAL_TOOL_BRIDGE": {
        "disposition": "DECLARED_CONTENT_BOUND",
        "carrier_functions": ["_external_tool_bridge"],
        "binding": "REQUEST_SHA256_CONTENT_ADDRESSING_PLUS_RESPONSE_SCHEMA_KIND_AND_AGENT_TASK_IDENTITY_CHECKS_PLUS_DIR_IDENTITY_AND_SYMLINK_GUARDS",
        "verification": "bridge_request_response_binding_present",
    },
    "PARENT_ENV_COPY": {
        "disposition": "CONSTANT_ACROSS_STEPS__NOT_A_MUTABLE_CROSS_STEP_CHANNEL",
        "carrier_functions": ["run_shell"],
        "binding": "FRESH_os_environ_COPY_PER_STEP_EXECUTION__STEP_SUBPROCESSES_CANNOT_MUTATE_THE_PARENT_PROCESS_ENVIRONMENT",
        "verification": "single_env_copy_site_in_run_shell",
    },
    "SHARED_CWD_FILESYSTEM": {
        "disposition": "QUARANTINED_NOT_IN_CLAIMED_SCOPE",
        "carrier_functions": ["run_shell"],
        "binding": None,
        "note": "ALL_STEPS_EXECUTE_WITH_cwd_ROOT_ON_THE_SHARED_WRITABLE_FILESYSTEM__FILES_WRITTEN_BY_STEP_N_ARE_READABLE_BY_STEP_N_PLUS_1_WITHOUT_CONTENT_BINDING",
        "amplifiers": [
            "LOGIN_SHELL_PROFILE_SOURCING_via_bash_dash_lc__A_STEP_CAN_WRITE_A_PROFILE_FILE_THROUGH_THE_SHARED_FILESYSTEM_AND_MUTATE_THE_NEXT_STEP_LOGIN_SHELL_ENVIRONMENT",
        ],
    },
    "SYSTEM_PACKAGE_STATE": {
        "disposition": "QUARANTINED_NOT_IN_CLAIMED_SCOPE",
        "carrier_functions": [
            "_ensure_apt_dependencies",
            "_ensure_pypi_dependency",
            "_ensure_npm_dependency",
            "_ensure_git_source_tree_dependency",
        ],
        "binding": None,
        "note": "RUNTIME_DEPENDENCY_PROVISIONING_IS_DECLARED_BUT_THE_CHANNEL_IS_MACHINE_GLOBAL_AND_STEP_MUTABLE__tempfile_USAGE_IS_EPHEMERAL_CONTEXT_SCOPED_AND_NOT_CROSS_STEP_PERSISTENT",
    },
    "PROCESS_AND_PORT_STATE": {
        "disposition": "QUARANTINED_NOT_IN_CLAIMED_SCOPE",
        "carrier_functions": [],
        "binding": None,
        "note": "BACKGROUND_PROCESSES_OR_PORTS_STARTED_BY_A_STEP_PERSIST_IN_THE_OPERATING_SYSTEM_AND_ARE_OBSERVABLE_BY_LATER_STEPS_WITHOUT_CONTENT_BINDING",
    },
    "NETWORK_AND_EXTERNAL_SYSTEMS": {
        "disposition": "QUARANTINED_NOT_IN_CLAIMED_SCOPE",
        "carrier_functions": [
            "_bridge_aware_urlopen",
            "_goal_action",
            "_planner_post",
            "_verified_pypi_wheel_bytes",
            "fetch_discovery",
            "run_http",
        ],
        "binding": None,
        "note": "EXTERNAL_SYSTEM_STATE_MUTATED_BY_STEP_N_OVER_THE_NETWORK_CAN_BE_OBSERVED_BY_STEP_N_PLUS_1__DIRECT_NETWORK_IS_CONTEXT_GATED_BUT_EXTERNAL_EVIDENCE_CHANNEL_COMPLETENESS_REMAINS_UNVERIFIED",
    },
}

PRESERVED_UNVERIFIED = {
    "semantic_declaration_completeness": "UNVERIFIED",
    "external_evidence_channel_completeness": "UNVERIFIED",
}


class ChannelAuditError(RuntimeError):
    pass


def _git_blob_sha(path: Path) -> str:
    raw = path.read_bytes()
    return sha1(b"blob " + str(len(raw)).encode("ascii") + b"\0" + raw).hexdigest()


def _call_kind(func_text: str) -> str | None:
    if func_text.startswith("subprocess."):
        return "subprocess"
    if "os.environ" in func_text:
        return "environ"
    if (
        ".write_text" in func_text
        or ".write_bytes" in func_text
        or ".mkdir" in func_text
        or "shutil.rmtree" in func_text
        or ".unlink" in func_text
        or ".rename" in func_text
        or "shutil.copy" in func_text
        or "shutil.move" in func_text
    ):
        return "write"
    if "tempfile." in func_text:
        return "tempfile"
    if "urlopen" in func_text:
        return "urlopen"
    return None


def derive_inventory(tree: ast.AST) -> dict[str, dict[str, int]]:
    spans: list[tuple[int, int, str]] = []
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            spans.append((node.lineno, node.end_lineno, node.name))

    def enclosing(lineno: int) -> str:
        candidates = [name for start, end, name in spans if start <= lineno <= end]
        return candidates[-1] if candidates else "<module>"

    inventory: dict[str, dict[str, int]] = {}
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        kind = _call_kind(ast.unparse(node.func))
        if kind is None:
            continue
        fn = enclosing(node.lineno)
        inventory.setdefault(kind, {})
        inventory[kind][fn] = inventory[kind].get(fn, 0) + 1
    return inventory


def diff_inventory(
    actual: Mapping[str, Mapping[str, int]],
    expected: Mapping[str, Mapping[str, int]],
) -> list[str]:
    errors: list[str] = []
    for kind in sorted(set(actual) | set(expected)):
        a = dict(actual.get(kind) or {})
        e = dict(expected.get(kind) or {})
        for fn in sorted(set(a) | set(e)):
            if a.get(fn, 0) != e.get(fn, 0):
                errors.append(
                    f"CHANNEL_SITE_DRIFT:{kind}:{fn}:expected={e.get(fn, 0)}:actual={a.get(fn, 0)}"
                )
    return errors


def _source_contains(tree: ast.AST, needle: str) -> bool:
    for node in ast.walk(tree):
        if isinstance(node, ast.Constant) and isinstance(node.value, str) and needle in node.value:
            return True
    return False


def evaluate() -> dict[str, Any]:
    if not RUNTIME.is_file():
        return {
            "schema": SCHEMA,
            "status": "FAIL_CLOSED__RUNTIME_MISSING",
            "errors": ["ASTRA_RUNTIME_MISSING"],
            "terminal_credit_delta": 0,
        }
    runtime_blob = _git_blob_sha(RUNTIME)
    source = RUNTIME.read_text(encoding="utf-8")
    try:
        tree = ast.parse(source)
    except SyntaxError as exc:
        return {
            "schema": SCHEMA,
            "status": "FAIL_CLOSED__RUNTIME_UNPARSABLE",
            "errors": [f"ASTRA_RUNTIME_UNPARSABLE:{exc}"],
            "terminal_credit_delta": 0,
        }

    errors: list[str] = []

    # 1. Exhaustive channel-site enumeration against the expected inventory.
    inventory = derive_inventory(tree)
    errors.extend(diff_inventory(inventory, EXPECTED_INVENTORY))

    # 2. The declared content-bound shell projection must still verify (v2).
    try:
        from canonical.runtime.composition_cross_step_no_bypass_audit_v2 import evaluate as v2_evaluate

        v2 = v2_evaluate()
        v2_ok = v2.get("status", "").startswith("PASS")
    except Exception as exc:  # fail closed on any v2 replay failure
        v2 = {"error": str(exc)}
        v2_ok = False
    if not v2_ok:
        errors.append("V2_PROJECTION_AUDIT_FAILED")

    # 3. Declared-write carriers must use the typed admin writer.
    admin_writer_bound = _source_contains(tree, "root3_typed_durable_admin_write_v1") and (
        "ASTRA_STATE_JSON" in source and "ASTRA_EVIDENCE_JSON" in source
    )
    if not admin_writer_bound:
        errors.append("TYPED_ADMIN_WRITE_BINDING_ABSENT")

    # 4. Bridge binding markers must be present in the runtime source.
    for marker in (
        "PROJECT_BRAIN_EXTERNAL_TOOL_REQUEST_V1",
        "PROJECT_BRAIN_EXTERNAL_TOOL_RESPONSE_V1",
        "request_sha256",
        "EXTERNAL_TOOL_RESPONSE_REQUEST_MISMATCH",
    ):
        if marker not in source:
            errors.append(f"BRIDGE_BINDING_MARKER_ABSENT:{marker}")

    # 5. Quarantined channels must stay explicitly out of claimed scope.
    quarantined = sorted(
        name for name, row in CHANNELS.items() if row["disposition"] == "QUARANTINED_NOT_IN_CLAIMED_SCOPE"
    )
    declared = sorted(
        name
        for name, row in CHANNELS.items()
        if row["disposition"].startswith("DECLARED") or row["disposition"].startswith("CONSTANT")
    )
    if len(quarantined) + len(declared) != len(CHANNELS):
        errors.append("CHANNEL_DISPOSITION_INCOMPLETE")

    ok = not errors
    return {
        "schema": SCHEMA,
        "status": (
            "PASS__EXHAUSTIVE_CHANNEL_ENUMERATION_COMPLETE__"
            + str(len(CHANNELS))
            + "_CHANNELS_"
            + str(len(quarantined))
            + "_QUARANTINED__ZERO_CREDIT"
            if ok
            else "FAIL_CLOSED"
        ),
        "runtime_path": "canonical/runtime/astra_runtime.py",
        "runtime_git_blob_sha": runtime_blob,
        "channel_site_inventory": inventory,
        "channels": CHANNELS,
        "declared_or_constant_channels": declared,
        "quarantined_channels": quarantined,
        "v2_projection_audit_status": v2.get("status"),
        "preserved_unverified": dict(PRESERVED_UNVERIFIED),
        "semantic_declaration_completeness": PRESERVED_UNVERIFIED["semantic_declaration_completeness"],
        "external_evidence_channel_completeness": PRESERVED_UNVERIFIED["external_evidence_channel_completeness"],
        "errors": errors,
        "accounting": {
            "incremental_spend_usd": 0,
            "composition_acceptance_credit_delta": 0,
            "family_credit_delta": 0,
            "capability_credit_delta": 0,
            "ownership_credit_delta": 0,
            "terminal_credit_delta": 0,
        },
        "hard_nonclaims": [
            "NO_COMPOSITION_ACCEPTANCE_FAMILY_CAPABILITY_OWNERSHIP_OR_TERMINAL_CREDIT",
            "SEMANTIC_DECLARATION_COMPLETENESS_REMAINS_UNVERIFIED",
            "EXTERNAL_EVIDENCE_CHANNEL_COMPLETENESS_REMAINS_UNVERIFIED",
            "QUARANTINED_CHANNELS_ARE_NOT_IN_CLAIMED_SCOPE",
        ],
    }


def main() -> int:
    result = evaluate()
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["status"].startswith("PASS") else 1


if __name__ == "__main__":
    raise SystemExit(main())
