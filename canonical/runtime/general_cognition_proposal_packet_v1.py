"""Provider-agnostic proposal packet boundary for general cognition substrates.

A general cognition substrate may suggest a candidate, but the packet:
- is bound to the exact task-contract SHA-256;
- is bound to the exact capability and action-contract SHA-256;
- is content-addressed;
- explicitly carries proposal_authority=False;
- contains no verification or success boolean with authority.

This module does not call any provider. It creates and validates the transport
boundary through which any replaceable proposer may feed the Universal Verified
Adaptive Solver.
"""
from __future__ import annotations

import base64
from hashlib import sha256
import json
from typing import Any, Mapping

SCHEMA = "PROJECT_BRAIN_GENERAL_COGNITION_PROPOSAL_PACKET_V1"
REQUEST_SCHEMA = "PROJECT_BRAIN_GENERAL_COGNITION_PROPOSAL_REQUEST_V1"
ROLE = "GENERAL_COGNITION_SUBSTRATE"


class ProposalPacketError(ValueError):
    pass


def _default(value: Any) -> Any:
    if isinstance(value, bytes):
        return {
            "__brain_type__": "bytes",
            "base64": base64.b64encode(value).decode("ascii"),
        }
    raise TypeError(type(value).__name__)


def _canon(value: Any) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        default=_default,
    ).encode("utf-8")


def digest(value: Any) -> str:
    return sha256(_canon(value)).hexdigest()


def make_request(
    *,
    task_contract_sha256: str,
    capability_id: str,
    action_contract_sha256: str,
    verifier_id: str,
    proposal_context: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    for value, label in (
        (task_contract_sha256, "TASK_CONTRACT_SHA256"),
        (action_contract_sha256, "ACTION_CONTRACT_SHA256"),
    ):
        if not isinstance(value, str) or len(value) != 64:
            raise ProposalPacketError(label + "_INVALID")
    if not isinstance(capability_id, str) or not capability_id:
        raise ProposalPacketError("CAPABILITY_ID_INVALID")
    if not isinstance(verifier_id, str) or not verifier_id:
        raise ProposalPacketError("VERIFIER_ID_INVALID")
    context = dict(proposal_context or {})
    body = {
        "schema": REQUEST_SCHEMA,
        "task_contract_sha256": task_contract_sha256,
        "capability_id": capability_id,
        "action_contract_sha256": action_contract_sha256,
        "verifier_id": verifier_id,
        "proposal_context": context,
        "proposal_authority": False,
    }
    return {**body, "request_sha256": digest(body)}


def make_packet(
    request: Mapping[str, Any],
    *,
    source_id: str,
    proposal: Mapping[str, Any],
) -> dict[str, Any]:
    if not isinstance(request, Mapping) or request.get("schema") != REQUEST_SCHEMA:
        raise ProposalPacketError("REQUEST_INVALID")
    expected = dict(request)
    request_sha = expected.pop("request_sha256", None)
    if not isinstance(request_sha, str) or request_sha != digest(expected):
        raise ProposalPacketError("REQUEST_DIGEST_INVALID")
    if request.get("proposal_authority") is not False:
        raise ProposalPacketError("REQUEST_AUTHORITY_INVALID")
    if not isinstance(source_id, str) or not source_id.strip():
        raise ProposalPacketError("SOURCE_ID_INVALID")
    if not isinstance(proposal, Mapping):
        raise ProposalPacketError("PROPOSAL_INVALID")

    core = {
        "schema": SCHEMA,
        "request_sha256": request_sha,
        "task_contract_sha256": request["task_contract_sha256"],
        "capability_id": request["capability_id"],
        "action_contract_sha256": request["action_contract_sha256"],
        "verifier_id": request["verifier_id"],
        "source_role": ROLE,
        "source_id": source_id.strip(),
        "proposal": dict(proposal),
        "proposal_authority": False,
    }
    return {**core, "packet_sha256": digest(core)}


def unwrap(
    packet: Mapping[str, Any],
    *,
    request: Mapping[str, Any],
) -> dict[str, Any]:
    if not isinstance(packet, Mapping) or packet.get("schema") != SCHEMA:
        raise ProposalPacketError("PACKET_SCHEMA_INVALID")
    if not isinstance(request, Mapping) or request.get("schema") != REQUEST_SCHEMA:
        raise ProposalPacketError("REQUEST_SCHEMA_INVALID")
    request_core = dict(request)
    request_sha = request_core.pop("request_sha256", None)
    if request_sha != digest(request_core):
        raise ProposalPacketError("REQUEST_DIGEST_INVALID")

    packet_core = dict(packet)
    packet_sha = packet_core.pop("packet_sha256", None)
    if packet_sha != digest(packet_core):
        raise ProposalPacketError("PACKET_DIGEST_INVALID")
    if packet.get("request_sha256") != request_sha:
        raise ProposalPacketError("PACKET_REQUEST_MISMATCH")

    for key in (
        "task_contract_sha256",
        "capability_id",
        "action_contract_sha256",
        "verifier_id",
    ):
        if packet.get(key) != request.get(key):
            raise ProposalPacketError("PACKET_BINDING_MISMATCH:" + key)
    if packet.get("source_role") != ROLE:
        raise ProposalPacketError("SOURCE_ROLE_INVALID")
    if packet.get("proposal_authority") is not False:
        raise ProposalPacketError("PROPOSAL_AUTHORITY_MUST_BE_FALSE")
    source_id = packet.get("source_id")
    if not isinstance(source_id, str) or not source_id.strip():
        raise ProposalPacketError("SOURCE_ID_INVALID")
    proposal = packet.get("proposal")
    if not isinstance(proposal, Mapping):
        raise ProposalPacketError("PROPOSAL_INVALID")
    return {
        "proposal": dict(proposal),
        "source_id": source_id.strip(),
        "packet_sha256": packet_sha,
        "proposal_authority": False,
    }
