#!/usr/bin/env python3
"""Bounded declared-contract testing using existing concrete oracle semantics.

Hypothesis generates integer inputs when available. Otherwise the existing
concrete sample really executes, but does not satisfy the requested Hypothesis
backend. Neither mode proves correctness outside the tested inputs. Source is
trusted executable Python; this adapter is not a sandbox.
"""
from __future__ import annotations
import ast
import hashlib
import json
import pathlib
from typing import Any
from canonical.runtime.bound_capabilities import concrete_execution_oracle as concrete
from canonical.runtime.write_authority_v1 import SOURCE_SUFFIXES, check_report

SCHEMA = "PROJECT_BRAIN_EVIDENCE_ORACLE_HYPOTHESIS_V1"
CAPABILITY_ID = "evidence.oracle.hypothesis_property.v1"
PROVIDES = ["evidence.hypothesis.property_violation", "evidence.property_test.verified"]
REQUIRES: list[str] = ["python.source.file.available"]
REPO = pathlib.Path(__file__).resolve().parents[3]


def run(args: dict[str, Any], root: str | pathlib.Path) -> dict[str, Any]:
    repo = pathlib.Path(root).resolve()
    output = (repo / str(args.get("output_path") or "canonical/tmp_hypothesis_oracle.json")).resolve()
    if output == repo or repo not in output.parents:
        raise RuntimeError("PATH_OUTSIDE_REPOSITORY")
    source = args.get("source")
    inputs = []
    if source is None and args.get("source_path"):
        path = (repo / str(args["source_path"])).resolve()
        if path == repo or repo not in path.parents:
            raise RuntimeError("PATH_OUTSIDE_REPOSITORY")
        inputs.append(path)
        source = path.read_text(encoding="utf-8")
    if not isinstance(source, str) or not source.strip():
        raise ValueError("SOURCE_REQUIRED")
    tree = ast.parse(source)  # Syntax errors must not become successful checks.
    fn = next((n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "f"), None)
    if fn is None:
        raise ValueError("NO_FUNCTION_F")
    if not concrete._posts(ast.get_docstring(fn) or ""):
        raise ValueError("POSTCONDITION_REQUIRED")
    check_report(repo, output, inputs)
    if output.suffix.lower() in SOURCE_SUFFIXES:
        raise RuntimeError("REPORT_DESTINATION_IS_SOURCE")
    try:
        from hypothesis import given, strategies as st, seed, settings
    except ImportError:
        available = False
        result = concrete.check_source(source)
        checked, violations = result["checked"], result["violations"]
    else:
        available = True
        checked, violations = 0, []

        @seed(0)
        @settings(max_examples=50, database=None, derandomize=True)
        @given(st.integers(min_value=-100, max_value=100))
        def prop(x):
            nonlocal checked, violations
            result = concrete.check_source(source, sample=[x])
            checked += result["checked"]
            if result["violations"]:
                violations = result["violations"]
                raise AssertionError("DECLARED_CONTRACT_VIOLATION")

        try:
            prop()
        except AssertionError:
            if not violations:
                raise
    verified = available and checked > 0 and not violations
    status = ("CONTRACT_VIOLATION_FOUND" if violations else
              "NO_COUNTEREXAMPLE_IN_GENERATED_SAMPLE" if available else
              "OPEN__HYPOTHESIS_UNAVAILABLE")
    artifact = {"schema": SCHEMA, "capability_id": CAPABILITY_ID,
                "source_excerpt": source[:500], "hypothesis_available": available,
                "checked": checked, "violations": violations, "verified": verified,
                "status": status, "evidence_scope": "bounded_declared_contract_testing",
                "model_dependency_count": 0, "incremental_spend_usd": 0}
    raw = json.dumps(artifact, sort_keys=True, separators=(",", ":")).encode()
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_bytes(raw)
    return {**artifact, "adapter": "evidence_oracle_hypothesis_v1",
            "output_path": str(output.relative_to(repo)),
            "output_sha256": hashlib.sha256(raw).hexdigest(),
            "output_verified": output.read_bytes() == raw}
