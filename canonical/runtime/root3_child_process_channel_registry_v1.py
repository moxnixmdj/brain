"""Exact child-process channel compiler for the current ASTRA runtime.

Turns Root3's open-ended CHILD_PROCESS_INTERNAL_EFFECTS residual into a finite,
content-addressed list of subprocess.run call sites. This is classification
only. It grants zero acceptance/Root3 credit until every material/opaque site
is either mediated or forbidden and the external binaries/dependencies are
scope-completely bound.
"""
from __future__ import annotations

import ast
import hashlib
import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
ASTRA = ROOT / "canonical/runtime/astra_runtime.py"
SCHEMA = "PROJECT_BRAIN_ROOT3_CHILD_PROCESS_CHANNEL_REGISTRY_V1"

EXPECTED_ASTRA_GIT_BLOB_SHA = "0912dfa4119950f6d235d501dfa784e65e9f71c9"


class ChildProcessRegistryError(RuntimeError):
    pass


def git_blob_sha(path: Path) -> str:
    raw = path.read_bytes()
    return hashlib.sha1(b"blob " + str(len(raw)).encode() + b"\0" + raw).hexdigest()


def _qname(node: ast.AST) -> str | None:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        left = _qname(node.value)
        return None if left is None else left + "." + node.attr
    if isinstance(node, ast.Call):
        return _qname(node.func)
    return None


def _string_literals(node: ast.AST) -> list[str]:
    out: list[str] = []
    for x in ast.walk(node):
        if isinstance(x, ast.Constant) and isinstance(x.value, str):
            out.append(x.value)
    return out


class _Visitor(ast.NodeVisitor):
    def __init__(self) -> None:
        self.stack: list[str] = []
        self.rows: list[dict[str, Any]] = []

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        self.stack.append(node.name)
        self.generic_visit(node)
        self.stack.pop()

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        self.stack.append(node.name)
        self.generic_visit(node)
        self.stack.pop()

    def visit_Call(self, node: ast.Call) -> None:
        if _qname(node.func) == "subprocess.run":
            fn = self.stack[-1] if self.stack else "<module>"
            first = node.args[0] if node.args else None
            literals = _string_literals(first) if first is not None else []
            self.rows.append({
                "function": fn,
                "lineno": int(getattr(node, "lineno", 0)),
                "command_literals": literals,
                "has_dynamic_command": bool(
                    first is not None
                    and any(isinstance(x, (ast.Name, ast.Call, ast.Starred)) for x in ast.walk(first))
                ),
            })
        self.generic_visit(node)


def _classify(row: dict[str, Any]) -> dict[str, Any]:
    fn = row["function"]
    literals = row["command_literals"]

    if fn == "run_shell":
        return {
            **row,
            "channel_class": "ARBITRARY_SHELL_STEP",
            "effect_class": "OPAQUE_MATERIAL_EFFECT_CAPABLE",
            "required_resolution": "ROUTE_THROUGH_FINAL_EFFECT_AUTHORIZER_OR_FORBID_FROM_CREDITED_RUNTIME",
        }

    if fn == "_ensure_pypi_dependency":
        if "pip" not in literals or "install" not in literals:
            raise ChildProcessRegistryError("PYPI_SUBPROCESS_SHAPE_DRIFT")
        return {
            **row,
            "channel_class": "PYPI_INSTALL_CHILD",
            "effect_class": "PACKAGE_ENV_MUTATION",
            "required_resolution": "BIND_TO_PACKAGE_ENV_MUTATION_AUTHORIZATION_AND_EXACT_WHEEL_CLOSURE",
        }

    if fn == "_ensure_apt_dependencies":
        if "apt-cache" in literals and "show" in literals:
            cls = "APT_METADATA_QUERY_CHILD"
            effect = "EXTERNAL_PROCESS_READ_WITH_BINARY_TRUST"
            resolution = "BIND_EXACT_BINARY_OR_SANDBOX_READ_ONLY_QUERY"
        elif "apt-get" in literals and "install" in literals:
            cls = "APT_INSTALL_CHILD"
            effect = "PACKAGE_ENV_MUTATION"
            resolution = "BIND_TO_PACKAGE_ENV_MUTATION_AUTHORIZATION_AND_EXACT_PACKAGE_SET"
        elif "dpkg-query" in literals:
            cls = "DPKG_STATE_QUERY_CHILD"
            effect = "EXTERNAL_PROCESS_READ_WITH_BINARY_TRUST"
            resolution = "BIND_EXACT_BINARY_OR_SANDBOX_READ_ONLY_QUERY"
        else:
            raise ChildProcessRegistryError("APT_SUBPROCESS_SHAPE_DRIFT")
        return {
            **row,
            "channel_class": cls,
            "effect_class": effect,
            "required_resolution": resolution,
        }

    if fn == "_goal_action":
        if "PYTHON_TEST_AUDIT_JSON_INVALID" not in ASTRA.read_text(encoding="utf-8"):
            raise ChildProcessRegistryError("GOAL_ACTION_TEST_AUDIT_CONTEXT_DRIFT")
        return {
            **row,
            "channel_class": "PYTHON_TEST_EXECUTION_CHILD",
            "effect_class": "OPAQUE_REPO_PROGRAM_EFFECT_CAPABLE",
            "required_resolution": "SANDBOX_OR_PROVE_TEST_PROGRAM_EFFECT_MEDIATION_BEFORE_CREDIT",
        }

    if fn == "_verify_and_promote_acquisition":
        return {
            **row,
            "channel_class": "RECURSIVE_ASTRA_VERIFICATION_CHILD",
            "effect_class": "NESTED_RUNTIME_EFFECT_CAPABLE",
            "required_resolution": "INHERIT_STRICT_EFFECT_BOUNDARY_AND_BIND_CHILD_RUNTIME_BYTES",
        }

    raise ChildProcessRegistryError("UNCLASSIFIED_SUBPROCESS_CALL:" + fn)


def compile_registry(root: Path = ROOT) -> dict[str, Any]:
    astra = root / "canonical/runtime/astra_runtime.py"
    actual = git_blob_sha(astra)
    if actual != EXPECTED_ASTRA_GIT_BLOB_SHA:
        raise ChildProcessRegistryError(
            "ASTRA_RUNTIME_BLOB_DRIFT:" + actual
        )

    tree = ast.parse(astra.read_text(encoding="utf-8"), filename=str(astra))
    v = _Visitor()
    v.visit(tree)
    rows = sorted((_classify(x) for x in v.rows), key=lambda x: x["lineno"])

    expected_counts = {
        "run_shell": 1,
        "_ensure_pypi_dependency": 2,
        "_ensure_apt_dependencies": 3,
        "_goal_action": 1,
        "_verify_and_promote_acquisition": 1,
    }
    counts: dict[str, int] = {}
    for row in rows:
        counts[row["function"]] = counts.get(row["function"], 0) + 1

    if counts != expected_counts:
        raise ChildProcessRegistryError(
            "SUBPROCESS_FUNCTION_COUNT_DRIFT:" + json.dumps(counts, sort_keys=True)
        )
    if len(rows) != 8:
        raise ChildProcessRegistryError("SUBPROCESS_TOTAL_COUNT_DRIFT:" + str(len(rows)))

    opaque = [
        x for x in rows
        if x["effect_class"] not in {"EXTERNAL_PROCESS_READ_WITH_BINARY_TRUST"}
    ]

    return {
        "schema": SCHEMA,
        "status": "PASS__CURRENT_CHILD_PROCESS_CALL_UNIVERSE_FINITE__8_EXACT_CALL_SITES__MEDIATION_STILL_OPEN",
        "astra_runtime_git_blob_sha": actual,
        "call_site_count": len(rows),
        "function_counts": counts,
        "call_sites": rows,
        "opaque_or_mutating_call_site_count": len(opaque),
        "read_query_with_binary_trust_call_site_count": len(rows) - len(opaque),
        "child_process_universe_closed_for_current_astra_bytes": True,
        "child_process_effect_totality_proved": False,
        "next": [
            "MEDIATE_OR_FORBID_ARBITRARY_SHELL_STEP",
            "MEDIATE_PACKAGE_ENV_MUTATIONS",
            "SANDBOX_OR_BIND_PYTHON_TEST_EXECUTION",
            "BIND_RECURSIVE_ASTRA_CHILD_TO_STRICT_EFFECT_BOUNDARY",
            "BIND_OR_SANDBOX_READ_ONLY_EXTERNAL_BINARIES",
        ],
        "hard_nonclaims": [
            "NO_CLAIM_CHILD_PROCESS_EFFECT_MEDIATION_COMPLETE",
            "NO_CLAIM_EXTERNAL_BINARY_IMPLEMENTATIONS_ARE_EFFECT_FREE",
            "NO_ROOT3_ACCEPTANCE_FAMILY_CAPABILITY_OR_OWNERSHIP_CREDIT",
        ],
        "accounting": {
            "incremental_spend_usd": 0,
            "acceptance_credit_delta": 0,
            "family_credit_delta": 0,
            "capability_credit_delta": 0,
            "ownership_credit_delta": 0,
        },
    }


if __name__ == "__main__":
    print(json.dumps(compile_registry(), indent=2, sort_keys=True))
