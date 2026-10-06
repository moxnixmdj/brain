from __future__ import annotations

import hashlib
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


def dispatch(repo_root: str | Path, raw_request: Mapping[str, Any]) -> dict[str, Any]:
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
        "terminal_credit_delta": 0,
    }
