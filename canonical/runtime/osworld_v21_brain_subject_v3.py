"""Credited model-independent OSWorld 2.1 subject V3.

V3 composes the explicit ordered-subgoal workflow overlay, product-native web-app observation overlay, and strict WebAppOps
controller. No external model/provider is reachable from the credited subject.
"""
from __future__ import annotations

from canonical.runtime.osworld_v21_brain_agent_adapter_v3 import BrainOSWorldAgentV3
from canonical.runtime.osworld_v21_positioned_ocr_observer_v1 import observe_screenshot
from canonical.runtime.osworld_v21_workflow_policy_v1 import decide

SUBJECT_ID = "brain-osworld-v21-model-independent-state-app-web-v3"


def build_subject() -> BrainOSWorldAgentV3:
    return BrainOSWorldAgentV3(
        decide,
        policy_id=SUBJECT_ID,
        ocr_provider=observe_screenshot,
    )
