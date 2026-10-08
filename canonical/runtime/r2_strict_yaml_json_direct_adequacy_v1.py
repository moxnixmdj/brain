"""R2 direct adequacy for a strict, ambiguity-free YAML-to-JSON family.

This is deliberately not arbitrary YAML. The admitted source is one repository-local
UTF-8 mapping with one key/value pair per nonblank line:

    key: <JSON literal>

Keys are simple identifiers. Values must be valid JSON literals, so strings are
quoted and arrays/objects use JSON flow syntax. Comments, anchors, tags, block
scalars, implicit strings, duplicate keys, indentation, and YAML-specific scalar
coercions are outside this family.

The verified Brain-owned yq capability is only the producer. Adequacy is granted
only after an independent stdlib parser recomputes the exact semantic mapping from
the original source bytes and the produced JSON equals that mapping. The source is
hash-bound before and after execution and the output file is transactional.
"""
from __future__ import annotations

from copy import deepcopy
from hashlib import sha256
import json
from pathlib import Path
import re
from typing import Any, Mapping

from canonical.runtime import live_integrated_brain_v1 as live_bound
from canonical.runtime import verified_bound_capability_execution_adapter_v1 as bound_exec
from canonical.runtime.lossless_raw_task_contract_v1 import compile_contract
from canonical.runtime.r2_grounded_candidate_policy_frontier_v1 import goal_scoped_policy_id

SCHEMA = "PROJECT_BRAIN_R2_STRICT_YAML_JSON_DIRECT_ADEQUACY_V1"
ROUTE_ID = "DIRECT_ADEQUACY::STRICT_YAML_JSON_MAPPING_FAMILY_V1"
CAPABILITY_ID = "yaml.to_json.yq"
ROOT = Path(__file__).resolve().parents[2]

_PATH = r"canonical/[A-Za-z0-9_.\-/]+"
GRAMMAR = re.compile(
    r"^Convert the strict YAML mapping in (?P<input>" + _PATH + r"\.(?:yaml|yml)) "
    r"to JSON and save the verified result to (?P<output>" + _PATH + r"\.json)\.?$",
    re.IGNORECASE,
)
_KEY = re.compile(r"^[A-Za-z_][A-Za-z0-9_.-]{0,127}$")
_MAX_SOURCE_BYTES = 1_000_000
_MAX_ROWS = 10_000


def _base(status: str, *, passed: bool = False) -> dict[str, Any]:
    return {
        "schema": SCHEMA,
        "status": status,
        "pass": passed,
        "matched": False,
        "semantic_acceptance_complete": False,
        "actual_goal_satisfaction_verified": False,
        "direct_adequacy_authority": False,
        "execution_authority": False,
        "terminal_authority": False,
        "terminal_credit_delta": 0,
        "incremental_spend_usd": 0,
    }


def _safe(root: Path, rel: str) -> Path:
    root = root.resolve()
    raw = Path(str(rel))
    if raw.is_absolute() or ".." in raw.parts:
        raise ValueError("PATH_INVALID")
    path = (root / raw).resolve()
    if path == root or root not in path.parents:
        raise ValueError("PATH_OUTSIDE_REPOSITORY")
    return path


def _sha_file(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()


def _canon(value: Any) -> bytes:
    return (
        json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        )
        + "\n"
    ).encode("utf-8")


def _strict_parse(raw: bytes) -> dict[str, Any]:
    if len(raw) > _MAX_SOURCE_BYTES:
        raise ValueError("STRICT_YAML_SOURCE_TOO_LARGE")
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise ValueError("STRICT_YAML_UTF8_REQUIRED") from exc
    if "\t" in text:
        raise ValueError("STRICT_YAML_TABS_FORBIDDEN")

    out: dict[str, Any] = {}
    rows = 0
    for lineno, line in enumerate(text.splitlines(), 1):
        if not line.strip():
            continue
        rows += 1
        if rows > _MAX_ROWS:
            raise ValueError("STRICT_YAML_ROW_LIMIT")
        if line != line.strip():
            raise ValueError("STRICT_YAML_INDENTATION_FORBIDDEN:" + str(lineno))
        if line.startswith(("#", "---", "...", "-", "!", "&", "*")):
            raise ValueError("STRICT_YAML_SYNTAX_OUTSIDE_FAMILY:" + str(lineno))
        if ": " not in line:
            raise ValueError("STRICT_YAML_KEY_VALUE_SEPARATOR_REQUIRED:" + str(lineno))
        key, value_text = line.split(": ", 1)
        if _KEY.fullmatch(key) is None:
            raise ValueError("STRICT_YAML_KEY_INVALID:" + str(lineno))
        if key in out:
            raise ValueError("STRICT_YAML_DUPLICATE_KEY:" + key)
        if not value_text or value_text.startswith(("&", "*", "!", "|", ">", "#")):
            raise ValueError("STRICT_YAML_VALUE_OUTSIDE_FAMILY:" + str(lineno))
        try:
            value = json.loads(value_text)
        except Exception as exc:
            raise ValueError("STRICT_YAML_VALUE_NOT_JSON_LITERAL:" + str(lineno)) from exc
        # json.loads accepts all JSON containers/scalars; NaN/Infinity are not legal
        # JSON input tokens under its default decoder except NaN/Infinity constants,
        # so reject non-finite floats explicitly.
        def validate(v: Any) -> None:
            if isinstance(v, float) and (v != v or v in (float("inf"), float("-inf"))):
                raise ValueError("STRICT_YAML_NONFINITE_NUMBER")
            if isinstance(v, list):
                for item in v:
                    validate(item)
            elif isinstance(v, dict):
                for k, item in v.items():
                    if not isinstance(k, str):
                        raise ValueError("STRICT_YAML_JSON_OBJECT_KEY_NOT_STRING")
                    validate(item)
        validate(value)
        out[key] = value
    if not out:
        raise ValueError("STRICT_YAML_NONEMPTY_MAPPING_REQUIRED")
    return out


def _raw_contract(goal: str) -> dict[str, Any]:
    contract = compile_contract(
        goal,
        source_id="user",
        routing_target_effects=["yaml.to_json"],
    )
    if contract.get("pass") is not True:
        raise ValueError("RAW_TASK_CONTRACT_FAIL_CLOSED")
    ids = list(
        (contract.get("acceptance_contract") or {}).get("required_obligation_ids") or []
    )
    if not ids:
        raise ValueError("RAW_ACCEPTANCE_OBLIGATIONS_MISSING")
    return contract


def preflight(
    request: Mapping[str, Any],
    *,
    repo_root: str | Path | None = None,
) -> dict[str, Any]:
    root = Path(repo_root).resolve() if repo_root is not None else ROOT
    if not isinstance(request, Mapping):
        return {**_base("FAIL_CLOSED"), "reason": "REQUEST_NOT_OBJECT"}
    task_id = str(request.get("task_id") or "").strip()
    goal = str(request.get("goal") or "").strip()
    if not task_id or not goal:
        return {**_base("FAIL_CLOSED"), "reason": "TASK_ID_AND_GOAL_REQUIRED"}
    match = GRAMMAR.fullmatch(goal)
    if match is None:
        return {**_base("NOT_APPLICABLE"), "matched": False}

    try:
        input_rel = match.group("input")
        output_rel = match.group("output")
        source = _safe(root, input_rel)
        destination = _safe(root, output_rel)
        if source == destination:
            raise ValueError("SOURCE_OUTPUT_COLLISION")
        if not source.is_file():
            raise ValueError("STRICT_YAML_SOURCE_MISSING")
        expected = _strict_parse(source.read_bytes())

        registry = live_bound.load_verified_registry()
        entry = registry.get(CAPABILITY_ID)
        if not isinstance(entry, Mapping) or entry.get("status") != "VERIFIED_BOUND_CAPABILITY":
            raise ValueError("YQ_VERIFIED_BOUND_CAPABILITY_REQUIRED")
        verification = entry.get("verification")
        if not isinstance(verification, Mapping):
            raise ValueError("YQ_VERIFICATION_BINDING_REQUIRED")

        goal_sha = sha256(goal.encode("utf-8")).hexdigest()
        instance_id = "r2-strict-yaml-json-" + goal_sha[:16]
        prepared = bound_exec.prepare(
            CAPABILITY_ID,
            inputs={
                "yaml_path": input_rel,
                "output_path": output_rel,
                "timeout_s": 60,
            },
            instance_id=instance_id,
        )
        contract = _raw_contract(goal)
        accepted = list(contract["acceptance_contract"]["required_obligation_ids"])
        return {
            **_base("DIRECT_ADEQUACY_ROUTE_MATCHED"),
            "matched": True,
            "route_id": ROUTE_ID,
            "task_id": task_id,
            "goal": goal,
            "goal_sha256": goal_sha,
            "policy_id": goal_scoped_policy_id(CAPABILITY_ID, goal),
            "capability_id": CAPABILITY_ID,
            "input_path": input_rel,
            "input_sha256": _sha_file(source),
            "output_path": output_rel,
            "expected_result_sha256": sha256(_canon(expected)).hexdigest(),
            "raw_task_contract_sha256": contract["task_contract_sha256"],
            "raw_acceptance_obligation_ids": accepted,
            "execution_instance_id": instance_id,
            "registry_file_sha256": prepared["registry_file_sha256"],
            "registry_entry_sha256": prepared["registry_entry_sha256"],
            "rendered_action_sha256": prepared["rendered_action_sha256"],
            "semantic_scope": (
                "STRICT_FLAT_YAML_MAPPING__SIMPLE_KEYS__JSON_LITERAL_VALUES_ONLY"
            ),
            "preflight_execution_authority": False,
        }
    except Exception as exc:
        return {
            **_base("FAIL_CLOSED"),
            "matched": True,
            "route_id": ROUTE_ID,
            "reason": type(exc).__name__ + ":" + str(exc),
        }


def _restore(path: Path, existed: bool, prior: bytes | None) -> None:
    if existed:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(prior or b"")
    else:
        try:
            path.unlink()
        except FileNotFoundError:
            pass


def run(
    request: Mapping[str, Any],
    *,
    repo_root: str | Path | None = None,
) -> dict[str, Any]:
    root = Path(repo_root).resolve() if repo_root is not None else ROOT
    pf = preflight(request, repo_root=root)
    if pf.get("matched") is not True or pf.get("status") == "FAIL_CLOSED":
        return pf

    source = _safe(root, str(pf["input_path"]))
    destination = _safe(root, str(pf["output_path"]))
    existed = destination.is_file()
    prior = destination.read_bytes() if existed else None

    try:
        if _sha_file(source) != pf["input_sha256"]:
            raise RuntimeError("STRICT_YAML_SOURCE_DRIFT_BEFORE_EXECUTION")
        expected = _strict_parse(source.read_bytes())
        if sha256(_canon(expected)).hexdigest() != pf["expected_result_sha256"]:
            raise RuntimeError("STRICT_YAML_REFERENCE_DRIFT")

        produced = bound_exec.execute(
            CAPABILITY_ID,
            inputs={
                "yaml_path": pf["input_path"],
                "output_path": pf["output_path"],
                "timeout_s": 60,
            },
            instance_id=pf["execution_instance_id"],
            expected_registry_file_sha256=pf["registry_file_sha256"],
            expected_registry_entry_sha256=pf["registry_entry_sha256"],
            expected_rendered_action_sha256=pf["rendered_action_sha256"],
        )
        if not isinstance(produced, Mapping) or produced.get("pass") is not True:
            raise RuntimeError("YQ_VERIFIED_EXECUTION_FAILED")
        result = produced.get("result")
        if (
            produced.get("capability_id") != CAPABILITY_ID
            or not isinstance(result, Mapping)
            or result.get("output_verified") is not True
            or result.get("output_path") != pf["output_path"]
        ):
            raise RuntimeError("YQ_EXECUTION_BINDING_MISMATCH")
        if _sha_file(source) != pf["input_sha256"]:
            raise RuntimeError("STRICT_YAML_SOURCE_MUTATED_BY_PRODUCER")
        if not destination.is_file():
            raise RuntimeError("STRICT_YAML_JSON_OUTPUT_MISSING")

        actual = json.loads(destination.read_text(encoding="utf-8"))
        recomputed = _strict_parse(source.read_bytes())
        if actual != recomputed:
            raise RuntimeError("INDEPENDENT_STRICT_YAML_SEMANTIC_VERIFICATION_FAILED")
        actual_sha = sha256(_canon(actual)).hexdigest()
        if actual_sha != pf["expected_result_sha256"]:
            raise RuntimeError("INDEPENDENT_STRICT_YAML_SEMANTIC_HASH_MISMATCH")

        contract = _raw_contract(str(request["goal"]))
        accepted = list(contract["acceptance_contract"]["required_obligation_ids"])
        if accepted != pf["raw_acceptance_obligation_ids"]:
            raise RuntimeError("RAW_ACCEPTANCE_SET_DRIFT")

        return {
            **_base("PASS__DIRECT_END_TO_END_ADEQUACY_VERIFIED", passed=True),
            "matched": True,
            "route_id": ROUTE_ID,
            "capability_id": CAPABILITY_ID,
            "selected_policy_id": pf["policy_id"],
            "goal_sha256": pf["goal_sha256"],
            "input_path": pf["input_path"],
            "input_sha256": pf["input_sha256"],
            "output_path": pf["output_path"],
            "output_sha256": _sha_file(destination),
            "semantic_scope": pf["semantic_scope"],
            "semantic_acceptance_complete": True,
            "actual_goal_satisfaction_verified": True,
            "direct_adequacy_authority": True,
            "accepted_raw_obligation_ids": accepted,
            "raw_acceptance_obligation_count": len(accepted),
            "producer_result": deepcopy(dict(produced)),
            "acceptance_receipt": {
                "verified": True,
                "producer_independent": True,
                "verifier": "r2_strict_yaml_json_direct_adequacy_v1._strict_parse",
                "source_sha256": pf["input_sha256"],
                "expected_semantic_sha256": pf["expected_result_sha256"],
                "actual_semantic_sha256": actual_sha,
                "source_immutability_verified": True,
                "yaml_specific_implicit_typing_admitted": False,
            },
            "execution_attempted": True,
            "retry_by_other_route_authorized": False,
            "transaction_committed": True,
            "transaction_rolled_back": False,
            "authority_boundary": (
                "EXACT_STRICT_FLAT_YAML_MAPPING_GOAL_ONLY;"
                "SIMPLE_KEYS_AND_JSON_LITERAL_VALUES_ONLY;"
                "YQ_PRODUCER_PLUS_INDEPENDENT_STDLIB_REFERENCE_PARSE;"
                "SOURCE_HASH_IMMUTABLE;ONE_REPOSITORY_LOCAL_JSON_OUTPUT;"
                "NO_YAML_COMMENTS_ANCHORS_TAGS_BLOCK_SCALARS_IMPLICIT_STRINGS_OR_INDENTED_STRUCTURES;"
                "NO_EXTERNAL_OR_IRREVERSIBLE_EFFECT_AUTHORITY"
            ),
        }
    except Exception as exc:
        _restore(destination, existed, prior)
        return {
            **_base("FAIL_CLOSED"),
            "matched": True,
            "route_id": ROUTE_ID,
            "capability_id": CAPABILITY_ID,
            "selected_policy_id": pf.get("policy_id"),
            "goal_sha256": pf.get("goal_sha256"),
            "reason": type(exc).__name__ + ":" + str(exc),
            "execution_attempted": True,
            "retry_by_other_route_authorized": False,
            "transaction_rolled_back": True,
        }
