"""Model-independent OSWorld capability subject V7.

V7 preserves V6 semantic workflows and Office transforms while adding structured
native app observations plus advanced spreadsheet/presentation operations.
"""
from __future__ import annotations
from canonical.runtime.osworld_v21_brain_agent_adapter_v3 import BrainOSWorldAgentV3
from canonical.runtime.osworld_v21_positioned_ocr_observer_v1 import observe_screenshot
from canonical.runtime.osworld_v21_workflow_policy_v3 import decide
SUBJECT_ID="brain-osworld-v21-model-independent-structured-app-workflow-v7"
def build_subject()->BrainOSWorldAgentV3:
    return BrainOSWorldAgentV3(decide,policy_id=SUBJECT_ID,ocr_provider=observe_screenshot)
