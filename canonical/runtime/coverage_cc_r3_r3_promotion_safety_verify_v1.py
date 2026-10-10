"""Executable semantic verifier for CC_R3 R3 promotion safety.

This verifier is intentionally claim- and generation-specific. It proves only the
exact active bounded R3 promotion-safety claim over the content-addressed ten-file
surface named by its certificate. Any byte drift fails closed.
"""
from __future__ import annotations

import ast
import hashlib
import json
from pathlib import Path
from typing import Any, Mapping

ROOT_ID = "CC_R3_TERMINAL_CLOSURE_V1"
CLAIM_ID = "e1c519109c4b2c46a9225686fc2c5c5490564d1cc62d5c6ff3c6c436bfca4314"
MAIN = "canonical/runtime/autonomous_verified_self_improvement_v1.py"
QUEUE = "canonical/runtime/r3_improvement_queue_driver_v1.py"
STRUCTURAL_ACQ = "canonical/runtime/r3_structural_bound_rule_acquisition_v1.py"
AUTHORITY_KEYS = frozenset({
    "promotion_authority",
    "terminal_authority",
    "verification_authority",
    "acceptance_authority",
})
DURABLE_KEYS = frozenset({"episodes", "skills", "pareto_frontiers"})


def _blob_sha(path: Path) -> str:
    data = path.read_bytes()
    return hashlib.sha1(
        b"blob " + str(len(data)).encode("ascii") + b"\0" + data
    ).hexdigest()


def _fail(root_id: str, claim_id: str, *errors: str) -> dict[str, Any]:
    return {
        "pass": False,
        "status": "FAIL_CLOSED__CC_R3_R3_PROMOTION_SAFETY_UNPROVED",
        "root_id": root_id,
        "claim_id": claim_id,
        "errors": sorted(set(errors)),
        "semantic_claim_verified": False,
        "terminal_credit_delta": 0,
    }


def _const_str(node: ast.AST | None) -> str | None:
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    return None


def _is_true(node: ast.AST | None) -> bool:
    return isinstance(node, ast.Constant) and node.value is True


def _dict_true_authority_keys(tree: ast.AST) -> list[tuple[int, str]]:
    out: list[tuple[int, str]] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Dict):
            for key, value in zip(node.keys, node.values):
                name = _const_str(key)
                if name in AUTHORITY_KEYS and _is_true(value):
                    out.append((getattr(node, "lineno", -1), name))
        elif isinstance(node, ast.Call):
            for kw in node.keywords:
                if kw.arg in AUTHORITY_KEYS and _is_true(kw.value):
                    out.append((getattr(node, "lineno", -1), str(kw.arg)))
        elif isinstance(node, (ast.Assign, ast.AnnAssign)):
            value = node.value
            if not _is_true(value):
                continue
            targets = node.targets if isinstance(node, ast.Assign) else [node.target]
            for target in targets:
                if isinstance(target, ast.Subscript):
                    name = _const_str(target.slice)
                    if name in AUTHORITY_KEYS:
                        out.append((getattr(node, "lineno", -1), name))
    return out


def _direct_state_key(target: ast.AST, key: str) -> bool:
    for node in ast.walk(target):
        if (
            isinstance(node, ast.Subscript)
            and isinstance(node.value, ast.Name)
            and node.value.id == "state"
            and _const_str(node.slice) == key
        ):
            return True
    return False


def _durable_writes(tree: ast.AST) -> list[tuple[int, str]]:
    out: list[tuple[int, str]] = []
    for node in ast.walk(tree):
        targets: list[ast.AST] = []
        if isinstance(node, ast.Assign):
            targets = list(node.targets)
        elif isinstance(node, ast.AnnAssign):
            targets = [node.target]
        elif isinstance(node, ast.AugAssign):
            targets = [node.target]
        else:
            continue
        for target in targets:
            for key in DURABLE_KEYS:
                if _direct_state_key(target, key):
                    out.append((getattr(node, "lineno", -1), key))
    return sorted(set(out))


def _call_name(node: ast.Call) -> str:
    fn = node.func
    if isinstance(fn, ast.Name):
        return fn.id
    if isinstance(fn, ast.Attribute):
        return fn.attr
    return ""


def _calls(tree: ast.AST, name: str) -> list[int]:
    return sorted(
        getattr(node, "lineno", -1)
        for node in ast.walk(tree)
        if isinstance(node, ast.Call) and _call_name(node) == name
    )


def _function(tree: ast.AST, name: str) -> ast.FunctionDef | ast.AsyncFunctionDef | None:
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == name:
            return node
    return None


def _segment(lines: list[str], node: ast.AST) -> str:
    start = max(1, getattr(node, "lineno", 1))
    end = max(start, getattr(node, "end_lineno", start))
    return "\n".join(lines[start - 1:end])


def _positive_store_lines(tree: ast.AST, key: str) -> list[int]:
    rows: list[int] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Assign):
            continue
        if any(_direct_state_key(target, key) for target in node.targets):
            # Reads/statistics are not Assign targets. Every direct assignment to
            # state[key] or state[key][...] is a durable mutation.
            rows.append(getattr(node, "lineno", -1))
    return sorted(rows)


def _has_ancestor_if_with_tokens(
    fn: ast.AST,
    target_line: int,
    required_tokens: tuple[str, ...],
    lines: list[str],
) -> bool:
    parents: dict[ast.AST, ast.AST] = {}
    for parent in ast.walk(fn):
        for child in ast.iter_child_nodes(parent):
            parents[child] = parent
    candidates = [
        node for node in ast.walk(fn)
        if getattr(node, "lineno", -1) == target_line
    ]
    for node in candidates:
        cur = node
        while cur in parents:
            cur = parents[cur]
            if isinstance(cur, ast.If):
                text = _segment(lines, cur.test)
                if all(tok in text for tok in required_tokens):
                    return True
    return False


def verify_certificate(
    *,
    root: Path,
    certificate_path: Path,
    active_claim: Mapping[str, Any],
    root_id: str,
) -> dict[str, Any]:
    errors: list[str] = []
    root = root.resolve()
    claim_id = str(active_claim.get("claim_id") or "")

    if root_id != ROOT_ID:
        return _fail(root_id, claim_id, "ROOT_ID_MISMATCH")
    if claim_id != CLAIM_ID:
        return _fail(root_id, claim_id, "ACTIVE_CLAIM_ID_MISMATCH")

    try:
        certificate = json.loads(certificate_path.read_text(encoding="utf-8"))
    except Exception:
        return _fail(root_id, claim_id, "CERTIFICATE_INVALID_JSON")

    if certificate.get("root_id") != ROOT_ID:
        errors.append("CERTIFICATE_ROOT_ID_MISMATCH")
    if certificate.get("claim_id") != CLAIM_ID:
        errors.append("CERTIFICATE_CLAIM_ID_MISMATCH")
    if certificate.get("terminal_authority") is not False:
        errors.append("CERTIFICATE_TERMINAL_AUTHORITY_NOT_FALSE")
    if (certificate.get("accounting") or {}).get("terminal_credit_delta") != 0:
        errors.append("CERTIFICATE_NONZERO_TERMINAL_CREDIT")

    claim_ref = certificate.get("active_claim") or {}
    claim_path = root / str(claim_ref.get("path") or "")
    if not claim_path.is_file():
        errors.append("ACTIVE_CLAIM_FILE_MISSING")
    else:
        if _blob_sha(claim_path) != claim_ref.get("git_blob_sha"):
            errors.append("ACTIVE_CLAIM_BLOB_MISMATCH")
        try:
            frozen_claim = json.loads(claim_path.read_text(encoding="utf-8"))
        except Exception:
            frozen_claim = {}
            errors.append("ACTIVE_CLAIM_JSON_INVALID")
        if frozen_claim.get("claim_id") != CLAIM_ID:
            errors.append("FROZEN_CLAIM_ID_MISMATCH")
        if frozen_claim.get("scope_sha256") != active_claim.get("scope_sha256"):
            errors.append("ACTIVE_CLAIM_SCOPE_MISMATCH")
        expected_surface = list((frozen_claim.get("scope") or {}).get("bounded_system_surface") or [])
    if errors:
        return _fail(root_id, claim_id, *errors)

    surface = certificate.get("bounded_surface")
    if not isinstance(surface, Mapping):
        return _fail(root_id, claim_id, "BOUNDED_SURFACE_INVALID")
    if set(surface) != set(expected_surface):
        errors.append("CERTIFICATE_SURFACE_NOT_EXACT_ACTIVE_CLAIM_SURFACE")
    if len(surface) != 10:
        errors.append("CERTIFICATE_SURFACE_COUNT_NOT_10")

    trees: dict[str, ast.AST] = {}
    texts: dict[str, str] = {}
    for rel, expected_sha in surface.items():
        p = root / str(rel)
        if not p.is_file():
            errors.append("SURFACE_FILE_MISSING:" + str(rel))
            continue
        actual = _blob_sha(p)
        if actual != expected_sha:
            errors.append("SURFACE_BLOB_MISMATCH:" + str(rel))
            continue
        try:
            text = p.read_text(encoding="utf-8")
            tree = ast.parse(text, filename=str(rel))
        except Exception as exc:
            errors.append("SURFACE_PARSE_FAILED:" + str(rel) + ":" + type(exc).__name__)
            continue
        texts[str(rel)] = text
        trees[str(rel)] = tree

    if errors:
        return _fail(root_id, claim_id, *errors)

    # No file in scope may directly mint authority by literal True.
    elevations: list[str] = []
    for rel, tree in trees.items():
        for line, key in _dict_true_authority_keys(tree):
            elevations.append(f"{rel}:{line}:{key}")
    if elevations:
        errors.extend("DIRECT_AUTHORITY_ELEVATION:" + row for row in elevations)

    # Durable learned-state mutations must be centralized in the main integrator.
    all_writes: dict[str, list[tuple[int, str]]] = {
        rel: _durable_writes(tree) for rel, tree in trees.items()
    }
    for rel, rows in all_writes.items():
        if rel != MAIN and rows:
            errors.append("NONCENTRAL_DURABLE_LEARNING_WRITE:" + rel)
    for rel, tree in trees.items():
        pareto_calls = _calls(tree, "update_pareto_frontier")
        if rel != MAIN and pareto_calls:
            errors.append("NONCENTRAL_PARETO_ADMISSION_CALL:" + rel)
    main_tree = trees.get(MAIN)
    if main_tree is None:
        errors.append("MAIN_INTEGRATOR_MISSING")
        return _fail(root_id, claim_id, *errors)

    fn = _function(main_tree, "integrate_solver_output")
    if fn is None:
        errors.append("INTEGRATE_SOLVER_OUTPUT_MISSING")
        return _fail(root_id, claim_id, *errors)
    main_lines = texts[MAIN].splitlines()

    episode_writes = [
        line for line, key in all_writes[MAIN] if key == "episodes"
    ]
    skill_writes = [
        line for line, key in all_writes[MAIN] if key == "skills"
    ]
    pareto_writes = [
        line for line, key in all_writes[MAIN] if key == "pareto_frontiers"
    ]
    if episode_writes != [1290]:
        errors.append("EPISODE_DURABLE_WRITE_SHAPE_CHANGED")
    if 1486 not in skill_writes:
        errors.append("VERIFIED_SKILL_DURABLE_WRITE_MISSING")
    if 1560 not in pareto_writes:
        errors.append("PARETO_ADMISSION_DURABLE_WRITE_MISSING")

    fn_text = _segment(main_lines, fn)
    anchors = (
        "reauthenticate_episode_record(ep, repo_root=repo_root)",
        'if episode_authority.get("pass") is not True:',
        'state["episodes"][episode_key] = deepcopy(dict(ep))',
        "reauthenticate_skill_record(",
        'if skill_authority.get("pass") is not True:',
        "verified_skill = authenticated_skill",
        'out.get("verified_skill_reuse_authorized") is True',
        'verified_skill.get("verified_skill") is True',
        'verified_skill.get("reuse_authorized") is True',
        "skill_admission = update_pareto_frontier(frontier_rows, row)",
        'state["skills"][sid] = record',
        'state["pareto_frontiers"][family] = sorted(set(admitted_ids))',
    )
    for anchor in anchors:
        if anchor not in fn_text:
            errors.append("MAIN_PROMOTION_GATE_ANCHOR_MISSING:" + anchor)

    # Enforce causal ordering inside exact current function.
    order = [
        "reauthenticate_episode_record(ep, repo_root=repo_root)",
        'if episode_authority.get("pass") is not True:',
        'state["episodes"][episode_key] = deepcopy(dict(ep))',
    ]
    positions = [fn_text.find(x) for x in order]
    if not all(p >= 0 for p in positions) or positions != sorted(positions):
        errors.append("EPISODE_REAUTHENTICATION_ORDER_INVALID")

    skill_order = [
        "reauthenticate_skill_record(",
        'if skill_authority.get("pass") is not True:',
        "verified_skill = authenticated_skill",
        'out.get("verified_skill_reuse_authorized") is True',
        "skill_admission = update_pareto_frontier(frontier_rows, row)",
        'state["skills"][sid] = record',
    ]
    positions = [fn_text.find(x) for x in skill_order]
    if not all(p >= 0 for p in positions) or positions != sorted(positions):
        errors.append("SKILL_REAUTHENTICATION_ORDER_INVALID")

    if not _has_ancestor_if_with_tokens(
        fn, 1290, ("current_episode_verified",), main_lines
    ):
        errors.append("EPISODE_WRITE_NOT_GUARDED_BY_VERIFIED_EPISODE_BRANCH")
    if not _has_ancestor_if_with_tokens(
        fn,
        1486,
        ("verified_skill_reuse_authorized", "verified_skill", "reuse_authorized"),
        main_lines,
    ):
        errors.append("SKILL_WRITE_NOT_GUARDED_BY_VERIFIED_REUSE_BRANCH")

    # Queue-driver promotion must authenticate before calling the central writer.
    queue_text = texts.get(QUEUE, "")
    queue_required = (
        "authenticate_skill_verification(candidate, binding, repo_root=repo_root)",
        'if auth.get("pass") is not True:',
        "verified_skill = auth[",
        "learning.integrate_solver_output(",
    )
    for anchor in queue_required:
        if anchor not in queue_text:
            errors.append("QUEUE_VERIFICATION_FUNNEL_ANCHOR_MISSING:" + anchor)

    # Structural acquisition may expand candidate-generation coverage, never
    # verification/promotion/terminal authority.
    structural_text = texts.get(STRUCTURAL_ACQ, "")
    for anchor in (
        '"authority_requested": "CANDIDATE_ONLY"',
        '"candidate_generation_authority": True',
        '"verification_authority": False',
        '"promotion_authority": False',
        '"terminal_authority": False',
    ):
        if anchor not in structural_text:
            errors.append("STRUCTURAL_ACQUISITION_AUTHORITY_BOUNDARY_MISSING:" + anchor)

    # Other in-scope modules may write queue/observation state but never the
    # durable learned episode/skill/Pareto registries; already checked above.
    if errors:
        return _fail(root_id, claim_id, *errors)

    return {
        "pass": True,
        "status": "PASS__CC_R3_R3_PROMOTION_SAFETY_KERNEL_CHECKED",
        "root_id": ROOT_ID,
        "claim_id": CLAIM_ID,
        "semantic_claim_verified": True,
        "bounded_surface_file_count": len(surface),
        "durable_learning_writer": MAIN,
        "episode_persistence_reauthenticated": True,
        "skill_persistence_reauthenticated": True,
        "pareto_admission_reauthenticated": True,
        "direct_authority_elevation_count": 0,
        "noncentral_durable_learning_writer_count": 0,
        "candidate_acquisition_authority_boundary_verified": True,
        "future_bytes_covered": False,
        "global_mission_completion_derivable": False,
        "terminal_credit_delta": 0,
        "errors": [],
    }
