"""Exact-subject binding wrapper for acceptance-quotient simulation V4.

V4 binds acceptance semantics, including stochastic distribution bridges, but
V1-V4 receipts can still be replayed against a structurally different
certificate because receipt identity is not cryptographically bound to the
certificate subject. V5 closes that cross-certificate replay channel.

This module verifies subject binding plus V4. It does not verify the external
receipt files themselves; exact receipt bytes remain a separate independent
promotion gate.
"""
from __future__ import annotations

import copy
import hashlib
import json
from collections.abc import Mapping, Sequence
from typing import Any

from canonical.runtime.acceptance_quotient_simulation_v4 import (
    verify_acceptance_quotient_certificate_v4 as verify_v4,
)

SCHEMA = "PROJECT_BRAIN_ACCEPTANCE_QUOTIENT_SIMULATION_V5"


class CertificateError(ValueError):
    pass


def _token(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise CertificateError(label + "_INVALID")
    return value.strip()


def _tokens(value: Any, label: str) -> list[str]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes, bytearray)):
        raise CertificateError(label + "_INVALID")
    out = [_token(x, label + "_ITEM") for x in value]
    if len(out) != len(set(out)):
        raise CertificateError(label + "_DUPLICATE")
    return out


def _sha256(value: Any) -> str:
    payload = json.dumps(
        value, sort_keys=True, ensure_ascii=False, separators=(",", ":")
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _edge_projection(edge: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "from": _token(edge.get("from"), "EDGE_FROM"),
        "to": _token(edge.get("to"), "EDGE_TO"),
        "covers_target_edge_ids": sorted(
            _tokens(edge.get("covers_target_edge_ids"), "EDGE_COVERS")
        ),
    }


def certificate_subject_projection(cert: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(cert, Mapping):
        raise CertificateError("CERT_NOT_OBJECT")

    relation = cert.get("relation")
    if not isinstance(relation, Sequence) or isinstance(relation, (str, bytes, bytearray)):
        raise CertificateError("RELATION_INVALID")
    pairs = []
    for index, raw in enumerate(relation):
        if (
            not isinstance(raw, Sequence)
            or isinstance(raw, (str, bytes, bytearray))
            or len(raw) != 2
        ):
            raise CertificateError(f"RELATION_{index}_INVALID")
        pairs.append(
            [
                _token(raw[0], f"RELATION_{index}_TARGET"),
                _token(raw[1], f"RELATION_{index}_BRAIN"),
            ]
        )

    target_edges = cert.get("target_cut_edges")
    if not isinstance(target_edges, Sequence) or isinstance(
        target_edges, (str, bytes, bytearray)
    ):
        raise CertificateError("TARGET_CUT_EDGES_INVALID")
    target_projection = []
    for index, edge in enumerate(target_edges):
        if not isinstance(edge, Mapping):
            raise CertificateError(f"TARGET_EDGE_{index}_INVALID")
        target_projection.append(
            {
                "id": _token(edge.get("id"), f"TARGET_EDGE_{index}_ID"),
                "from": _token(edge.get("from"), f"TARGET_EDGE_{index}_FROM"),
                "to": _token(edge.get("to"), f"TARGET_EDGE_{index}_TO"),
            }
        )

    brain_edges = cert.get("brain_macro_edges")
    if not isinstance(brain_edges, Sequence) or isinstance(
        brain_edges, (str, bytes, bytearray)
    ):
        raise CertificateError("BRAIN_MACRO_EDGES_INVALID")

    return {
        "acceptance_semantics_class": _token(
            cert.get("acceptance_semantics_class"), "ACCEPTANCE_SEMANTICS_CLASS"
        ),
        "target_states": sorted(_tokens(cert.get("target_states"), "TARGET_STATES")),
        "brain_states": sorted(_tokens(cert.get("brain_states"), "BRAIN_STATES")),
        "initial_target_states": sorted(
            _tokens(cert.get("initial_target_states"), "INITIAL_TARGET_STATES")
        ),
        "initial_brain_states": sorted(
            _tokens(cert.get("initial_brain_states"), "INITIAL_BRAIN_STATES")
        ),
        "terminal_target_states": sorted(
            _tokens(cert.get("terminal_target_states"), "TERMINAL_TARGET_STATES")
        ),
        "terminal_brain_states": sorted(
            _tokens(cert.get("terminal_brain_states"), "TERMINAL_BRAIN_STATES")
        ),
        "relation": sorted(pairs),
        "target_cut_edges": sorted(
            target_projection, key=lambda x: (x["id"], x["from"], x["to"])
        ),
        "brain_macro_edges": sorted(
            [_edge_projection(x) for x in brain_edges],
            key=lambda x: (x["from"], x["to"], tuple(x["covers_target_edge_ids"])),
        ),
    }


def certificate_subject_sha256(cert: Mapping[str, Any]) -> str:
    return _sha256(certificate_subject_projection(cert))


def edge_subject_sha256(certificate_sha256: str, edge: Mapping[str, Any]) -> str:
    return _sha256(
        {
            "certificate_subject_sha256": _token(
                certificate_sha256, "CERTIFICATE_SUBJECT_SHA256"
            ),
            "edge": _edge_projection(edge),
        }
    )


def _require_subject(value: Any, label: str, field: str, expected: str) -> None:
    if not isinstance(value, Mapping):
        raise CertificateError(label + "_INVALID")
    _token(value.get("path"), label + "_PATH")
    _token(value.get("git_blob_sha"), label + "_SHA")
    supplied = _token(value.get(field), label + "_" + field.upper())
    if supplied != expected:
        raise CertificateError(
            label + "_" + field.upper() + "_MISMATCH:" + expected + ":" + supplied
        )


def verify_acceptance_quotient_certificate_v5(cert: Mapping[str, Any]) -> dict[str, Any]:
    try:
        if not isinstance(cert, Mapping):
            raise CertificateError("CERT_NOT_OBJECT")

        subject_sha = certificate_subject_sha256(cert)

        binding = cert.get("certificate_subject_binding_receipt")
        if not isinstance(binding, Mapping):
            raise CertificateError("CERTIFICATE_SUBJECT_BINDING_RECEIPT_INVALID")
        _token(binding.get("path"), "CERTIFICATE_SUBJECT_BINDING_RECEIPT_PATH")
        _token(binding.get("git_blob_sha"), "CERTIFICATE_SUBJECT_BINDING_RECEIPT_SHA")
        for field in (
            "scope_complete",
            "binds_relation_terminal_edges_and_acceptance_class",
            "independent_or_objective",
        ):
            if binding.get(field) is not True:
                raise CertificateError(
                    "CERTIFICATE_SUBJECT_BINDING_RECEIPT_" + field.upper() + "_NOT_TRUE"
                )
        supplied = _token(
            binding.get("subject_sha256"),
            "CERTIFICATE_SUBJECT_BINDING_RECEIPT_SUBJECT_SHA256",
        )
        if supplied != subject_sha:
            raise CertificateError(
                "CERTIFICATE_SUBJECT_BINDING_RECEIPT_SUBJECT_SHA256_MISMATCH:"
                + subject_sha + ":" + supplied
            )

        global_keys = [
            ("abstraction_receipt", "ABSTRACTION_RECEIPT"),
            ("relation_soundness_receipt", "RELATION_SOUNDNESS_RECEIPT"),
            ("terminal_acceptance_receipt", "TERMINAL_ACCEPTANCE_RECEIPT"),
            ("causal_strategy_receipt", "CAUSAL_STRATEGY_RECEIPT"),
        ]
        semantics = cert.get("acceptance_semantics_class")
        if semantics == "STOCHASTIC_MATCHED_NONINFERIORITY":
            global_keys.append(
                ("policy_distribution_bridge_receipt", "POLICY_DISTRIBUTION_BRIDGE_RECEIPT")
            )
        else:
            global_keys.append(
                ("distribution_free_dominance_receipt", "DISTRIBUTION_FREE_DOMINANCE_RECEIPT")
            )

        for key, label in global_keys:
            _require_subject(cert.get(key), label, "subject_sha256", subject_sha)

        raw_edges = cert.get("brain_macro_edges")
        if not isinstance(raw_edges, list):
            raise CertificateError("BRAIN_MACRO_EDGES_INVALID")
        edge_digests = []
        for index, edge in enumerate(raw_edges):
            if not isinstance(edge, Mapping):
                raise CertificateError(f"BRAIN_EDGE_{index}_INVALID")
            edge_sha = edge_subject_sha256(subject_sha, edge)
            for key, label in (
                ("scope_authority_receipt", "SCOPE_AUTHORITY_RECEIPT"),
                ("realizability_receipt", "REALIZABILITY_RECEIPT"),
                ("causal_policy_binding_receipt", "CAUSAL_POLICY_BINDING_RECEIPT"),
            ):
                _require_subject(
                    edge.get(key),
                    f"BRAIN_EDGE_{index}_{label}",
                    "edge_subject_sha256",
                    edge_sha,
                )
            edge_digests.append(edge_sha)

        v4 = verify_v4(copy.deepcopy(dict(cert)))
        if v4.get("status") != "PASS":
            return {
                "schema": SCHEMA,
                "status": "FAIL_CLOSED",
                "reason": "V4_ACCEPTANCE_CAUSAL_SEMANTIC_GRAPH_CHECK_FAILED:"
                + str(v4.get("reason") or "UNKNOWN"),
                "acceptance_credit_delta": 0,
            }

        return {
            "schema": SCHEMA,
            "status": "PASS",
            "theorem": "EXACT_SUBJECT_BOUND_ACCEPTANCE_CLASS_AND_CAUSAL_POLICY_QUOTIENT_SIMULATION_V5",
            "certificate_subject_sha256": subject_sha,
            "edge_subject_sha256": edge_digests,
            "v4": v4,
            "cross_certificate_receipt_replay_forbidden": True,
            "independent_receipt_byte_verification_still_required": True,
            "acceptance_credit_delta": 0,
        }
    except Exception as exc:
        return {
            "schema": SCHEMA,
            "status": "FAIL_CLOSED",
            "reason": type(exc).__name__ + ":" + str(exc),
            "acceptance_credit_delta": 0,
        }
