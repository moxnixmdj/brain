from __future__ import annotations

import json
import unittest

from canonical.runtime.automationbench_policy_state_machine_v1 import next_policy_action


class AutomationBenchPolicyStateMachineV1Tests(unittest.TestCase):
    def test_first_phase_discovers_endpoints(self):
        out = next_policy_action(
            prompt="Mark the Salesforce opportunity as won and send a Gmail notice.",
            history=[],
        )
        self.assertEqual(out["phase"], "DISCOVER_ENDPOINTS")
        self.assertEqual(out["status"], "CALL_TOOLS")
        self.assertTrue(all(x["tool"] == "api_search" for x in out["calls"]))

    def test_second_phase_observes_get_endpoints_only(self):
        history = [{
            "kind":"tool_result",
            "name":"api_search",
            "content": json.dumps({
                "results":[
                    {"id":"salesforce.query","method":"GET","url":"https://x.salesforce.com/query","description":"search opportunities","parameters":{"q":{"required":true,"location":"query"}}},
                    {"id":"sf.update","method":"PATCH","url":"https://x.salesforce.com/opportunity/{id}","description":"update opportunity","parameters":{"id":{"required":True}}},
                ]
            }),
        }]
        out = next_policy_action(
            prompt="Find the Salesforce opportunity and mark it as won.",
            history=history,
        )
        self.assertEqual(out["phase"], "OBSERVE_STATE")
        self.assertTrue(out["calls"])
        self.assertTrue(all(x["arguments"]["method"] == "GET" for x in out["calls"]))

    def test_third_phase_compiles_salesforce_mutation(self):
        prompt = "We just closed the Meridian Corp Platform Deal! Mark it as won in Salesforce."
        history = [
            {"kind":"tool_result","name":"api_search","content":'{"results":[]}'},
            {
                "kind":"tool_result",
                "name":"api_fetch",
                "content": json.dumps({
                    "records":[
                        {"Id":"006xx000004MER1","Name":"Meridian Corp - Platform Deal","StageName":"Negotiation"}
                    ]
                }),
            },
        ]
        out = next_policy_action(prompt=prompt, history=history)
        self.assertEqual(out["phase"], "MUTATE")
        self.assertEqual(out["semantic"], "SALESFORCE_OPPORTUNITY_MARK_WON")
        self.assertEqual(out["calls"][0]["arguments"]["method"], "PATCH")

    def test_third_phase_compiles_asana_from_authoritative_candidate(self):
        prompt = "Add the fire drill task to Asana project proj_facilities."
        history = [
            {"kind":"tool_result","name":"api_search","content":'{"results":[]}'},
            {
                "kind":"tool_result",
                "name":"api_fetch",
                "content": json.dumps({
                    "messages":[
                        {"id":"draft","subject":"Fire drill","body_plain":"DRAFT - DO NOT ACTION: Create task: Wrong. Due: 2026-03-01.","date":"2026-02-02T00:00:00Z"},
                        {"id":"good","subject":"Fire drill","body_plain":"Create task: Monthly Fire Drill Checklist - February. Due: 2026-02-18. Tag: Compliance.","date":"2026-02-01T00:00:00Z"},
                    ]
                }),
            },
        ]
        out = next_policy_action(prompt=prompt, history=history)
        self.assertEqual(out["phase"], "MUTATE")
        body = json.loads(out["calls"][0]["arguments"]["body"])
        self.assertEqual(body["name"], "Monthly Fire Drill Checklist - February")

    def test_asana_scans_past_relevant_non_action_record(self):
        prompt = "Add the fire drill task to Asana project proj_facilities."
        history = [
            {"kind":"tool_result","name":"api_search","content":'{"results":[]}'},
            {
                "kind":"tool_result",
                "name":"api_fetch",
                "content": json.dumps({
                    "records":[
                        {
                            "id":"policy",
                            "title":"Fire Drill Policy",
                            "description":"Fire drill task policy for facilities",
                            "date":"2026-02-03T00:00:00Z"
                        },
                        {
                            "id":"good",
                            "subject":"Fire drill",
                            "body_plain":"Create task: Monthly Fire Drill Checklist - February. Due: 2026-02-18. Tag: Compliance.",
                            "date":"2026-02-01T00:00:00Z"
                        }
                    ]
                }),
            },
        ]
        out = next_policy_action(prompt=prompt, history=history)
        self.assertEqual(out["semantic"], "ASANA_TASK_CREATE")

    def test_semantic_metadata_prevents_repeat_mutation(self):
        prompt = "We just closed the Meridian Corp Platform Deal! Mark it as won in Salesforce."
        history = [
            {"kind":"tool_result","name":"api_search","content":'{"results":[]}'},
            {
                "kind":"tool_result",
                "name":"api_fetch",
                "content":json.dumps({
                    "records":[
                        {"Id":"006xx000004MER1","Name":"Meridian Corp - Platform Deal"}
                    ]
                })
            },
            {
                "kind":"assistant_state",
                "metadata":{
                    "project_brain/automationbench_semantic":"SALESFORCE_OPPORTUNITY_MARK_WON"
                }
            },
        ]
        out = next_policy_action(prompt=prompt, history=history)
        self.assertNotEqual(out.get("semantic"), "SALESFORCE_OPPORTUNITY_MARK_WON")

    def test_created_asana_task_advances_to_section_placement(self):
        prompt = (
            "Add the fire drill task to Asana project proj_facilities "
            "under the 'February' section."
        )
        history = [
            {"kind":"tool_result","name":"api_search","content":'{"results":[]}'},
            {
                "kind":"tool_result",
                "name":"api_fetch",
                "content":json.dumps({
                    "messages":[
                        {
                            "id":"source",
                            "body_plain":"Create task: Monthly Fire Drill Checklist - February. Due: 2026-02-18."
                        }
                    ],
                    "sections":[
                        {
                            "gid":"sec_feb",
                            "name":"February",
                            "project":{"gid":"proj_facilities"}
                        }
                    ]
                })
            },
            {
                "kind":"assistant_state",
                "metadata":{
                    "project_brain/automationbench_semantic":"ASANA_TASK_CREATE"
                }
            },
            {
                "kind":"tool_result",
                "name":"api_fetch",
                "content":json.dumps({
                    "data":{
                        "gid":"task_new",
                        "name":"Monthly Fire Drill Checklist - February",
                        "due_on":"2026-02-18",
                        "completed":False
                    }
                })
            }
        ]
        out = next_policy_action(prompt=prompt, history=history)
        self.assertEqual(out["semantic"], "ASANA_TASK_ADD_TO_SECTION")
        self.assertIn("/sections/sec_feb/addTask", out["calls"][0]["arguments"]["url"])

    def test_unsupported_semantics_fail_closed(self):
        history = [
            {"kind":"tool_result","name":"api_search","content":'{"results":[]}'},
            {"kind":"tool_result","name":"api_fetch","content":'{"records":[{"id":"x","name":"x"}]}'},
        ]
        out = next_policy_action(
            prompt="Perform a workflow type that has no compiler yet.",
            history=history,
        )
        self.assertEqual(out["status"], "NEEDS_POLICY_EXTENSION")
        self.assertEqual(out["calls"], [])


if __name__ == "__main__":
    unittest.main(verbosity=2)
