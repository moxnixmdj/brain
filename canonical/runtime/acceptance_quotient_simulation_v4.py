"""Subject-binding hardening wrapper for acceptance-quotient simulation V3.

V3 requires semantic, terminal, scope, realizability, and causal-policy receipts,
but those receipts are only identified by path/blob SHA plus Boolean claims. Without
an explicit digest of the certificate subject, a receipt proved for certificate A can
be replayed against structurally different certificate B.

V4 computes a canonical structural subject digest and requires every load-bearing
global receipt and every edge-local receipt to bind to that exact subject.
External receipt bytes must still be independently verified by the surrounding
proof system before any acceptance credit.
"""
from __future__ import annotations

import copy
import hashlib
import json
from collections.abc import Mapping, Sequence
from typing import Any

from canonical.runtime.acceptance_quotient_simulation_v3 import (
    verify_acceptance_quotient_certificate_v3 as verify_v3,
)

SCHEMA = "PROJECT_BRAIN_ACCEPTANCE_QUOTIENT_SIMULATION_V4"


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
    covers = sorted(_tokens(edge.get("covers_target_edge_ids"), "EDGE_COVERS"))
    return {
        "from": _token(edge.get("from"), "EDGE_FROM"),
        "to": _token(edge.get("to"), "EDGE_TO"),
        "covers_target_edge_ids": covers,
    }


def certificate_subject_projection(cert: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(cert, Mapping):
        raise CertificateError("CERT_NOT_OBJECT")

    relation = cert.get("relation")
    if not isinstance(relation, Sequence) or isinstance(relation, (str, bytes, bytearray)):
        raise CertificateError("RELATION_INVALID")
    pairs = []
    for i, raw in enumerate(relation):
        if not isinstance(raw, Sequence) or isinstance(raw, (str, bytes, bytearray)) or len(raw) != 2:
            raise CertificateError(f"RELATION_{i}_INVALID")
        pairs.append([_token(raw[0], f"RELATION_{i}_TARGET"), _token(raw[1], f"RELATION_{i}_BRAIN")])

    target_edges = cert.get("target_cut_edges")
    if not isinstance(target_edges, Sequence) or isinstance(target_edges, (str, bytes, bytearray)):
        raise CertificateError("TARGET_CUT_EDGES_INVALID")
    tproj = []
    for i, edge in enumerate(target_edges):
        if not isinstance(edge, Mapping):
            raise CertificateError(f"TARGET_EDGE_{i}_INVALID")
        tproj.append({
            "id": _token(edge.get("id"), f"TARGET_EDGE_{i}_ID"),
            "from": _token(edge.get("from"), f"TARGET_EDGE_{i}_FROM"),
            "to": _token(edge.get("to"), f"TARGET_EDGE_{i}_TO"),
        })

    brain_edges = cert.get("brain_macro_edges")
    if not isinstance(brain_edges, Sequence) or isinstance(brain_edges, (str, bytes, bytearray)):
        raise CertificateError("BRAIN_MACRO_EDGES_INVALID")

    return {
        "target_states": sorted(_tokens(cert.get("target_states"), "TARGET_STATES")),
        "brain_states": sorted(_tokens(cert.get("brain_states"), "BRAIN_STATES")),
        "initial_target_states": sorted(_tokens(cert.get("initial_target_states"), "INITIAL_TARGET_STATES")),
        "initial_brain_states": sorted(_tokens(cert.get("initial_brain_states"), "INITIAL_BRAIN_STATES")),
        "terminal_target_states": sorted(_tokens(cert.get("terminal_target_states"), "TERMINAL_TARGET_STATES")),
        "terminal_brain_states": sorted(_tokens(cert.get("terminal_brain_states"), "TERMINAL_BRAIN_STATES")),
        "relation": sorted(pairs),
        "target_cut_edges": sorted(tproj, key=lambda x: (x["id"], x["from"], x["to"])),
        "brain_macro_edges": sorted(
            [_edge_projection(x) for x in brain_edges],
            key=lambda x: (x["from"], x["to"], tuple(x["covers_target_edge_ids"])),
        ),
    }


def certificate_subject_sha256(cert: Mapping[str, Any]) -> str:
    return _sha256(certificate_subject_projection(cert))


def edge_subject_sha256(certificate_sha256: str, edge: Mapping[str, Any]) -> str:
    return _sha256({
        "certificate_subject_sha256": _token(certificate_sha256, "CERTIFICATE_SUBJECT_SHA256"),
        "edge": _edge_projection(edge),
    })


def _receipt(
    value: Any,
    label: str,
    required_true: Sequence[str],
    digest_field: str,
    expected_digest: str,
) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        raise CertificateError(label + "_INVALID")
    path = _token(value.get("path"), label + "_PATH")
    sha = _token(value.get("git_blob_sha"), label + "_SHA")
    for field in required_true:
        if value.get(field) is not True:
            raise CertificateError(label + "_" + field.upper() + "_NOT_TRUE")
    supplied = _token(value.get(digest_field), label + "_" + digest_field.upper())
    if supplied != expected_digest:
        raise CertificateError(
            label + "_" + digest_field.upper() + "_MISMATCH:" + expected_digest + ":" + supplied
        )
    return {
        "path": path,
        "git_blob_sha": sha,
        digest_field: supplied,
        **{f: True for f in required_true},
    }


def verify_acceptance_quotient_certificate_v4(cert: Mapping[str, Any]) -> dict[str, Any]:
    try:
        if not isinstance(cert, Mapping):
            raise CertificateError("CERT_NOT_OBJECT")

        subject_sha = certificate_subject_sha256(cert)

        subject_binding = _receipt(
            cert.get("certificate_subject_binding_receipt"),
            "CERTIFICATE_SUBJECT_BINDING_RECEIPT",
            ("scope_complete", "binds_relation_terminal_and_edges", "independent_or_objective"),
            "subject_sha256",
            subject_sha,
        )

        global_receipts = {}
        for key, label in (
            ("abstraction_receipt", "ABSTRACTION_RECEIPT"),
            ("relation_soundness_receipt", "RELATION_SOUNDNESS_RECEIPT"),
            ("terminal_acceptance_receipt", "TERMINAL_ACCEPTANCE_RECEIPT"),
            ("causal_strategy_receipt", "CAUSAL_STRATEGY_RECEIPT"),
        ):
            raw = cert.get(key)
            if not isinstance(raw, Mapping):
                raise CertificateError(label + "_INVALID")
            supplied = _token(raw.get("subject_sha256"), label + "_SUBJECT_SHA256")
            if supplied != subject_sha:
                raise CertificateError(
                    label + "_SUBJECT_SHA256_MISMATCH:" + subject_sha + ":" + supplied
                )
            global_receipts[key] = {"path": _token(raw.get("path"), label + "_PATH"),
                                    "git_blob_sha": _token(raw.get("git_blob_sha"), label + "_SHA"),
                                    "subject_sha256": supplied}

        raw_edges = cert.get("brain_macro_edges")
        if not isinstance(raw_edges, list):
            raise CertificateError("BRAIN_MACRO_EDGES_INVALID")
        edge_bindings = []
        for i, edge in enumerate(raw_edges):
            if not isinstance(edge, Mapping):
                raise CertificateError(f"BRAIN_EDGE_{i}_INVALID")
            edge_sha = edge_subject_sha256(subject_sha, edge)
            bound = {"edge_subject_sha256": edge_sha}
            for key, label in (
                ("scope_authority_receipt", "SCOPE_AUTHORITY_RECEIPT"),
                ("realizability_receipt", "REALIZABILITY_RECEIPT"),
                ("causal_policy_binding_receipt", "CAUSAL_POLICY_BINDING_RECEIPT"),
            ):
                raw = edge.get(key)
                if not isinstance(raw, Mapping):
                    raise CertificateError(f"BRAIN_EDGE_{i}_{label}_INVALID")
                supplied = _token(
                    raw.get("edge_subject_sha256"),
                    f"BRAIN_EDGE_{i}_{label}_EDGE_SUBJECT_SHA256",
                )
                if supplied != edge_sha:
                    raise CertificateError(
                        f"BRAIN_EDGE_{i}_{label}_EDGE_SUBJECT_SHA256_MISMATCH:"
                        + edge_sha + ":" + supplied
                    )
            edge_bindings.append(bound)

        v3 = verify_v3(copy.deepcopy(dict(cert)))
        if v3.get("status") != "PASS":
            return {
                "schema": SCHEMA,
                "status": "FAIL_CLOSED",
                "reason": "V3_CAUSAL_SEMANTIC_OR_GRAPH_CHECK_FAILED:" + str(v3.get("reason") or "UNKNOWN"),
                "acceptance_credit_delta": 0,
            }

        return {
            "schema": SCHEMA,
            "status": "PASS",
            "theorem": "SUBJECT_BOUND_SEMANTICALLY_SOUND_UNIFORM_CAUSAL_ACCEPTANCE_QUOTIENT_SIMULATION_V4",
            "certificate_subject_sha256": subject_sha,
            "certificate_subject_binding_receipt": subject_binding,
            "global_receipt_bindings": global_receipts,
            "edge_receipt_bindings": edge_bindings,
            "v3": v3,
            "receipt_reuse_across_structurally_different_certificates_forbidden": True,
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
