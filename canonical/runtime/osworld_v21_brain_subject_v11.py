"""Model-independent OSWorld computer-use subject V11.

Adds pinned host media transformations with guest pull/upload/readback to the
verified V10 capability stack. No general-purpose model runtime cognition.
"""
from __future__ import annotations

from canonical.runtime.osworld_v21_brain_agent_adapter_v5 import BrainOSWorldAgentV5
from canonical.runtime.osworld_v21_positioned_ocr_observer_v1 import observe_screenshot
from canonical.runtime.osworld_v21_workflow_policy_v7 import decide

SUBJECT_ID="brain-osworld-v21-model-independent-media-workflow-v11"

def build_subject()->BrainOSWorldAgentV5:
    return BrainOSWorldAgentV5(decide,policy_id=SUBJECT_ID,ocr_provider=observe_screenshot)
