"""Frozen Brain OSWorld v2.1 subject composition."""
from __future__ import annotations

from typing import Any, Callable, Mapping

from canonical.runtime.osworld_v21_brain_agent_adapter_v1 import BrainOSWorldAgent
from canonical.runtime.osworld_v21_local_qwen_policy_v1 import plan_state
from canonical.runtime.osworld_v21_positioned_ocr_observer_v1 import observe_screenshot

SUBJECT_ID = "brain-osworld-v21-local-qwen35-9b-state-first-v1"
MODEL_SHA256 = "f41c0a0c0e43bf721fb2da29374cd1a97271bac0bab08a9dc42964525e82350c"
MODEL_BYTES = 5060174144
LLAMA_CPP_COMMIT = "bec4772f6a2527d371557b5d2032641e5ff7619c"
MODEL_ALIAS = "brain-qwen3.5-9b"


def build_subject(
    *,
    policy_provider: Callable[[Mapping[str, Any]], Mapping[str, Any]] = plan_state,
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
        "schema": "PROJECT_BRAIN_OSWORLD_V21_SUBJECT_MANIFEST_V1",
        "subject_id": SUBJECT_ID,
        "policy": "canonical/runtime/osworld_v21_local_qwen_policy_v1.py",
        "adapter": "canonical/runtime/osworld_v21_brain_agent_adapter_v1.py",
        "browser_ops": "canonical/runtime/osworld_v21_host_browser_ops_v1.py",
        "state_ops": "canonical/runtime/osworld_v21_state_ops_v1.py",
        "ocr": "canonical/runtime/osworld_v21_positioned_ocr_observer_v1.py",
        "runner_bridge": "canonical/runtime/osworld_v21_runner_bridge_v1.py",
        "model": {
            "alias": MODEL_ALIAS,
            "file": "Qwen3.5-9B-M-TS-Q4_K_M.gguf",
            "bytes": MODEL_BYTES,
            "sha256": MODEL_SHA256,
            "llama_cpp_commit": LLAMA_CPP_COMMIT,
            "transport": "loopback-only OpenAI-compatible llama.cpp endpoint",
        },
        "task_specific_policy_data": False,
        "reference_trajectory_execution_input": False,
        "external_generation_provider": False,
        "incremental_spend_usd": 0,
    }
