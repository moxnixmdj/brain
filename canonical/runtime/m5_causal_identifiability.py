"""Constructive non-identifiability witness for non-interventional root-cause claims.

The witness disproves any universal rule that claims a unique root cause can always
be recovered from an observational trajectory alone when no validated causal graph,
effect model, replay, or intervention is available.

Two admissible worlds expose the same observations:
  A) observed action X directly causes failure Y;
  B) latent U causes both observed X and later failure Y, so X is non-causal.
The observable trace is identical while the true root cause differs.

Therefore an evidence-safe system must preserve ambiguity or acquire discriminating
causal information rather than manufacture unique causal support from temporal order.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class CausalWorld:
    world_id: str
    observable_trace: tuple[tuple[str, str, str], ...]
    root_cause: str
    causal_edges: tuple[tuple[str, str], ...]
    validated_causal_graph_available: bool = False
    intervention_or_replay_available: bool = False


def construct_nonidentifiability_witness() -> tuple[CausalWorld, CausalWorld]:
    trace = (
        ("t0", "system", "healthy"),
        ("t1", "X", "changed"),
        ("t2", "Y", "failed"),
    )
    direct = CausalWorld(
        world_id="DIRECT_CAUSE_WORLD",
        observable_trace=trace,
        root_cause="X",
        causal_edges=(("X", "Y"),),
    )
    confounded = CausalWorld(
        world_id="LATENT_CONFOUNDER_WORLD",
        observable_trace=trace,
        root_cause="U",
        causal_edges=(("U", "X"), ("U", "Y")),
    )
    return direct, confounded


def verify_nonidentifiability_witness() -> dict:
    a, b = construct_nonidentifiability_witness()
    if a.observable_trace != b.observable_trace:
        return {"status": "FAIL", "reason": "OBSERVATIONS_DIFFER"}
    if a.root_cause == b.root_cause:
        return {"status": "FAIL", "reason": "ROOT_CAUSES_NOT_DISTINCT"}
    if a.validated_causal_graph_available or b.validated_causal_graph_available:
        return {"status": "FAIL", "reason": "CAUSAL_GRAPH_AVAILABLE"}
    if a.intervention_or_replay_available or b.intervention_or_replay_available:
        return {"status": "FAIL", "reason": "INTERVENTION_OR_REPLAY_AVAILABLE"}
    return {
        "status": "PASS",
        "same_observable_trace": True,
        "distinct_root_causes": True,
        "consequence": "UNIQUE_ROOT_CAUSE_NOT_IDENTIFIABLE_FROM_DECLARED_OBSERVATIONS_ALONE",
        "required_behavior": "PRESERVE_AMBIGUITY_OR_ACQUIRE_AUTHORIZED_DISCRIMINATING_CAUSAL_EVIDENCE",
        "terminal_authority": False,
    }
