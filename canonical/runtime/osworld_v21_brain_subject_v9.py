"""Model-independent computer-use capability subject V9.

V9 extends V8 with typed spreadsheet formula planning and fixed write/read-back
verification. No external generation model is used in the credited runtime.
"""
from __future__ import annotations
from canonical.runtime.osworld_v21_brain_agent_adapter_v3 import BrainOSWorldAgentV3
from canonical.runtime.osworld_v21_positioned_ocr_observer_v1 import observe_screenshot
from canonical.runtime.osworld_v21_workflow_policy_v5 import decide
SUBJECT_ID="brain-osworld-v21-model-independent-verified-formula-workflow-v9"
def build_subject()->BrainOSWorldAgentV3:
    return BrainOSWorldAgentV3(decide,policy_id=SUBJECT_ID,ocr_provider=observe_screenshot)
