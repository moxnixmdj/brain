"""R2 direct adequacy for exact structured-table artifact goals.

Bounded family only:
- XLSX table from repository-local JSON records.
- SQLite table from repository-local JSON records.

A route is admitted only when the exact grammar compiles to the expected verified
Brain-owned producer. The single repository-local output is transactional:
preexisting bytes are restored, or a new file removed, unless an independent
producer-independent verifier proves the artifact semantics against the exact
source JSON. This module grants no authority outside these exact cells.
"""
from __future__ import annotations

from copy import deepcopy
from hashlib import sha256
import json
from pathlib import Path
import re
from typing import Any, Callable, Mapping

from canonical.runtime import goal_compiler
from canonical.runtime import live_integrated_brain_v1 as live_bound
from canonical.runtime.bound_capabilities import sqlite_verify_cli, xlsx_verify_openpyxl
from canonical.runtime.lossless_raw_task_contract_v1 import compile_contract
from canonical.runtime.r2_grounded_candidate_policy_frontier_v1 import goal_scoped_policy_id

SCHEMA = "PROJECT_BRAIN_R2_STRUCTURED_TABLE_DIRECT_ADEQUACY_V1"
ROOT = Path(__file__).resolve().parents[2]

_PATH = r"canonical/[A-Za-z0-9_.\-/]+"
_COLUMNS = r"[A-Za-z_][A-Za-z0-9_]*(?:\s*,\s*[A-Za-z_][A-Za-z0-9_]*){0,63}"

XLSX_GRAMMAR = re.compile(
    r"^Create (?P<output>" + _PATH + r"\.xlsx) from "
    r"(?P<json>" + _PATH + r"\.json) with columns "
    r"(?P<columns>" + _COLUMNS + r")\.?$",
    re.IGNORECASE,
)
SQLITE_GRAMMAR = re.compile(
    r"^Create (?P<output>" + _PATH + r"\.(?:sqlite|db|sqlite3)) from "
    r"(?P<json>" + _PATH + r"\.json) with table named "
    r"(?P<table>[A-Za-z_][A-Za-z0-9_]{0,127}), status "
    r"(?P<status>[A-Z][A-Z0-9_]{3,}), and columns "
    r"(?P<columns>" + _COLUMNS + r")\.?$",
    re.IGNORECASE,
)

_FORMATS = {
    "xlsx": {
        "capability_id": "xlsx.table.create_from_json_records",
        "verifier_id": "xlsx.table.verify_against_json_records",
    },
    "sqlite": {
        "capability_id": "sqlite.table.create_from_json_records",
        "verifier_id": "sqlite.table.verify_against_json_records",
    },
}


def _base(status: str, passed: bool = False) -> dict[str, Any]:
    return {
        "schema": SCHEMA,
        "status": status,
        "pass": passed,
        "semantic_acceptance_complete": False,
        "actual_goal_satisfaction_verified": False,
        "policy_adequacy_authority": False,
        "execution_authority": False,
        "terminal_authority": False,
        "terminal_credit_delta": 0,
        "incremental_spend_usd": 0,
    }


def _inside(root: Path, rel: str) -> Path:
    p = (root / rel).resolve()
    rr = root.resolve()
    if p == rr or rr not in p.parents:
        raise ValueError("PATH_OUTSIDE_REPOSITORY")
    return p


def _sha(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()


def _match(goal: str) -> tuple[str, re.Match[str]] | None:
    m = XLSX_GRAMMAR.fullmatch(goal)
    if m is not None:
        return "xlsx", m
    m = SQLITE_GRAMMAR.fullmatch(goal)
    if m is not None:
        return "sqlite", m
    return None


def _verified_entry(registry: Mapping[str, Any], capability_id: str) -> Mapping[str, Any]:
    entry = registry.get(capability_id)
    if not isinstance(entry, Mapping) or entry.get("status") != "VERIFIED_BOUND_CAPABILITY":
        raise ValueError("VERIFIED_BOUND_CAPABILITY_REQUIRED:" + capability_id)
    return entry


def preflight(request: Mapping[str, Any], *, repo_root: str | Path = ROOT) -> dict[str, Any]:
    if not isinstance(request, Mapping):
        return {**_base("FAIL_CLOSED"), "reason": "REQUEST_NOT_OBJECT"}
    task_id = str(request.get("task_id") or "").strip()
    goal = str(request.get("goal") or "").strip()
    if not task_id or not goal:
        return {**_base("FAIL_CLOSED"), "reason": "TASK_ID_AND_GOAL_REQUIRED"}

    matched = _match(goal)
    if matched is None:
        return {**_base("NOT_APPLICABLE"), "matched": False}

    fmt, match = matched
    root = Path(repo_root).resolve()
    json_path = match.group("json")
    output_path = match.group("output")
    spec = _FORMATS[fmt]

    try:
        source = _inside(root, json_path)
        destination = _inside(root, output_path)
        if not source.is_file():
            raise ValueError("SOURCE_JSON_MISSING")
        json.loads(source.read_text(encoding="utf-8"))

        registry = live_bound.load_verified_registry()
        producer = _verified_entry(registry, spec["capability_id"])
        verifier = _verified_entry(registry, spec["verifier_id"])

        if fmt == "xlsx":
            if str(producer.get("adapter_module") or "") != "xlsx_table_xlsxwriter":
                raise ValueError("XLSX_PRODUCER_ADAPTER_MISMATCH")
            if str(verifier.get("adapter_module") or "") != "xlsx_verify_openpyxl":
                raise ValueError("XLSX_VERIFIER_ADAPTER_MISMATCH")
        else:
            if str(producer.get("adapter_module") or "") != "sqlite_table_stdlib":
                raise ValueError("SQLITE_PRODUCER_ADAPTER_MISMATCH")
            if str(verifier.get("adapter_module") or "") != "sqlite_verify_cli":
                raise ValueError("SQLITE_VERIFIER_ADAPTER_MISMATCH")

        compiled_registry = goal_compiler._platform_admissible_registry(dict(registry))
        compiled = goal_compiler.compile_goal(goal, compiled_registry, root)
        if compiled.get("controller_actions") is not None:
            raise ValueError("COMPOUND_CONTROLLER_NOT_ALLOWED")
        if compiled.get("selected_capability") != spec["capability_id"]:
            raise ValueError("COMPILED_CAPABILITY_MISMATCH")
        inputs = compiled.get("inputs")
        if not isinstance(inputs, Mapping):
            raise ValueError("COMPILED_INPUTS_INVALID")
        if inputs.get("json_path") != json_path or inputs.get("output_path") != output_path:
            raise ValueError("COMPILED_PATH_BINDING_MISMATCH")

        targets = compiled.get("target_effects")
        if not isinstance(targets, list) or not targets:
            raise ValueError("COMPILED_TARGETS_INVALID")
        contract = compile_contract(
            goal,
            source_id="user",
            routing_target_effects=targets,
        )
        if contract.get("pass") is not True:
            raise ValueError("LOSSLESS_RAW_CONTRACT_FAILED")

        return {
            **_base("DIRECT_STRUCTURED_TABLE_ADEQUACY_ROUTE_MATCHED"),
            "matched": True,
            "task_id": task_id,
            "goal": goal,
            "goal_sha256": sha256(goal.encode("utf-8")).hexdigest(),
            "policy_id": goal_scoped_policy_id(spec["capability_id"], goal),
            "capability_id": spec["capability_id"],
            "verifier_capability_id": spec["verifier_id"],
            "format": fmt,
            "json_path": json_path,
            "output_path": output_path,
            "source_sha256": _sha(source),
            "columns": [x.strip() for x in match.group("columns").split(",")],
            "table_name": match.groupdict().get("table"),
            "status_value": match.groupdict().get("status"),
            "raw_contract": contract,
            "raw_task_contract_sha256": contract["task_contract_sha256"],
            "acceptance_obligation_count": len(contract["acceptance_contract"]["obligations"]),
            "transaction_scope": "ONE_REPOSITORY_LOCAL_OUTPUT_FILE",
            "preflight_execution_authority": False,
            "destination_existed_before": destination.exists(),
        }
    except Exception as exc:
        return {
            **_base("FAIL_CLOSED"),
            "matched": True,
            "reason": type(exc).__name__ + ":" + str(exc),
        }


def _independent_verify(pf: Mapping[str, Any], *, repo_root: str | Path) -> Mapping[str, Any]:
    args = {
        "goal": pf["goal"],
        "json_path": pf["json_path"],
    }
    if pf["format"] == "xlsx":
        args["xlsx_path"] = pf["output_path"]
        return xlsx_verify_openpyxl.run(args, repo_root)
    args["sqlite_path"] = pf["output_path"]
    return sqlite_verify_cli.run(args, repo_root)


def _restore(path: Path, existed: bool, prior: bytes | None) -> None:
    if existed:
        assert prior is not None
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(prior)
    elif path.exists():
        path.unlink()


def run(
    request: Mapping[str, Any],
    *,
    repo_root: str | Path = ROOT,
    verifier_provider: Callable[[Mapping[str, Any]], Mapping[str, Any]] | None = None,
) -> dict[str, Any]:
    pf = preflight(request, repo_root=repo_root)
    if pf.get("matched") is not True or pf.get("status") == "FAIL_CLOSED":
        return pf

    root = Path(repo_root).resolve()
    source = _inside(root, str(pf["json_path"]))
    destination = _inside(root, str(pf["output_path"]))
    existed = destination.exists()
    prior = destination.read_bytes() if existed else None

    try:
        raw = live_bound.run_raw_goal(request)
        if not isinstance(raw, Mapping) or raw.get("pass") is not True:
            _restore(destination, existed, prior)
            return {
                **_base("OPEN__TRANSACTIONAL_TABLE_EXECUTION_DID_NOT_VERIFY"),
                "matched": True,
                "policy_id": pf["policy_id"],
                "capability_id": pf["capability_id"],
                "transaction_rolled_back": True,
                "raw_result": deepcopy(dict(raw)) if isinstance(raw, Mapping) else raw,
            }

        if (
            raw.get("compiled_capability_id") != pf["capability_id"]
            or raw.get("raw_goal_sha256") != pf["goal_sha256"]
            or raw.get("raw_source_coverage_complete") is not True
            or not destination.is_file()
            or _sha(source) != pf["source_sha256"]
        ):
            _restore(destination, existed, prior)
            return {
                **_base("FAIL_CLOSED"),
                "matched": True,
                "reason": "EXECUTION_IDENTITY_OUTPUT_OR_SOURCE_IMMUTABILITY_MISMATCH",
                "transaction_rolled_back": True,
            }

        evidence = (
            verifier_provider(pf)
            if verifier_provider is not None
            else _independent_verify(pf, repo_root=root)
        )
        if (
            not isinstance(evidence, Mapping)
            or evidence.get("verified") is not True
            or evidence.get("producer_independent_verifier") is not True
        ):
            _restore(destination, existed, prior)
            return {
                **_base("OPEN__INDEPENDENT_TABLE_ACCEPTANCE_DID_NOT_VERIFY"),
                "matched": True,
                "policy_id": pf["policy_id"],
                "capability_id": pf["capability_id"],
                "transaction_rolled_back": True,
                "independent_verification": deepcopy(dict(evidence))
                if isinstance(evidence, Mapping) else None,
            }

        obligations = pf["raw_contract"]["acceptance_contract"]["obligations"]
        accepted_ids = [str(row["obligation_id"]) for row in obligations]
        return {
            **_base("PASS__TRANSACTIONAL_STRUCTURED_TABLE_POLICY_ADEQUACY_VERIFIED", True),
            "matched": True,
            "policy_id": pf["policy_id"],
            "capability_id": pf["capability_id"],
            "verifier_capability_id": pf["verifier_capability_id"],
            "goal_sha256": pf["goal_sha256"],
            "raw_task_contract_sha256": pf["raw_task_contract_sha256"],
            "format": pf["format"],
            "json_path": pf["json_path"],
            "output_path": pf["output_path"],
            "source_sha256": pf["source_sha256"],
            "accepted_raw_obligation_ids": accepted_ids,
            "raw_acceptance_obligation_count": len(accepted_ids),
            "semantic_acceptance_complete": True,
            "actual_goal_satisfaction_verified": True,
            "policy_adequacy_authority": True,
            "transaction_committed": True,
            "transaction_rolled_back": False,
            "independent_verification": deepcopy(dict(evidence)),
            "raw_result": deepcopy(dict(raw)),
            "authority_boundary": (
                "ONLY_EXACT_JSON_RECORDS_TO_XLSX_OR_SQLITE_GRAMMARS;"
                "ONE_REPOSITORY_LOCAL_OUTPUT;VERIFIED_BOUND_PRODUCER;"
                "PRODUCER_INDEPENDENT_SOURCE_JSON_SEMANTIC_VERIFICATION;"
                "SOURCE_BYTES_IMMUTABLE;"
                "NO_EXTERNAL_OR_IRREVERSIBLE_EFFECT_AUTHORITY"
            ),
        }
    except Exception as exc:
        _restore(destination, existed, prior)
        return {
            **_base("FAIL_CLOSED"),
            "matched": True,
            "policy_id": pf.get("policy_id"),
            "capability_id": pf.get("capability_id"),
            "reason": type(exc).__name__ + ":" + str(exc),
            "transaction_rolled_back": True,
        }
