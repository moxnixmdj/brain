"""Brain-owned vendored causal-falsification kernel.

Upstream core is trajectory-causal-attribution v1.0.0 (MIT).
Only the verified replay/ablation/attribution dependency closure is exposed.
"""
from .attribution import attribute, contrastive_attribution, point_of_commitment
from .recorder import AgentContext, AsyncAgentContext, record, arecord
from .replayer import ReplayPlan, ReplayContext, AsyncReplayContext, replay, areplay
from .ablation import AblationEngine, RolloutCache
from .types import (
    AttributionResult, ConfidenceInterval, InterventionKind,
    Step, StepAttribution, StepKind, Trajectory,
)
__all__=[
    "attribute","contrastive_attribution","point_of_commitment",
    "record","arecord","AgentContext","AsyncAgentContext",
    "replay","areplay","ReplayPlan","ReplayContext","AsyncReplayContext",
    "AblationEngine","RolloutCache","Trajectory","Step","StepKind",
    "StepAttribution","AttributionResult","ConfidenceInterval","InterventionKind",
]
