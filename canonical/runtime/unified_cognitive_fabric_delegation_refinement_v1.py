"""Delegation/non-amplification proof for unified_cognitive_fabric_v1."""
from __future__ import annotations

import ast
from hashlib import sha1, sha256
import json
from pathlib import Path
from typing import Any, Mapping

SCHEMA = "PROJECT_BRAIN_UNIFIED_FABRIC_DELEGATION_REFINEMENT_RECEIPT_V1"
ROOT = Path(__file__).resolve().parents[2]
SPEC_PATH = Path("canonical/governance/UNIFIED_FABRIC_DELEGATION_SPEC_20261010_V1.json")
AUTHORITY_KEYS = {
    "execution_authority",
    "promotion_authority",
    "capability_promotion_authority",
    "terminal_authority",
    "physical_deletion_authority",
}
ALLOWED_CANONICAL_CALLS = {
    "authority_runtime_census",
    "capability_scheduler.rank_work",
    "certified_route.dispatch",
    "certified_route.preflight",
    "closure_census",
    "execute_bound",
    "finance_concept_verify.verify_claim",
    "h100_inference.predict",
    "h100_inference.registry_snapshot",
    "h100_inference.resolve_verified_capability",
    "improvement_driver.drain",
    "live_brain.load_verified_registry",
    "live_composition.execute",
    "live_invoker.coverage",
    "live_invoker.invoke",
    "live_ownership.evaluate",
    "live_runtime.execute_failure_repair_cycle",
    "live_runtime.observe_runtime_outcome",
    "live_runtime.run",
    "live_runtime.synthesize_failure_repair",
    "mystery_information.solve",
    "mystery_polytope.solve",
    "oewn_decision_sense.resolve",
    "one_shot_reality_closure.run",
    "p3.evaluate",
    "r1_closure_gate.evaluate",
    "self_improvement.load_state",
    "self_improvement.run_learning_episode",
    "semantic_ambiguity.decide",
    "semantic_relation.resolve",
    "terminal_autopilot.build_manifest_from_repo",
    "terminal_autopilot.plan",
    "terminal_closure.evaluate_frontier_state",
    "terminal_closure.evaluate_manifest",
    "terminal_root.evaluate",
    "universal_escape.resolve",
}
FORBIDDEN_IMPORT_ROOTS = {"subprocess", "requests", "httpx", "aiohttp", "socket", "urllib", "os", "shutil"}
FORBIDDEN_BUILTIN_CALLS = {"open", "exec", "eval", "compile"}
FORBIDDEN_MUTATION_METHODS = {"write_text", "write_bytes", "unlink", "mkdir", "touch", "rename"}


def _canon(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode("utf-8")


def _git_blob_sha(path: Path) -> str:
    data = path.read_bytes()
    return sha1(b"blob " + str(len(data)).encode("ascii") + b"\0" + data).hexdigest()


def _load(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError("JSON_OBJECT_REQUIRED:" + str(path))
    return value


def _chain(node: ast.AST) -> tuple[str, ...]:
    if isinstance(node, ast.Name):
        return (node.id,)
    if isinstance(node, ast.Attribute):
        return (*_chain(node.value), node.attr)
    return ()


def _fail(reason: str, **extra: Any) -> dict[str, Any]:
    return {
        "pass": False,
        "schema": SCHEMA,
        "status": "FAIL_CLOSED",
        "reason": reason,
        "delegation_refinement_verified": False,
        "execution_authority": False,
        "terminal_authority": False,
        "terminal_credit_delta": 0,
        **extra,
    }


def _inspect(path: Path) -> dict[str, Any]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    aliases: dict[str, str] = {}
    bad_imports: set[str] = set()
    bad_calls: list[str] = []
    authority_true: list[str] = []
    bad_credit = 0
    terminal_executor_imported = False

    for node in tree.body:
        if isinstance(node, ast.ImportFrom):
            module = str(node.module or "")
            root = module.split(".", 1)[0]
            if root in FORBIDDEN_IMPORT_ROOTS:
                bad_imports.add(module)
            for alias in node.names:
                aliases[alias.asname or alias.name] = (module + "." + alias.name).strip(".")
                if "terminal_autopilot_executor" in module or "terminal_autopilot_executor" in alias.name:
                    terminal_executor_imported = True
        elif isinstance(node, ast.Import):
            for alias in node.names:
                aliases[alias.asname or alias.name] = alias.name
                if alias.name.split(".", 1)[0] in FORBIDDEN_IMPORT_ROOTS:
                    bad_imports.add(alias.name)
                if "terminal_autopilot_executor" in alias.name:
                    terminal_executor_imported = True

    canonical_calls: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            chain = _chain(node.func)
            if chain:
                if len(chain) == 1 and chain[0] in FORBIDDEN_BUILTIN_CALLS:
                    bad_calls.append(".".join(chain))
                if chain[-1] in FORBIDDEN_MUTATION_METHODS:
                    bad_calls.append(".".join(chain))
                if chain[0] in aliases and aliases[chain[0]].startswith("canonical.runtime"):
                    canonical_calls.add(".".join(chain))

        if isinstance(node, ast.Dict):
            for key, value in zip(node.keys, node.values):
                if not isinstance(key, ast.Constant) or not isinstance(key.value, str):
                    continue
                if key.value in AUTHORITY_KEYS and isinstance(value, ast.Constant) and value.value is True:
                    authority_true.append(key.value)
                if key.value == "terminal_credit_delta":
                    if not (isinstance(value, ast.Constant) and value.value == 0 and not isinstance(value.value, bool)):
                        bad_credit += 1
                if key.value == "terminal_credit" and isinstance(value, ast.Constant) and value.value is True:
                    bad_credit += 1

    source = path.read_text(encoding="utf-8")
    return {
        "pass": (
            not bad_imports
            and not bad_calls
            and not authority_true
            and bad_credit == 0
            and canonical_calls == ALLOWED_CANONICAL_CALLS
            and not terminal_executor_imported
            and "LIVE_COMPOSITION_RECURSION_LIMIT" in source
            and "LIVE_CAPABILITY_RECURSION_LIMIT" in source
        ),
        "canonical_calls": sorted(canonical_calls),
        "missing_canonical_calls": sorted(ALLOWED_CANONICAL_CALLS - canonical_calls),
        "unexpected_canonical_calls": sorted(canonical_calls - ALLOWED_CANONICAL_CALLS),
        "forbidden_imports": sorted(bad_imports),
        "direct_effect_calls": sorted(set(bad_calls)),
        "authority_true_literals": sorted(authority_true),
        "nonzero_terminal_credit_literals": bad_credit,
        "terminal_executor_imported": terminal_executor_imported,
        "composition_recursion_guard_present": "LIVE_COMPOSITION_RECURSION_LIMIT" in source,
        "capability_recursion_guard_present": "LIVE_CAPABILITY_RECURSION_LIMIT" in source,
    }


def prove(repo_root: str | Path = ROOT) -> dict[str, Any]:
    root = Path(repo_root).resolve()
    try:
        spec = _load(root / SPEC_PATH)
    except Exception as exc:
        return _fail("SPEC_LOAD_FAILED:" + type(exc).__name__ + ":" + str(exc))
    if spec.get("schema") != "PROJECT_BRAIN_UNIFIED_FABRIC_DELEGATION_SPEC_V1":
        return _fail("SPEC_SCHEMA_INVALID")
    if spec.get("terminal_credit_delta") != 0:
        return _fail("SPEC_NONZERO_TERMINAL_CREDIT")

    subject = spec.get("subject")
    if not isinstance(subject, Mapping):
        return _fail("SUBJECT_BINDING_INVALID")
    rel = str(subject.get("path") or "")
    expected = str(subject.get("git_blob_sha") or "")
    path = root / rel
    if not path.is_file() or _git_blob_sha(path) != expected:
        return _fail("SUBJECT_BLOB_MISMATCH")

    static = _inspect(path)
    if static.get("pass") is not True:
        return _fail("DELEGATION_MEMBRANE_STATIC_PROOF_FAILED", static=static)

    verification_path = root / str(spec.get("component_receipt") or "")
    try:
        verification = _load(verification_path)
    except Exception as exc:
        return _fail("COMPONENT_RECEIPT_LOAD_FAILED:" + type(exc).__name__ + ":" + str(exc))
    rows = verification.get("exact_runtime_blobs")
    if not isinstance(rows, list):
        return _fail("COMPONENT_RECEIPT_ROWS_INVALID")
    row = next(
        (x for x in rows if isinstance(x, Mapping) and x.get("path") == rel),
        None,
    )
    if not isinstance(row, Mapping):
        return _fail("FABRIC_COMPONENT_RECEIPT_MISSING")
    if (
        row.get("git_blob_sha") != expected
        or int(row.get("tests_run", 0)) != 25
        or int(row.get("failures", -1)) != 0
        or int(row.get("errors", -1)) != 0
    ):
        return _fail("FABRIC_COMPONENT_RECEIPT_INVALID", row=dict(row))

    body = {
        "pass": True,
        "schema": SCHEMA,
        "status": "PASS__UNIFIED_FABRIC_DELEGATION_MEMBRANE_VERIFIED",
        "delegation_refinement_verified": True,
        "subject_path": rel,
        "subject_git_blob_sha": expected,
        "component_test_count": 25,
        "canonical_runtime_call_count": len(ALLOWED_CANONICAL_CALLS),
        "all_canonical_runtime_calls_classified": True,
        "no_direct_external_effect_calls": True,
        "no_authority_true_literals": True,
        "no_nonzero_terminal_credit_literals": True,
        "terminal_executor_bypass_absent": True,
        "subordinate_semantics_reproved": False,
        "static_proof": static,
        "execution_authority": False,
        "terminal_authority": False,
        "terminal_credit_delta": 0,
    }
    return {**body, "receipt_sha256": sha256(_canon(body)).hexdigest()}


if __name__ == "__main__":
    print(json.dumps(prove(ROOT), indent=2, sort_keys=True))
