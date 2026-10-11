from __future__ import annotations
from canonical.runtime.osworld_v21_brain_agent_adapter_v8 import BrainOSWorldAgentV8
from canonical.runtime.osworld_v21_positioned_ocr_observer_v1 import observe_screenshot
from canonical.runtime.osworld_v21_workflow_policy_v13 import decide

SUBJECT_ID="brain-osworld-v21-model-independent-gui-goal-verification-v19"

def build_subject()->BrainOSWorldAgentV8:
    return BrainOSWorldAgentV8(decide,policy_id=SUBJECT_ID,ocr_provider=observe_screenshot)
