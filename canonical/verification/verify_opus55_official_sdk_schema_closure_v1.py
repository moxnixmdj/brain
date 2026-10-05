#!/usr/bin/env python3
from __future__ import annotations

import argparse
import ast
import hashlib
import json
import pathlib
import urllib.request

UPSTREAM_REPO = "anthropics/anthropic-sdk-python"
UPSTREAM_COMMIT = "18f25547f20cf5f01da69ac611e700e3bc9ebf21"

FILES = {
    "stable_output": ("src/anthropic/types/content_block.py", "a0baaeb69bab7c74ae6e6aa9613f3381ad416811", "ContentBlock"),
    "stable_input": ("src/anthropic/types/content_block_param.py", "b6a481a0ab64424475760b6e63316ed9177dc532", "ContentBlockParam"),
    "stable_stop": ("src/anthropic/types/stop_reason.py", "d28f681b8464057da3ddac61a83548e266880e10", "StopReason"),
    "stable_request": ("src/anthropic/types/message_create_params.py", "585e92451d6399aba980aff392fbc0ba942e85d4", "MessageCreateParamsBase"),
    "beta_output": ("src/anthropic/types/beta/beta_content_block.py", "8034b978b7fdb990faf0e3c9fdb0e1a338817f2d", "BetaContentBlock"),
    "beta_input": ("src/anthropic/types/beta/beta_content_block_param.py", "84f0e1466477a278371f88b507ae86ab308ba8d1", "BetaContentBlockParam"),
    "beta_stop": ("src/anthropic/types/beta/beta_stop_reason.py", "f3d0d3070d0eac3065917a5d11cbbc935faebeb8", "BetaStopReason"),
    "beta_request": ("src/anthropic/types/beta/message_create_params.py", "7f688b24dfc9744f5e0df2678c5fe0bba1b50f44", "MessageCreateParamsBase"),
}

EXPECTED = {
    "stable_output": {
        "TextBlock", "ThinkingBlock", "RedactedThinkingBlock", "ToolUseBlock",
        "ServerToolUseBlock", "WebSearchToolResultBlock", "WebFetchToolResultBlock",
        "CodeExecutionToolResultBlock", "BashCodeExecutionToolResultBlock",
        "TextEditorCodeExecutionToolResultBlock", "ToolSearchToolResultBlock",
        "ContainerUploadBlock",
    },
    "stable_input": {
        "TextBlockParam", "ImageBlockParam", "DocumentBlockParam", "SearchResultBlockParam",
        "ThinkingBlockParam", "RedactedThinkingBlockParam", "ToolUseBlockParam",
        "ToolResultBlockParam", "ServerToolUseBlockParam", "WebSearchToolResultBlockParam",
        "WebFetchToolResultBlockParam", "CodeExecutionToolResultBlockParam",
        "BashCodeExecutionToolResultBlockParam", "TextEditorCodeExecutionToolResultBlockParam",
        "ToolSearchToolResultBlockParam", "ContainerUploadBlockParam",
    },
    "stable_stop": {
        "end_turn", "max_tokens", "stop_sequence", "tool_use", "pause_turn",
        "refusal", "model_context_window_exceeded",
    },
    "beta_output": {
        "BetaTextBlock", "BetaThinkingBlock", "BetaRedactedThinkingBlock", "BetaToolUseBlock",
        "BetaServerToolUseBlock", "BetaWebSearchToolResultBlock", "BetaWebFetchToolResultBlock",
        "BetaAdvisorToolResultBlock", "BetaCodeExecutionToolResultBlock",
        "BetaBashCodeExecutionToolResultBlock", "BetaTextEditorCodeExecutionToolResultBlock",
        "BetaToolSearchToolResultBlock", "BetaMCPToolUseBlock", "BetaMCPToolResultBlock",
        "BetaContainerUploadBlock", "BetaCompactionBlock", "BetaFallbackBlock",
        "BetaMCPToolListingBlock",
    },
    "beta_input": {
        "BetaTextBlockParam", "BetaImageBlockParam", "BetaRequestDocumentBlockParam",
        "BetaSearchResultBlockParam", "BetaThinkingBlockParam", "BetaRedactedThinkingBlockParam",
        "BetaToolUseBlockParam", "BetaToolResultBlockParam", "BetaServerToolUseBlockParam",
        "BetaWebSearchToolResultBlockParam", "BetaWebFetchToolResultBlockParam",
        "BetaAdvisorToolResultBlockParam", "BetaCodeExecutionToolResultBlockParam",
        "BetaBashCodeExecutionToolResultBlockParam", "BetaTextEditorCodeExecutionToolResultBlockParam",
        "BetaToolSearchToolResultBlockParam", "BetaMCPToolUseBlockParam",
        "BetaRequestMCPToolResultBlockParam", "BetaContainerUploadBlockParam",
        "BetaCompactionBlockParam", "BetaRequestToolAdditionBlockParam",
        "BetaRequestToolRemovalBlockParam", "BetaMCPToolListingBlockParam",
        "BetaFallbackBlockParam", "BetaContentBlock",
    },
    "beta_stop": {
        "end_turn", "max_tokens", "stop_sequence", "tool_use", "pause_turn", "compaction",
        "refusal", "model_context_window_exceeded",
    },
}

LOAD_BEARING_BETA_ONLY_REQUEST_FIELDS = {
    "compaction", "context_management", "fallback_credit_token", "fallbacks",
    "mcp_servers", "speed", "betas",
}


def git_blob_sha(data: bytes) -> str:
    header = f"blob {len(data)}\0".encode("ascii")
    return hashlib.sha1(header + data).hexdigest()


def fetch(path: str, source_dir: pathlib.Path | None) -> bytes:
    if source_dir is not None:
        return (source_dir / path).read_bytes()
    url = f"https://raw.githubusercontent.com/{UPSTREAM_REPO}/{UPSTREAM_COMMIT}/{path}"
    req = urllib.request.Request(url, headers={"User-Agent": "project-brain-schema-verifier/1"})
    with urllib.request.urlopen(req, timeout=30) as response:
        return response.read()


def _slice_items(node: ast.Subscript) -> list[ast.AST]:
    sl = node.slice
    return list(sl.elts) if isinstance(sl, ast.Tuple) else [sl]


def _find_assignment(tree: ast.Module, name: str) -> ast.AST:
    for stmt in tree.body:
        if isinstance(stmt, ast.Assign):
            if any(isinstance(t, ast.Name) and t.id == name for t in stmt.targets):
                return stmt.value
        elif isinstance(stmt, ast.AnnAssign) and isinstance(stmt.target, ast.Name) and stmt.target.id == name:
            if stmt.value is not None:
                return stmt.value
    raise ValueError(f"ASSIGNMENT_NOT_FOUND:{name}")


def _unwrap_annotated(node: ast.AST) -> ast.AST:
    if isinstance(node, ast.Subscript) and isinstance(node.value, ast.Name) and node.value.id == "Annotated":
        return _slice_items(node)[0]
    return node


def union_names(source: str, alias: str) -> set[str]:
    node = _unwrap_annotated(_find_assignment(ast.parse(source), alias))
    if not (isinstance(node, ast.Subscript) and isinstance(node.value, ast.Name) and node.value.id == "Union"):
        raise ValueError(f"NOT_UNION:{alias}")
    result = set()
    for item in _slice_items(node):
        if not isinstance(item, ast.Name):
            raise ValueError(f"NON_NAME_UNION_MEMBER:{alias}:{ast.dump(item, include_attributes=False)}")
        result.add(item.id)
    return result


def literal_strings(source: str, alias: str) -> set[str]:
    node = _find_assignment(ast.parse(source), alias)
    if not (isinstance(node, ast.Subscript) and isinstance(node.value, ast.Name) and node.value.id == "Literal"):
        raise ValueError(f"NOT_LITERAL:{alias}")
    result = set()
    for item in _slice_items(node):
        if not (isinstance(item, ast.Constant) and isinstance(item.value, str)):
            raise ValueError(f"NON_STRING_LITERAL:{alias}:{ast.dump(item, include_attributes=False)}")
        result.add(item.value)
    return result


def class_annotated_fields(source: str, class_name: str) -> set[str]:
    tree = ast.parse(source)
    for stmt in tree.body:
        if isinstance(stmt, ast.ClassDef) and stmt.name == class_name:
            return {
                child.target.id
                for child in stmt.body
                if isinstance(child, ast.AnnAssign) and isinstance(child.target, ast.Name)
            }
    raise ValueError(f"CLASS_NOT_FOUND:{class_name}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-dir", type=pathlib.Path, default=None)
    args = parser.parse_args()

    verdict = {
        "schema": "PROJECT_BRAIN_OPUS55_OFFICIAL_SDK_SCHEMA_CLOSURE_VERIFIER_V1",
        "upstream_repository": UPSTREAM_REPO,
        "upstream_commit": UPSTREAM_COMMIT,
        "status": "FAIL_CLOSED",
        "reasons": [],
        "observed": {},
        "credit": {"acceptance": 0, "family": 0, "capability": 0, "ownership": 0},
    }

    try:
        sources: dict[str, str] = {}
        for key, (path, expected_sha, _symbol) in FILES.items():
            data = fetch(path, args.source_dir)
            actual_sha = git_blob_sha(data)
            if actual_sha != expected_sha:
                verdict["reasons"].append(f"BLOB_DRIFT:{key}:{actual_sha}!={expected_sha}")
            sources[key] = data.decode("utf-8")
            verdict["observed"][f"{key}_blob"] = actual_sha

        for key in ("stable_output", "stable_input", "beta_output", "beta_input"):
            symbol = FILES[key][2]
            observed = union_names(sources[key], symbol)
            verdict["observed"][key] = sorted(observed)
            if observed != EXPECTED[key]:
                verdict["reasons"].append(
                    f"UNION_DRIFT:{key}:missing={sorted(EXPECTED[key]-observed)}:extra={sorted(observed-EXPECTED[key])}"
                )

        for key in ("stable_stop", "beta_stop"):
            symbol = FILES[key][2]
            observed = literal_strings(sources[key], symbol)
            verdict["observed"][key] = sorted(observed)
            if observed != EXPECTED[key]:
                verdict["reasons"].append(
                    f"STOP_REASON_DRIFT:{key}:missing={sorted(EXPECTED[key]-observed)}:extra={sorted(observed-EXPECTED[key])}"
                )

        stable_fields = class_annotated_fields(sources["stable_request"], "MessageCreateParamsBase")
        beta_fields = class_annotated_fields(sources["beta_request"], "MessageCreateParamsBase")
        beta_only = beta_fields - stable_fields
        verdict["observed"]["stable_request_fields"] = sorted(stable_fields)
        verdict["observed"]["beta_request_fields"] = sorted(beta_fields)
        verdict["observed"]["beta_only_request_fields"] = sorted(beta_only)
        missing_load_bearing = LOAD_BEARING_BETA_ONLY_REQUEST_FIELDS - beta_only
        if missing_load_bearing:
            verdict["reasons"].append(
                f"LOAD_BEARING_BETA_ONLY_FIELDS_MISSING:{sorted(missing_load_bearing)}"
            )

        if EXPECTED["stable_stop"] == EXPECTED["beta_stop"]:
            verdict["reasons"].append("BETA_STOP_DOMAIN_NOT_STRICTLY_DIFFERENT")
        if "compaction" not in EXPECTED["beta_stop"] or "compaction" in EXPECTED["stable_stop"]:
            verdict["reasons"].append("COMPACTION_SEPARATION_NOT_ESTABLISHED")
        if not (EXPECTED["beta_output"] - {"Beta" + x for x in EXPECTED["stable_output"]}):
            verdict["reasons"].append("NO_BETA_ONLY_OUTPUT_CLASS_ESTABLISHED")

        if not verdict["reasons"]:
            verdict["status"] = "PASS"
            verdict["conclusion"] = (
                "PINNED_OFFICIAL_SDK_STABLE_AND_BETA_SCHEMA_ROOTS_EXTRACTED_EXACTLY__"
                "BETA_SURFACE_IS_SEMANTICALLY_LOAD_BEARING__FLAT_STABLE_ONLY_S_EPOCH_IS_INCOMPLETE"
            )
            verdict["nonclaims"] = [
                "NO_CLAIM_ALL_BETA_FEATURES_ARE_AUTHORIZED_FOR_ANY_OPUS55_PROFILE",
                "NO_CLAIM_PROFILE_TO_BETA_AUTHORIZATION_REGISTRY_IS_COMPLETE",
                "NO_CLAIM_SDK_TYPE_GRAPH_ALONE_PROVES_ALL_USEFUL_TARGET_BEHAVIORS",
                "NO_TERMINAL_ACCEPTANCE_OR_CAPABILITY_CREDIT",
            ]
    except Exception as exc:
        verdict["reasons"].append(f"EXCEPTION:{type(exc).__name__}:{exc}")

    print(json.dumps(verdict, indent=2, sort_keys=True))
    return 0 if verdict["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
