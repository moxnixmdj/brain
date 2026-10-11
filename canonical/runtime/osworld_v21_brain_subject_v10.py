"""Model-independent OSWorld computer-use subject V10.

Adds bounded code-workspace edit/compile/test/status operations to the verified
V9 capability stack. No general-purpose model runtime cognition is used.
"""
from __future__ import annotations

from canonical.runtime.osworld_v21_brain_agent_adapter_v4 import BrainOSWorldAgentV4
from canonical.runtime.osworld_v21_positioned_ocr_observer_v1 import observe_screenshot
from canonical.runtime.osworld_v21_workflow_policy_v6 import decide

SUBJECT_ID="brain-osworld-v21-model-independent-code-workflow-v10"

def build_subject()->BrainOSWorldAgentV4:
    return BrainOSWorldAgentV4(decide,policy_id=SUBJECT_ID,ocr_provider=observe_screenshot)
