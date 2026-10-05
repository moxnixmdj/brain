"""Verify the production ASTRA workflow is wired through Root3 before ASTRA."""
from __future__ import annotations

import ast
import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
SCHEMA = "PROJECT_BRAIN_ROOT3_PRODUCTION_BOOTSTRAP_WIRING_VERIFIER_V1"
WORKFLOW = ".github/workflows/astra-shared-runtime.yml"
LAUNCHER = "canonical/runtime/astra_root3_strict_runtime_v1.py"


class WiringError(RuntimeError):
    pass


def _main_order(root: Path) -> dict[str, int]:
    p = root / LAUNCHER
    tree = ast.parse(p.read_text(encoding="utf-8"), filename=LAUNCHER)
    main = next(
        (x for x in tree.body if isinstance(x, ast.FunctionDef) and x.name == "main"),
        None,
    )
    if main is None:
        raise WiringError("LAUNCHER_MAIN_MISSING")
    install_lines = []
    import_lines = []
    for node in ast.walk(main):
        if not isinstance(node, ast.Call):
            continue
        q = None
        if isinstance(node.func, ast.Attribute) and isinstance(node.func.value, ast.Name):
            q = node.func.value.id + "." + node.func.attr
        if q == "bootstrap.install_current":
            install_lines.append(node.lineno)
        if q == "importlib.import_module":
            if (
                node.args
                and isinstance(node.args[0], ast.Constant)
                and node.args[0].value == "canonical.runtime.astra_runtime"
            ):
                import_lines.append(node.lineno)
    if len(install_lines) != 1 or len(import_lines) != 1:
        raise WiringError("BOOTSTRAP_OR_ASTRA_IMPORT_CARDINALITY_INVALID")
    return {"install_line": install_lines[0], "astra_import_line": import_lines[0]}


def verify(root: Path = ROOT) -> dict[str, Any]:
    root = Path(root).resolve()
    workflow = (root / WORKFLOW).read_text(encoding="utf-8")
    strict_command = (
        'python canonical/runtime/astra_root3_strict_runtime_v1.py '
        '"${{ steps.mission.outputs.path }}"'
    )
    direct_command = (
        'python canonical/runtime/astra_runtime.py '
        '"${{ steps.mission.outputs.path }}"'
    )
    if strict_command not in workflow:
        raise WiringError("STRICT_ROOT3_LAUNCH_COMMAND_MISSING")
    if direct_command in workflow:
        raise WiringError("DIRECT_ASTRA_RUNTIME_BYPASS_STILL_PRESENT")

    order = _main_order(root)
    if order["install_line"] >= order["astra_import_line"]:
        raise WiringError("ROOT3_INSTALL_NOT_BEFORE_ASTRA_IMPORT")

    return {
        "schema": SCHEMA,
        "status": "PASS__PRODUCTION_WORKFLOW_HAS_NO_DIRECT_ASTRA_BYPASS__ROOT3_INSTALL_PRECEDES_ASTRA_IMPORT__ZERO_CREDIT",
        "workflow": WORKFLOW,
        "launcher": LAUNCHER,
        **order,
        "direct_astra_command_present": False,
        "strict_root3_command_present": True,
        "acceptance_credit_delta": 0,
    }


if __name__ == "__main__":
    print(json.dumps(verify(), indent=2, sort_keys=True))
