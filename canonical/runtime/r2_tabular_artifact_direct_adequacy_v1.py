"""R2 transactional direct adequacy for exact JSON-records -> tabular artifacts.

This bounded family admits only two exact single-action grammars:

  Create <repo-local .xlsx> from <repo-local .json> with columns <ids>.
  Create <repo-local .sqlite> from <repo-local .json> for status <TOKEN>
  in table named <IDENT> with columns <ids>.

Membership is proved before execution. The selected producer and verifier must
already be verified Brain-owned bound capabilities. Execution is transactional
at one repository-local output. The source JSON must remain byte-identical.
Success requires producer-independent semantic readback of the produced artifact
against the canonical JSON source; every raw obligation is then accepted.
"""
from __future__ import annotations

from copy import deepcopy
from hashlib import sha256
import json
from pathlib import Path
import re
from typing import Any, Mapping

from canonical.runtime import goal_compiler
from canonical.runtime import live_integrated_brain_v1 as live_bound
from canonical.runtime.bound_capabilities import sqlite_table_stdlib
from canonical.runtime.bound_capabilities import sqlite_verify_cli
from canonical.runtime.bound_capabilities import xlsx_table_xlsxwriter
from canonical.runtime.bound_capabilities import xlsx_verify_openpyxl
from canonical.runtime.lossless_raw_task_contract_v1 import compile_contract
from canonical.runtime.r2_grounded_candidate_policy_frontier_v1 import goal_scoped_policy_id

SCHEMA = "PROJECT_BRAIN_R2_TABULAR_ARTIFACT_DIRECT_ADEQUACY_V1"
ROOT = Path(__file__).resolve().parents[2]

_PATH = r"canonical/[A-Za-z0-9_.\-/]+"
_IDENT = r"[A-Za-z_][A-Za-z0-9_]{0,127}"
_COLS = rf"{_IDENT}(?:\s*,\s*{_IDENT})*"

XLSX_GRAMMAR = re.compile(
    rf"^Create (?P<output>{_PATH}\.xlsx) from (?P<json>{_PATH}\.json) "
    rf"with columns (?P<columns>{_COLS})\.?$",
    re.IGNORECASE,
)
SQLITE_GRAMMAR = re.compile(
    rf"^Create (?P<output>{_PATH}\.(?:sqlite|db|sqlite3)) from "
    rf"(?P<json>{_PATH}\.json) for status (?P<status>[A-Z][A-Z0-9_]{{3,}}) "
    rf"in table named (?P<table>{_IDENT}) with columns (?P<columns>{_COLS})\.?$",
)

PRODUCERS = {
    "xlsx": "xlsx.table.create_from_json_records",
    "sqlite": "sqlite.table.create_from_json_records",
}
VERIFIERS = {
    "xlsx": "xlsx.table.verify_against_json_records",
    "sqlite": "sqlite.table.verify_against_json_records",
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
    rr = root.resolve()
    p = (rr / str(rel)).resolve()
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


def _capability_pair(registry: Mapping[str, Any], kind: str) -> tuple[Mapping[str, Any], Mapping[str, Any]]:
    producer_id = PRODUCERS[kind]
    verifier_id = VERIFIERS[kind]
    producer = registry.get(producer_id)
    verifier = registry.get(verifier_id)
    if not isinstance(producer, Mapping) or producer.get("status") != "VERIFIED_BOUND_CAPABILITY":
        raise ValueError("TABULAR_PRODUCER_NOT_VERIFIED")
    if not isinstance(verifier, Mapping) or verifier.get("status") != "VERIFIED_BOUND_CAPABILITY":
        raise ValueError("TABULAR_VERIFIER_NOT_VERIFIED")
    pv = producer.get("verification")
    vv = verifier.get("verification")
    if not isinstance(pv, Mapping) or pv.get("independently_verified") is not True:
        raise ValueError("TABULAR_PRODUCER_INDEPENDENT_VERIFICATION_REQUIRED")
    if not isinstance(vv, Mapping) or vv.get("independently_verified") is not True:
        raise ValueError("TABULAR_VERIFIER_INDEPENDENT_VERIFICATION_REQUIRED")
    return producer, verifier


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

    kind, m = matched
    root = Path(repo_root).resolve()
    json_path = m.group("json")
    output_path = m.group("output")
    columns = [x.strip() for x in m.group("columns").split(",") if x.strip()]

    try:
        source = _inside(root, json_path)
        destination = _inside(root, output_path)
        if not source.is_file():
            raise ValueError("SOURCE_JSON_MISSING")
        data = json.loads(source.read_text(encoding="utf-8"))
        if not columns or len(columns) != len(set(columns)):
            raise ValueError("TABULAR_COLUMNS_INVALID")

        if kind == "xlsx":
            if not (columns[0] == "capability_id" or columns[0].endswith("_id")):
                raise ValueError("XLSX_FIRST_COLUMN_STABLE_ID_REQUIRED")
            # Reuse the producer's side-effect-free source-selection semantics.
            xlsx_table_xlsxwriter._select_collection(data, columns)
        else:
            if columns[0] != "capability_id":
                raise ValueError("SQLITE_FIRST_COLUMN_CAPABILITY_ID_REQUIRED")
            status = m.group("status")
            found = sqlite_table_stdlib._find_collection(data, status)
            if found is None:
                raise ValueError("SQLITE_STATUS_COLLECTION_NOT_FOUND")
            if sqlite_table_stdlib._table_name(goal) != m.group("table"):
                raise ValueError("SQLITE_TABLE_BINDING_MISMATCH")
            if sqlite_table_stdlib._columns(goal) != columns:
                raise ValueError("SQLITE_COLUMN_BINDING_MISMATCH")

        registry = live_bound.load_verified_registry()
        admissible = goal_compiler._platform_admissible_registry(dict(registry))
        _capability_pair(admissible, kind)

        compiled = goal_compiler.compile_goal(goal, admissible, root)
        if compiled.get("controller_actions") is not None:
            raise ValueError("COMPOUND_CONTROLLER_NOT_ALLOWED")
        producer_id = PRODUCERS[kind]
        if compiled.get("selected_capability") != producer_id:
            raise ValueError(
                "TABULAR_PRODUCER_SELECTION_MISMATCH:"
                + str(compiled.get("selected_capability"))
            )
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
            **_base("DIRECT_TABULAR_ADEQUACY_ROUTE_MATCHED"),
            "matched": True,
            "task_id": task_id,
            "goal": goal,
            "goal_sha256": sha256(goal.encode("utf-8")).hexdigest(),
            "policy_id": goal_scoped_policy_id(producer_id, goal),
            "artifact_kind": kind,
            "capability_id": producer_id,
            "verifier_capability_id": VERIFIERS[kind],
            "json_path": json_path,
            "output_path": output_path,
            "columns": columns,
            "source_sha256": _sha(source),
            "raw_contract": contract,
            "raw_task_contract_sha256": contract["task_contract_sha256"],
            "acceptance_obligation_count": len(
                contract["acceptance_contract"]["obligations"]
            ),
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


def _verify(pf: Mapping[str, Any], *, root: Path) -> Mapping[str, Any]:
    if pf["artifact_kind"] == "xlsx":
        return xlsx_verify_openpyxl.run(
            {
                "capability_id": VERIFIERS["xlsx"],
                "goal": pf["goal"],
                "json_path": pf["json_path"],
                "xlsx_path": pf["output_path"],
            },
            root,
        )
    return sqlite_verify_cli.run(
        {
            "capability_id": VERIFIERS["sqlite"],
            "goal": pf["goal"],
            "json_path": pf["json_path"],
            "sqlite_path": pf["output_path"],
        },
        root,
    )


def _restore(path: Path, existed: bool, prior: bytes | None) -> None:
    if existed:
        assert prior is not None
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(prior)
    elif path.exists():
        path.unlink()


def run(request: Mapping[str, Any], *, repo_root: str | Path = ROOT) -> dict[str, Any]:
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
                **_base("OPEN__TRANSACTIONAL_TABULAR_EXECUTION_DID_NOT_VERIFY"),
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

        evidence = _verify(pf, root=root)
        if not isinstance(evidence, Mapping) or evidence.get("verified") is not True:
            _restore(destination, existed, prior)
            return {
                **_base("OPEN__INDEPENDENT_TABULAR_ACCEPTANCE_DID_NOT_VERIFY"),
                "matched": True,
                "policy_id": pf["policy_id"],
                "capability_id": pf["capability_id"],
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

        obligations = pf["raw_contract"]["acceptance_contract"]["obligations"]
        accepted_ids = [str(row["obligation_id"]) for row in obligations]
        return {
            **_base("PASS__TRANSACTIONAL_TABULAR_POLICY_ADEQUACY_VERIFIED", True),
            "matched": True,
            "policy_id": pf["policy_id"],
            "capability_id": pf["capability_id"],
            "verifier_capability_id": pf["verifier_capability_id"],
            "goal_sha256": pf["goal_sha256"],
            "raw_task_contract_sha256": pf["raw_task_contract_sha256"],
            "artifact_kind": pf["artifact_kind"],
            "json_path": pf["json_path"],
            "output_path": pf["output_path"],
            "columns": list(pf["columns"]),
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
                "ONLY_THE_EXACT_SINGLE_ACTION_JSON_TO_XLSX_OR_SQLITE_GRAMMARS;"
                "ONE_REPOSITORY_LOCAL_OUTPUT;VERIFIED_BOUND_PRODUCER_AND_VERIFIER;"
                "PRODUCER_INDEPENDENT_SEMANTIC_READBACK_EQUALS_CANONICAL_SOURCE;"
                "SOURCE_BYTES_IMMUTABLE;NO_EXTERNAL_OR_IRREVERSIBLE_EFFECT_AUTHORITY"
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
