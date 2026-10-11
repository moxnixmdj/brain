"""Model-independent OSWorld capability subject V5.

V5 adds only capability-grounded semantic conjunction decomposition above the
verified V4 cross-tool dataflow stack.
"""
from __future__ import annotations
from canonical.runtime.osworld_v21_brain_agent_adapter_v3 import BrainOSWorldAgentV3
from canonical.runtime.osworld_v21_positioned_ocr_observer_v1 import observe_screenshot
from canonical.runtime.osworld_v21_workflow_policy_v3 import decide
SUBJECT_ID="brain-osworld-v21-model-independent-semantic-workflow-v5"
def build_subject()->BrainOSWorldAgentV3:
    return BrainOSWorldAgentV3(decide,policy_id=SUBJECT_ID,ocr_provider=observe_screenshot)
