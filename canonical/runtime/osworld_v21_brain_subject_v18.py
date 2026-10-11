from __future__ import annotations
from canonical.runtime.osworld_v21_brain_agent_adapter_v7 import BrainOSWorldAgentV7
from canonical.runtime.osworld_v21_positioned_ocr_observer_v1 import observe_screenshot
from canonical.runtime.osworld_v21_workflow_policy_v12 import decide

SUBJECT_ID="brain-osworld-v21-model-independent-terminal-authority-v18"

def build_subject()->BrainOSWorldAgentV7:
    return BrainOSWorldAgentV7(decide,policy_id=SUBJECT_ID,ocr_provider=observe_screenshot)
