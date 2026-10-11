"""Model-independent OSWorld computer-use subject V12.

Adds explicit path-invariant preservation across long workflows to the verified
V11 capability stack. No general-purpose model runtime cognition.
"""
from __future__ import annotations

from canonical.runtime.osworld_v21_brain_agent_adapter_v6 import BrainOSWorldAgentV6
from canonical.runtime.osworld_v21_positioned_ocr_observer_v1 import observe_screenshot
from canonical.runtime.osworld_v21_workflow_policy_v7 import decide

SUBJECT_ID="brain-osworld-v21-model-independent-invariant-workflow-v12"

def build_subject()->BrainOSWorldAgentV6:
    return BrainOSWorldAgentV6(decide,policy_id=SUBJECT_ID,ocr_provider=observe_screenshot)
