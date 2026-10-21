"""Independent raw-goal acceptance for the compound archive create-and-verify goal.

The existing ``raw_goal_archive_acceptance_v1`` accepts one exact sentence that
names both paths -- "Create a tar.gz archive from the manifest X, including all
its verification_paths files, and save it to Y." No benchmark goal is written
that way, so that verifier cannot fire on any of them, and the front door's
acceptance gate has therefore never accepted anything: ``semantic_acceptance_complete``
has been ``False`` for every goal.

This module accepts the compound form the machine actually executes --
"Create a tar.gz archive from a manifest and verify the archive against that
manifest." -- which asks for two things, and the compiler really does plan two
capabilities for it: ``archive.tar_gz.create_from_manifest`` then
``archive.verify.tar_gz.gnu``.

Acceptance here is not a restatement of what the plan claimed. The archive is
re-opened from disk, its members are listed, and every member is required to
exist inside the repository. The verify step is required to have been pointed at
the SAME archive and the SAME manifest the create step used, because that is
what "against that manifest" means. Anything else is refused with a reason.
"""
from __future__ import annotations

import hashlib
import json
import re
import tarfile
from collections.abc import Mapping
from pathlib import Path
from typing import Any

SCHEMA = "PROJECT_BRAIN_RAW_GOAL_ARCHIVE_COMPOUND_ACCEPTANCE_V1"
CREATE_CAPABILITY = "archive.tar_gz.create_from_manifest"
VERIFY_CAPABILITY = "archive.verify.tar_gz.gnu"
GRAMMAR = re.compile(
    r"Create a tar\.gz archive from a manifest and verify the archive "
    r"against that manifest\.",
    re.IGNORECASE | re.ASCII,
)


def _digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _unresolved(reason: str) -> dict[str, Any]:
    return {
        "schema": SCHEMA,
        "status": "RAW_GOAL_ACCEPTANCE_UNRESOLVED",
        "pass": False,
        "reason": reason,
        "semantic_acceptance_complete": False,
        "terminal_authority": False,
        "accepted_obligation_ids": [],
        "model_dependency_count": 0,
        "incremental_spend_usd": 0,
    }


def _inside(root: Path, relative: Any) -> Path | None:
    if not isinstance(relative, str) or not relative.strip():
        return None
    candidate = (root / relative).resolve()
    try:
        candidate.relative_to(root.resolve())
    except ValueError:
        return None
    return candidate


def _action_rows(execution: Any) -> list[dict[str, Any]]:
    """The capability actions of a compound controller trace, in order."""
    if not isinstance(execution, list):
        return []
    rows = []
    for row in execution:
        if not isinstance(row, Mapping):
            continue
        plan = row.get("plan")
        args = (plan or {}).get("args") if isinstance(plan, Mapping) else None
        if isinstance(args, Mapping) and args.get("capability_id"):
            rows.append({"args": dict(args), "result": row.get("result") or {}})
    return rows


def verify(
    *,
    goal: str,
    capability_id: Any = None,
    inputs: Any = None,
    execution: Any = None,
    raw_contract: Mapping[str, Any],
    root: Path,
) -> dict[str, Any]:
    """Accept only after the sentence, the trace, and the archive bytes agree."""
    try:
        if not isinstance(goal, str):
            return _unresolved("RAW_GOAL_INVALID")
        if GRAMMAR.fullmatch(goal) is None:
            return _unresolved("NO_EXACT_AUTHENTICATED_GOAL_GRAMMAR")
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
        if (
            len(ids) != len(obligations)
            or not all(isinstance(x, str) and x for x in ids)
            or len(set(ids)) != len(ids)
            or required_ids != ids
            or any(o.get("task_sha256") != raw_contract["task_sha256"] for o in obligations)
        ):
            return _unresolved("RAW_OBLIGATION_BINDING_INVALID")

        rows = _action_rows(execution)
        # The sentence asks for two things in this order: create, then verify.
        # A third capability would mean the plan did something the sentence did
        # not ask for, and accepting it would be accepting a different goal.
        if [r["args"].get("capability_id") for r in rows] != [
            CREATE_CAPABILITY, VERIFY_CAPABILITY
        ]:
            return _unresolved("TRACE_IS_NOT_CREATE_THEN_VERIFY")

        create, verify_row = rows[0], rows[1]
        if create["result"].get("output_verified") is not True:
            return _unresolved("CREATE_STEP_NOT_OUTPUT_VERIFIED")
        if verify_row["result"].get("verified") is not True:
            return _unresolved("VERIFY_STEP_NOT_VERIFIED")

        manifest_rel = create["args"].get("manifest_path")
        output_rel = create["args"].get("output_path")
        manifest = _inside(root, manifest_rel)
        archive = _inside(root, output_rel)
        if manifest is None or archive is None:
            return _unresolved("CREATE_PATH_OUTSIDE_REPOSITORY")
        # "against that manifest" -- the verify step must have been pointed at
        # the same two paths the create step used. Not the same manifest is a
        # different sentence.
        if verify_row["args"].get("manifest_path") != manifest_rel:
            return _unresolved("VERIFY_USED_A_DIFFERENT_MANIFEST")
        if verify_row["args"].get("archive_path") != output_rel:
            return _unresolved("VERIFY_USED_A_DIFFERENT_ARCHIVE")

        if not manifest.is_file():
            return _unresolved("MANIFEST_ABSENT_FROM_DISK")
        if not archive.is_file():
            return _unresolved("ARCHIVE_ABSENT_FROM_DISK")

        # Independent of anything the plan asserted: open the bytes.
        try:
            with tarfile.open(archive, "r:gz") as handle:
                members = sorted(handle.getnames())
        except (tarfile.TarError, OSError, EOFError):
            return _unresolved("ARCHIVE_NOT_A_READABLE_GZIP_TAR")
        if not members:
            return _unresolved("ARCHIVE_HAS_NO_MEMBERS")
        for name in members:
            member = _inside(root, name)
            if member is None or not member.is_file():
                return _unresolved("ARCHIVE_MEMBER_ABSENT_FROM_REPOSITORY")

        return {
            "schema": SCHEMA,
            "status": "RAW_GOAL_ACCEPTANCE_VERIFIED",
            "pass": True,
            "semantic_acceptance_complete": True,
            "terminal_authority": False,
            "accepted_obligation_ids": list(ids),
            "archive_path": output_rel,
            "manifest_path": manifest_rel,
            "archive_member_count": len(members),
            "archive_members": members,
            "archive_sha256": _digest(archive.read_bytes()),
            "independent_reinspection": True,
            "model_dependency_count": 0,
            "incremental_spend_usd": 0,
        }
    except Exception as exc:  # fail closed on anything unexpected
        return _unresolved("ACCEPTANCE_VERIFIER_EXCEPTION:" + type(exc).__name__)
