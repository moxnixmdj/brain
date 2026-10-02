import json, pathlib, unittest

from canonical.runtime import enforce_goal_hierarchy


class FrontierTargetMirrorTests(unittest.TestCase):
    def setUp(self):
        self.hierarchy={
            "active_capability_target":"CAP_A",
            "current_parent_blocker":"BLOCKER_A",
            "next_required_action_class":"ACTION_A",
        }
        self.target={
            "capability_id":"CAP_A",
            "residual_gap":"BLOCKER_A",
            "next_action":"ACTION_A",
        }

    def test_exact_match_passes(self):
        self.assertEqual(enforce_goal_hierarchy.active_target_mirror_errors(self.hierarchy,self.target),[])

    def test_target_id_drift_fails(self):
        bad=dict(self.target); bad["capability_id"]="CAP_B"
        self.assertIn("FRONTIER_TARGET_CAPABILITY_ID_MISMATCH",enforce_goal_hierarchy.active_target_mirror_errors(self.hierarchy,bad))

    def test_blocker_drift_fails(self):
        bad=dict(self.target); bad["residual_gap"]="BLOCKER_B"
        self.assertIn("FRONTIER_TARGET_RESIDUAL_GAP_MISMATCH",enforce_goal_hierarchy.active_target_mirror_errors(self.hierarchy,bad))

    def test_next_action_drift_fails(self):
        bad=dict(self.target); bad["next_action"]="ACTION_B"
        self.assertIn("FRONTIER_TARGET_NEXT_ACTION_MISMATCH",enforce_goal_hierarchy.active_target_mirror_errors(self.hierarchy,bad))

    def test_live_target_record_mirrors_the_authority(self):
        """The live frontier target record must mirror the live authority.

        The four cases above exercise the checker on synthetic dicts, which is
        why they kept passing while the real record sat stale at a live base:
        nothing compared the two against each other. This is the standing
        oracle for the pair the guard now enforces, and it discovers both files
        from the hierarchy rather than hardcoding a rank or a target id.
        """
        root=pathlib.Path(__file__).resolve().parents[2]
        hierarchy=json.loads((root/"canonical/governance/ACTIVE_GOAL_HIERARCHY_V1.json").read_text(encoding="utf-8"))
        target_id=str(hierarchy.get("active_capability_target") or "").strip()
        self.assertTrue(target_id,"the authority names no active capability target")
        path=root/("canonical/capabilities/frontier/"+target_id+".json")
        self.assertTrue(path.is_file(),"missing frontier target record: %s"%path)
        target=json.loads(path.read_text(encoding="utf-8"))
        self.assertEqual(
            enforce_goal_hierarchy.active_target_mirror_errors(hierarchy,target),[],
            "the live frontier target record drifted from the authority; recompute it with"
            " python3 canonical/runtime/reconcile_frontier_mirrors.py .",
        )


if __name__=="__main__":
    unittest.main()
