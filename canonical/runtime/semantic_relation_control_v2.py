"""Decision-relative semantic relation control V2.

V2 preserves semantic_relation_control_v1 and automatically uses the Brain-owned
V4 edge registry when every row in a supplied entailment DAG independently
recomputes successfully. An explicit verifier still has precedence.
"""
from __future__ import annotations

from copy import deepcopy
from typing import Any, Callable, Mapping, Sequence

from canonical.runtime import semantic_relation_control_v1 as v1
from canonical.runtime import brain_owned_semantic_relation_edge_registry_v4 as registry

SCHEMA="PROJECT_BRAIN_DECISION_RELATIVE_SEMANTIC_RELATION_CONTROL_V2"


def _rows(problem:Mapping[str,Any])->list[Mapping[str,Any]]:
    evidence=problem.get("entailment_dag_evidence")
    if not isinstance(evidence,Mapping):
        return []
    entail=evidence.get("entailment_receipts")
    counter=evidence.get("counterexample_receipts")
    if (
        not isinstance(entail,Sequence)
        or isinstance(entail,(str,bytes))
        or not isinstance(counter,Sequence)
        or isinstance(counter,(str,bytes))
    ):
        return []
    rows=list(entail)+list(counter)
    if not all(isinstance(row,Mapping) for row in rows):
        return []
    return rows


def resolve(
    problem:Mapping[str,Any],
    *,
    concept_identity_verifier:Callable[[Mapping[str,Any]],Mapping[str,Any]|None]|None=None,
    terminal_signature_verifier:Callable[[Mapping[str,Any]],Mapping[str,Any]|None]|None=None,
    relation_edge_verifier:Callable[[Mapping[str,Any]],Mapping[str,Any]|None]|None=None,
)->dict[str,Any]:
    effective=relation_edge_verifier
    internal=False
    if effective is None and isinstance(problem,Mapping):
        rows=_rows(problem)
        if rows and all(registry.can_prove(row) for row in rows):
            effective=registry.verify
            internal=True

    out=v1.resolve(
        problem,
        concept_identity_verifier=concept_identity_verifier,
        terminal_signature_verifier=terminal_signature_verifier,
        relation_edge_verifier=effective,
    )
    result=deepcopy(dict(out))
    result["semantic_relation_controller_schema"]=SCHEMA
    result["brain_owned_relation_registry_v4_used"]=internal
    result["relation_edge_verifier_source"]=(
        "BRAIN_OWNED_REGISTRY_V4"
        if internal
        else ("CALLER_SUPPLIED" if callable(relation_edge_verifier) else "NONE")
    )
    result["relation_registry_v4_supported_proof_classes"]=registry.supported_proof_classes()
    return result
