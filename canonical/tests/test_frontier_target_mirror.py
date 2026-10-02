import json, pathlib, shutil, tempfile, unittest

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


class TargetAtomicEventMirrorTests(unittest.TestCase):
    """The target record's THIRD atomic mirror, which the guard compared by nothing.

    current_state_obs_reducer.py has always compared
    record.current_atomic_progress_event to hierarchy.next_progress_event_target, but
    the guard compared only the atomic blocker and action. So a tree the guard passed
    could still fail the reducer -- and did: the field was found stale on main, still
    naming an earlier phase's progress event, with the guard green and the reducer red.
    """

    def setUp(self):
        enforce_goal_hierarchy.FAIL.clear()
        root=pathlib.Path(__file__).resolve().parents[2]
        self.hierarchy=json.loads((root/"canonical/governance/ACTIVE_GOAL_HIERARCHY_V1.json").read_text(encoding="utf-8"))
        target_id=str(self.hierarchy.get("active_capability_target") or "").strip()
        self.target=json.loads((root/("canonical/capabilities/frontier/"+target_id+".json")).read_text(encoding="utf-8"))
        self.predicate="TARGET_RECORD_HIERARCHY_ATOMIC_EVENT_MISMATCH"

    def check(self,target):
        enforce_goal_hierarchy.FAIL.clear()
        enforce_goal_hierarchy.enforce_active_target_record_consistency(self.hierarchy,target)
        return list(enforce_goal_hierarchy.FAIL)

    def test_live_record_matches_the_authority(self):
        self.assertEqual(self.check(self.target),[],
                         "the live target record disagrees with the authority; recompute the mirrors "
                         "with python3 canonical/runtime/reconcile_frontier_mirrors.py .")

    def test_atomic_event_drift_fails_closed(self):
        bad=json.loads(json.dumps(self.target))
        bad["current_atomic_progress_event"]="STALE_EVENT_FROM_AN_EARLIER_PHASE"
        self.assertIn(self.predicate,self.check(bad))

    def test_a_missing_atomic_event_fails_closed(self):
        bad=json.loads(json.dumps(self.target))
        bad.pop("current_atomic_progress_event",None)
        self.assertIn(self.predicate,self.check(bad),
                      "absence read as agreement; an unknown mirror must fail closed")

    def test_atomic_event_drift_alone_is_still_drift(self):
        """The other two atomic mirrors agreeing must not mask the third."""
        bad=json.loads(json.dumps(self.target))
        bad["current_atomic_progress_event"]="STALE_EVENT_FROM_AN_EARLIER_PHASE"
        self.assertEqual(self.check(bad),[self.predicate],
                         "a drift in the third atomic mirror must report exactly that predicate")


class ControlPathCurrencyTests(unittest.TestCase):
    """Teeth for enforce_control_path_currency, the repair for guard version-pin rot.

    The check was wired into main() and nothing in the repository tested it: replacing
    its whole body with `return None` left all 121 tests across the guard and oracle
    modules passing. That is the silence in which a check stops being a check -- the same
    silence that let the frontier mirror fields rot for 565 commits while every run
    printed PASS. Each case builds its own control surface under a temporary ROOT so the
    assertions are about the check rather than about whichever artifact versions happen
    to be canonical on the day the test runs; a test that reads the live tree for this
    would pass or fail with the frontier instead of with the code.
    """
    KEY="example_control_law_path"

    def setUp(self):
        self.tmp=pathlib.Path(tempfile.mkdtemp(prefix="controlpath"))
        self._root=enforce_goal_hierarchy.ROOT
        self._fail=list(enforce_goal_hierarchy.FAIL)
        enforce_goal_hierarchy.ROOT=self.tmp
        enforce_goal_hierarchy.FAIL.clear()

    def tearDown(self):
        enforce_goal_hierarchy.ROOT=self._root
        enforce_goal_hierarchy.FAIL.clear()
        enforce_goal_hierarchy.FAIL.extend(self._fail)
        shutil.rmtree(self.tmp,ignore_errors=True)

    def _write(self,rel,text="{}"):
        p=self.tmp/rel
        p.parent.mkdir(parents=True,exist_ok=True)
        p.write_text(text,encoding="utf-8")
        return rel

    def _check(self,declared):
        enforce_goal_hierarchy.FAIL.clear()
        enforce_goal_hierarchy.enforce_control_path_currency(self.KEY,declared)
        return list(enforce_goal_hierarchy.FAIL)

    def test_the_highest_version_present_passes(self):
        rel=self._write("canonical/governance/EXAMPLE_CONTROL_LAW_V3.md","current law")
        self.assertEqual(self._check(rel),[])

    def test_a_superseded_lower_version_fails_closed_and_names_both_versions(self):
        self._write("canonical/governance/EXAMPLE_CONTROL_LAW_V3.md","current law")
        rel=self._write("canonical/governance/EXAMPLE_CONTROL_LAW_V2.md","older law")
        got=self._check(rel)
        self.assertEqual(len(got),1,got)
        self.assertTrue(got[0].startswith("POINTER_CONTROL_PATH_NOT_CURRENT:"+self.KEY),got)
        self.assertIn("declared_V2",got[0])
        self.assertIn("current_V3",got[0])

    def test_the_same_declaration_fails_closed_once_the_family_advances(self):
        """The rot mechanism itself, which an exact-version constant cannot express.

        A guard pinned to `expected == V3` passes this declaration forever, and goes red
        on every frontier-sensitive PR the day the canonical surface moves to V4 while
        the pointer is still correct. Comparing against the highest version present makes
        the identical declaration fail closed the moment a newer sibling lands, so the
        check cannot itself go stale -- that is the whole reason it exists.
        """
        rel=self._write("canonical/governance/EXAMPLE_CONTROL_LAW_V3.md","current law")
        self.assertEqual(self._check(rel),[])
        self._write("canonical/governance/EXAMPLE_CONTROL_LAW_V4.md","newer law")
        got=self._check(rel)
        self.assertTrue(any(g.startswith("POINTER_CONTROL_PATH_NOT_CURRENT:") for g in got),got)

    def test_a_missing_file_fails_closed(self):
        got=self._check("canonical/governance/EXAMPLE_CONTROL_LAW_V9.md")
        self.assertEqual(got,["POINTER_CONTROL_PATH_FILE_MISSING:"+self.KEY])

    def test_an_empty_declaration_fails_closed(self):
        for declared in ("",None,"   ",3):
            self.assertEqual(self._check(declared),
                             ["POINTER_CONTROL_PATH_MISSING:"+self.KEY],declared)

    def test_an_unversioned_path_fails_closed(self):
        rel=self._write("canonical/governance/EXAMPLE_CONTROL_LAW.md","current law")
        self.assertEqual(self._check(rel),["POINTER_CONTROL_PATH_NOT_VERSIONED:"+self.KEY])

    def test_a_superseded_artifact_fails_closed_even_at_the_current_version(self):
        rel=self._write("canonical/governance/EXAMPLE_CONTROL_LAW_V3.md",
                        "# example\n\n"+enforce_goal_hierarchy.SUPERSEDED_MARKER+"\n")
        self.assertEqual(self._check(rel),["POINTER_CONTROL_PATH_SUPERSEDED:"+self.KEY])

    def test_families_are_resolved_independently(self):
        """A newer .md sibling must not excuse a stale .json declaration, or vice versa."""
        json_rel=self._write("canonical/governance/EXAMPLE_CONTROL_LAW_V2.json","{}")
        self._write("canonical/governance/EXAMPLE_CONTROL_LAW_V3.md","current law")
        self.assertEqual(self._check(json_rel),[],
                         "the .md family advancing must not affect the .json family")
        self._write("canonical/governance/EXAMPLE_CONTROL_LAW_V7.json","{}")
        got=self._check(json_rel)
        self.assertTrue(any(g.startswith("POINTER_CONTROL_PATH_NOT_CURRENT:") for g in got),got)


if __name__=="__main__":
    unittest.main()
