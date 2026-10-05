"""Representation-invariant accounting primitives for H100 research.

The point is not to infer provenance from arbitrary source code. That is
undecidable in general. The point is to make the accounting contract explicit:

* representation/file type does not decide whether state is learned;
* causal data dependence does;
* a pre-exposure prior/codebook lets us quantify persisted selection
  information for finite choices;
* lossless re-encoding of a learned payload as source code cannot erase its
  learned classification.
"""
from __future__ import annotations

import math
import re
from dataclasses import dataclass

SCHEMA = "PROJECT_BRAIN_H100_REPRESENTATION_INVARIANT_ACCOUNTING_V1"
_HEX_RE = re.compile(r'^PAYLOAD_HEX = "([0-9a-f]*)"\n$', re.ASCII)

class AccountingError(ValueError):
    pass

@dataclass(frozen=True)
class Provenance:
    artifact_id: str
    persisted_after_exposure: bool
    value_selected_using_capability_evidence: bool
    lossless_transform_of_learned_artifact: bool = False
    source_artifact_id: str | None = None

    @property
    def learned(self) -> bool:
        return bool(
            self.persisted_after_exposure
            and (
                self.value_selected_using_capability_evidence
                or self.lossless_transform_of_learned_artifact
            )
        )

def encode_payload_as_deterministic_source(payload: bytes) -> bytes:
    """Losslessly place arbitrary bytes into syntactically boring source text."""
    if not isinstance(payload, (bytes, bytearray)):
        raise AccountingError("PAYLOAD_NOT_BYTES")
    return f'PAYLOAD_HEX = "{bytes(payload).hex()}"\n'.encode("ascii")

def recover_payload_from_deterministic_source(source: bytes) -> bytes:
    if not isinstance(source, (bytes, bytearray)):
        raise AccountingError("SOURCE_NOT_BYTES")
    try:
        text = bytes(source).decode("ascii")
    except UnicodeDecodeError as exc:
        raise AccountingError("SOURCE_NOT_ASCII") from exc
    m = _HEX_RE.fullmatch(text)
    if m is None:
        raise AccountingError("SOURCE_FORMAT_INVALID")
    return bytes.fromhex(m.group(1))

def legacy_extension_based_learned_bytes(*, artifact_kind: str, stored_bytes: int) -> int:
    """Model the legacy categorical exemption being falsified."""
    if stored_bytes < 0:
        raise AccountingError("STORED_BYTES_NEGATIVE")
    exempt = {
        "DETERMINISTIC_PROGRAM",
        "SOURCE_CODE",
        "LOOKUP_TABLE_DECLARED_PROGRAM",
        "CONFIG_DECLARED_PROGRAM",
    }
    return 0 if artifact_kind in exempt else int(stored_bytes)

def provenance_aware_learned_classification(provenance: Provenance) -> dict:
    return {
        "schema": SCHEMA,
        "artifact_id": provenance.artifact_id,
        "learned": provenance.learned,
        "reason": (
            "POST_EXPOSURE_DATA_SELECTED"
            if provenance.persisted_after_exposure and provenance.value_selected_using_capability_evidence
            else "LOSSLESS_TRANSFORM_OF_LEARNED_ARTIFACT"
            if provenance.persisted_after_exposure and provenance.lossless_transform_of_learned_artifact
            else "NO_POST_EXPOSURE_LEARNED_DEPENDENCE_ESTABLISHED"
        ),
    }

def selection_information_bits(prior_probability: float) -> float:
    """Surprisal of the selected persistent choice under a frozen pre-data prior."""
    try:
        p = float(prior_probability)
    except Exception as exc:
        raise AccountingError("PRIOR_PROBABILITY_INVALID") from exc
    if not math.isfinite(p) or p <= 0.0 or p > 1.0:
        raise AccountingError("PRIOR_PROBABILITY_OUT_OF_RANGE")
    return -math.log2(p)

def uniform_selection_information_bits(candidate_count: int) -> float:
    if not isinstance(candidate_count, int) or isinstance(candidate_count, bool) or candidate_count < 1:
        raise AccountingError("CANDIDATE_COUNT_INVALID")
    return math.log2(candidate_count)

def finite_selector_storage_bytes(candidate_count: int) -> int:
    """Minimum whole-byte storage sufficient for a uniform N-way selector."""
    bits = uniform_selection_information_bits(candidate_count)
    return int(math.ceil(bits / 8.0))

def representation_invariant_certificate(
    *,
    semantic_payload_bytes: int,
    prior_probability: float,
    provenance: Provenance,
) -> dict:
    if not isinstance(semantic_payload_bytes, int) or isinstance(semantic_payload_bytes, bool) or semantic_payload_bytes < 0:
        raise AccountingError("SEMANTIC_PAYLOAD_BYTES_INVALID")
    learned = provenance.learned
    info = selection_information_bits(prior_probability) if learned else 0.0
    return {
        "schema": SCHEMA,
        "status": "LEARNED_PROVENANCE_ESTABLISHED" if learned else "NO_LEARNED_PROVENANCE_ESTABLISHED",
        "artifact_id": provenance.artifact_id,
        "learned": learned,
        "semantic_payload_bytes": semantic_payload_bytes if learned else 0,
        "selection_information_bits": info,
        "representation_rule": "FILE_TYPE_AND_EXECUTABILITY_DO_NOT_ERASE_CAUSAL_DATA_DEPENDENCE",
        "hard_nonclaims": [
            "THIS_DOES_NOT_COMPUTE_KOLMOGOROV_COMPLEXITY",
            "THIS_DOES_NOT_INFER_HIDDEN_PROVENANCE_FROM_ARBITRARY_BYTES",
            "THIS_DOES_NOT_EQUATE_SOURCE_FILE_SIZE_WITH_LEARNED_INFORMATION",
            "THIS_DOES_NOT_PROVE_FRONTIER_CAPABILITY_REQUIRES_NONZERO_LEARNED_STATE",
        ],
    }
