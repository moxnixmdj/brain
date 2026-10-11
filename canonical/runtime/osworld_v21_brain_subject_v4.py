"""Credited model-independent OSWorld capability subject V4.

V4 differs from V3 only by using workflow policy V2 with provenance-bound
cross-tool receipt dataflow. No external generation model/provider is reachable.
"""
from __future__ import annotations

from canonical.runtime.osworld_v21_brain_agent_adapter_v3 import BrainOSWorldAgentV3
from canonical.runtime.osworld_v21_positioned_ocr_observer_v1 import observe_screenshot
from canonical.runtime.osworld_v21_workflow_policy_v2 import decide

SUBJECT_ID = "brain-osworld-v21-model-independent-state-app-web-dataflow-v4"

def build_subject() -> BrainOSWorldAgentV3:
    return BrainOSWorldAgentV3(decide, policy_id=SUBJECT_ID, ocr_provider=observe_screenshot)
