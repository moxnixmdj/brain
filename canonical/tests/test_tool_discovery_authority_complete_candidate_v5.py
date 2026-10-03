from __future__ import annotations

import hashlib
import json
import unittest

from canonical.runtime import tool_discovery_authority_complete_candidate_v5 as v5
from canonical.runtime import tool_discovery_information_safe_candidate as legacy


def _sha(v):
    raw=json.dumps(v,sort_keys=True,separators=(",",":"),ensure_ascii=False).encode()
    return hashlib.sha256(raw).hexdigest()


def _authority(actions, epoch=11):
    normalized=[]
    for raw in actions:
        normalized.append({
            "action_id":raw["action_id"],
            "kind":raw["kind"],
            "source_id":raw.get("source_id"),
            "epoch":raw.get("epoch"),
            "cost":raw.get("cost"),
            "available":raw.get("available") is True,
            "authorized":raw.get("authorized") is True,
            "result_semantics":raw.get("result_semantics"),
        })
    return {
        "kind":"TOOL_AUTHORITY",
        "epoch":epoch,
        "actions":actions,
        "action_manifest_sha256":_sha(sorted(normalized,key=lambda x:x["action_id"])),
    }


def _source(aid,sid,cost,epoch=0,available=True,authorized=True):
    return {
        "action_id":aid,
        "kind":"DISCOVERY_SOURCE",
        "source_id":sid,
        "epoch":epoch,
        "cost":float(cost),
        "available":available,
        "authorized":authorized,
        "result_semantics":"EXHAUSTIVE_CURRENT_TOOL_LIST",
    }


class ToolDiscoveryAuthorityCompleteV5Tests(unittest.TestCase):
    def test_exact_legacy_projection_without_authority_or_registry(self):
        public={
            "required_capabilities":["CAP"],
            "tools":[
                {"tool_id":"A","cost":1.0,"available":True,"authorized":True},
                {"tool_id":"B","cost":2.0,"available":True,"authorized":True},
            ],
            "prior_probe_receipts":[
                {"kind":"SAFE_CAPABILITY_PROBE","tool_id":"A","capability":"CAP","epoch":0,"supported":True}
            ],
            "version_events":[],
        }
        self.assertEqual(v5.next_action(public),legacy.next_action(public))

    def test_authority_derivation_ignores_injected_smaller_registry(self):
        actions=[_source("D0","S0",2),_source("D1","S1",1)]
        public={
            "required_capabilities":["CAP"],
            "tools":[],
            "prior_probe_receipts":[],
            "version_events":[],
            "discovery_receipts":[],
            "tool_authority":_authority(actions),
            "discovery_registry":{
                "kind":"COMPLETE_DISCOVERY_REGISTRY",
                "complete":True,
                "epoch":11,
                "sources":[{"source_id":"S0","epoch":0,"cost":2.0,"available":True,"authorized":True}],
                "source_manifest_sha256":"attacker-subset",
            },
        }
        action=v5.next_action(public)
        self.assertEqual(action["action"],"DISCOVER")
        self.assertEqual(action["source_id"],"S1")

    def test_every_authorized_authority_source_is_exhausted_before_probe(self):
        actions=[_source("D0","S0",2),_source("D1","S1",1)]
        authority=_authority(actions)
        public={
            "required_capabilities":["CAP"],
            "tools":[
                {"tool_id":"VISIBLE","cost":10.0,"epoch":0,"available":True,
                 "authorized":True,"safe_probe_allowed":True}
            ],
            "prior_probe_receipts":[
                {"kind":"SAFE_CAPABILITY_PROBE","tool_id":"VISIBLE","capability":"CAP","epoch":0,"supported":True}
            ],
            "version_events":[],
            "tool_authority":authority,
            "discovery_receipts":[{
                "kind":"DISCOVERY_RESULT","source_id":"S1","registry_epoch":11,
                "source_epoch":0,"complete":True,"tools":[]
            }],
        }
        action=v5.next_action(public)
        self.assertEqual(action["action"],"DISCOVER")
        self.assertEqual(action["source_id"],"S0")

    def test_nonexhaustive_discovery_action_fails_closed(self):
        bad=_source("D0","S0",1)
        bad["result_semantics"]="PAGINATED_PARTIAL"
        public={
            "required_capabilities":["CAP"],
            "tools":[],
            "prior_probe_receipts":[],
            "version_events":[],
            "discovery_receipts":[],
            "tool_authority":_authority([bad]),
        }
        out=v5.next_action(public)
        self.assertEqual(out["action"],"ESCALATE")
        self.assertIn("RESULT_NOT_EXHAUSTIVE",out["reason"])

    def test_action_manifest_drift_fails_closed(self):
        actions=[_source("D0","S0",1)]
        authority=_authority(actions)
        authority["actions"][0]["cost"]=99
        public={
            "required_capabilities":["CAP"],
            "tools":[],
            "prior_probe_receipts":[],
            "version_events":[],
            "discovery_receipts":[],
            "tool_authority":authority,
        }
        out=v5.next_action(public)
        self.assertEqual(out["action"],"ESCALATE")
        self.assertIn("TOOL_AUTHORITY_MANIFEST_MISMATCH",out["reason"])

    def test_non_discovery_actions_do_not_disappear_from_authority_integrity(self):
        actions=[
            _source("D0","S0",1),
            {"action_id":"OTHER","kind":"NORMAL_TOOL","available":True,"authorized":True},
        ]
        authority=_authority(actions)
        public={
            "required_capabilities":["CAP"],
            "tools":[],
            "prior_probe_receipts":[],
            "version_events":[],
            "discovery_receipts":[],
            "tool_authority":authority,
        }
        self.assertEqual(v5.next_action(public)["source_id"],"S0")
        authority["actions"][1]["kind"]="MUTATED_TOOL"
        out=v5.next_action({**public,"tool_authority":authority})
        self.assertEqual(out["action"],"ESCALATE")
        self.assertIn("MANIFEST_MISMATCH",out["reason"])


if __name__=="__main__":
    unittest.main(verbosity=2)
