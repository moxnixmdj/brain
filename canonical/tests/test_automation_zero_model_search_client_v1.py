from __future__ import annotations

import unittest
from dataclasses import dataclass

from canonical.runtime.automation_zero_model_search_client_v1 import (
    MODEL_SLUG,
    ZeroModelAutomationSearchError,
    next_search_action,
)


@dataclass
class Message:
    role: str
    content: str | None = None
    name: str | None = None
    success: bool = False


class SearchClientCoreTests(unittest.TestCase):
    def test_first_turn_emits_one_api_search(self):
        action = next_search_action(
            [Message("user", "Find the customer record and update the phone number.")],
            {"api_search": object()},
        )
        self.assertEqual(action["kind"], "tool_call")
        self.assertEqual(action["name"], "api_search")
        self.assertEqual(action["arguments"]["top_k"], 5)
        self.assertIn("find", action["arguments"]["query"])
        self.assertEqual(action["model_dependency_count"], 0)

    def test_successful_search_advances_to_next_clause(self):
        messages = [
            Message("user", "Find the customer record and update the phone number."),
            Message("assistant"),
            Message("tool", content="[]", name="api_search", success=True),
        ]
        action = next_search_action(messages, {"api_search": object()})
        self.assertEqual(action["kind"], "tool_call")
        self.assertIn("update", action["arguments"]["query"])

    def test_all_discovery_clauses_complete_stops_without_mutation(self):
        messages = [
            Message("user", "Find the customer record."),
            Message("tool", content="[]", name="api_search", success=True),
        ]
        action = next_search_action(messages, {"api_search": object()})
        self.assertEqual(action["kind"], "text")
        self.assertEqual(
            action["text"],
            "DISCOVERY_COMPLETE__ENDPOINT_BINDING_NOT_IMPLEMENTED_V1",
        )

    def test_failed_search_fails_closed(self):
        messages = [
            Message("user", "Find the customer record."),
            Message("tool", content="error", name="api_search", success=False),
        ]
        with self.assertRaisesRegex(
            ZeroModelAutomationSearchError, "API_SEARCH_RESULT_FAILED"
        ):
            next_search_action(messages, {"api_search": object()})

    def test_api_search_must_exist(self):
        with self.assertRaisesRegex(
            ZeroModelAutomationSearchError, "API_SEARCH_TOOL_REQUIRED"
        ):
            next_search_action([Message("user", "Find the record.")], {})

    def test_no_action_prompt_fails_closed(self):
        with self.assertRaisesRegex(
            ZeroModelAutomationSearchError, "TASK_IR_UNRESOLVED"
        ):
            next_search_action(
                [Message("user", "The account is healthy.")],
                {"api_search": object()},
            )

    def test_non_string_user_content_fails_closed(self):
        with self.assertRaisesRegex(
            ZeroModelAutomationSearchError, "STRING_USER_PROMPT_REQUIRED"
        ):
            next_search_action(
                [Message("user", None)],
                {"api_search": object()},
            )

    def test_candidate_identity_is_explicitly_zero_model(self):
        self.assertIn("zero-model", MODEL_SLUG)
        action = next_search_action(
            [Message("user", "Create a follow-up task.")],
            {"api_search": object()},
        )
        self.assertEqual(action["model_role"], "NONE")
        self.assertEqual(action["model_dependency_count"], 0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
