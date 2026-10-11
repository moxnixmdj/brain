from __future__ import annotations

import inspect

from canonical.runtime.osworld_v21_brain_agent_adapter_v3 import BrainOSWorldAgentV3
from canonical.runtime.osworld_v21_brain_subject_v3 import SUBJECT_ID, build_subject


def test_v3_subject_is_model_independent_state_app_web_subject():
    subject = build_subject()
    assert isinstance(subject, BrainOSWorldAgentV3)
    assert SUBJECT_ID == "brain-osworld-v21-model-independent-state-app-web-v3"
    assert subject.policy_id == SUBJECT_ID
    assert subject.policy_provider.__module__ == "canonical.runtime.osworld_v21_web_app_policy_overlay_v1"


def test_v3_operative_policy_chain_has_no_external_generation_provider_imports():
    modules = [
        "canonical.runtime.osworld_v21_brain_subject_v3",
        "canonical.runtime.osworld_v21_brain_agent_adapter_v3",
        "canonical.runtime.osworld_v21_brain_agent_adapter_v2",
        "canonical.runtime.osworld_v21_brain_agent_adapter_v1",
        "canonical.runtime.osworld_v21_web_app_policy_overlay_v1",
        "canonical.runtime.osworld_v21_app_policy_overlay_v2",
        "canonical.runtime.osworld_v21_generic_policy_v1",
    ]
    forbidden = (
        "import openai",
        "from openai",
        "import anthropic",
        "from anthropic",
        "google.generativeai",
        "import qwen",
        "from qwen",
        "qwen35_planner",
        "local_qwen_policy",
    )
    for name in modules:
        mod = __import__(name, fromlist=["*"])
        source = inspect.getsource(mod).casefold()
        for token in forbidden:
            assert token not in source, (name, token)


def test_v3_subject_source_has_no_task_id_or_reference_trajectory_lookup():
    import canonical.runtime.osworld_v21_brain_subject_v3 as subject_mod
    import canonical.runtime.osworld_v21_web_app_policy_overlay_v1 as policy_mod

    source = (inspect.getsource(subject_mod) + "\n" + inspect.getsource(policy_mod)).casefold()
    forbidden = (
        "task_001",
        "task_id_lookup",
        "reference_trajectory",
        "expected_answer",
        "evaluation_examples",
        "benchmark_releases",
    )
    for token in forbidden:
        assert token not in source
