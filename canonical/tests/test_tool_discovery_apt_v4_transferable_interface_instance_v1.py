from __future__ import annotations
import copy
import unittest

from canonical.runtime import tool_discovery_apt_v4_transferable_interface_instance_v1 as m


class Tests(unittest.TestCase):
    def test_v4_property_set_is_exact_twelve(self):
        self.assertEqual(len(m.REQUIRED_PROPERTIES),12)
        self.assertIn(
            "COMPLETE_CATALOG_RECEIPT_IS_REUSABLE_ACROSS_TASK_REQUIREMENT_AND_DECISION_EPOCH_CHANGES_WITHIN_THE_SAME_AUTHORITY_SOURCE_EPOCHS",
            m.REQUIRED_PROPERTIES,
        )

    def test_source_epoch_is_content_sensitive(self):
        self.assertNotEqual(m._source_epoch("1"*64),m._source_epoch("2"*64))

    def test_authority_epoch_is_content_sensitive(self):
        self.assertNotEqual(m._authority_epoch("a"*64),m._authority_epoch("b"*64))

    def test_policy_transfer_blocking_and_restart_properties(self):
        tool={
            "tool_id":"T0",
            "epoch":7,
            "cost":1.0,
            "available":True,
            "authorized":True,
            "safe_probe_capabilities":["CLI_SHA256SUM_VERSION_EXECUTES"],
        }
        out=m._policy_transfer_and_blocking_checks(coreutils_tool=tool,authority_epoch=9)
        self.assertTrue(all(out.values()),out)

    def test_state_is_catalog_bound_not_visible_tool_bound(self):
        tool={
            "tool_id":"T0",
            "epoch":0,
            "cost":0.0,
            "available":True,
            "authorized":True,
            "safe_probe_capabilities":["CAP"],
        }
        s=m._v8_single_source_state(
            [tool],required=["CAP"],authority_epoch=3,decision_epoch=4,
            probe_rows=[{
                "kind":"SAFE_CAPABILITY_PROBE",
                "tool_id":"T0","capability":"CAP","epoch":0,
                "authority_epoch":3,"supported":True,
            }],
        )
        self.assertEqual(s["visible_tools"],[])
        self.assertTrue(s["discovery_receipts"][0]["complete"])


if __name__=="__main__":
    unittest.main(verbosity=2)
