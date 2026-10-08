"""R2 direct adequacy for exact structured-binary codec goals.

This is a bounded family-level direct route, not a generic language or adequacy
oracle.  It accepts only one exact grammar:

    Encode the JSON value in <repo-local .json> as <FORMAT> and save it to
    <repo-local output>.

An optional *exactly enumerated* execution-surface prefix may require npm/Node or
PyPI/Python.  The selected Brain-owned bound codec must already be independently
verified.  Execution is file-transactional at the declared output path: the old
bytes are restored (or the new file removed) unless a producer-independent
cross-supplier decoder proves that the produced binary decodes to exactly the
source JSON value.

Thus adequacy is established by contained execution plus independent semantic
acceptance, not by grounding confidence or producer self-attestation.
"""
from __future__ import annotations

from copy import deepcopy
from hashlib import sha256
import json
from pathlib import Path
import re
from typing import Any, Callable, Mapping

from canonical.runtime import goal_compiler
from canonical.runtime import independent_npm_codec_verifier
from canonical.runtime import independent_pypi_codec_verifier
from canonical.runtime import live_integrated_brain_v1 as live_bound
from canonical.runtime.lossless_raw_task_contract_v1 import compile_contract
from canonical.runtime.r2_grounded_candidate_policy_frontier_v1 import goal_scoped_policy_id

SCHEMA = "PROJECT_BRAIN_R2_STRUCTURED_BINARY_DIRECT_ADEQUACY_V1"
ROOT = Path(__file__).resolve().parents[2]

_SURFACE = (
    r"(?:(?:Using a zero-cost npm JavaScript library executed by Node\.js, )|"
    r"(?:Using a zero-cost PyPI Python library, ))?"
)
_PATH = r"canonical/[A-Za-z0-9_.\-/]+"
GRAMMAR = re.compile(
    r"^" + _SURFACE
    + r"Encode the JSON value in (?P<json>" + _PATH + r"\.json) "
    + r"as (?P<format>CBOR|MessagePack|MsgPack|BSON) "
    + r"and save it to (?P<output>" + _PATH + r"\.(?:cbor|msgpack|bson))\.?$",
    re.IGNORECASE,
)

_FORMAT_ALIASES = {
    "cbor": "cbor",
    "messagepack": "msgpack",
    "msgpack": "msgpack",
    "bson": "bson",
}

_ALLOWED_ADAPTERS = {
    "npm": "node_library_codec",
    "pypi": "python_library_codec",
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


def _format_from_entry(entry: Mapping[str, Any]) -> str | None:
    values = sorted({
        str(effect)[len("structured.binary.encode."):].lower()
        for effect in entry.get("provides", [])
        if str(effect).startswith("structured.binary.encode.")
        and str(effect) != "structured.binary.encode"
    })
    return values[0] if len(values) == 1 else None


def _producer_identity(entry: Mapping[str, Any]) -> tuple[str, str] | None:
    source = entry.get("source")
    if not isinstance(source, Mapping):
        return None
    source_type = str(source.get("type") or "").lower()
    adapter = str(entry.get("adapter_module") or "")
    if source_type not in _ALLOWED_ADAPTERS or adapter != _ALLOWED_ADAPTERS[source_type]:
        return None
    if source_type == "npm":
        producer = str(source.get("package") or "").strip()
    else:
        producer = str(source.get("project") or "").strip()
    if not producer:
        return None
    return source_type, producer


def preflight(request: Mapping[str, Any], *, repo_root: str | Path = ROOT) -> dict[str, Any]:
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
    requested_format = _FORMAT_ALIASES[match.group("format").lower()]
    json_path = match.group("json")
    output_path = match.group("output")
    if Path(output_path).suffix.lower().lstrip(".") != requested_format:
        return {
            **_base("FAIL_CLOSED"),
            "matched": True,
            "reason": "DECLARED_FORMAT_OUTPUT_SUFFIX_MISMATCH",
        }

    try:
        source_path = _inside(root, json_path)
        destination = _inside(root, output_path)
        if not source_path.is_file():
            raise ValueError("SOURCE_JSON_MISSING")
        json.loads(source_path.read_text(encoding="utf-8"))

        registry = live_bound.load_verified_registry()
        admissible = goal_compiler._platform_admissible_registry(dict(registry))
        compiled = goal_compiler.compile_goal(goal, admissible, root)
        if compiled.get("controller_actions") is not None:
            raise ValueError("COMPOUND_CONTROLLER_NOT_ALLOWED")
        cid = str(compiled.get("selected_capability") or "").strip()
        if cid not in admissible:
            raise ValueError("SELECTED_CAPABILITY_NOT_VERIFIED")
        entry = admissible[cid]
        if entry.get("status") != "VERIFIED_BOUND_CAPABILITY":
            raise ValueError("SELECTED_CAPABILITY_NOT_VERIFIED")
        if (entry.get("verification") or {}).get("independent_verified") is not True:
            raise ValueError("CAPABILITY_INDEPENDENT_VERIFICATION_REQUIRED")

        actual_format = _format_from_entry(entry)
        if actual_format != requested_format:
            raise ValueError("CAPABILITY_FORMAT_MISMATCH")
        producer = _producer_identity(entry)
        if producer is None:
            raise ValueError("CODEC_PRODUCER_IDENTITY_OR_ADAPTER_UNSUPPORTED")

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

        source_type, producer_id = producer
        return {
            **_base("DIRECT_CODEC_ADEQUACY_ROUTE_MATCHED"),
            "matched": True,
            "task_id": task_id,
            "goal": goal,
            "goal_sha256": sha256(goal.encode("utf-8")).hexdigest(),
            "policy_id": goal_scoped_policy_id(cid, goal),
            "capability_id": cid,
            "source_type": source_type,
            "producer_id": producer_id,
            "format": requested_format,
            "json_path": json_path,
            "output_path": output_path,
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


def _independent_verify(
    pf: Mapping[str, Any],
    *,
    repo_root: str | Path,
) -> Mapping[str, Any]:
    if pf["source_type"] == "npm":
        return independent_pypi_codec_verifier.verify(
            pf["format"],
            pf["json_path"],
            pf["output_path"],
            pf["producer_id"],
            repo_root,
        )
    return independent_npm_codec_verifier.verify(
        pf["format"],
        pf["json_path"],
        pf["output_path"],
        pf["producer_id"],
        repo_root,
    )


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
    if pf.get("matched") is not True:
        return pf
    if pf.get("status") == "FAIL_CLOSED":
        return pf

    root = Path(repo_root).resolve()
    destination = _inside(root, str(pf["output_path"]))
    existed = destination.exists()
    prior = destination.read_bytes() if existed else None

    try:
        raw = live_bound.run_raw_goal(request)
        if not isinstance(raw, Mapping) or raw.get("pass") is not True:
            _restore(destination, existed, prior)
            return {
                **_base("OPEN__TRANSACTIONAL_CODEC_EXECUTION_DID_NOT_VERIFY"),
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
        ):
            _restore(destination, existed, prior)
            return {
                **_base("FAIL_CLOSED"),
                "matched": True,
                "reason": "EXECUTION_IDENTITY_OR_OUTPUT_BINDING_MISMATCH",
                "transaction_rolled_back": True,
            }

        evidence = (
            verifier_provider(pf)
            if verifier_provider is not None
            else _independent_verify(pf, repo_root=root)
        )
        if not isinstance(evidence, Mapping) or evidence.get("verified") is not True:
            _restore(destination, existed, prior)
            return {
                **_base("OPEN__INDEPENDENT_CODEC_ACCEPTANCE_DID_NOT_VERIFY"),
                "matched": True,
                "policy_id": pf["policy_id"],
                "capability_id": pf["capability_id"],
                "transaction_rolled_back": True,
                "independent_verification": deepcopy(dict(evidence))
                if isinstance(evidence, Mapping) else None,
            }

        independent = evidence.get("producer_independent") is True and (
            evidence.get("dependency_independent") is True
            or (
                evidence.get("implementation_independent") is True
                and evidence.get("supplier_class_independent") is True
            )
        )
        if not independent:
            _restore(destination, existed, prior)
            return {
                **_base("FAIL_CLOSED"),
                "matched": True,
                "reason": "CODEC_VERIFIER_NOT_SUFFICIENTLY_INDEPENDENT",
                "transaction_rolled_back": True,
            }

        obligations = pf["raw_contract"]["acceptance_contract"]["obligations"]
        accepted_ids = [str(row["obligation_id"]) for row in obligations]
        return {
            **_base("PASS__TRANSACTIONAL_STRUCTURED_BINARY_POLICY_ADEQUACY_VERIFIED", True),
            "matched": True,
            "policy_id": pf["policy_id"],
            "capability_id": pf["capability_id"],
            "goal_sha256": pf["goal_sha256"],
            "raw_task_contract_sha256": pf["raw_task_contract_sha256"],
            "format": pf["format"],
            "source_type": pf["source_type"],
            "producer_id": pf["producer_id"],
            "json_path": pf["json_path"],
            "output_path": pf["output_path"],
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
                "ONLY_THE_EXACT_SINGLE_ACTION_CODEC_GRAMMAR;ONE_REPOSITORY_LOCAL_OUTPUT;"
                "VERIFIED_BOUND_CODEC;PRODUCER_INDEPENDENT_SEMANTIC_DECODE_EQUALS_EXACT_SOURCE_JSON;"
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
