"""Frozen Brain OSWorld v2.1 subject composition."""
from __future__ import annotations

from typing import Any, Callable, Mapping

from canonical.runtime.osworld_v21_brain_agent_adapter_v1 import BrainOSWorldAgent
from canonical.runtime.osworld_v21_generic_policy_v1 import decide
from canonical.runtime.osworld_v21_positioned_ocr_observer_v1 import observe_screenshot

SUBJECT_ID = "brain-osworld-v21-model-independent-state-first-v1"


def build_subject(
    *,
    policy_provider: Callable[[Mapping[str, Any]], Mapping[str, Any]] = decide,
    ocr_provider: Callable[[bytes], Mapping[str, Any]] | None = observe_screenshot,
    browser_controller: Any | None = None,
) -> BrainOSWorldAgent:
    """Build the frozen state-first subject without starting external services."""
    return BrainOSWorldAgent(
        policy_provider,
        policy_id=SUBJECT_ID,
        screen_width=1920,
        screen_height=1080,
        browser_controller=browser_controller,
        ocr_provider=ocr_provider,
    )


def subject_manifest() -> dict[str, Any]:
    return {
        "schema": "PROJECT_BRAIN_OSWORLD_V21_SUBJECT_MANIFEST_V2",
        "subject_id": SUBJECT_ID,
        "policy": "canonical/runtime/osworld_v21_generic_policy_v1.py",
        "adapter": "canonical/runtime/osworld_v21_brain_agent_adapter_v1.py",
        "browser_ops": "canonical/runtime/osworld_v21_host_browser_ops_v1.py",
        "state_ops": "canonical/runtime/osworld_v21_state_ops_v1.py",
        "computer_surface": "canonical/runtime/osworld_computer_surface_v1.py",
        "text_grounding": "canonical/runtime/text_ui_grounding_v1.py",
        "ocr": "canonical/runtime/osworld_v21_positioned_ocr_observer_v1.py",
        "runner_bridge": "canonical/runtime/osworld_v21_runner_bridge_v1.py",
        "producer_cognition_general_purpose_model_dependency": False,
        "task_specific_policy_data": False,
        "reference_trajectory_execution_input": False,
        "external_generation_provider": False,
        "quarantined_diagnostic_routes": [
            "canonical/runtime/osworld_v21_local_qwen_policy_v1.py",
            "canonical/runtime/osworld_v21_qwen35_planner_v1.py"
        ],
        "incremental_spend_usd": 0,
    }
