"""Fail-closed compiler for a typed task-acceptance coverage/dominance sandwich.

The runtime composes already-admissible certificates only over one exact
content-addressed *partition* of task/acceptance semantics. It does not prove
the semantic premises itself.
"""
from __future__ import annotations

from collections.abc import Mapping, Sequence
import hashlib
import json
import re
from typing import Any

SCHEMA = "PROJECT_BRAIN_OPUS55_TYPED_COVERAGE_DOMINANCE_BRIDGE_RUNTIME_V1"
_SHA_RE = re.compile(r"^(?:[0-9a-f]{40}|[0-9a-f]{64})$")
_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")

class BridgeError(ValueError):
    pass

def _require_true(obj: Mapping[str, Any], key: str) -> None:
    if obj.get(key) is not True:
        raise BridgeError(f"{key}_REQUIRED_TRUE")

def _sha(value: Any, label: str) -> str:
    if not isinstance(value, str) or not _SHA_RE.fullmatch(value):
        raise BridgeError(f"{label}_INVALID_CONTENT_ADDRESS")
    return value

def _universe(value: Any) -> tuple[set[str], str]:
    if not isinstance(value, Mapping) or not value:
        raise BridgeError("UNIVERSE_ATOMS_NOT_NONEMPTY_OBJECT")
    normalized={}
    for atom, semantic_sha in value.items():
        if not isinstance(atom,str) or not atom:
            raise BridgeError("UNIVERSE_ATOM_ID_INVALID")
        normalized[atom]=_sha(semantic_sha,f"UNIVERSE_ATOM_{atom}_SEMANTIC_SHA")
    canonical=json.dumps(normalized,sort_keys=True,separators=(",",":"),ensure_ascii=True).encode()
    return set(normalized),hashlib.sha256(canonical).hexdigest()

def _ids(value: Any, label: str) -> set[str]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes, bytearray)):
        raise BridgeError(f"{label}_NOT_SEQUENCE")
    out=set()
    for item in value:
        if not isinstance(item,str) or not item:
            raise BridgeError(f"{label}_INVALID_ATOM")
        if item in out:
            raise BridgeError(f"{label}_DUPLICATE_ATOM:{item}")
        out.add(item)
    return out

def compile_typed_sandwich(manifest: Mapping[str, Any]) -> dict[str, Any]:
    try:
        if not isinstance(manifest, Mapping):
            raise BridgeError("MANIFEST_NOT_OBJECT")
        universe_id=manifest.get("universe_id")
        if not isinstance(universe_id,str) or not universe_id:
            raise BridgeError("UNIVERSE_ID_INVALID")
        universe,derived_digest=_universe(manifest.get("universe_atoms"))
        declared_digest=manifest.get("universe_sha256")
        if not isinstance(declared_digest,str) or not _SHA256_RE.fullmatch(declared_digest):
            raise BridgeError("UNIVERSE_SHA256_INVALID")
        if declared_digest != derived_digest:
            raise BridgeError("UNIVERSE_SHA256_CONTENT_MISMATCH")

        partition=manifest.get("partition_certificate")
        if not isinstance(partition,Mapping):
            raise BridgeError("PARTITION_CERTIFICATE_MISSING")
        _sha(partition.get("source_sha"),"PARTITION_SOURCE_SHA")
        _require_true(partition,"independent_or_objective")
        _require_true(partition,"pairwise_disjoint_proved")
        _require_true(partition,"atoms_define_declared_omega_proved")

        coverage=manifest.get("coverage_certificates")
        dominance=manifest.get("dominance_certificates")
        if not isinstance(coverage,Sequence) or isinstance(coverage,(str,bytes,bytearray)) or not coverage:
            raise BridgeError("NO_COVERAGE_CERTIFICATE")
        if not isinstance(dominance,Sequence) or isinstance(dominance,(str,bytes,bytearray)):
            raise BridgeError("DOMINANCE_CERTIFICATES_NOT_SEQUENCE")

        c_star=set(universe)
        cov_ids=[]
        for i,cert in enumerate(coverage):
            if not isinstance(cert,Mapping):
                raise BridgeError(f"COVERAGE_{i}_NOT_OBJECT")
            if cert.get("universe_id") != universe_id:
                raise BridgeError(f"COVERAGE_{i}_UNIVERSE_ID_MISMATCH")
            if cert.get("universe_sha256") != declared_digest:
                raise BridgeError(f"COVERAGE_{i}_UNIVERSE_SHA256_MISMATCH")
            _sha(cert.get("source_sha"),f"COVERAGE_{i}_SOURCE_SHA")
            _require_true(cert,"independent_or_objective")
            _require_true(cert,"exact_atom_union_embedding_proved")
            _require_true(cert,"u_subset_domain_proved")
            cells=_ids(cert.get("cells"),f"COVERAGE_{i}_CELLS")
            if not cells <= universe:
                raise BridgeError(f"COVERAGE_{i}_UNKNOWN_REGION")
            c_star &= cells
            cov_ids.append(str(cert.get("id",f"coverage_{i}")))

        b_star=set()
        dom_ids=[]
        for i,cert in enumerate(dominance):
            if not isinstance(cert,Mapping):
                raise BridgeError(f"DOMINANCE_{i}_NOT_OBJECT")
            if cert.get("universe_id") != universe_id:
                raise BridgeError(f"DOMINANCE_{i}_UNIVERSE_ID_MISMATCH")
            if cert.get("universe_sha256") != declared_digest:
                raise BridgeError(f"DOMINANCE_{i}_UNIVERSE_SHA256_MISMATCH")
            _sha(cert.get("source_sha"),f"DOMINANCE_{i}_SOURCE_SHA")
            _require_true(cert,"independent_or_objective")
            _require_true(cert,"exact_atom_union_embedding_proved")
            _require_true(cert,"scope_complete")
            _require_true(cert,"b_subset_q_proved")
            cells=_ids(cert.get("cells"),f"DOMINANCE_{i}_CELLS")
            if not cells <= universe:
                raise BridgeError(f"DOMINANCE_{i}_UNKNOWN_REGION")
            b_star |= cells
            dom_ids.append(str(cert.get("id",f"dominance_{i}")))

        residual=c_star-b_star
        return {
            "schema":SCHEMA,
            "status":"CLOSED" if not residual else "OPEN",
            "universe_id":universe_id,
            "universe_sha256":declared_digest,
            "coverage_certificate_ids":cov_ids,
            "dominance_certificate_ids":dom_ids,
            "c_star":sorted(c_star),
            "b_star":sorted(b_star),
            "residual":sorted(residual),
            "residual_count":len(residual),
            "behavioral_parity_certificate_sufficient":not residual,
            "capability_credit_delta":0,
        }
    except Exception as exc:
        return {
            "schema":SCHEMA,
            "status":"FAIL_CLOSED",
            "reason":type(exc).__name__+":"+str(exc),
            "behavioral_parity_certificate_sufficient":False,
            "capability_credit_delta":0,
        }
