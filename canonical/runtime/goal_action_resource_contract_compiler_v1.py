"""Compile exact source-derived resource contracts for Astra goal actions.

This is a fail-closed *candidate contract extractor*. It proves neither runtime
enforcement nor transitive helper purity. An action is DIRECT_CONTRACTIBLE only
when every directly observed repository path access is bound to an explicit
action argument, every directly observed network access has an explicit URL
argument, and the branch has no direct process or dynamic bound-capability sink.

All other actions remain BLOCKED_PENDING_GATEWAY_PROOF.
"""
from __future__ import annotations

import hashlib
import pathlib
import re
from typing import Any

SCHEMA = "PROJECT_BRAIN_GOAL_ACTION_RESOURCE_CONTRACT_COMPILER_V1"
ROOT = pathlib.Path(__file__).resolve().parents[2]
RUNTIME_REL = "canonical/runtime/astra_runtime.py"
EXPECTED_RUNTIME_BLOB = "b7efc08e64a483e9a759c181a4f9a1cf29e47a9a"


def _git_blob_sha(raw: bytes) -> str:
    return hashlib.sha1(
        b"blob " + str(len(raw)).encode("ascii") + b"\0" + raw
    ).hexdigest()


def _function_slice(lines: list[str], name: str) -> tuple[int, int, list[str]]:
    needle = "def " + name + "("
    start = next((i for i, line in enumerate(lines) if line.startswith(needle)), -1)
    if start < 0:
        raise ValueError("FUNCTION_MISSING:" + name)
    end = start + 1
    while end < len(lines) and not lines[end].startswith("def "):
        end += 1
    return start, end, lines[start:end]


def _branches(source: str) -> list[dict[str, Any]]:
    lines = source.splitlines()
    start, _end, body = _function_slice(lines, "_goal_action")
    heads = []
    for offset, line in enumerate(body):
        match = re.match(r'^\s*if typ=="([^"]+)":', line)
        if match:
            heads.append({
                "action_type": match.group(1),
                "offset": offset,
                "source_line": start + offset + 1,
            })
    out = []
    for index, head in enumerate(heads):
        a = head["offset"]
        b = heads[index + 1]["offset"] if index + 1 < len(heads) else len(body)
        out.append({**head, "source": "\n".join(body[a:b])})
    return out


def _arg_fields(pattern: str, text: str) -> list[str]:
    return sorted(set(re.findall(pattern, text)))


def compile_contracts(source: str) -> dict[str, Any]:
    rows = []
    for branch in _branches(source):
        text = branch["source"]
        reads = _arg_fields(
            r'_safe_repo_path\(\s*args\.get\(["\']([^"\']+)["\']',
            text,
        )
        writes = _arg_fields(
            r'_safe_repo_mutation_path\(\s*args\.get\(["\']([^"\']+)["\']',
            text,
        )
        safe_calls = len(re.findall(r"_safe_repo_path\(", text)) + len(
            re.findall(r"_safe_repo_mutation_path\(", text)
        )
        exact_path_calls = len(reads) + len(writes)
        direct_root = bool(re.search(r"ROOT\s*/|\(ROOT/[\"\']", text))
        direct_process = bool(
            re.search(r"subprocess\.(?:run|Popen)|os\.(?:fork|kill|system)", text)
        )
        external = bool(
            re.search(r"urllib\.request|_external_tool_bridge|run_http\(", text)
        )
        url_fields = _arg_fields(
            r'args\.get\(["\']([^"\']*url[^"\']*)["\']',
            text,
        )
        dynamic_capability = "_invoke_bound_capability" in text

        reasons = []
        if safe_calls != exact_path_calls:
            reasons.append("DERIVED_OR_UNBOUND_REPO_PATH")
        if direct_root:
            reasons.append("DIRECT_ROOT_ACCESS_OUTSIDE_SAFE_PATH_GATEWAY")
        if direct_process:
            reasons.append("DIRECT_PROCESS_EFFECT")
        if external and not url_fields:
            reasons.append("EXTERNAL_ACCESS_WITHOUT_DIRECT_URL_ARGUMENT")
        if dynamic_capability:
            reasons.append("DYNAMIC_BOUND_CAPABILITY_EFFECT")
        if (
            safe_calls == 0
            and not direct_root
            and not direct_process
            and not external
            and not dynamic_capability
        ):
            reasons.append("TRANSITIVE_HELPER_EFFECTS_NOT_PROVED_ABSENT")

        contractible = not reasons
        rows.append({
            "action_type": branch["action_type"],
            "source_line": branch["source_line"],
            "status": (
                "DIRECT_CONTRACTIBLE"
                if contractible
                else "BLOCKED_PENDING_GATEWAY_PROOF"
            ),
            "repo_read_argument_fields": reads,
            "repo_write_argument_fields": writes,
            "network_url_argument_fields": url_fields,
            "direct_safe_path_call_count": safe_calls,
            "exact_path_argument_binding_count": exact_path_calls,
            "missing_gateway_proofs": reasons,
            "candidate_mediator_disposition": (
                {
                    "repo_reads": "CAPSULE_RESOURCE_STATE",
                    "repo_writes": "BROKERED_OR_CAPSULE_RESOURCE_STATE",
                    "network": "BROKERED_EXTERNAL_INFORMATION",
                }
                if contractible
                else "FAIL_CLOSED_UNTIL_LISTED_GATEWAY_PROOFS_CLOSE"
            ),
        })

    contractible_rows = [x for x in rows if x["status"] == "DIRECT_CONTRACTIBLE"]
    blocked_rows = [x for x in rows if x["status"] != "DIRECT_CONTRACTIBLE"]

    reason_counts: dict[str, int] = {}
    for row in blocked_rows:
        for reason in row["missing_gateway_proofs"]:
            reason_counts[reason] = reason_counts.get(reason, 0) + 1

    return {
        "schema": SCHEMA,
        "status": "PASS__DIRECT_RESOURCE_CONTRACT_PARTITION_COMPILED",
        "action_count": len(rows),
        "direct_contractible_count": len(contractible_rows),
        "blocked_pending_gateway_count": len(blocked_rows),
        "direct_contractible_actions": [x["action_type"] for x in contractible_rows],
        "blocked_actions": [x["action_type"] for x in blocked_rows],
        "missing_gateway_reason_counts": reason_counts,
        "rows": rows,
        "candidate_only": True,
        "runtime_enforcement_proved": False,
        "transitive_helper_completeness_proved": False,
        "no_bypass_credit": False,
        "acceptance_credit_delta": 0,
        "terminal_credit_delta": 0,
    }


def evaluate(root: pathlib.Path = ROOT) -> dict[str, Any]:
    path = root / RUNTIME_REL
    if not path.is_file():
        return {
            "schema": SCHEMA,
            "status": "FAIL_CLOSED__RUNTIME_MISSING",
            "errors": ["RUNTIME_MISSING"],
            "acceptance_credit_delta": 0,
            "terminal_credit_delta": 0,
        }
    raw = path.read_bytes()
    got = _git_blob_sha(raw)
    if got != EXPECTED_RUNTIME_BLOB:
        return {
            "schema": SCHEMA,
            "status": "FAIL_CLOSED__RUNTIME_BLOB_DRIFT",
            "errors": ["RUNTIME_BLOB_DRIFT:" + got],
            "expected_git_blob_sha": EXPECTED_RUNTIME_BLOB,
            "acceptance_credit_delta": 0,
            "terminal_credit_delta": 0,
        }
    out = compile_contracts(raw.decode("utf-8"))
    out["runtime_path"] = RUNTIME_REL
    out["runtime_git_blob_sha"] = got
    return out


if __name__ == "__main__":
    import json
    print(json.dumps(evaluate(), indent=2, sort_keys=True))
