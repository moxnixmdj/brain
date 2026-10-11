"""Model-independent app-capable OSWorld 2.1 successor."""
from canonical.runtime.osworld_v21_app_policy_overlay_v2 import decide
from canonical.runtime.osworld_v21_brain_agent_adapter_v2 import BrainOSWorldAgentV2
from canonical.runtime.osworld_v21_positioned_ocr_observer_v1 import observe_screenshot

SUBJECT_ID="brain-osworld-v21-model-independent-state-app-v2"

def build_subject(**kwargs):
    return BrainOSWorldAgentV2(
        kwargs.pop("policy_provider", decide),
        policy_id=SUBJECT_ID,
        screen_width=1920,
        screen_height=1080,
        ocr_provider=kwargs.pop("ocr_provider", observe_screenshot),
        **kwargs,
    )
