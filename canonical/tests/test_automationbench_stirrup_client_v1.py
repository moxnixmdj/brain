from __future__ import annotations

import unittest
from dataclasses import dataclass, field

from canonical.runtime.automationbench_stirrup_client_v1 import (
    CONTEXT_WINDOW_TOKENS,
    MODEL_SLUG,
    ProjectBrainAutomationBenchClient,
    extract_task_prompt,
    normalize_history,
)


@dataclass
class Msg:
    role: str
    content: object = ""
    kind: str = ""
    name: str = ""
    tool_call_id: str = ""
    metadata: dict = field(default_factory=dict)


class StirrupAdapterPureTests(unittest.TestCase):
    def test_protocol_properties_are_stable(self):
        c = ProjectBrainAutomationBenchClient()
        self.assertEqual(c.model_slug, MODEL_SLUG)
        self.assertGreater(CONTEXT_WINDOW_TOKENS, 0)
        self.assertEqual(c.context_window_tokens, CONTEXT_WINDOW_TOKENS)

    def test_prompt_uses_first_real_user_task_not_summary(self):
        messages = [
            Msg(role="user", kind="summary", content="summary"),
            Msg(role="user", kind="user", content="Mark the Salesforce deal as won."),
            Msg(role="user", kind="turn_warning", content="one turn left"),
        ]
        self.assertEqual(
            extract_task_prompt(messages),
            "Mark the Salesforce deal as won.",
        )

    def test_history_keeps_tool_results_and_owned_semantic_only(self):
        messages = [
            Msg(role="user", kind="user", content="task"),
            Msg(
                role="assistant",
                metadata={
                    "project_brain/automationbench_semantic":
                        "SALESFORCE_OPPORTUNITY_MARK_WON",
                    "irrelevant": "x",
                },
            ),
            Msg(
                role="tool",
                name="api_fetch",
                tool_call_id="call1",
                content='{"records":[]}',
            ),
        ]
        out = normalize_history(messages)
        self.assertEqual(out[0]["kind"], "assistant_state")
        self.assertEqual(
            out[0]["metadata"]["project_brain/automationbench_semantic"],
            "SALESFORCE_OPPORTUNITY_MARK_WON",
        )
        self.assertEqual(out[1]["kind"], "tool_result")
        self.assertEqual(out[1]["name"], "api_fetch")

    def test_summary_does_not_replace_original_task_prompt(self):
        messages = [
            Msg(role="user", kind="user", content="Original benchmark task"),
            Msg(role="user", kind="summary", content="compressed history"),
        ]
        self.assertEqual(extract_task_prompt(messages), "Original benchmark task")


if __name__ == "__main__":
    unittest.main(verbosity=2)
