"""R2 direct adequacy for exact JSON-record -> DOCX report goals.

Bounded family only. Adequacy is granted only when:
1. an exact grammar binds one repository-local JSON source and DOCX destination;
2. the current goal compiler independently selects the verified
   docx.document.create_from_json_record capability with those exact inputs;
3. source JSON semantics are frozen across execution by SHA-256;
4. execution writes only the declared DOCX plus its declared intent sidecar;
5. the intent sidecar is independently rebound to the exact raw goal/source/output;
6. the producer-independent OOXML verifier reparses the raw goal and source JSON,
   reopens word/document.xml, and verifies the exact title/paragraph/table semantics.

The DOCX and intent sidecar form one transaction. Any execution, binding, or
acceptance failure restores both pre-existing artifacts byte-for-byte (or removes
new ones). No external/irreversible effect authority is granted.
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
from canonical.runtime.bound_capabilities import (
    docx_verify_ooxml_intent as independent_docx_verifier,
)
from canonical.runtime.lossless_raw_task_contract_v1 import compile_contract
from canonical.runtime.r2_grounded_candidate_policy_frontier_v1 import (
    goal_scoped_policy_id,
)

SCHEMA = "PROJECT_BRAIN_R2_DOCX_JSON_DIRECT_ADEQUACY_V1"
ROOT = Path(__file__).resolve().parents[2]

CAPABILITY_ID = "docx.document.create_from_json_record"
VERIFIER_CAPABILITY_ID = "docx.document.verify.intent_ooxml"

_PATH = r"canonical/[A-Za-z0-9_.\-/]+"
_FIELD = r"[A-Za-z_][A-Za-z0-9_]*"
_FIELDS = _FIELD + r"(?:\s*,\s*" + _FIELD + r")*(?:\s*,?\s+and\s+" + _FIELD + r")?"
GRAMMAR = re.compile(
    r"^Create (?P<output>" + _PATH + r"\.docx) "
    r"from the normalized JSON (?P<json>" + _PATH + r"\.json) "
    r"with title (?P<title>[^,]+), "
    r"paragraph (?P<paragraph>[^,]+), "
    r"and a two-column table with headers (?P<header1>[^,]+?) and (?P<header2>[^,]+?) "
    r"containing one row for each of (?P<fields>" + _FIELDS + r") "
    r"using their values from the normalized JSON\.?$",
    re.IGNORECASE,
)


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
    p = (rr / rel).resolve()
    if p == rr or rr not in p.parents:
        raise ValueError("PATH_OUTSIDE_REPOSITORY")
    return p


def _canon(value: Any) -> str:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    )


def _snapshot(path: Path) -> tuple[bool, bytes | None]:
    if path.exists() and not path.is_file():
        raise ValueError("TRANSACTION_PATH_NOT_REGULAR_FILE:" + str(path))
    return path.is_file(), path.read_bytes() if path.is_file() else None


def _restore(path: Path, existed: bool, prior: bytes | None) -> None:
    if existed:
        if prior is None:
            raise ValueError("TRANSACTION_PRIOR_BYTES_MISSING")
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(prior)
    elif path.exists():
        if not path.is_file():
            raise ValueError("TRANSACTION_ROLLBACK_PATH_NOT_FILE:" + str(path))
        path.unlink()


def _restore_transaction(
    destination: Path,
    destination_snapshot: tuple[bool, bytes | None],
    intent: Path,
    intent_snapshot: tuple[bool, bytes | None],
) -> None:
    # Restore the dependent intent first and primary artifact second. Both are
    # repository-local and neither is authority-bearing after a failed route.
    _restore(intent, *intent_snapshot)
    _restore(destination, *destination_snapshot)


def _load_registry_pair() -> tuple[Mapping[str, Any], Mapping[str, Any]]:
    registry = live_bound.load_verified_registry()
    producer = registry.get(CAPABILITY_ID)
    verifier = registry.get(VERIFIER_CAPABILITY_ID)
    if not isinstance(producer, Mapping) or not isinstance(verifier, Mapping):
        raise ValueError("DOCX_CAPABILITY_PAIR_NOT_REGISTERED")
    return producer, verifier


def _authenticate_capability_pair(
    producer: Mapping[str, Any],
    verifier: Mapping[str, Any],
) -> None:
    if producer.get("status") != "VERIFIED_BOUND_CAPABILITY":
        raise ValueError("DOCX_PRODUCER_NOT_VERIFIED_BOUND_CAPABILITY")
    if producer.get("adapter_module") != "docx_report_from_json":
        raise ValueError("DOCX_PRODUCER_ADAPTER_MISMATCH")
    verification = producer.get("verification")
    if (
        not isinstance(verification, Mapping)
        or verification.get("independently_verified_by") != VERIFIER_CAPABILITY_ID
        or verification.get("source_record_verified") is not True
    ):
        raise ValueError("DOCX_PRODUCER_INDEPENDENT_VERIFICATION_BINDING_INVALID")

    if verifier.get("status") != "VERIFIED_BOUND_CAPABILITY":
        raise ValueError("DOCX_VERIFIER_NOT_VERIFIED_BOUND_CAPABILITY")
    if verifier.get("adapter_module") != "docx_verify_ooxml_intent":
        raise ValueError("DOCX_VERIFIER_ADAPTER_MISMATCH")
    v = verifier.get("verification")
    if not isinstance(v, Mapping) or v.get("independently_verified") is not True:
        raise ValueError("DOCX_VERIFIER_INDEPENDENT_VERIFICATION_REQUIRED")
    source = verifier.get("source")
    if (
        not isinstance(source, Mapping)
        or source.get("type") != "python_stdlib"
        or sorted(source.get("modules") or [])
        != sorted(["zipfile", "xml.etree.ElementTree"])
    ):
        raise ValueError("DOCX_VERIFIER_SOURCE_IDENTITY_INVALID")


def preflight(
    request: Mapping[str, Any],
    *,
    repo_root: str | Path = ROOT,
) -> dict[str, Any]:
    if not isinstance(request, Mapping):
        return {**_base("FAIL_CLOSED"), "reason": "REQUEST_NOT_OBJECT"}
    task_id = str(request.get("task_id") or "").strip()
    goal = str(request.get("goal") or "").strip()
    if not task_id or not goal:
        return {**_base("FAIL_CLOSED"), "reason": "TASK_ID_AND_GOAL_REQUIRED"}

    match = GRAMMAR.fullmatch(goal)
    if match is None:
        return {**_base("NOT_APPLICABLE"), "matched": False}

    root = Path(repo_root).resolve()
    json_path = match.group("json")
    output_path = match.group("output")
    try:
        source = _inside(root, json_path)
        destination = _inside(root, output_path)
        intent = Path(str(destination) + ".intent.json")
        if not source.is_file():
            raise ValueError("SOURCE_JSON_MISSING")
        if source == destination or source == intent:
            raise ValueError("SOURCE_OUTPUT_ALIAS_FORBIDDEN")
        if destination.exists() and not destination.is_file():
            raise ValueError("DOCX_DESTINATION_NOT_REGULAR_FILE")
        if intent.exists() and not intent.is_file():
            raise ValueError("DOCX_INTENT_DESTINATION_NOT_REGULAR_FILE")

        source_bytes = source.read_bytes()
        source_data = json.loads(source_bytes.decode("utf-8"))
        # Reuse the producer-independent verifier's pure raw-intent parser to
        # establish that this source/goal pair is within its accepted semantic
        # fragment before any effect occurs.
        expected = independent_docx_verifier._expected_json(goal, source_data)

        producer, verifier = _load_registry_pair()
        _authenticate_capability_pair(producer, verifier)

        admissible = goal_compiler._platform_admissible_registry(
            dict(live_bound.load_verified_registry())
        )
        compiled = goal_compiler.compile_goal(goal, admissible, root)
        if compiled.get("controller_actions") is not None:
            raise ValueError("COMPOUND_CONTROLLER_NOT_ALLOWED")
        if compiled.get("selected_capability") != CAPABILITY_ID:
            raise ValueError("DOCX_COMPILED_CAPABILITY_MISMATCH")
        inputs = compiled.get("inputs")
        if not isinstance(inputs, Mapping):
            raise ValueError("DOCX_COMPILED_INPUTS_INVALID")
        if (
            inputs.get("goal") != goal
            or inputs.get("json_path") != json_path
            or inputs.get("output_path") != output_path
        ):
            raise ValueError("DOCX_COMPILED_INPUT_BINDING_MISMATCH")
        targets = compiled.get("target_effects")
        if targets != ["docx.document.create_from_json_record"]:
            raise ValueError("DOCX_COMPILED_TARGET_EFFECT_MISMATCH")

        raw_contract = compile_contract(
            goal,
            source_id="user",
            routing_target_effects=targets,
        )
        if raw_contract.get("pass") is not True:
            raise ValueError("LOSSLESS_RAW_CONTRACT_FAILED")

        return {
            **_base("DIRECT_DOCX_JSON_ADEQUACY_ROUTE_MATCHED"),
            "matched": True,
            "task_id": task_id,
            "goal": goal,
            "goal_sha256": sha256(goal.encode("utf-8")).hexdigest(),
            "policy_id": goal_scoped_policy_id(CAPABILITY_ID, goal),
            "capability_id": CAPABILITY_ID,
            "verifier_capability_id": VERIFIER_CAPABILITY_ID,
            "json_path": json_path,
            "output_path": output_path,
            "intent_path": str(
                intent.relative_to(root)
            ).replace("\\", "/"),
            "source_json_sha256": sha256(source_bytes).hexdigest(),
            "expected_semantics_sha256": sha256(
                _canon(expected).encode("utf-8")
            ).hexdigest(),
            "raw_contract": raw_contract,
            "raw_task_contract_sha256": raw_contract["task_contract_sha256"],
            "acceptance_obligation_count": len(
                raw_contract["acceptance_contract"]["obligations"]
            ),
            "transaction_scope": "DOCX_PLUS_INTENT_SIDECAR",
            "preflight_execution_authority": False,
            "destination_existed_before": destination.is_file(),
            "intent_existed_before": intent.is_file(),
        }
    except Exception as exc:
        return {
            **_base("FAIL_CLOSED"),
            "matched": True,
            "reason": type(exc).__name__ + ":" + str(exc),
        }


def _independent_verify(
    pf: Mapping[str, Any],
    *,
    repo_root: str | Path,
) -> Mapping[str, Any]:
    return independent_docx_verifier.run(
        {"path": pf["output_path"]},
        Path(repo_root).resolve(),
    )


def run(
    request: Mapping[str, Any],
    *,
    repo_root: str | Path = ROOT,
    verifier_provider: Callable[
        [Mapping[str, Any]], Mapping[str, Any]
    ]
    | None = None,
) -> dict[str, Any]:
    pf = preflight(request, repo_root=repo_root)
    if pf.get("matched") is not True:
        return pf
    if pf.get("status") == "FAIL_CLOSED":
        return pf

    root = Path(repo_root).resolve()
    destination = _inside(root, str(pf["output_path"]))
    intent = _inside(root, str(pf["intent_path"]))
    source = _inside(root, str(pf["json_path"]))

    try:
        destination_snapshot = _snapshot(destination)
        intent_snapshot = _snapshot(intent)
    except Exception as exc:
        return {
            **_base("FAIL_CLOSED"),
            "matched": True,
            "policy_id": pf.get("policy_id"),
            "capability_id": CAPABILITY_ID,
            "reason": type(exc).__name__ + ":" + str(exc),
        }

    try:
        raw = live_bound.run_raw_goal(request)
        if not isinstance(raw, Mapping) or raw.get("pass") is not True:
            _restore_transaction(
                destination,
                destination_snapshot,
                intent,
                intent_snapshot,
            )
            return {
                **_base("OPEN__TRANSACTIONAL_DOCX_EXECUTION_DID_NOT_VERIFY"),
                "matched": True,
                "policy_id": pf["policy_id"],
                "capability_id": CAPABILITY_ID,
                "transaction_rolled_back": True,
                "raw_result": deepcopy(dict(raw))
                if isinstance(raw, Mapping)
                else raw,
            }

        if (
            raw.get("compiled_capability_id") != CAPABILITY_ID
            or raw.get("raw_goal_sha256") != pf["goal_sha256"]
            or raw.get("raw_source_coverage_complete") is not True
            or not destination.is_file()
            or not intent.is_file()
        ):
            _restore_transaction(
                destination,
                destination_snapshot,
                intent,
                intent_snapshot,
            )
            return {
                **_base("FAIL_CLOSED"),
                "matched": True,
                "reason": "DOCX_EXECUTION_IDENTITY_OR_ARTIFACT_BINDING_MISMATCH",
                "transaction_rolled_back": True,
            }

        # The source record is an input to both production and acceptance.
        # It must remain exactly the preflighted source throughout the route.
        if sha256(source.read_bytes()).hexdigest() != pf["source_json_sha256"]:
            _restore_transaction(
                destination,
                destination_snapshot,
                intent,
                intent_snapshot,
            )
            return {
                **_base("FAIL_CLOSED"),
                "matched": True,
                "reason": "DOCX_SOURCE_JSON_CHANGED_DURING_EXECUTION",
                "transaction_rolled_back": True,
            }

        sidecar = json.loads(intent.read_text(encoding="utf-8"))
        if (
            sidecar.get("schema")
            != "PROJECT_BRAIN_DOCUMENT_JSON_INTENT_V1"
            or sidecar.get("source_goal") != pf["goal"]
            or sidecar.get("source_json_path") != pf["json_path"]
            or sidecar.get("output_path") != pf["output_path"]
        ):
            _restore_transaction(
                destination,
                destination_snapshot,
                intent,
                intent_snapshot,
            )
            return {
                **_base("FAIL_CLOSED"),
                "matched": True,
                "reason": "DOCX_INTENT_SIDECAR_BINDING_MISMATCH",
                "transaction_rolled_back": True,
            }

        evidence = (
            verifier_provider(pf)
            if verifier_provider is not None
            else _independent_verify(pf, repo_root=root)
        )
        if not isinstance(evidence, Mapping):
            raise ValueError("DOCX_INDEPENDENT_VERIFIER_RESULT_NOT_OBJECT")

        expected = evidence.get("intent_derived_expected")
        verified = (
            evidence.get("verified") is True
            and evidence.get("producer_independent_verifier") is True
            and evidence.get("source_record_verified") is True
            and evidence.get("path") == pf["output_path"]
            and evidence.get("source_json_path") == pf["json_path"]
            and evidence.get("intent_source_goal") == pf["goal"]
            and isinstance(expected, Mapping)
            and sha256(_canon(expected).encode("utf-8")).hexdigest()
            == pf["expected_semantics_sha256"]
        )
        if not verified:
            _restore_transaction(
                destination,
                destination_snapshot,
                intent,
                intent_snapshot,
            )
            return {
                **_base("OPEN__INDEPENDENT_DOCX_ACCEPTANCE_DID_NOT_VERIFY"),
                "matched": True,
                "policy_id": pf["policy_id"],
                "capability_id": CAPABILITY_ID,
                "transaction_rolled_back": True,
                "independent_verification": deepcopy(dict(evidence)),
            }

        if sha256(source.read_bytes()).hexdigest() != pf["source_json_sha256"]:
            _restore_transaction(
                destination,
                destination_snapshot,
                intent,
                intent_snapshot,
            )
            return {
                **_base("FAIL_CLOSED"),
                "matched": True,
                "reason": "DOCX_SOURCE_JSON_CHANGED_DURING_VERIFICATION",
                "transaction_rolled_back": True,
            }

        obligations = pf["raw_contract"]["acceptance_contract"]["obligations"]
        accepted_ids = [str(row["obligation_id"]) for row in obligations]
        return {
            **_base("PASS__TRANSACTIONAL_DOCX_JSON_POLICY_ADEQUACY_VERIFIED", True),
            "matched": True,
            "policy_id": pf["policy_id"],
            "capability_id": CAPABILITY_ID,
            "verifier_capability_id": VERIFIER_CAPABILITY_ID,
            "goal_sha256": pf["goal_sha256"],
            "raw_task_contract_sha256": pf["raw_task_contract_sha256"],
            "json_path": pf["json_path"],
            "output_path": pf["output_path"],
            "intent_path": pf["intent_path"],
            "source_json_sha256": pf["source_json_sha256"],
            "expected_semantics_sha256": pf["expected_semantics_sha256"],
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
                "ONLY_THE_EXACT_JSON_RECORD_TO_DOCX_REPORT_GRAMMAR;"
                "ONE_REPOSITORY_LOCAL_SOURCE_JSON;"
                "ONE_DOCX_PLUS_ITS_INTENT_SIDECAR_TRANSACTION;"
                "VERIFIED_BOUND_DOCX_PRODUCER;"
                "PRODUCER_INDEPENDENT_RAW_GOAL_PLUS_SOURCE_JSON_REPARSE;"
                "OOXML_DOCUMENT_XML_SEMANTIC_VERIFICATION;"
                "NO_EXTERNAL_OR_IRREVERSIBLE_EFFECT_AUTHORITY"
            ),
        }
    except Exception as exc:
        try:
            _restore_transaction(
                destination,
                destination_snapshot,
                intent,
                intent_snapshot,
            )
            rolled_back = True
        except Exception:
            rolled_back = False
        return {
            **_base("FAIL_CLOSED"),
            "matched": True,
            "policy_id": pf.get("policy_id"),
            "capability_id": CAPABILITY_ID,
            "reason": type(exc).__name__ + ":" + str(exc),
            "transaction_rolled_back": rolled_back,
        }
