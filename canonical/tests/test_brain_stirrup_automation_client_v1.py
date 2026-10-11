from __future__ import annotations

import asyncio
import json
import unittest
from dataclasses import dataclass

from canonical.runtime.brain_stirrup_automation_client_v1 import (
    BRAIN_AUTOMATION_POLICY_V1,
    BrainAutomationClient,
    BrainAutomationPolicyError,
    policy_sha256,
    validate_assistant_message,
)


@dataclass
class Msg:
    role: str
    content: str = ""


@dataclass
class Block:
    kind: str
    name: str | None = None
    arguments: str | None = None


@dataclass
class Assistant:
    blocks: list[Block]


class Params:
    @classmethod
    def model_validate(cls, value):
        if set(value) != {"record_id", "status"}:
            raise ValueError("fields")
        if not isinstance(value["record_id"], str):
            raise ValueError("record_id")
        if value["status"] not in {"approved", "rejected"}:
            raise ValueError("status")
        return value


@dataclass
class Tool:
    parameters: object = Params


class BaseClient:
    model_slug = "example/subthreshold-general-substrate"
    context_window_tokens = 131072

    def __init__(self, response):
        self.response = response
        self.calls = []

    async def generate(self, messages, tools):
        self.calls.append((messages, tools))
        return self.response


def factory(content: str):
    return Msg("system", content)


class BrainAutomationClientTests(unittest.TestCase):
    def test_policy_is_benchmark_neutral(self):
        lower = BRAIN_AUTOMATION_POLICY_V1.lower()
        self.assertNotIn("automationbench", lower)
        self.assertNotIn("657", lower)
        self.assertNotIn("zapier", lower)
        self.assertNotIn("artificial analysis", lower)

    def test_policy_hash_is_stable_sha256(self):
        digest = policy_sha256()
        self.assertEqual(len(digest), 64)
        int(digest, 16)

    def test_injects_policy_after_leading_system_messages_without_mutating_input(self):
        response = Assistant([Block("text")])
        base = BaseClient(response)
        client = BrainAutomationClient(base, system_message_factory=factory)
        original = [Msg("system", "evaluator"), Msg("user", "do task")]
        before_ids = [id(x) for x in original]

        out = asyncio.run(client.generate(original, {}))

        self.assertIs(out, response)
        self.assertEqual(len(base.calls), 1)
        sent = base.calls[0][0]
        self.assertEqual([x.role for x in sent], ["system", "system", "user"])
        self.assertEqual(sent[0].content, "evaluator")
        self.assertEqual(sent[1].content, BRAIN_AUTOMATION_POLICY_V1)
        self.assertEqual([id(x) for x in original], before_ids)
        self.assertEqual(len(original), 2)

    def test_exactly_one_base_call_per_generate(self):
        base = BaseClient(Assistant([Block("text")]))
        client = BrainAutomationClient(base, system_message_factory=factory)
        asyncio.run(client.generate([Msg("user", "x")], {}))
        asyncio.run(client.generate([Msg("user", "y")], {}))
        self.assertEqual(len(base.calls), 2)
        self.assertEqual(client.base_generate_call_count, 2)

    def test_properties_bind_base_dependency(self):
        base = BaseClient(Assistant([Block("text")]))
        client = BrainAutomationClient(base, system_message_factory=factory)
        self.assertEqual(client.base_model_slug, BaseClient.model_slug)
        self.assertEqual(client.context_window_tokens, BaseClient.context_window_tokens)
        self.assertIn(BaseClient.model_slug, client.model_slug)
        self.assertEqual(client.brain_policy_sha256, policy_sha256())

    def test_valid_single_tool_call_is_passed_through_by_identity(self):
        response = Assistant([
            Block(
                "tool_call",
                "update_record",
                json.dumps({"record_id": "R-7", "status": "approved"}),
            )
        ])
        out = validate_assistant_message(response, {"update_record": Tool()})
        self.assertIs(out, response)

    def test_text_only_response_is_passed_through(self):
        response = Assistant([Block("text")])
        self.assertIs(validate_assistant_message(response, {}), response)

    def test_unknown_tool_fails_closed(self):
        response = Assistant([Block("tool_call", "unlisted_tool", "{}")])
        with self.assertRaisesRegex(BrainAutomationPolicyError, "TOOL_CALL_NOT_DECLARED"):
            validate_assistant_message(response, {"update_record": Tool()})

    def test_invalid_json_fails_closed(self):
        response = Assistant([Block("tool_call", "update_record", "{bad")])
        with self.assertRaisesRegex(BrainAutomationPolicyError, "TOOL_ARGUMENTS_INVALID_JSON"):
            validate_assistant_message(response, {"update_record": Tool()})

    def test_non_object_arguments_fail_closed(self):
        response = Assistant([Block("tool_call", "update_record", "[]")])
        with self.assertRaisesRegex(
            BrainAutomationPolicyError, "TOOL_ARGUMENTS_MUST_DECODE_TO_OBJECT"
        ):
            validate_assistant_message(response, {"update_record": Tool()})

    def test_schema_invalid_arguments_fail_closed(self):
        response = Assistant([
            Block("tool_call", "update_record", json.dumps({"record_id": "R-7"}))
        ])
        with self.assertRaisesRegex(BrainAutomationPolicyError, "TOOL_ARGUMENTS_SCHEMA_INVALID"):
            validate_assistant_message(response, {"update_record": Tool()})

    def test_multiple_tool_calls_fail_closed_without_silent_dropping(self):
        response = Assistant([
            Block("tool_call", "update_record", json.dumps({"record_id": "R-1", "status": "approved"})),
            Block("tool_call", "update_record", json.dumps({"record_id": "R-2", "status": "approved"})),
        ])
        with self.assertRaisesRegex(BrainAutomationPolicyError, "MULTIPLE_TOOL_CALLS_FORBIDDEN"):
            validate_assistant_message(response, {"update_record": Tool()})

    def test_missing_blocks_fails_closed(self):
        class Bad:
            pass
        with self.assertRaisesRegex(BrainAutomationPolicyError, "ASSISTANT_MESSAGE_BLOCKS_REQUIRED"):
            validate_assistant_message(Bad(), {})

    def test_invalid_base_client_rejected(self):
        with self.assertRaises(TypeError):
            BrainAutomationClient(object(), system_message_factory=factory)

    def test_generate_propagates_base_failure_without_hidden_retry(self):
        class FailingBase(BaseClient):
            async def generate(self, messages, tools):
                self.calls.append((messages, tools))
                raise RuntimeError("provider-down")

        base = FailingBase(Assistant([]))
        client = BrainAutomationClient(base, system_message_factory=factory)
        with self.assertRaisesRegex(RuntimeError, "provider-down"):
            asyncio.run(client.generate([Msg("user", "x")], {}))
        self.assertEqual(len(base.calls), 1)
        self.assertEqual(client.base_generate_call_count, 1)


if __name__ == "__main__":
    unittest.main(verbosity=2)
