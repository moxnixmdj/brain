"""Three-axis persistent capability accounting for H100 research.

M_fit:
    Persistent state produced by empirical fitting/search/selection, plus any
    lossless recoding of such state. This is the closest representation-
    invariant replacement for "learned parameters/state".

M_dev:
    Persistent engineered code/config whose content changed in response to
    capability evidence, but which is not a direct fitted/search-selected
    artifact. This captures development adaptation without pretending it is a
    neural parameter.

M_cap:
    All persistent capability-bearing bytes required for runtime capability,
    regardless of provenance.

The axes are deliberately non-exclusive at the artifact level; the ledger
reports byte totals by declared semantic payload and refuses silent category
collapse.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

SCHEMA="PROJECT_BRAIN_H100_THREE_AXIS_PERSISTENT_ACCOUNTING_V1"

class ThreeAxisAccountingError(ValueError):
    pass

@dataclass(frozen=True)
class Artifact:
    artifact_id: str
    semantic_payload_bytes: int
    capability_bearing: bool
    machine_fit_or_selected: bool = False
    lossless_transform_of_fit_state: bool = False
    engineered_after_capability_evidence: bool = False
    runtime_task_state_only: bool = False
    raw_external_knowledge_only: bool = False

    def validate(self) -> None:
        if not isinstance(self.artifact_id,str) or not self.artifact_id.strip():
            raise ThreeAxisAccountingError("ARTIFACT_ID_INVALID")
        if not isinstance(self.semantic_payload_bytes,int) or isinstance(self.semantic_payload_bytes,bool) or self.semantic_payload_bytes < 0:
            raise ThreeAxisAccountingError("SEMANTIC_PAYLOAD_BYTES_INVALID")
        if self.runtime_task_state_only and self.capability_bearing:
            raise ThreeAxisAccountingError("TASK_STATE_CANNOT_BE_DECLARED_CAPABILITY_BEARING")
        if self.raw_external_knowledge_only and self.capability_bearing:
            raise ThreeAxisAccountingError("RAW_KNOWLEDGE_CANNOT_BE_DECLARED_CAPABILITY_BEARING")

    @property
    def fit_state(self) -> bool:
        return bool(self.machine_fit_or_selected or self.lossless_transform_of_fit_state)

    @property
    def dev_state(self) -> bool:
        return bool(self.engineered_after_capability_evidence and not self.fit_state)

def classify(artifact: Artifact) -> dict:
    artifact.validate()
    return {
        "artifact_id":artifact.artifact_id,
        "m_fit_bytes":artifact.semantic_payload_bytes if artifact.fit_state else 0,
        "m_dev_bytes":artifact.semantic_payload_bytes if artifact.dev_state else 0,
        "m_cap_bytes":artifact.semantic_payload_bytes if artifact.capability_bearing else 0,
        "excluded_runtime_task_state_bytes":artifact.semantic_payload_bytes if artifact.runtime_task_state_only else 0,
        "excluded_raw_external_knowledge_bytes":artifact.semantic_payload_bytes if artifact.raw_external_knowledge_only else 0,
    }

def ledger(artifacts: Iterable[Artifact]) -> dict:
    rows=[classify(a) for a in artifacts]
    ids=[r["artifact_id"] for r in rows]
    if len(ids)!=len(set(ids)):
        raise ThreeAxisAccountingError("DUPLICATE_ARTIFACT_ID")
    keys=[
        "m_fit_bytes","m_dev_bytes","m_cap_bytes",
        "excluded_runtime_task_state_bytes","excluded_raw_external_knowledge_bytes",
    ]
    totals={k:sum(int(r[k]) for r in rows) for k in keys}
    return {
        "schema":SCHEMA,
        "artifact_count":len(rows),
        "rows":rows,
        **totals,
        "claims":{
            "zero_fit_state":totals["m_fit_bytes"]==0,
            "zero_dev_state":totals["m_dev_bytes"]==0,
            "zero_total_capability_bytes":totals["m_cap_bytes"]==0,
        },
    }

def recoded_fit_artifact(artifact_id:str, payload_bytes:int)->Artifact:
    return Artifact(
        artifact_id=artifact_id,
        semantic_payload_bytes=payload_bytes,
        capability_bearing=True,
        lossless_transform_of_fit_state=True,
    )
