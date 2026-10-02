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


class ScoreboardMirrorTests(unittest.TestCase):
    """The scoreboard's mirrors, top-level and nested, against the same authority.

    The nested active_frontier_accounting copies of residual_gap and
    next_required_action were maintained by reconcile_frontier_mirrors.py but
    compared by nothing, so they were found drifted on main while the top-level
    mirrors agreed. These cases pin all five comparisons, including that a missing
    nested block fails closed rather than reading as a match.
    """

    def setUp(self):
        self.hierarchy={
            "active_capability_target":"CAP_A",
            "current_parent_blocker":"BLOCKER_A",
            "next_required_action_class":"ACTION_A",
            "next_progress_event_target":"EVENT_A",
        }
        self.scoreboard={
            "next_required_action":"ACTION_A",
            "next_progress_event_target":"EVENT_A",
            "active_frontier_accounting":{
                "parent_frontier_capability":"CAP_A",
                "residual_gap":"BLOCKER_A",
                "next_required_action":"ACTION_A",
            },
        }

    def errors(self,scoreboard):
        return enforce_goal_hierarchy.scoreboard_mirror_errors(self.hierarchy,scoreboard)

    def test_exact_match_passes(self):
        self.assertEqual(self.errors(self.scoreboard),[])

    def test_nested_capability_drift_fails(self):
        bad=json.loads(json.dumps(self.scoreboard))
        bad["active_frontier_accounting"]["parent_frontier_capability"]="CAP_B"
        self.assertIn("SCOREBOARD_HIERARCHY_ACTIVE_CAPABILITY_TARGET_MISMATCH",self.errors(bad))

    def test_top_level_action_drift_fails(self):
        bad=json.loads(json.dumps(self.scoreboard)); bad["next_required_action"]="ACTION_B"
        self.assertIn("SCOREBOARD_HIERARCHY_NEXT_ACTION_MISMATCH",self.errors(bad))

    def test_progress_event_drift_fails(self):
        bad=json.loads(json.dumps(self.scoreboard)); bad["next_progress_event_target"]="EVENT_B"
        self.assertIn("SCOREBOARD_HIERARCHY_NEXT_PROGRESS_EVENT_MISMATCH",self.errors(bad))

    def test_nested_residual_gap_drift_fails(self):
        bad=json.loads(json.dumps(self.scoreboard))
        bad["active_frontier_accounting"]["residual_gap"]="BLOCKER_B"
        self.assertIn("SCOREBOARD_HIERARCHY_NESTED_RESIDUAL_GAP_MISMATCH",self.errors(bad))

    def test_nested_action_drift_fails(self):
        bad=json.loads(json.dumps(self.scoreboard))
        bad["active_frontier_accounting"]["next_required_action"]="ACTION_B"
        self.assertIn("SCOREBOARD_HIERARCHY_NESTED_NEXT_ACTION_MISMATCH",self.errors(bad))

    def test_missing_nested_accounting_fails_closed(self):
        """Absence is unknown, never agreement -- the failure mode this repo keeps rediscovering."""
        bad=json.loads(json.dumps(self.scoreboard)); del bad["active_frontier_accounting"]
        found=self.errors(bad)
        self.assertIn("SCOREBOARD_HIERARCHY_NESTED_RESIDUAL_GAP_MISMATCH",found)
        self.assertIn("SCOREBOARD_HIERARCHY_NESTED_NEXT_ACTION_MISMATCH",found)
        self.assertIn("SCOREBOARD_HIERARCHY_ACTIVE_CAPABILITY_TARGET_MISMATCH",found)

    def test_nested_drift_alone_is_still_drift(self):
        """The top-level mirrors agreeing must not mask the nested ones."""
        bad=json.loads(json.dumps(self.scoreboard))
        bad["active_frontier_accounting"]["residual_gap"]="BLOCKER_B"
        bad["active_frontier_accounting"]["next_required_action"]="ACTION_B"
        found=self.errors(bad)
        self.assertEqual(
            sorted(found),
            ["SCOREBOARD_HIERARCHY_NESTED_NEXT_ACTION_MISMATCH",
             "SCOREBOARD_HIERARCHY_NESTED_RESIDUAL_GAP_MISMATCH"],
            "a nested-only drift must report exactly the two nested predicates and nothing else")

    def test_live_scoreboard_mirrors_the_authority(self):
        """Standing oracle on the live tree, discovering both files from the authority."""
        root=pathlib.Path(__file__).resolve().parents[2]
        hierarchy=json.loads((root/"canonical/governance/ACTIVE_GOAL_HIERARCHY_V1.json").read_text(encoding="utf-8"))
        scoreboard=json.loads((root/"canonical/governance/REAL_OUTPUT_SCOREBOARD_V1.json").read_text(encoding="utf-8"))
        self.assertEqual(
            enforce_goal_hierarchy.scoreboard_mirror_errors(hierarchy,scoreboard),[],
            "the live scoreboard drifted from the authority, including its nested "
            "active_frontier_accounting mirrors; recompute them with"
            " python3 canonical/runtime/reconcile_frontier_mirrors.py .",
        )


if __name__=="__main__":
    unittest.main()
