#!/usr/bin/env python3
"""Independent GA+beta schema snapshot verifier for the frozen Opus 5.5 route.

The verifier refetches every source file declared by the canonical snapshot from
the official Anthropic SDK tag, computes Git blob object hashes locally, and
reconstructs the snapshot's typed unions/control-state partitions from Python AST.

It intentionally does not prove product/profile completeness, beta admissibility,
Brain encoder totality, or performance dominance.
"""
from __future__ import annotations

import ast
import hashlib
import json
import sys
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any

SNAPSHOT_PATH = Path(
    "canonical/governance/OPUS55_FIRST_PARTY_SDK_TYPED_SCHEMA_SNAPSHOT_20261005_V1.json"
)
EXPECTED_REPOSITORY = "anthropics/anthropic-sdk-python"
EXPECTED_REF = "v1.11.0"


class VerificationError(RuntimeError):
    pass


def fail(reason: str) -> None:
    raise VerificationError(reason)


def git_blob_sha(data: bytes) -> str:
    return hashlib.sha1(
        b"blob " + str(len(data)).encode("ascii") + b"\0" + data
    ).hexdigest()


def fetch_raw(repo: str, ref: str, path: str) -> bytes:
    qref = urllib.parse.quote(ref, safe="")
    qpath = urllib.parse.quote(path, safe="/")
    url = f"https://raw.githubusercontent.com/{repo}/{qref}/{qpath}"
    req = urllib.request.Request(
        url,
        headers={"User-Agent": "project-brain-opus55-sdk-schema-verifier-v2"},
    )
    with urllib.request.urlopen(req, timeout=30) as response:
        data = response.read()
    if not data:
        fail("EMPTY_SOURCE:" + path)
    return data


def parse(source: str, path: str) -> ast.Module:
    try:
        return ast.parse(source, filename=path)
    except Exception as exc:
        fail("PARSE_FAILURE:" + path + ":" + type(exc).__name__ + ":" + str(exc))


def name_of(node: ast.AST) -> str | None:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        return node.attr
    return None


def direct_subscript_items(node: ast.Subscript) -> list[ast.AST]:
    return list(node.slice.elts) if isinstance(node.slice, ast.Tuple) else [node.slice]


def all_subscripts(root: ast.AST, target: str) -> list[ast.Subscript]:
    out: list[ast.Subscript] = []
    for node in ast.walk(root):
        if isinstance(node, ast.Subscript) and name_of(node.value) == target:
            out.append(node)
    return out


def direct_names(node: ast.Subscript) -> set[str]:
    out: set[str] = set()
    for item in direct_subscript_items(node):
        name = name_of(item)
        if name is not None:
            out.add(name)
    return out


def largest_union_names(root: ast.AST) -> set[str]:
    candidates = [(direct_names(node), node) for node in all_subscripts(root, "Union")]
    if not candidates:
        fail("UNION_NOT_FOUND")
    names, _node = max(candidates, key=lambda item: len(item[0]))
    if not names:
        fail("UNION_HAS_NO_DIRECT_NAMES")
    return names


def assignment_expr(tree: ast.Module, target: str) -> ast.AST:
    for node in tree.body:
        if isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
            if node.target.id == target and node.value is not None:
                return node.value
        if isinstance(node, ast.Assign):
            if any(isinstance(t, ast.Name) and t.id == target for t in node.targets):
                return node.value
    fail("ASSIGNMENT_NOT_FOUND:" + target)


def type_alias_union(source: str, path: str, target: str) -> set[str]:
    tree = parse(source, path)
    expr = assignment_expr(tree, target)
    return largest_union_names(expr)


def literal_assignment(source: str, path: str, target: str) -> set[str]:
    tree = parse(source, path)
    expr = assignment_expr(tree, target)
    literals = all_subscripts(expr, "Literal")
    if not literals:
        fail("LITERAL_NOT_FOUND:" + target)
    values: set[str] = set()
    for item in direct_subscript_items(max(literals, key=lambda x: len(direct_subscript_items(x)))):
        if not isinstance(item, ast.Constant) or not isinstance(item.value, str):
            fail("LITERAL_NON_STRING:" + target)
        values.add(item.value)
    return values


def class_node(source: str, path: str, class_name: str) -> ast.ClassDef:
    tree = parse(source, path)
    for node in tree.body:
        if isinstance(node, ast.ClassDef) and node.name == class_name:
            return node
    fail("CLASS_NOT_FOUND:" + class_name)


def class_fields(source: str, path: str, class_name: str) -> set[str]:
    node = class_node(source, path, class_name)
    return {
        stmt.target.id
        for stmt in node.body
        if isinstance(stmt, ast.AnnAssign) and isinstance(stmt.target, ast.Name)
    }


def class_field_annotation(
    source: str, path: str, class_name: str, field_name: str
) -> ast.AST:
    node = class_node(source, path, class_name)
    for stmt in node.body:
        if (
            isinstance(stmt, ast.AnnAssign)
            and isinstance(stmt.target, ast.Name)
            and stmt.target.id == field_name
        ):
            return stmt.annotation
    fail("CLASS_FIELD_NOT_FOUND:" + class_name + ":" + field_name)


def class_field_largest_union(
    source: str, path: str, class_name: str, field_name: str
) -> set[str]:
    return largest_union_names(
        class_field_annotation(source, path, class_name, field_name)
    )


def as_set(value: Any, label: str) -> set[str]:
    if not isinstance(value, list) or any(not isinstance(x, str) for x in value):
        fail("SNAPSHOT_LIST_INVALID:" + label)
    if len(value) != len(set(value)):
        fail("SNAPSHOT_LIST_DUPLICATE:" + label)
    return set(value)


def source_file_map(snapshot: dict[str, Any]) -> dict[str, str]:
    exact = snapshot.get("exact_source_files")
    if not isinstance(exact, dict):
        fail("EXACT_SOURCE_FILES_INVALID")
    out: dict[str, str] = {}
    for lane in ("ga", "beta"):
        rows = exact.get(lane)
        if not isinstance(rows, list) or not rows:
            fail("SOURCE_LANE_INVALID:" + lane)
        for row in rows:
            if not isinstance(row, dict):
                fail("SOURCE_ROW_INVALID:" + lane)
            path = row.get("path")
            sha = row.get("git_blob_sha")
            if not isinstance(path, str) or not path.startswith("src/anthropic/"):
                fail("SOURCE_PATH_INVALID:" + lane)
            if not isinstance(sha, str) or len(sha) != 40:
                fail("SOURCE_SHA_INVALID:" + path)
            if path in out:
                fail("SOURCE_PATH_DUPLICATE:" + path)
            out[path] = sha
    return out


def require_text(texts: dict[str, str], path: str) -> str:
    if path not in texts:
        fail("REQUIRED_BOUND_SOURCE_MISSING:" + path)
    return texts[path]


def verify() -> dict[str, Any]:
    snapshot = json.loads(SNAPSHOT_PATH.read_text(encoding="utf-8"))
    source = snapshot.get("source") or {}
    if source.get("repository") != EXPECTED_REPOSITORY:
        fail("SOURCE_REPOSITORY_DRIFT")
    if source.get("ref") != EXPECTED_REF:
        fail("SOURCE_REF_DRIFT")

    expected_files = source_file_map(snapshot)
    texts: dict[str, str] = {}
    actual_blobs: dict[str, str] = {}

    for path, expected_sha in sorted(expected_files.items()):
        data = fetch_raw(EXPECTED_REPOSITORY, EXPECTED_REF, path)
        actual_sha = git_blob_sha(data)
        if actual_sha != expected_sha:
            fail(
                "BLOB_SHA_MISMATCH:"
                + path
                + ":"
                + actual_sha
                + ":"
                + expected_sha
            )
        actual_blobs[path] = actual_sha
        try:
            texts[path] = data.decode("utf-8")
        except Exception as exc:
            fail("UTF8_DECODE_FAILURE:" + path + ":" + str(exc))

    p_ga_msg = "src/anthropic/types/message_param.py"
    p_ga_content = "src/anthropic/types/content_block.py"
    p_ga_stop = "src/anthropic/types/stop_reason.py"
    p_ga_create = "src/anthropic/types/message_create_params.py"
    p_ga_response = "src/anthropic/types/message.py"

    p_beta_msg = "src/anthropic/types/beta/beta_message_param.py"
    p_beta_content_param = "src/anthropic/types/beta/beta_content_block_param.py"
    p_beta_content = "src/anthropic/types/beta/beta_content_block.py"
    p_beta_stop = "src/anthropic/types/beta/beta_stop_reason.py"
    p_beta_transform = "src/anthropic/types/beta/beta_input_transformation.py"
    p_beta_create = "src/anthropic/types/beta/message_create_params.py"
    p_beta_response = "src/anthropic/types/beta/beta_message.py"

    reconstructed = {
        "ga_request_message_content": class_field_largest_union(
            require_text(texts, p_ga_msg), p_ga_msg, "MessageParam", "content"
        ),
        "ga_response_content": type_alias_union(
            require_text(texts, p_ga_content), p_ga_content, "ContentBlock"
        ),
        "ga_stop_reasons": literal_assignment(
            require_text(texts, p_ga_stop), p_ga_stop, "StopReason"
        ),
        "beta_request_message_content": type_alias_union(
            require_text(texts, p_beta_content_param),
            p_beta_content_param,
            "BetaContentBlockParam",
        ),
        "beta_response_content": type_alias_union(
            require_text(texts, p_beta_content), p_beta_content, "BetaContentBlock"
        ),
        "beta_stop_reasons": literal_assignment(
            require_text(texts, p_beta_stop), p_beta_stop, "BetaStopReason"
        ),
        "beta_input_transformations": type_alias_union(
            require_text(texts, p_beta_transform),
            p_beta_transform,
            "BetaInputTransformation",
        ),
    }

    declared_unions = snapshot.get("extracted_typed_unions")
    if not isinstance(declared_unions, dict):
        fail("EXTRACTED_TYPED_UNIONS_INVALID")

    union_checks: dict[str, bool] = {}
    for key, actual in reconstructed.items():
        expected = as_set(declared_unions.get(key), key)
        union_checks[key] = actual == expected

    ga_create = require_text(texts, p_ga_create)
    beta_create = require_text(texts, p_beta_create)
    ga_msg = require_text(texts, p_ga_msg)
    beta_msg = require_text(texts, p_beta_msg)
    ga_response = require_text(texts, p_ga_response)
    beta_response = require_text(texts, p_beta_response)

    ga_request_fields = class_fields(
        ga_create, p_ga_create, "MessageCreateParamsBase"
    ) | class_fields(
        ga_create, p_ga_create, "MessageCreateParamsNonStreaming"
    ) | class_fields(
        ga_create, p_ga_create, "MessageCreateParamsStreaming"
    )
    ga_response_fields = class_fields(ga_response, p_ga_response, "Message") - {
        "id",
        "type",
    }

    beta_request_fields = class_fields(
        beta_create, p_beta_create, "MessageCreateParamsBase"
    ) | class_fields(
        beta_create, p_beta_create, "MessageCreateParamsNonStreaming"
    ) | class_fields(
        beta_create, p_beta_create, "MessageCreateParamsStreaming"
    )
    beta_message_fields = class_fields(beta_msg, p_beta_msg, "BetaMessageParam")
    ga_message_fields = class_fields(ga_msg, p_ga_msg, "MessageParam")
    beta_response_fields = class_fields(beta_response, p_beta_response, "BetaMessage") - {
        "id",
        "type",
    }

    reconstructed_control = {
        "ga_request": ga_request_fields,
        "ga_response": ga_response_fields,
        "beta_request_additions_or_variants": beta_request_fields - ga_request_fields,
        "beta_message_level_additions": beta_message_fields - ga_message_fields,
        "beta_response_additions_or_variants": beta_response_fields - ga_response_fields,
    }

    declared_control = snapshot.get("top_level_control_and_state_surface")
    if not isinstance(declared_control, dict):
        fail("TOP_LEVEL_CONTROL_SURFACE_INVALID")

    control_checks: dict[str, bool] = {}
    for key, actual in reconstructed_control.items():
        expected = as_set(declared_control.get(key), key)
        control_checks[key] = actual == expected

    failed = sorted(
        [f"union:{key}" for key, ok in union_checks.items() if not ok]
        + [f"control:{key}" for key, ok in control_checks.items() if not ok]
    )
    if failed:
        diagnostics = {
            "failed": failed,
            "reconstructed_unions": {
                key: sorted(value) for key, value in reconstructed.items()
            },
            "reconstructed_control": {
                key: sorted(value) for key, value in reconstructed_control.items()
            },
        }
        fail("SNAPSHOT_RECONSTRUCTION_MISMATCH:" + json.dumps(diagnostics, sort_keys=True))

    return {
        "schema": "PROJECT_BRAIN_OPUS55_FIRST_PARTY_SDK_TYPED_SCHEMA_SNAPSHOT_VERIFIER_V2",
        "status": "PASS__ALL_BOUND_BLOBS_AND_DECLARED_TYPED_UNIONS_CONTROL_PARTITIONS_RECONSTRUCTED",
        "repository": EXPECTED_REPOSITORY,
        "ref": EXPECTED_REF,
        "bound_blob_count": len(actual_blobs),
        "blob_shas": actual_blobs,
        "typed_union_checks": union_checks,
        "control_state_checks": control_checks,
        "reconstructed_typed_unions": {
            key: sorted(value) for key, value in reconstructed.items()
        },
        "reconstructed_control_state_surface": {
            key: sorted(value) for key, value in reconstructed_control.items()
        },
        "acceptance_credit_delta": 0,
        "family_credit_delta": 0,
        "capability_credit_delta": 0,
        "ownership_credit_delta": 0,
        "hard_nonclaims": [
            "NO_PROFILE_COMPLETENESS_PROOF",
            "NO_BETA_ADMISSIBILITY_PROOF",
            "NO_TOTAL_BRAIN_IR_ENCODER_PROOF",
            "NO_PERFORMANCE_DOMINANCE_PROOF",
            "NO_TARGET_DISCOVERY_ACCEPTANCE_FAMILY_CAPABILITY_OR_OWNERSHIP_CREDIT",
            "NO_TERMINAL_FINALITY",
        ],
    }


def main() -> int:
    try:
        result = verify()
    except Exception as exc:
        print(
            json.dumps(
                {
                    "schema": "PROJECT_BRAIN_OPUS55_FIRST_PARTY_SDK_TYPED_SCHEMA_SNAPSHOT_VERIFIER_V2",
                    "status": "FAIL_CLOSED",
                    "reason": type(exc).__name__ + ":" + str(exc),
                    "acceptance_credit_delta": 0,
                },
                sort_keys=True,
            )
        )
        return 1

    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
