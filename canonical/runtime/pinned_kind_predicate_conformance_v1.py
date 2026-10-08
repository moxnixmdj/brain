"""Restricted AST validation of an actual content-addressed Brain predicate.

Proves a narrow source-to-contract equivalence for builtin dict contexts with
a missing or string-valued 'kind' key. Only one exact, side-effect-free Python
AST function shape is admitted. No source is executed by this validator.
No global scope, Brain credit, or terminal promotion is authorized.
"""
from __future__ import annotations

import ast
import re
from pathlib import Path
from typing import Any, Mapping

from canonical.runtime.effect_broker_receipt_resolver_v2 import git_blob_id

SCHEMA = "PROJECT_BRAIN_PINNED_KIND_PREDICATE_CONFORMANCE_V1"
SHA_RE = re.compile("[0-9a-f]{40}\\Z")


def _fail(reason: str) -> dict[str, Any]:
    return {
        "schema": SCHEMA, "pass": False, "status": "FAIL_CLOSED",
        "reason": reason, "source_to_contract_conformance": False,
        "production_route_adequacy": False,
        "target_scope_complete": False, "creditable": False,
        "u_empty_authorized": False, "terminal_authority": False,
        "terminal_credit_delta": 0,
    }


def validate(source: Mapping[str, Any], *, repo_root: str | Path,
             expected_kind: str) -> dict[str, Any]:
    try:
        if not isinstance(expected_kind, str) or not expected_kind:
            return _fail("EXPECTED_KIND_REQUIRED")
        if not isinstance(source, Mapping):
            return _fail("SOURCE_REF_REQUIRED")
        rel, sha = source.get("path"), source.get("git_blob_sha")
        if (not isinstance(rel, str) or not rel.startswith("canonical/runtime/")
                or not isinstance(sha, str) or SHA_RE.fullmatch(sha) is None
                or "\\" in rel or "\x00" in rel):
            return _fail("PINNED_SOURCE_REF_INVALID")
        parts = rel.split("/")
        if any(not p or p in (".", "..") for p in parts):
            return _fail("NONCANONICAL_SOURCE_PATH")
        root = Path(repo_root).resolve(strict=True)
        checked = root
        for part in parts:
            checked = checked / part
            if checked.is_symlink():
                return _fail("SYMLINK_SOURCE_DISALLOWED")
        checked = checked.resolve(strict=True)
        if root not in checked.parents or not checked.is_file():
            return _fail("SOURCE_OUTSIDE_ROOT")
        if checked.stat().st_size > 250000:
            return _fail("SOURCE_OVERSIZE")
        raw = checked.read_bytes()
        if git_blob_id(raw, object_format="sha1") != sha:
            return _fail("SOURCE_BLOB_MISMATCH")
        tree = ast.parse(raw.decode("utf-8"))
        defs = [node for node in tree.body if isinstance(node, ast.FunctionDef)]
        if len(defs) != 1:
            return _fail("EXACT_ONE_FUNCTION_REQUIRED")
        fn = defs[0]
        for node in tree.body:
            if node is fn:
                continue
            if isinstance(node, ast.Expr) and isinstance(node.value, ast.Constant) and isinstance(node.value.value, str):
                continue
            if isinstance(node, ast.ImportFrom) and node.module == "__future__" and [a.name for a in node.names] == ["annotations"]:
                continue
            if isinstance(node, ast.ImportFrom) and node.module == "typing" and all(a.name in ("Any", "Mapping") and a.asname is None for a in node.names) and set(a.name for a in node.names) == {"Any","Mapping"}:
                continue
            if isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name) and node.targets[0].id == "SCHEMA" and isinstance(node.value, ast.Constant) and isinstance(node.value.value, str):
                continue
            return _fail("UNSUPPORTED_MODULE_STATEMENT")
        expected = (
            "def admit(context: Mapping[str, Any]) -> bool:\n"
            "    if not isinstance(context, Mapping):\n"
            "        return False\n"
            "    return context.get('kind') == " + repr(expected_kind) + "\n"
        )
        reference = ast.parse(expected).body[0]
        if ast.dump(fn, include_attributes=False) != ast.dump(reference, include_attributes=False):
            return _fail("FUNCTION_SEMANTICS_DO_NOT_MATCH_RESTRICTED_FORM")
        return {
            "schema": SCHEMA, "pass": True,
            "status": "PASS__PINNED_PYTHON_KIND_PREDICATE_TRANSLATION_VALIDATED",
            "source_git_blob_sha": sha,
            "admission_literal": expected_kind,
            "proved_input_domain": "BUILTIN_DICT__KIND_IS_MISSING_OR_STRING",
            "proved_equivalence": "admit(context) IFF context.get('kind') == admission_literal",
            "source_to_contract_conformance": True,
            "source_executed_by_validator": False,
            "production_route_adequacy": False, "target_scope_complete": False,
            "creditable": False, "u_empty_authorized": False,
            "terminal_authority": False, "terminal_credit_delta": 0,
        }
    except Exception as exc:
        return _fail(type(exc).__name__ + ":" + str(exc)[:100])
