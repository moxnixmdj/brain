#!/usr/bin/env python3
"""Independent verifier for the Opus 5.5 content-addressed typed protocol snapshot.

This verifies only the finite pinned SDK snapshot and its mechanically declared
type/control sets. It deliberately grants zero target-coverage or performance
credit and does not claim full semantic completeness.
"""
from __future__ import annotations

import ast
import base64
import json
import sys
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any

MANIFEST_PATH = Path(
    "canonical/governance/OPUS55_CONTENT_ADDRESSED_TYPED_PROTOCOL_MANIFEST_20261005_V1.json"
)
EXPECTED_REPO = "anthropics/anthropic-sdk-python"
EXPECTED_COMMIT = "18f25547f20cf5f01da69ac611e700e3bc9ebf21"
EXPECTED_FILES = {
    "src/anthropic/types/content_block.py": "a0baaeb69bab7c74ae6e6aa9613f3381ad416811",
    "src/anthropic/types/content_block_param.py": "b6a481a0ab64424475760b6e63316ed9177dc532",
    "src/anthropic/types/stop_reason.py": "d28f681b8464057da3ddac61a83548e266880e10",
    "src/anthropic/types/message.py": "34dc178ccec1f6b49bfacd0743dcd18689bc3c0d",
    "src/anthropic/types/message_param.py": "c3a2046f2ad752cd87722fac4bae8545e317d474",
}
EXPECTED_RESPONSE_UNION = {
    "TextBlock",
    "ThinkingBlock",
    "RedactedThinkingBlock",
    "ToolUseBlock",
    "ServerToolUseBlock",
    "WebSearchToolResultBlock",
    "WebFetchToolResultBlock",
    "CodeExecutionToolResultBlock",
    "BashCodeExecutionToolResultBlock",
    "TextEditorCodeExecutionToolResultBlock",
    "ToolSearchToolResultBlock",
    "ContainerUploadBlock",
}
EXPECTED_REQUEST_UNION = {
    "TextBlockParam",
    "ImageBlockParam",
    "DocumentBlockParam",
    "SearchResultBlockParam",
    "ThinkingBlockParam",
    "RedactedThinkingBlockParam",
    "ToolUseBlockParam",
    "ToolResultBlockParam",
    "ServerToolUseBlockParam",
    "WebSearchToolResultBlockParam",
    "WebFetchToolResultBlockParam",
    "CodeExecutionToolResultBlockParam",
    "BashCodeExecutionToolResultBlockParam",
    "TextEditorCodeExecutionToolResultBlockParam",
    "ToolSearchToolResultBlockParam",
    "ContainerUploadBlockParam",
}
EXPECTED_STOP_REASONS = {
    "end_turn",
    "max_tokens",
    "stop_sequence",
    "tool_use",
    "pause_turn",
    "refusal",
    "model_context_window_exceeded",
}
EXPECTED_MESSAGE_FIELDS_NEEDING_CLASSIFICATION = {
    "container",
    "diagnostics",
    "model",
    "role",
    "stop_details",
    "stop_reason",
    "stop_sequence",
    "usage",
}
EXPECTED_MESSAGE_PARAM_ROLES = {"user", "assistant", "system"}


class VerificationError(RuntimeError):
    pass


def fail(reason: str) -> None:
    raise VerificationError(reason)


def _name(node: ast.AST) -> str | None:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        return node.attr
    return None


def _find_subscript(node: ast.AST, target: str) -> ast.Subscript | None:
    if isinstance(node, ast.Subscript) and _name(node.value) == target:
        return node
    for child in ast.iter_child_nodes(node):
        hit = _find_subscript(child, target)
        if hit is not None:
            return hit
    return None


def _slice_elts(node: ast.Subscript) -> list[ast.AST]:
    sl = node.slice
    if isinstance(sl, ast.Tuple):
        return list(sl.elts)
    return [sl]


def _assigned_expr(tree: ast.Module, target: str) -> ast.AST:
    for node in tree.body:
        if isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
            if node.target.id == target and node.value is not None:
                return node.value
        if isinstance(node, ast.Assign):
            if any(isinstance(t, ast.Name) and t.id == target for t in node.targets):
                return node.value
    fail("ASSIGNMENT_NOT_FOUND:" + target)


def _union_names(source: str, target: str) -> set[str]:
    tree = ast.parse(source)
    expr = _assigned_expr(tree, target)
    union = _find_subscript(expr, "Union")
    if union is None:
        fail("UNION_NOT_FOUND:" + target)
    out = {_name(x) for x in _slice_elts(union)}
    if None in out:
        fail("UNION_NON_NAME_MEMBER:" + target)
    return {str(x) for x in out}


def _literal_strings_from_expr(expr: ast.AST) -> set[str]:
    literal = _find_subscript(expr, "Literal")
    if literal is None:
        return set()
    out: set[str] = set()
    for item in _slice_elts(literal):
        if isinstance(item, ast.Constant) and isinstance(item.value, str):
            out.add(item.value)
        else:
            fail("LITERAL_NON_STRING_MEMBER")
    return out


def _literal_assignment(source: str, target: str) -> set[str]:
    tree = ast.parse(source)
    return _literal_strings_from_expr(_assigned_expr(tree, target))


def _class_fields(source: str, class_name: str) -> set[str]:
    tree = ast.parse(source)
    for node in tree.body:
        if isinstance(node, ast.ClassDef) and node.name == class_name:
            return {
                child.target.id
                for child in node.body
                if isinstance(child, ast.AnnAssign)
                and isinstance(child.target, ast.Name)
            }
    fail("CLASS_NOT_FOUND:" + class_name)


def _class_field_literal(source: str, class_name: str, field: str) -> set[str]:
    tree = ast.parse(source)
    for node in tree.body:
        if isinstance(node, ast.ClassDef) and node.name == class_name:
            for child in node.body:
                if (
                    isinstance(child, ast.AnnAssign)
                    and isinstance(child.target, ast.Name)
                    and child.target.id == field
                ):
                    return _literal_strings_from_expr(child.annotation)
    fail("CLASS_FIELD_NOT_FOUND:" + class_name + ":" + field)


def _fetch_public_github_file(repo: str, ref: str, path: str) -> tuple[str, str]:
    qpath = urllib.parse.quote(path, safe="/")
    qref = urllib.parse.quote(ref, safe="")
    url = f"https://api.github.com/repos/{repo}/contents/{qpath}?ref={qref}"
    req = urllib.request.Request(
        url,
        headers={
            "Accept": "application/vnd.github+json",
            "User-Agent": "project-brain-opus55-protocol-verifier-v1",
            "X-GitHub-Api-Version": "2022-11-28",
        },
    )
    with urllib.request.urlopen(req, timeout=30) as response:
        payload = json.loads(response.read().decode("utf-8"))
    if payload.get("encoding") != "base64" or not isinstance(payload.get("content"), str):
        fail("GITHUB_CONTENT_ENCODING_INVALID:" + path)
    raw = base64.b64decode(payload["content"]).decode("utf-8")
    sha = str(payload.get("sha") or "")
    if not sha:
        fail("GITHUB_BLOB_SHA_MISSING:" + path)
    return sha, raw


def _manifest_file_map(manifest: dict[str, Any]) -> dict[str, str]:
    files = ((manifest.get("source") or {}).get("files") or [])
    out: dict[str, str] = {}
    for row in files:
        if not isinstance(row, list) or len(row) != 2:
            fail("MANIFEST_FILE_ROW_INVALID")
        out[str(row[0])] = str(row[1])
    return out


def verify() -> dict[str, Any]:
    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    source = manifest.get("source") or {}
    if source.get("repository") != EXPECTED_REPO:
        fail("SOURCE_REPOSITORY_DRIFT")
    if source.get("release_commit_sha") != EXPECTED_COMMIT:
        fail("SOURCE_COMMIT_DRIFT")
    if _manifest_file_map(manifest) != EXPECTED_FILES:
        fail("MANIFEST_FILE_SET_OR_SHA_DRIFT")

    fetched: dict[str, str] = {}
    texts: dict[str, str] = {}
    for path, expected_sha in EXPECTED_FILES.items():
        actual_sha, source_text = _fetch_public_github_file(
            EXPECTED_REPO, EXPECTED_COMMIT, path
        )
        if actual_sha != expected_sha:
            fail(f"BLOB_SHA_MISMATCH:{path}:{actual_sha}:{expected_sha}")
        fetched[path] = actual_sha
        texts[path] = source_text

    response_union = _union_names(
        texts["src/anthropic/types/content_block.py"], "ContentBlock"
    )
    request_union = _union_names(
        texts["src/anthropic/types/content_block_param.py"], "ContentBlockParam"
    )
    stop_reasons = _literal_assignment(
        texts["src/anthropic/types/stop_reason.py"], "StopReason"
    )
    message_fields = _class_fields(
        texts["src/anthropic/types/message.py"], "Message"
    )
    message_fields_needing_classification = message_fields - {"id", "content", "type"}
    message_param_roles = _class_field_literal(
        texts["src/anthropic/types/message_param.py"], "MessageParam", "role"
    )

    exact = manifest.get("exact_sets") or {}
    checks = {
        "response_union_source": response_union == EXPECTED_RESPONSE_UNION,
        "response_union_manifest": set(exact.get("response_content_union") or [])
        == response_union,
        "request_union_source": request_union == EXPECTED_REQUEST_UNION,
        "request_union_manifest": set(exact.get("request_content_param_union") or [])
        == request_union,
        "stop_reasons_source": stop_reasons == EXPECTED_STOP_REASONS,
        "stop_reasons_manifest": set(exact.get("stop_reason_union") or [])
        == stop_reasons,
        "message_fields_source": message_fields_needing_classification
        == EXPECTED_MESSAGE_FIELDS_NEEDING_CLASSIFICATION,
        "message_fields_manifest": set(
            exact.get("message_fields_needing_load_bearing_classification") or []
        )
        == message_fields_needing_classification,
        "message_param_roles_include_sdk_system": message_param_roles
        == EXPECTED_MESSAGE_PARAM_ROLES,
    }
    failed = sorted(name for name, ok in checks.items() if not ok)
    if failed:
        fail("SEMANTIC_SET_MISMATCH:" + ",".join(failed))

    return {
        "schema": "PROJECT_BRAIN_OPUS55_CONTENT_ADDRESSED_TYPED_PROTOCOL_MANIFEST_VERIFIER_V1",
        "status": "PASS__PINNED_SDK_SNAPSHOT_INTEGRITY_AND_DECLARED_SET_RECONSTRUCTION_ONLY",
        "repository": EXPECTED_REPO,
        "commit": EXPECTED_COMMIT,
        "blob_shas": fetched,
        "response_content_union": sorted(response_union),
        "request_content_param_union": sorted(request_union),
        "stop_reason_union": sorted(stop_reasons),
        "message_fields_needing_load_bearing_classification": sorted(
            message_fields_needing_classification
        ),
        "message_param_roles": sorted(message_param_roles),
        "checks": checks,
        "acceptance_credit_delta": 0,
        "family_credit_delta": 0,
        "capability_credit_delta": 0,
        "ownership_credit_delta": 0,
        "hard_nonclaims": [
            "NO_TARGET_COVERAGE_CREDIT",
            "NO_PERFORMANCE_CREDIT",
            "NO_TOTAL_LOSSLESS_NORMALIZATION_PROOF",
            "NO_W3_ACTIVATION",
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
                    "schema": "PROJECT_BRAIN_OPUS55_CONTENT_ADDRESSED_TYPED_PROTOCOL_MANIFEST_VERIFIER_V1",
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
