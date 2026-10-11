"""Model-independent computer-use capability subject V8.

V8 extends V7 only with bounded relational/aggregate dataflow over structured
receipts. Execution surfaces and app/browser/file capability layers are unchanged.
"""
from __future__ import annotations
from canonical.runtime.osworld_v21_brain_agent_adapter_v3 import BrainOSWorldAgentV3
from canonical.runtime.osworld_v21_positioned_ocr_observer_v1 import observe_screenshot
from canonical.runtime.osworld_v21_workflow_policy_v5 import decide
SUBJECT_ID="brain-osworld-v21-model-independent-relational-workflow-v8"
def build_subject()->BrainOSWorldAgentV3:
    return BrainOSWorldAgentV3(decide,policy_id=SUBJECT_ID,ocr_provider=observe_screenshot)
