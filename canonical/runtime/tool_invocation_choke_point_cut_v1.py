#!/usr/bin/env python3
"""Fail-closed inventory of live Project Brain tool/external invocation surfaces.

This module does NOT claim gateway coverage. It converts the system-level premise
"every Brain-invocable tool is registered" into an exact, drift-sensitive source
inventory. Any invocation surface remains OPEN until a separate integration proof
shows that its identity is derived from and gated by ToolUniverseGateway.
"""
from __future__ import annotations

import ast
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterable

ROOT = Path(__file__).resolve().parents[2]
RUNTIME = ROOT / "canonical" / "runtime"

HIGH_RISK_EXACT = {
    "subprocess.run", "subprocess.Popen", "subprocess.call",
    "subprocess.check_call", "subprocess.check_output",
    "os.system", "os.popen",
    "urllib.request.urlopen", "urllib.request.urlretrieve",
    "requests.get", "requests.post", "requests.put", "requests.patch",
    "requests.delete", "requests.head", "requests.request",
    "httpx.get", "httpx.post", "httpx.put", "httpx.patch",
    "httpx.delete", "httpx.head", "httpx.request",
    "socket.create_connection",
}
HIGH_RISK_PREFIX = (
    "os.exec", "os.spawn", "aiohttp.", "http.client.", "webbrowser.open",
)
SYSTEM_BOUNDARIES = {
    "canonical/runtime/astra_runtime.py": {
        "_goal_action", "_invoke_bound_capability",
    },
    "canonical/runtime/external_tool_relay.py": {
        "validate_request", "execute_urlopen", "execute_package_name_search",
        "execute_pypi_wheel_closure", "execute_npm_package_closure",
    },
}


@dataclass(frozen=True)
class Surface:
    path: str
    line: int
    function: str
    kind: str
    callee: str


def _name(node: ast.AST) -> str:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        left = _name(node.value)
        return f"{left}.{node.attr}" if left else node.attr
    return ""


class _Visitor(ast.NodeVisitor):
    def __init__(self, path: str):
        self.path = path
        self.stack: list[str] = []
        self.surfaces: list[Surface] = []
        self.seen_boundaries: set[str] = set()

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        self.stack.append(node.name)
        if node.name in SYSTEM_BOUNDARIES.get(self.path, set()):
            self.seen_boundaries.add(node.name)
            self.surfaces.append(Surface(
                self.path, node.lineno, node.name,
                "SYSTEM_INVOCATION_BOUNDARY", node.name,
            ))
        self.generic_visit(node)
        self.stack.pop()

    visit_AsyncFunctionDef = visit_FunctionDef

    def visit_Call(self, node: ast.Call) -> None:
        callee = _name(node.func)
        if callee in HIGH_RISK_EXACT or callee.startswith(HIGH_RISK_PREFIX):
            self.surfaces.append(Surface(
                self.path,
                getattr(node, "lineno", 0),
                self.stack[-1] if self.stack else "<module>",
                "DIRECT_INVOCATION_PRIMITIVE",
                callee,
            ))
        self.generic_visit(node)


def inventory(paths: Iterable[Path] | None = None) -> list[Surface]:
    files = list(paths) if paths is not None else sorted(RUNTIME.rglob("*.py"))
    out: list[Surface] = []
    for path in files:
        rel = path.relative_to(ROOT).as_posix()
        if rel.endswith("tool_invocation_choke_point_cut_v1.py"):
            continue
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=rel)
        except (OSError, UnicodeError, SyntaxError):
            out.append(Surface(rel, 0, "<parse>", "UNINSPECTABLE_RUNTIME_SOURCE", ""))
            continue
        v = _Visitor(rel)
        v.visit(tree)
        out.extend(v.surfaces)

        expected = SYSTEM_BOUNDARIES.get(rel, set())
        missing = expected - v.seen_boundaries
        for name in sorted(missing):
            out.append(Surface(rel, 0, name, "EXPECTED_BOUNDARY_MISSING", name))
    return sorted(out, key=lambda x: (x.path, x.line, x.kind, x.callee))


def evaluate() -> dict:
    surfaces = inventory()
    paths = sorted({x.path for x in surfaces})
    return {
        "schema": "PROJECT_BRAIN_TOOL_INVOCATION_CHOKE_POINT_CUT_V1",
        "status": (
            "OPEN__TOTAL_INVOCATION_CHOKE_POINT_COVERAGE_REQUIRED"
            if surfaces else
            "FAIL_CLOSED__NO_INVOCATION_SURFACES_DETECTED"
        ),
        "proof_obligation": "TOTAL_INVOCATION_CHOKE_POINT_COVERAGE_BY_OWNED_GATEWAY",
        "runtime_python_files_scanned": len(list(RUNTIME.rglob("*.py"))),
        "surface_count": len(surfaces),
        "surface_paths": paths,
        "surfaces": [asdict(x) for x in surfaces],
        "closure_rule": (
            "NO_TOOL_DISCOVERY_IDENTITY_COMPLETENESS_CREDIT_UNTIL_EVERY_SURFACE_"
            "IS_EITHER_GATEWAY_GATED_WITH_IDENTITY_BINDING_OR_MACHINE_PROVED_NON_TOOL"
        ),
        "new_reality_units_consumed": 0,
        "incremental_spend_usd": 0,
        "capability_credit_delta": 0,
        "family_credit_delta": 0,
        "execution_authority": False,
        "promotion_authority": False,
    }


def main() -> int:
    print(json.dumps(evaluate(), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
