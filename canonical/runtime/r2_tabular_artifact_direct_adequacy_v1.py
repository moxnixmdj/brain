"""R2 direct adequacy for exact transactional JSON -> tabular artifact goals.

This is a bounded family-level direct route for two already-verified producer /
independent-verifier pairs:

* JSON records -> SQLite, independently queried with sqlite3 CLI.
* JSON records -> XLSX, independently reopened with OpenPyXL.

The route is deliberately narrow.  Exact grammar is required before any effect.
The declared repository-local output is snapshotted, the verified Brain-owned
producer executes once, and the artifact is committed only if the independent
verifier reconstructs the requested table/workbook semantics from canonical
source JSON.  Any execution or acceptance failure restores the previous bytes
(or removes a newly-created artifact).

This proves adequacy only for the exact grammar below.  It is not a general
spreadsheet/database semantic oracle and grants no external-effect authority.
"""
from __future__ import annotations

from copy import deepcopy
from hashlib import sha256
import json
from pathlib import Path
import re
from typing import Any, Callable, Mapping

from canonical.runtime import live_integrated_brain_v1 as live_bound
from canonical.runtime.lossless_raw_task_contract_v1 import compile_contract
from canonical.runtime.r2_grounded_candidate_policy_frontier_v1 import goal_scoped_policy_id
from canonical.runtime.bound_capabilities import sqlite_table_stdlib as sqlite_producer
from canonical.runtime.bound_capabilities import sqlite_verify_cli as sqlite_verifier
from canonical.runtime.bound_capabilities import xlsx_table_xlsxwriter as xlsx_producer
from canonical.runtime.bound_capabilities import xlsx_verify_openpyxl as xlsx_verifier

SCHEMA = "PROJECT_BRAIN_R2_TABULAR_ARTIFACT_DIRECT_ADEQUACY_V1"
ROOT = Path(__file__).resolve().parents[2]

_PATH = r"canonical/[A-Za-z0-9_.\-/]+"
_IDENT = r"[A-Za-z_][A-Za-z0-9_]{0,127}"
_COLS = _IDENT + r"(?:, " + _IDENT + r"){0,63}"
_STATUS = r"[A-Z][A-Z0-9_]{3,}"

SQLITE_GRAMMAR = re.compile(
    r"^Read (?P<json>" + _PATH + r"\.json)\. "
    r"Create a SQLite database at (?P<output>" + _PATH + r"\.(?:sqlite|db|sqlite3)) "
    r"with a table named (?P<table>" + _IDENT + r") containing exactly one row "
    r"for every record containing the exact scalar value (?P<status>" + _STATUS + r") "
    r"and columns (?P<columns>" + _COLS + r")\. "
    r"Finally independently query the SQLite database and verify that exactly those "
    r"source records appear once and that every stored value matches the source JSON\.$"
)

XLSX_GRAMMAR = re.compile(
    r"^Read (?P<json>" + _PATH + r"\.json)\. "
    r"Create an XLSX spreadsheet workbook at (?P<output>" + _PATH + r"\.xlsx) "
    r"containing exactly one row for every record in the unambiguous source record "
    r"collection with columns (?P<columns>" + _COLS + r")\. "
    r"Finally independently reopen the workbook and verify that every source record "
    r"appears exactly once and that every stored value matches the source JSON\.$"
)

_PAIRS = {
    "sqlite": {
        "producer_id": "sqlite.table.create_from_json_records",
        "producer_adapter": "sqlite_table_stdlib",
        "verifier_id": "sqlite.table.verify_against_json_records",
        "verifier_adapter": "sqlite_verify_cli",
        "producer": sqlite_producer,
        "verifier": sqlite_verifier,
        "output_result_field": "output_path",
        "verifier_path_field": "sqlite_path",
        "verifier_sha_field": "sqlite_sha256",
    },
    "xlsx": {
        "producer_id": "xlsx.table.create_from_json_records",
        "producer_adapter": "xlsx_table_xlsxwriter",
        "verifier_id": "xlsx.table.verify_against_json_records",
        "verifier_adapter": "xlsx_verify_openpyxl",
        "producer": xlsx_producer,
        "verifier": xlsx_verifier,
        "output_result_field": "output_path",
        "verifier_path_field": "xlsx_path",
        "verifier_sha_field": "xlsx_sha256",
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


def _columns(match: re.Match[str]) -> list[str]:
    cols = [x.strip() for x in match.group("columns").split(",")]
    if not cols or len(cols) > 64 or len(cols) != len(set(cols)):
        raise ValueError("COLUMN_DECLARATION_INVALID")
    return cols


def _registry_pair(kind: str) -> dict[str, Any]:
    pair = _PAIRS[kind]
    registry = live_bound.load_verified_registry()
    producer = registry.get(pair["producer_id"])
    verifier = registry.get(pair["verifier_id"])
    if not isinstance(producer, Mapping) or not isinstance(verifier, Mapping):
        raise ValueError("TABULAR_CAPABILITY_PAIR_MISSING")
    if producer.get("status") != "VERIFIED_BOUND_CAPABILITY":
        raise ValueError("TABULAR_PRODUCER_NOT_VERIFIED")
    if verifier.get("status") != "VERIFIED_BOUND_CAPABILITY":
        raise ValueError("TABULAR_VERIFIER_NOT_VERIFIED")
    if producer.get("adapter_module") != pair["producer_adapter"]:
        raise ValueError("TABULAR_PRODUCER_ADAPTER_DRIFT")
    if verifier.get("adapter_module") != pair["verifier_adapter"]:
        raise ValueError("TABULAR_VERIFIER_ADAPTER_DRIFT")
    if (producer.get("verification") or {}).get("independently_verified") is not True:
        raise ValueError("TABULAR_PRODUCER_VERIFICATION_REQUIRED")
    if (verifier.get("verification") or {}).get("independently_verified") is not True:
        raise ValueError("TABULAR_VERIFIER_VERIFICATION_REQUIRED")
    observed = (verifier.get("verification") or {}).get("observed_effect") or {}
    if observed.get("producer_independent_verifier") is not True:
        raise ValueError("TABULAR_VERIFIER_INDEPENDENCE_REQUIRED")
    if pair["producer_adapter"] == pair["verifier_adapter"]:
        raise ValueError("TABULAR_PRODUCER_VERIFIER_ADAPTER_COLLISION")
    return {
        "producer_id": pair["producer_id"],
        "verifier_id": pair["verifier_id"],
        "producer_adapter": pair["producer_adapter"],
        "verifier_adapter": pair["verifier_adapter"],
    }


def preflight(request: Mapping[str, Any], *, repo_root: str | Path = ROOT) -> dict[str, Any]:
    if not isinstance(request, Mapping):
        return {**_base("FAIL_CLOSED"), "reason": "REQUEST_NOT_OBJECT"}
    task_id = str(request.get("task_id") or "").strip()
    goal = str(request.get("goal") or "").strip()
    if not task_id or not goal:
        return {**_base("FAIL_CLOSED"), "reason": "TASK_ID_AND_GOAL_REQUIRED"}

    sqlite_match = SQLITE_GRAMMAR.fullmatch(goal)
    xlsx_match = XLSX_GRAMMAR.fullmatch(goal)
    if sqlite_match is None and xlsx_match is None:
        return {**_base("NOT_APPLICABLE"), "matched": False}

    kind = "sqlite" if sqlite_match is not None else "xlsx"
    match = sqlite_match if sqlite_match is not None else xlsx_match
    assert match is not None
    root = Path(repo_root).resolve()

    try:
        json_path = match.group("json")
        output_path = match.group("output")
        source = _inside(root, json_path)
        destination = _inside(root, output_path)
        if not source.is_file():
            raise ValueError("SOURCE_JSON_MISSING")
        json.loads(source.read_text(encoding="utf-8"))
        cols = _columns(match)
        if kind == "sqlite" and "capability_id" not in cols:
            raise ValueError("SQLITE_CAPABILITY_ID_COLUMN_REQUIRED")
        pair = _registry_pair(kind)

        target_effects = [pair["producer_id"], pair["verifier_id"]]
        contract = compile_contract(
            goal,
            source_id="user",
            routing_target_effects=target_effects,
        )
        if contract.get("pass") is not True:
            raise ValueError("LOSSLESS_RAW_CONTRACT_FAILED")

        out = {
            **_base("DIRECT_TABULAR_ADEQUACY_ROUTE_MATCHED"),
            "matched": True,
            "task_id": task_id,
            "goal": goal,
            "goal_sha256": sha256(goal.encode("utf-8")).hexdigest(),
            "kind": kind,
            "json_path": json_path,
            "output_path": output_path,
            "columns": cols,
            "producer_capability_id": pair["producer_id"],
            "verifier_capability_id": pair["verifier_id"],
            "policy_id": goal_scoped_policy_id(pair["producer_id"], goal),
            "raw_contract": contract,
            "raw_task_contract_sha256": contract["task_contract_sha256"],
            "acceptance_obligation_count": len(contract["acceptance_contract"]["obligations"]),
            "transaction_scope": "ONE_REPOSITORY_LOCAL_OUTPUT_FILE",
            "preflight_execution_authority": False,
            "destination_existed_before": destination.exists(),
        }
        if kind == "sqlite":
            out["table_name"] = match.group("table")
            out["status_value"] = match.group("status")
        return out
    except Exception as exc:
        return {
            **_base("FAIL_CLOSED"),
            "matched": True,
            "reason": type(exc).__name__ + ":" + str(exc),
        }


def _restore(path: Path, existed: bool, prior: bytes | None) -> None:
    if existed:
        assert prior is not None
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(prior)
    elif path.exists():
        path.unlink()


def _default_execute(pf: Mapping[str, Any], *, repo_root: Path) -> Mapping[str, Any]:
    pair = _PAIRS[str(pf["kind"])]
    return pair["producer"].run(
        {
            "capability_id": pf["producer_capability_id"],
            "goal": pf["goal"],
            "json_path": pf["json_path"],
            "output_path": pf["output_path"],
        },
        repo_root,
    )


def _default_verify(pf: Mapping[str, Any], *, repo_root: Path) -> Mapping[str, Any]:
    pair = _PAIRS[str(pf["kind"])]
    args = {
        "capability_id": pf["verifier_capability_id"],
        "goal": pf["goal"],
        "json_path": pf["json_path"],
    }
    if pf["kind"] == "sqlite":
        args["sqlite_path"] = pf["output_path"]
    else:
        args["xlsx_path"] = pf["output_path"]
    return pair["verifier"].run(args, repo_root)


def run(
    request: Mapping[str, Any],
    *,
    repo_root: str | Path = ROOT,
    producer_provider: Callable[[Mapping[str, Any]], Mapping[str, Any]] | None = None,
    verifier_provider: Callable[[Mapping[str, Any]], Mapping[str, Any]] | None = None,
) -> dict[str, Any]:
    pf = preflight(request, repo_root=repo_root)
    if pf.get("matched") is not True:
        return pf
    if pf.get("status") == "FAIL_CLOSED":
        return pf

    root = Path(repo_root).resolve()
    destination = _inside(root, str(pf["output_path"]))
    existed = destination.exists()
    prior = destination.read_bytes() if existed else None
    pair = _PAIRS[str(pf["kind"])]

    try:
        produced = (
            producer_provider(pf)
            if producer_provider is not None
            else _default_execute(pf, repo_root=root)
        )
        if not isinstance(produced, Mapping) or produced.get("output_verified") is not True:
            _restore(destination, existed, prior)
            return {
                **_base("OPEN__TRANSACTIONAL_TABULAR_EXECUTION_DID_NOT_VERIFY"),
                "matched": True,
                "policy_id": pf["policy_id"],
                "producer_capability_id": pf["producer_capability_id"],
                "transaction_rolled_back": True,
                "producer_result": deepcopy(dict(produced))
                if isinstance(produced, Mapping) else None,
            }

        if not destination.is_file():
            _restore(destination, existed, prior)
            return {
                **_base("FAIL_CLOSED"),
                "matched": True,
                "reason": "TABULAR_OUTPUT_MISSING_AFTER_EXECUTION",
                "transaction_rolled_back": True,
            }

        rel_output = str(destination.relative_to(root)).replace("\\", "/")
        if produced.get(pair["output_result_field"]) != rel_output:
            _restore(destination, existed, prior)
            return {
                **_base("FAIL_CLOSED"),
                "matched": True,
                "reason": "TABULAR_PRODUCER_OUTPUT_BINDING_MISMATCH",
                "transaction_rolled_back": True,
            }

        evidence = (
            verifier_provider(pf)
            if verifier_provider is not None
            else _default_verify(pf, repo_root=root)
        )
        if not isinstance(evidence, Mapping) or evidence.get("verified") is not True:
            _restore(destination, existed, prior)
            return {
                **_base("OPEN__INDEPENDENT_TABULAR_ACCEPTANCE_DID_NOT_VERIFY"),
                "matched": True,
                "policy_id": pf["policy_id"],
                "producer_capability_id": pf["producer_capability_id"],
                "verifier_capability_id": pf["verifier_capability_id"],
                "transaction_rolled_back": True,
                "independent_verification": deepcopy(dict(evidence))
                if isinstance(evidence, Mapping) else None,
            }

        if evidence.get("producer_independent_verifier") is not True:
            _restore(destination, existed, prior)
            return {
                **_base("FAIL_CLOSED"),
                "matched": True,
                "reason": "TABULAR_VERIFIER_NOT_PRODUCER_INDEPENDENT",
                "transaction_rolled_back": True,
            }
        if evidence.get(pair["verifier_path_field"]) != rel_output:
            _restore(destination, existed, prior)
            return {
                **_base("FAIL_CLOSED"),
                "matched": True,
                "reason": "TABULAR_VERIFIER_OUTPUT_BINDING_MISMATCH",
                "transaction_rolled_back": True,
            }

        producer_sha = str(produced.get("output_sha256") or "")
        verifier_sha = str(evidence.get(pair["verifier_sha_field"]) or "")
        actual_sha = sha256(destination.read_bytes()).hexdigest()
        if not producer_sha or producer_sha != verifier_sha or producer_sha != actual_sha:
            _restore(destination, existed, prior)
            return {
                **_base("FAIL_CLOSED"),
                "matched": True,
                "reason": "TABULAR_ARTIFACT_HASH_BINDING_MISMATCH",
                "transaction_rolled_back": True,
            }

        if produced.get("row_count") != evidence.get("verified_rows"):
            _restore(destination, existed, prior)
            return {
                **_base("FAIL_CLOSED"),
                "matched": True,
                "reason": "TABULAR_ROW_COUNT_MISMATCH",
                "transaction_rolled_back": True,
            }
        if list(produced.get("columns") or []) != list(evidence.get("columns") or []):
            _restore(destination, existed, prior)
            return {
                **_base("FAIL_CLOSED"),
                "matched": True,
                "reason": "TABULAR_COLUMN_BINDING_MISMATCH",
                "transaction_rolled_back": True,
            }
        if list(produced.get("columns") or []) != list(pf["columns"]):
            _restore(destination, existed, prior)
            return {
                **_base("FAIL_CLOSED"),
                "matched": True,
                "reason": "TABULAR_DECLARED_COLUMN_MISMATCH",
                "transaction_rolled_back": True,
            }

        if pf["kind"] == "sqlite":
            if (
                produced.get("table_name") != pf.get("table_name")
                or evidence.get("table_name") != pf.get("table_name")
                or produced.get("status_value") != pf.get("status_value")
                or evidence.get("status_value") != pf.get("status_value")
            ):
                _restore(destination, existed, prior)
                return {
                    **_base("FAIL_CLOSED"),
                    "matched": True,
                    "reason": "SQLITE_DECLARED_SEMANTIC_BINDING_MISMATCH",
                    "transaction_rolled_back": True,
                }

        obligations = pf["raw_contract"]["acceptance_contract"]["obligations"]
        accepted_ids = [str(row["obligation_id"]) for row in obligations]
        return {
            **_base("PASS__TRANSACTIONAL_TABULAR_POLICY_ADEQUACY_VERIFIED", True),
            "matched": True,
            "kind": pf["kind"],
            "policy_id": pf["policy_id"],
            "producer_capability_id": pf["producer_capability_id"],
            "verifier_capability_id": pf["verifier_capability_id"],
            "goal_sha256": pf["goal_sha256"],
            "raw_task_contract_sha256": pf["raw_task_contract_sha256"],
            "json_path": pf["json_path"],
            "output_path": pf["output_path"],
            "columns": list(pf["columns"]),
            "accepted_raw_obligation_ids": accepted_ids,
            "raw_acceptance_obligation_count": len(accepted_ids),
            "semantic_acceptance_complete": True,
            "actual_goal_satisfaction_verified": True,
            "policy_adequacy_authority": True,
            "transaction_committed": True,
            "transaction_rolled_back": False,
            "producer_result": deepcopy(dict(produced)),
            "independent_verification": deepcopy(dict(evidence)),
            "authority_boundary": (
                "ONLY_THE_TWO_EXACT_TRANSACTIONAL_TABULAR_GRAMMARS;"
                "ONE_REPOSITORY_LOCAL_OUTPUT;VERIFIED_BOUND_PRODUCER;"
                "PRODUCER_INDEPENDENT_REOPEN_OR_QUERY_AGAINST_CANONICAL_SOURCE_JSON;"
                "EXACT_DECLARED_COLUMNS_AND_ARTIFACT_HASH_BINDING;"
                "NO_EXTERNAL_OR_IRREVERSIBLE_EFFECT_AUTHORITY"
            ),
        }
    except Exception as exc:
        _restore(destination, existed, prior)
        return {
            **_base("FAIL_CLOSED"),
            "matched": True,
            "policy_id": pf.get("policy_id"),
            "producer_capability_id": pf.get("producer_capability_id"),
            "verifier_capability_id": pf.get("verifier_capability_id"),
            "reason": type(exc).__name__ + ":" + str(exc),
            "transaction_rolled_back": True,
        }
