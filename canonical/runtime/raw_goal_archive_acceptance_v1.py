"""Conservative post-execution, raw-intent acceptance for one exact archive goal.

This is a bounded semantic acceptance cell, not general natural-language understanding.
An authenticated execution trace is necessary but not sufficient. Acceptance requires
an exact, unambiguous user directive and independent inspection of the resulting tar.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import re
import tarfile
from typing import Any, Mapping


def _unwrap_result(result: Any) -> Any:
    """The capability's own fields, whether or not an adapter wrapped them.

    Imported lazily so this module keeps no import-time dependency on the trace
    verifier; a union where the wrapper's own keys win, so nothing it recorded
    is displaced.
    """
    if not isinstance(result, Mapping):
        return result
    inner = result.get("result")
    if not isinstance(inner, Mapping):
        return result
    merged = dict(result)
    for key, value in inner.items():
        merged.setdefault(key, value)
    return merged

SCHEMA = "PROJECT_BRAIN_RAW_GOAL_ARCHIVE_ACCEPTANCE_V1"
CAPABILITY = "archive.tar_gz.create_from_manifest"
GRAMMAR = re.compile(
    r"Create a tar\.gz archive from the manifest "
    r"(?P<manifest>[A-Za-z0-9_./-]+\.json), including all its "
    r"verification_paths files, and save it to "
    r"(?P<output>[A-Za-z0-9_./-]+\.tar\.gz)\.",
    re.IGNORECASE | re.ASCII,
)


def _digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _inside(root: Path, relative: str) -> Path:
    if not isinstance(relative, str) or not relative or Path(relative).is_absolute():
        raise ValueError("INVALID_RELATIVE_PATH")
    if ".." in Path(relative).parts or "\\" in relative or relative.startswith("/"):
        raise ValueError("UNSAFE_RELATIVE_PATH")
    p = (root / relative).resolve()
    if root not in p.parents:
        raise ValueError("PATH_OUTSIDE_REPOSITORY")
    return p


def _unresolved(reason: str) -> dict[str, Any]:
    return {
        "schema": SCHEMA,
        "pass": False,
        "status": "UNRESOLVED__RAW_GOAL_ACCEPTANCE",
        "reason": reason,
        "accepted_obligation_ids": [],
        "semantic_acceptance_complete": False,
        "terminal_authority": False,
        "terminal_credit_delta": 0,
    }


def verify(
    *,
    goal: str,
    capability_id: str,
    inputs: Mapping[str, Any],
    execution: Mapping[str, Any],
    raw_contract: Mapping[str, Any],
    root: Path,
) -> dict[str, Any]:
    """Only assert acceptance after exact task semantics and artifact bytes agree."""
    try:
        if not isinstance(goal, str) or not isinstance(inputs, Mapping):
            return _unresolved("RAW_GOAL_OR_INPUTS_INVALID")
        match = GRAMMAR.fullmatch(goal)
        if match is None:
            return _unresolved("NO_EXACT_AUTHENTICATED_GOAL_GRAMMAR")
        if capability_id != CAPABILITY:
            return _unresolved("EXECUTED_CAPABILITY_DOES_NOT_MATCH_SEMANTIC_GOAL")
        manifest_rel = match.group("manifest")
        output_rel = match.group("output")
        if inputs.get("manifest_path") != manifest_rel or inputs.get("output_path") != output_rel:
            return _unresolved("GOAL_TO_EXECUTION_INPUT_BINDING_MISMATCH")
        if not isinstance(raw_contract, Mapping) or raw_contract.get("pass") is not True:
            return _unresolved("RAW_TASK_CONTRACT_NOT_VERIFIED")
        if raw_contract.get("task_sha256") != _digest(goal.encode("utf-8")):
            return _unresolved("RAW_GOAL_HASH_MISMATCH")
        acceptance = raw_contract.get("acceptance_contract")
        if not isinstance(acceptance, Mapping):
            return _unresolved("ACCEPTANCE_CONTRACT_MISSING")
        obligations = acceptance.get("obligations")
        if not isinstance(obligations, list) or not obligations:
            return _unresolved("RAW_OBLIGATIONS_MISSING")
        required_ids = acceptance.get("required_obligation_ids")
        ids = [o.get("obligation_id") for o in obligations if isinstance(o, Mapping)]
        if (len(ids) != len(obligations) or not all(isinstance(x, str) and x for x in ids)
                or len(set(ids)) != len(ids) or required_ids != ids
                or any(o.get("task_sha256") != raw_contract["task_sha256"] for o in obligations)):
            return _unresolved("RAW_OBLIGATION_BINDING_INVALID")
        if not isinstance(execution, Mapping) or execution.get("pass") is not True:
            return _unresolved("PROMOTED_CAPABILITY_EXECUTION_NOT_VERIFIED")
        if execution.get("capability_id") != capability_id:
            return _unresolved("EXECUTION_CAPABILITY_ID_MISMATCH")

        if not execution.get("composition_capsule_head_hash"):
            if execution.get("execution_proof_type") != "MODEL_INDEPENDENT_CONTROLLER_TRACE_V1":
                return _unresolved("INDEPENDENT_TRACE_PROOF_MISSING")
            trace = execution.get("controller_trace")
            plan_sha = execution.get("controller_plan_sha256")
            if (
                not isinstance(trace, list)
                or len(trace) != 2
                or not isinstance(plan_sha, str)
                or len(plan_sha) != 64
            ):
                return _unresolved("CONTROLLER_TRACE_PROOF_INVALID")
            expected_finish = {"type": "finish", "args": {"summary": "RAW_GOAL_COMPLETE"}}
            observed_actions = []
            for index, row in enumerate(trace):
                if (
                    not isinstance(row, Mapping)
                    or row.get("cycle") != index
                    or not isinstance(row.get("plan"), Mapping)
                    or not isinstance(row.get("result"), Mapping)
                ):
                    return _unresolved("CONTROLLER_TRACE_RECORD_INVALID")
                observed_actions.append(dict(row["plan"]))

            # The work step must be this capability, carrying the manifest and
            # the output this sentence named, whether the controller sent it as
            # the registry template or as the verified bound adapter action.
            # Both name the same capability and the same two arguments; the
            # bound form is the one whose trace carries the proof digests the
            # learning adapters bind an episode to, so refusing it here meant a
            # goal could be executed, accepted and re-inspected and still never
            # become experience. The bound form nests its arguments under
            # ``inputs``, so both places are read.
            def _bound_arg(args: Mapping[str, Any], name: str) -> Any:
                if name in args:
                    return args[name]
                nested = args.get("inputs")
                if isinstance(nested, Mapping) and name in nested:
                    return nested[name]
                return None

            work = observed_actions[0]
            work_args = work.get("args") if isinstance(work.get("args"), Mapping) else {}
            if (
                work.get("type")
                not in {"invoke_capability", "invoke_verified_bound_capability_adapter"}
                or str(work_args.get("capability_id") or "") != capability_id
                or _bound_arg(work_args, "manifest_path") != manifest_rel
                or _bound_arg(work_args, "output_path") != output_rel
                or observed_actions[1] != expected_finish
            ):
                return _unresolved("CONTROLLER_TRACE_ACTION_BINDING_MISMATCH")
            # Bound to the actions that actually ran, which is what the
            # controller hashed into ``controller_plan_sha256``. Recomputing it
            # over the observed plan rather than over a shape this file expects
            # keeps the tamper check exact: change any byte of the recorded plan
            # and the digest still stops matching.
            canonical = json.dumps(
                observed_actions,
                sort_keys=True,
                separators=(",", ":"),
                ensure_ascii=False,
            ).encode("utf-8")
            if hashlib.sha256(canonical).hexdigest() != plan_sha:
                return _unresolved("CONTROLLER_TRACE_PLAN_HASH_MISMATCH")
            if trace[-1]["result"].get("summary") != "RAW_GOAL_COMPLETE":
                return _unresolved("CONTROLLER_TRACE_FINISH_INVALID")

        # The verified bound adapter nests the capability's own result one
        # level down; unwrap so this verifier reads the same fields either way.
        result = _unwrap_result(execution.get("result"))
        if not isinstance(result, Mapping) or result.get("output_verified") is not True:
            return _unresolved("CAPABILITY_OUTPUT_PROOF_MISSING")
        root = Path(root).resolve()
        manifest = _inside(root, manifest_rel)
        output = _inside(root, output_rel)
        if not manifest.is_file() or not output.is_file() or manifest == output:
            return _unresolved("SOURCE_OR_OUTPUT_MISSING")
        doc = json.loads(manifest.read_text(encoding="utf-8"))
        if not isinstance(doc, Mapping) or not isinstance(doc.get("records"), list):
            return _unresolved("MANIFEST_SHAPE_INVALID")
        members = {manifest_rel}
        for record in doc["records"]:
            if not isinstance(record, Mapping) or not isinstance(record.get("verification_paths"), list):
                return _unresolved("MANIFEST_RECORD_INVALID")
            for rel in record["verification_paths"]:
                if not isinstance(rel, str) or not rel.startswith("canonical/"):
                    return _unresolved("MANIFEST_MEMBER_INVALID")
                members.add(rel)
        if output_rel in members:
            return _unresolved("OUTPUT_EQUALS_ARCHIVE_MEMBER")
        if (result.get("output_path") != output_rel
                or result.get("output_sha256") != _digest(output.read_bytes())
                or result.get("members") != sorted(members)
                or result.get("member_count") != len(members)):
            return _unresolved("TRACE_OUTPUT_DIGEST_OR_MEMBERS_MISMATCH")
        actual_source_hashes = {}
        for rel in sorted(members):
            src = _inside(root, rel)
            if not src.is_file() or src.is_symlink():
                return _unresolved("SOURCE_FILE_UNSAFE_OR_MISSING")
            actual_source_hashes[rel] = _digest(src.read_bytes())
        if result.get("source_sha256") != actual_source_hashes:
            return _unresolved("SOURCE_CHANGED_SINCE_EXECUTION")
        with tarfile.open(output, "r:gz") as archive:
            infos = archive.getmembers()
            if len(infos) != len(members) or sorted(i.name for i in infos) != sorted(members):
                return _unresolved("ARCHIVE_MEMBER_SET_NOT_EXACT")
            if any(not info.isfile() or info.issym() or info.islnk() for info in infos):
                return _unresolved("ARCHIVE_UNSAFE_MEMBER_TYPE")
            for info in infos:
                data_file = archive.extractfile(info)
                if data_file is None or _digest(data_file.read()) != actual_source_hashes[info.name]:
                    return _unresolved("ARCHIVE_MEMBER_BYTES_MISMATCH")
        return {
            "schema": SCHEMA,
            "pass": True,
            "status": "PASS__EXACT_RAW_GOAL_ARCHIVE_ACCEPTED",
            "goal_sha256": raw_contract["task_sha256"],
            "task_contract_sha256": raw_contract.get("task_contract_sha256"),
            "accepted_obligation_ids": ids,
            "verified_output_path": output_rel,
            "verified_output_sha256": result["output_sha256"],
            "verified_archive_members": sorted(members),
            "semantic_acceptance_complete": True,
            "acceptance_scope": "EXACT_ARCHIVE_MANIFEST_VERIFICATION_PATHS_GOAL_ONLY",
            "terminal_authority": False,
            "terminal_credit_delta": 0,
        }
    except Exception as exc:
        return _unresolved(type(exc).__name__ + ":" + str(exc))
