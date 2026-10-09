"""D-finality execution epoch primitive V1.

This module is intentionally small. It does not grant ownership by itself.
It verifies a content-addressed D-final certificate against current load-bearing
bytes, installs an immutable authority epoch for one execution, and prevents
nested capability, knowledge-channel, effect-channel, or material authority
from widening during that epoch.

A caller that does not enter a verified epoch has zero D-final ownership
authority. Experimental execution may exist elsewhere, but cannot use this
primitive to claim D-final ownership.
"""
from __future__ import annotations

import contextlib
import contextvars
import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterator, Mapping, Sequence

SCHEMA = "PROJECT_BRAIN_D_FINALITY_EXECUTION_EPOCH_V1"
CERT_SCHEMA = "PROJECT_BRAIN_D_FINALITY_CERTIFICATE_V1"
POLICY_SCHEMA = "PROJECT_BRAIN_D_FINALITY_POLICY_V1"


class DFinalityError(ValueError):
    pass


def _canon(value: Any) -> bytes:
    try:
        return json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        ).encode("utf-8")
    except (TypeError, ValueError) as exc:
        raise DFinalityError("NON_CANONICAL_JSON") from exc


def sha256_json(value: Any) -> str:
    return hashlib.sha256(_canon(value)).hexdigest()


def git_blob_sha_bytes(raw: bytes) -> str:
    return hashlib.sha1(b"blob " + str(len(raw)).encode("ascii") + b"\0" + raw).hexdigest()


def git_blob_sha_file(path: Path) -> str:
    return git_blob_sha_bytes(path.read_bytes())


def _hex(value: Any, length: int, label: str) -> str:
    text = str(value or "").lower()
    if len(text) != length or any(c not in "0123456789abcdef" for c in text):
        raise DFinalityError(label + "_INVALID")
    return text


def _tokens(value: Any, label: str) -> tuple[str, ...]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes, bytearray)):
        raise DFinalityError(label + "_NOT_SEQUENCE")
    out: list[str] = []
    for raw in value:
        token = str(raw or "").strip()
        if not token or "\x00" in token:
            raise DFinalityError(label + "_ITEM_INVALID")
        out.append(token)
    if len(out) != len(set(out)):
        raise DFinalityError(label + "_DUPLICATE")
    return tuple(sorted(out))


def _safe_file(root: Path, raw: Any) -> Path:
    rel = str(raw or "").strip()
    p = Path(rel)
    if not rel or p.is_absolute() or ".." in p.parts:
        raise DFinalityError("MATERIAL_PATH_INVALID")
    full = (root / p).resolve()
    try:
        full.relative_to(root.resolve())
    except ValueError as exc:
        raise DFinalityError("MATERIAL_PATH_ESCAPES_ROOT") from exc
    if not full.is_file():
        raise DFinalityError("MATERIAL_FILE_MISSING:" + rel)
    return full


def normalize_materials(materials: Any) -> tuple[dict[str, str], ...]:
    if not isinstance(materials, Sequence) or isinstance(materials, (str, bytes, bytearray)):
        raise DFinalityError("MATERIALS_NOT_SEQUENCE")
    if not materials:
        raise DFinalityError("MATERIALS_EMPTY")
    rows: list[dict[str, str]] = []
    seen: set[str] = set()
    for raw in materials:
        if not isinstance(raw, Mapping):
            raise DFinalityError("MATERIAL_ROW_NOT_OBJECT")
        path = str(raw.get("path") or "").strip()
        blob = _hex(raw.get("git_blob_sha"), 40, "MATERIAL_GIT_BLOB_SHA")
        if not path or path in seen:
            raise DFinalityError("MATERIAL_PATH_INVALID_OR_DUPLICATE")
        seen.add(path)
        rows.append({"path": path, "git_blob_sha": blob})
    return tuple(sorted(rows, key=lambda row: row["path"]))


def material_closure_root(materials: Any) -> str:
    return sha256_json(list(normalize_materials(materials)))


def policy_sha256(policy: Mapping[str, Any]) -> str:
    if not isinstance(policy, Mapping):
        raise DFinalityError("POLICY_NOT_OBJECT")
    body = dict(policy)
    body.pop("policy_sha256", None)
    # Revocation is a mutable deny set, not part of the semantic policy root.
    # Otherwise revoking one certificate would invalidate every certificate.
    body.pop("revoked_certificate_sha256", None)
    return sha256_json(body)


def certificate_sha256(certificate: Mapping[str, Any]) -> str:
    if not isinstance(certificate, Mapping):
        raise DFinalityError("CERTIFICATE_NOT_OBJECT")
    body = dict(certificate)
    body.pop("certificate_sha256", None)
    return sha256_json(body)


@dataclass(frozen=True)
class DExecutionEpoch:
    epoch_sha256: str
    certificate_sha256: str
    policy_sha256: str
    root_capability_id: str
    current_capability_id: str
    capability_contract_sha256: str
    substrate_contract_sha256: str
    substrate_contract_canonical_json: str
    material_closure_root: str
    registry_snapshot_root: str
    state_snapshot_root: str
    allowed_capability_ids: frozenset[str]
    allowed_knowledge_channels: frozenset[str]
    allowed_effect_channels: frozenset[str]
    material_bindings: tuple[tuple[str, str], ...]


_ACTIVE_EPOCH: contextvars.ContextVar[DExecutionEpoch | None] = contextvars.ContextVar(
    "project_brain_d_finality_execution_epoch", default=None
)


def verify_certificate(
    certificate: Mapping[str, Any],
    *,
    policy: Mapping[str, Any],
    repo_root: str | Path,
) -> DExecutionEpoch:
    if not isinstance(certificate, Mapping):
        raise DFinalityError("CERTIFICATE_NOT_OBJECT")
    if certificate.get("schema") != CERT_SCHEMA:
        raise DFinalityError("CERTIFICATE_SCHEMA_INVALID")
    if certificate.get("status") != "VERIFIED_D_FINAL":
        raise DFinalityError("CERTIFICATE_NOT_VERIFIED_D_FINAL")
    if policy.get("schema") != POLICY_SCHEMA:
        raise DFinalityError("POLICY_SCHEMA_INVALID")
    if policy.get("status") != "ACTIVE_FAIL_CLOSED":
        raise DFinalityError("POLICY_NOT_ACTIVE")

    actual_policy_sha = policy_sha256(policy)
    declared_policy_sha = policy.get("policy_sha256")
    if declared_policy_sha is not None and _hex(
        declared_policy_sha, 64, "POLICY_SHA256"
    ) != actual_policy_sha:
        raise DFinalityError("POLICY_SELF_DIGEST_MISMATCH")
    if _hex(certificate.get("policy_sha256"), 64, "CERTIFICATE_POLICY_SHA256") != actual_policy_sha:
        raise DFinalityError("CERTIFICATE_POLICY_DRIFT")

    actual_cert_sha = certificate_sha256(certificate)
    if _hex(certificate.get("certificate_sha256"), 64, "CERTIFICATE_SHA256") != actual_cert_sha:
        raise DFinalityError("CERTIFICATE_SELF_DIGEST_MISMATCH")

    revoked = set(_tokens(policy.get("revoked_certificate_sha256", []), "REVOKED_CERTIFICATES"))
    if actual_cert_sha in revoked:
        raise DFinalityError("CERTIFICATE_REVOKED")

    capability_id = str(certificate.get("capability_id") or "").strip()
    if not capability_id:
        raise DFinalityError("CAPABILITY_ID_REQUIRED")

    allowed_caps = _tokens(certificate.get("allowed_capability_ids"), "ALLOWED_CAPABILITY_IDS")
    if capability_id not in allowed_caps:
        raise DFinalityError("ROOT_CAPABILITY_NOT_IN_ALLOWED_SET")
    allowed_knowledge = _tokens(
        certificate.get("allowed_knowledge_channels", []), "ALLOWED_KNOWLEDGE_CHANNELS"
    )
    allowed_effects = _tokens(
        certificate.get("allowed_effect_channels", []), "ALLOWED_EFFECT_CHANNELS"
    )

    contract_sha = _hex(
        certificate.get("capability_contract_sha256"), 64, "CAPABILITY_CONTRACT_SHA256"
    )
    substrate_contract = certificate.get("substrate_contract")
    if not isinstance(substrate_contract, Mapping) or not substrate_contract:
        raise DFinalityError("SUBSTRATE_CONTRACT_REQUIRED")
    substrate_sha = sha256_json(dict(substrate_contract))
    if _hex(
        certificate.get("substrate_contract_sha256"),
        64,
        "SUBSTRATE_CONTRACT_SHA256",
    ) != substrate_sha:
        raise DFinalityError("SUBSTRATE_CONTRACT_DIGEST_MISMATCH")
    substrate_json = _canon(dict(substrate_contract)).decode("utf-8")
    registry_root = _hex(
        certificate.get("registry_snapshot_root"), 64, "REGISTRY_SNAPSHOT_ROOT"
    )
    state_root = _hex(certificate.get("state_snapshot_root"), 64, "STATE_SNAPSHOT_ROOT")

    if certificate.get("donor_authority_zero") is not True:
        raise DFinalityError("DONOR_AUTHORITY_NOT_ZERO")
    if certificate.get("fresh_replay_pass") is not True:
        raise DFinalityError("FRESH_REPLAY_NOT_PASS")
    if certificate.get("independent_replay_pass") is not True:
        raise DFinalityError("INDEPENDENT_REPLAY_NOT_PASS")
    if certificate.get("knowledge_capability_nonsmuggling_pass") is not True:
        raise DFinalityError("NONSMUGGLING_NOT_PASS")
    if int(certificate.get("undeclared_dependency_count", -1)) != 0:
        raise DFinalityError("UNDECLARED_DEPENDENCY_COUNT_NOT_ZERO")

    materials = normalize_materials(certificate.get("materials"))
    expected_root = material_closure_root(materials)
    if _hex(certificate.get("material_closure_root"), 64, "MATERIAL_CLOSURE_ROOT") != expected_root:
        raise DFinalityError("MATERIAL_CLOSURE_ROOT_MISMATCH")

    root = Path(repo_root).resolve()
    for row in materials:
        full = _safe_file(root, row["path"])
        if git_blob_sha_file(full) != row["git_blob_sha"]:
            raise DFinalityError("MATERIAL_BLOB_DRIFT:" + row["path"])

    material_bindings = tuple((row["path"], row["git_blob_sha"]) for row in materials)
    epoch_core = {
        "certificate_sha256": actual_cert_sha,
        "policy_sha256": actual_policy_sha,
        "root_capability_id": capability_id,
        "capability_contract_sha256": contract_sha,
        "substrate_contract_sha256": substrate_sha,
        "material_closure_root": expected_root,
        "registry_snapshot_root": registry_root,
        "state_snapshot_root": state_root,
        "allowed_capability_ids": list(allowed_caps),
        "allowed_knowledge_channels": list(allowed_knowledge),
        "allowed_effect_channels": list(allowed_effects),
        "material_bindings": list(material_bindings),
    }
    return DExecutionEpoch(
        epoch_sha256=sha256_json(epoch_core),
        certificate_sha256=actual_cert_sha,
        policy_sha256=actual_policy_sha,
        root_capability_id=capability_id,
        current_capability_id=capability_id,
        capability_contract_sha256=contract_sha,
        substrate_contract_sha256=substrate_sha,
        substrate_contract_canonical_json=substrate_json,
        material_closure_root=expected_root,
        registry_snapshot_root=registry_root,
        state_snapshot_root=state_root,
        allowed_capability_ids=frozenset(allowed_caps),
        allowed_knowledge_channels=frozenset(allowed_knowledge),
        allowed_effect_channels=frozenset(allowed_effects),
        material_bindings=material_bindings,
    )


def has_active_epoch() -> bool:
    return _ACTIVE_EPOCH.get() is not None


def current_epoch() -> DExecutionEpoch:
    epoch = _ACTIVE_EPOCH.get()
    if epoch is None:
        raise DFinalityError("NO_ACTIVE_D_FINALITY_EPOCH")
    return epoch


def require_capability(capability_id: str) -> DExecutionEpoch:
    epoch = current_epoch()
    cid = str(capability_id or "").strip()
    if cid not in epoch.allowed_capability_ids:
        raise DFinalityError("CAPABILITY_OUTSIDE_EPOCH:" + cid)
    return epoch


def require_knowledge_channel(channel: str) -> DExecutionEpoch:
    epoch = current_epoch()
    value = str(channel or "").strip()
    if value not in epoch.allowed_knowledge_channels:
        raise DFinalityError("KNOWLEDGE_CHANNEL_OUTSIDE_EPOCH:" + value)
    return epoch


def require_effect_channel(channel: str) -> DExecutionEpoch:
    epoch = current_epoch()
    value = str(channel or "").strip()
    if value not in epoch.allowed_effect_channels:
        raise DFinalityError("EFFECT_CHANNEL_OUTSIDE_EPOCH:" + value)
    return epoch


def require_material(path: str, *, repo_root: str | Path) -> DExecutionEpoch:
    epoch = current_epoch()
    rel = str(path or "").strip()
    bindings = dict(epoch.material_bindings)
    expected = bindings.get(rel)
    if expected is None:
        raise DFinalityError("MATERIAL_OUTSIDE_EPOCH:" + rel)
    full = _safe_file(Path(repo_root).resolve(), rel)
    if git_blob_sha_file(full) != expected:
        raise DFinalityError("MATERIAL_CHANGED_DURING_EPOCH:" + rel)
    return epoch


def require_material_file_if_active(
    path: str | Path,
    *,
    repo_root: str | Path | None = None,
) -> DExecutionEpoch | None:
    """Point-of-use material guard for loaders.

    Outside a D epoch this is a no-op so experimental runtime behavior is
    preserved. Inside one, the exact repository-relative file must already be
    part of the certified material closure and its bytes must still match.
    """
    if not has_active_epoch():
        return None
    root = (
        Path(repo_root).resolve()
        if repo_root is not None
        else Path(__file__).resolve().parents[2]
    )
    full = Path(path).resolve()
    try:
        rel = full.relative_to(root).as_posix()
    except ValueError as exc:
        raise DFinalityError("MATERIAL_PATH_OUTSIDE_REPO") from exc
    return require_material(rel, repo_root=root)


@contextlib.contextmanager
def activate(
    certificate: Mapping[str, Any],
    *,
    policy: Mapping[str, Any],
    repo_root: str | Path,
) -> Iterator[DExecutionEpoch]:
    if _ACTIVE_EPOCH.get() is not None:
        raise DFinalityError("NESTED_ROOT_EPOCH_FORBIDDEN")
    epoch = verify_certificate(certificate, policy=policy, repo_root=repo_root)
    token = _ACTIVE_EPOCH.set(epoch)
    try:
        yield epoch
    finally:
        _ACTIVE_EPOCH.reset(token)


@contextlib.contextmanager
def child_scope(
    capability_id: str,
    *,
    allowed_capability_ids: Sequence[str] | None = None,
    allowed_knowledge_channels: Sequence[str] | None = None,
    allowed_effect_channels: Sequence[str] | None = None,
) -> Iterator[DExecutionEpoch]:
    parent = require_capability(capability_id)
    child_caps = frozenset(
        _tokens(
            sorted(parent.allowed_capability_ids) if allowed_capability_ids is None else allowed_capability_ids,
            "CHILD_ALLOWED_CAPABILITY_IDS",
        )
    )
    child_knowledge = frozenset(
        _tokens(
            sorted(parent.allowed_knowledge_channels) if allowed_knowledge_channels is None else allowed_knowledge_channels,
            "CHILD_ALLOWED_KNOWLEDGE_CHANNELS",
        )
    )
    child_effects = frozenset(
        _tokens(
            sorted(parent.allowed_effect_channels) if allowed_effect_channels is None else allowed_effect_channels,
            "CHILD_ALLOWED_EFFECT_CHANNELS",
        )
    )
    if not child_caps.issubset(parent.allowed_capability_ids):
        raise DFinalityError("CHILD_CAPABILITY_AUTHORITY_WIDENING")
    if not child_knowledge.issubset(parent.allowed_knowledge_channels):
        raise DFinalityError("CHILD_KNOWLEDGE_AUTHORITY_WIDENING")
    if not child_effects.issubset(parent.allowed_effect_channels):
        raise DFinalityError("CHILD_EFFECT_AUTHORITY_WIDENING")
    if capability_id not in child_caps:
        raise DFinalityError("CHILD_CURRENT_CAPABILITY_NOT_ALLOWED")

    child = DExecutionEpoch(
        epoch_sha256=parent.epoch_sha256,
        certificate_sha256=parent.certificate_sha256,
        policy_sha256=parent.policy_sha256,
        root_capability_id=parent.root_capability_id,
        current_capability_id=capability_id,
        capability_contract_sha256=parent.capability_contract_sha256,
        substrate_contract_sha256=parent.substrate_contract_sha256,
        substrate_contract_canonical_json=parent.substrate_contract_canonical_json,
        material_closure_root=parent.material_closure_root,
        registry_snapshot_root=parent.registry_snapshot_root,
        state_snapshot_root=parent.state_snapshot_root,
        allowed_capability_ids=child_caps,
        allowed_knowledge_channels=child_knowledge,
        allowed_effect_channels=child_effects,
        material_bindings=parent.material_bindings,
    )
    token = _ACTIVE_EPOCH.set(child)
    try:
        yield child
    finally:
        _ACTIVE_EPOCH.reset(token)
