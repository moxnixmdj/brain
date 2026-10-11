"""Model-independent OSWorld capability subject V6.

V6 keeps V5 provenance dataflow and capability-grounded semantic workflows,
with expanded high-confidence Writer/Calc/Impress native transformations.
"""
from __future__ import annotations
from canonical.runtime.osworld_v21_brain_agent_adapter_v3 import BrainOSWorldAgentV3
from canonical.runtime.osworld_v21_positioned_ocr_observer_v1 import observe_screenshot
from canonical.runtime.osworld_v21_workflow_policy_v3 import decide
SUBJECT_ID="brain-osworld-v21-model-independent-office-workflow-v6"
def build_subject()->BrainOSWorldAgentV3:
    return BrainOSWorldAgentV3(decide,policy_id=SUBJECT_ID,ocr_provider=observe_screenshot)
