from __future__ import annotations

import hashlib
import re
from pathlib import Path
from typing import Any, Mapping

from canonical.runtime import root3_admin_persistence_driver_v1 as admin_driver
from canonical.runtime.root3_broker_rpc_v1 import verify_request

REGISTRY_SCHEMA = "PROJECT_BRAIN_ROOT3_PARENT_DRIVER_REGISTRY_V1"
ADMIN_DRIVER_ID = "ASTRA_ADMIN_PERSISTENCE_V1"

REGISTRY = {
    ADMIN_DRIVER_ID: {
        "contract_path": (
            "canonical/governance/"
            "ROOT3_ADMIN_PERSISTENCE_DRIVER_CONTRACT_20261007_V1.json"
        ),
        "contract_git_blob_sha": "51d28ddd3ebbe4dd1b213f5b7a27736d5aa85e0b",
        "implementation_path": "canonical/runtime/root3_admin_persistence_driver_v1.py",
        "implementation_git_blob_sha": "b49e03915f05599831f3eedf047341c3f24f3bad",
    }
}

_MISSION_ID = re.compile(r"^[A-Za-z0-9_.-]{1,200}$")
_SHA256 = re.compile(r"^[0-9a-f]{64}$")


class ParentDriverRegistryError(RuntimeError):
    pass


def _git_blob_sha(path: Path) -> str:
    raw = path.read_bytes()
    return hashlib.sha1(
        b"blob " + str(len(raw)).encode("ascii") + b"\0" + raw
    ).hexdigest()


def _verify_spec(repo_root: Path, spec: Mapping[str, str]) -> None:
    for path_key, sha_key in (
        ("contract_path", "contract_git_blob_sha"),
        ("implementation_path", "implementation_git_blob_sha"),
    ):
        path = (repo_root / spec[path_key]).resolve()
        root = repo_root.resolve()
        if path != root and root not in path.parents:
            raise ParentDriverRegistryError("DRIVER_PATH_ESCAPES_REPO")
        if not path.is_file():
            raise ParentDriverRegistryError("DRIVER_BOUND_FILE_MISSING:" + spec[path_key])
        actual = _git_blob_sha(path)
        if actual != spec[sha_key]:
            raise ParentDriverRegistryError(
                "DRIVER_BOUND_FILE_DRIFT:" + spec[path_key] + ":" + actual
            )


def _mission_context(raw: Mapping[str, Any] | None) -> dict[str, str]:
    if not isinstance(raw, Mapping) or set(raw) != {
        "mission_id",
        "mission_sha256",
        "mission_rel",
    }:
        raise ParentDriverRegistryError("MISSION_AUTHORITY_CONTEXT_REQUIRED")
    mission_id = str(raw.get("mission_id") or "")
    mission_sha256 = str(raw.get("mission_sha256") or "")
    mission_rel = str(raw.get("mission_rel") or "").replace("\\", "/")
    if _MISSION_ID.fullmatch(mission_id) is None:
        raise ParentDriverRegistryError("MISSION_ID_INVALID")
    if _SHA256.fullmatch(mission_sha256) is None:
        raise ParentDriverRegistryError("MISSION_SHA256_INVALID")
    if (
        not mission_rel.startswith("canonical/astra_runtime/missions/")
        or not mission_rel.endswith(".json")
        or ".." in Path(mission_rel).parts
    ):
        raise ParentDriverRegistryError("MISSION_REL_INVALID")
    return {
        "mission_id": mission_id,
        "mission_sha256": mission_sha256,
        "mission_rel": mission_rel,
    }


def _authorize_admin_path(
    typed_args: Mapping[str, Any],
    authority_context: Mapping[str, Any] | None,
) -> dict[str, str]:
    if not isinstance(typed_args, Mapping):
        raise ParentDriverRegistryError("TYPED_ARGS_NOT_OBJECT")
    destination_class = str(typed_args.get("destination_class") or "")
    path = str(typed_args.get("path") or "").replace("\\", "/")
    if destination_class == "ASTRA_STATE_JSON":
        if not path.startswith("canonical/astra_runtime/state/"):
            raise ParentDriverRegistryError("PATH_NOT_ALLOWED")
    elif destination_class in {"ASTRA_EVIDENCE_JSON", "ASTRA_EVIDENCE_JSONL"}:
        if not path.startswith("canonical/astra_runtime/evidence/"):
            raise ParentDriverRegistryError("PATH_NOT_ALLOWED")
    else:
        raise ParentDriverRegistryError("PATH_NOT_ALLOWED")
    ctx = _mission_context(authority_context)
    mid = ctx["mission_id"]

    state_exact = f"canonical/astra_runtime/state/{mid}.json"
    state_prefix = f"canonical/astra_runtime/state/{mid}__"
    evidence_prefix = f"canonical/astra_runtime/evidence/{mid}__"

    allowed = False
    if destination_class == "ASTRA_STATE_JSON":
        allowed = (
            path == state_exact
            or (path.startswith(state_prefix) and path.endswith(".json"))
        )
    elif destination_class == "ASTRA_EVIDENCE_JSON":
        allowed = path.startswith(evidence_prefix) and path.endswith(".json")
    elif destination_class == "ASTRA_EVIDENCE_JSONL":
        allowed = path.startswith(evidence_prefix) and path.endswith(".jsonl")

    if not allowed:
        raise ParentDriverRegistryError("MISSION_SCOPED_ADMIN_PATH_DENY")
    return ctx


def dispatch(
    repo_root: str | Path,
    raw_request: Mapping[str, Any],
    *,
    authority_context: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    request = verify_request(raw_request)
    spec = REGISTRY.get(request["driver_id"])
    if spec is None:
        raise ParentDriverRegistryError("UNKNOWN_DRIVER_DENY")

    if request["driver_contract_git_blob_sha"] != spec["contract_git_blob_sha"]:
        raise ParentDriverRegistryError("DRIVER_CONTRACT_BINDING_MISMATCH")
    if (
        request["driver_implementation_git_blob_sha"]
        != spec["implementation_git_blob_sha"]
    ):
        raise ParentDriverRegistryError("DRIVER_IMPLEMENTATION_BINDING_MISMATCH")

    root = Path(repo_root).resolve()
    _verify_spec(root, spec)

    if request["driver_id"] == ADMIN_DRIVER_ID:
        ctx = _authorize_admin_path(request["typed_args"], authority_context)
        expected_impl = (root / spec["implementation_path"]).resolve()
        actual_impl = Path(str(admin_driver.__file__ or "")).resolve()
        if actual_impl != expected_impl:
            raise ParentDriverRegistryError(
                "EXECUTED_DRIVER_MODULE_PATH_MISMATCH:"
                + str(actual_impl)
                + ":"
                + str(expected_impl)
            )
        result = admin_driver.execute(str(root), request["typed_args"])
    else:
        raise ParentDriverRegistryError("UNKNOWN_DRIVER_DENY")

    return {
        "schema": REGISTRY_SCHEMA,
        "driver_id": request["driver_id"],
        "request_sha256": request["request_sha256"],
        "result": result,
        "closed_registry": True,
        "generic_fallback": False,
        "mission_scoped_authority": True,
        "mission_id": ctx["mission_id"],
        "mission_sha256": ctx["mission_sha256"],
        "terminal_credit_delta": 0,
    }
