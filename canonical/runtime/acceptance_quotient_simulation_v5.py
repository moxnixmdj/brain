"""Content-bound single-policy hardening for acceptance quotient simulation V4.

V4 binds the acceptance semantics class, but its inherited V3 causal-policy
premise is still represented as one global Boolean receipt plus per-edge Boolean
receipts. Nothing in V3/V4 structurally proves those receipts name the same
policy implementation, epoch, claimed quotient domain, or exact macroedge.

V5 makes those equalities machine-checkable, then delegates all earlier
acceptance/causal/graph semantics to V4. Receipt truth and referenced policy
bytes still require independent verification before any acceptance credit.
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


def _hex(value: Any, n: int, label: str) -> str:
    token = _token(value, label).lower()
    if len(token) != n or any(c not in "0123456789abcdef" for c in token):
        raise CertificateError(label + "_INVALID")
    return token


def _canonical_sha256(value: Any) -> str:
    raw = json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


_DOMAIN_FIELDS = (
    "target_states",
    "brain_states",
    "initial_target_states",
    "initial_brain_states",
    "terminal_target_states",
    "terminal_brain_states",
    "relation",
    "target_cut_edges",
)


def acceptance_domain_sha256(cert: Mapping[str, Any]) -> str:
    if not isinstance(cert, Mapping):
        raise CertificateError("CERT_NOT_OBJECT")
    domain = {field: copy.deepcopy(cert.get(field)) for field in _DOMAIN_FIELDS}
    return _canonical_sha256(domain)


def brain_macroedge_sha256(edge: Mapping[str, Any]) -> str:
    if not isinstance(edge, Mapping):
        raise CertificateError("BRAIN_EDGE_INVALID")
    payload = copy.deepcopy(dict(edge))
    payload.pop("causal_policy_binding_receipt", None)
    return _canonical_sha256(payload)


def _binding(value: Any, label: str, required_true: Sequence[str]) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        raise CertificateError(label + "_INVALID")
    out = {
        "path": _token(value.get("path"), label + "_PATH"),
        "git_blob_sha": _hex(value.get("git_blob_sha"), 40, label + "_SHA"),
        "policy_id": _token(value.get("policy_id"), label + "_POLICY_ID"),
        "policy_git_blob_sha": _hex(
            value.get("policy_git_blob_sha"), 40, label + "_POLICY_GIT_BLOB_SHA"
        ),
        "policy_epoch": _token(value.get("policy_epoch"), label + "_POLICY_EPOCH"),
        "claimed_domain_sha256": _hex(
            value.get("claimed_domain_sha256"), 64, label + "_CLAIMED_DOMAIN_SHA256"
        ),
    }
    for field in required_true:
        if value.get(field) is not True:
            raise CertificateError(label + "_" + field.upper() + "_NOT_TRUE")
        out[field] = True
    return out


def verify_acceptance_quotient_certificate_v5(cert: Mapping[str, Any]) -> dict[str, Any]:
    try:
        if not isinstance(cert, Mapping):
            raise CertificateError("CERT_NOT_OBJECT")

        expected_domain = acceptance_domain_sha256(cert)
        strategy = _binding(
            cert.get("causal_strategy_receipt"),
            "CAUSAL_STRATEGY_RECEIPT",
            (
                "single_owned_policy",
                "complete_on_claimed_domain",
                "history_adapted",
                "no_future_or_target_oracle",
                "existential_matches_induced_by_policy",
                "independent_or_objective",
            ),
        )
        if strategy["claimed_domain_sha256"] != expected_domain:
            raise CertificateError("CAUSAL_STRATEGY_RECEIPT_DOMAIN_BINDING_MISMATCH")

        policy_key = (
            strategy["policy_id"],
            strategy["policy_git_blob_sha"],
            strategy["policy_epoch"],
            strategy["claimed_domain_sha256"],
        )

        raw_edges = cert.get("brain_macro_edges")
        if not isinstance(raw_edges, list):
            raise CertificateError("BRAIN_MACRO_EDGES_INVALID")

        edge_bindings = []
        for index, raw in enumerate(raw_edges):
            if not isinstance(raw, Mapping):
                raise CertificateError(f"BRAIN_EDGE_{index}_INVALID")
            binding = _binding(
                raw.get("causal_policy_binding_receipt"),
                f"BRAIN_EDGE_{index}_CAUSAL_POLICY_BINDING_RECEIPT",
                (
                    "induced_by_bound_policy",
                    "choice_uses_current_or_past_information_only",
                    "no_target_edge_or_future_branch_oracle",
                    "scope_complete",
                    "independent_or_objective",
                ),
            )
            edge_key = (
                binding["policy_id"],
                binding["policy_git_blob_sha"],
                binding["policy_epoch"],
                binding["claimed_domain_sha256"],
            )
            if edge_key != policy_key:
                raise CertificateError(f"BRAIN_EDGE_{index}_SPLIT_POLICY_BINDING")

            expected_edge = brain_macroedge_sha256(raw)
            supplied_edge = _hex(
                raw.get("causal_policy_binding_receipt", {}).get("brain_edge_sha256"),
                64,
                f"BRAIN_EDGE_{index}_CAUSAL_POLICY_BINDING_RECEIPT_BRAIN_EDGE_SHA256",
            )
            if supplied_edge != expected_edge:
                raise CertificateError(f"BRAIN_EDGE_{index}_CONTENT_BINDING_MISMATCH")
            binding["brain_edge_sha256"] = supplied_edge
            edge_bindings.append(binding)

        v4 = verify_v4(cert)
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
            "theorem": "CONTENT_BOUND_SINGLE_OWNED_CAUSAL_POLICY_ACCEPTANCE_QUOTIENT_SIMULATION_V5",
            "v4": v4,
            "policy_binding": {
                "policy_id": strategy["policy_id"],
                "policy_git_blob_sha": strategy["policy_git_blob_sha"],
                "policy_epoch": strategy["policy_epoch"],
                "claimed_domain_sha256": strategy["claimed_domain_sha256"],
            },
            "brain_macroedge_bindings": edge_bindings,
            "split_policy_witness_structurally_forbidden": True,
            "domain_rebinding_structurally_forbidden": True,
            "macroedge_receipt_reuse_after_edge_mutation_structurally_forbidden": True,
            "independent_receipt_and_policy_byte_verification_still_required": True,
            "acceptance_credit_delta": 0,
        }
    except Exception as exc:
        return {
            "schema": SCHEMA,
            "status": "FAIL_CLOSED",
            "reason": type(exc).__name__ + ":" + str(exc),
            "acceptance_credit_delta": 0,
        }
