"""Tests for the frontier mirror reconciler.

ACTIVE_GOAL_HIERARCHY_V1 is the authority; every restatement of it is a mirror
that rots on each frontier advance. These tests seed drift in a temporary copy of
the canonical tree and require the tool to detect it, repair exactly the mirror
fields, and refuse to touch anything it has no authority over.
"""
import contextlib, io, json, shutil, tempfile, unittest
from pathlib import Path

from canonical.runtime.reconcile_frontier_mirrors import (
    HIERARCHY,
    POINTER,
    QUEUE,
    SCOREBOARD,
    reconcile,
)

ROOT = Path(__file__).resolve().parents[2]

STALE_BLOCKER = "STALE_MIRROR_BLOCKER_FROM_A_PREVIOUS_FRONTIER"
STALE_ACTION = "STALE_MIRROR_ACTION_FROM_A_PREVIOUS_FRONTIER"

# Directories whose version families the control-path currency check globs over.
SUPPORT_DIRS = ("canonical/gates", "canonical/laws")
SUPPORT_FILES = (
    "canonical/governance/WHITE_BOX_CAPABILITY_CAPSULE_SCHEMA_V1.json",
    "canonical/governance/RECURSIVE_OBS_RECEIPT_SCHEMA_V6.json",
    "canonical/governance/ACTION_INTENT_WITH_RECURSIVE_OBS_TEMPLATE_V10.json",
    "canonical/gates/GOAL_HIERARCHY_ACTION_GATE_V10.json",
)


class ReconcileFrontierMirrorsTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.hierarchy = json.loads((ROOT / HIERARCHY).read_text(encoding="utf-8"))
        self.blocker = self.hierarchy["current_parent_blocker"]
        self.action = self.hierarchy["next_required_action_class"]
        self.target = self.hierarchy["active_capability_target"]
        # The guard compares the scoreboard's progress-event mirror to this field,
        # not to next_required_action_class.
        self.progress_event = (
            self.hierarchy.get("next_progress_event_target") or self.action
        )

        paths = [HIERARCHY, POINTER, QUEUE, SCOREBOARD]
        paths.append(f"canonical/capabilities/frontier/{self.target}.json")
        for rel in paths + list(SUPPORT_FILES):
            src = ROOT / rel
            if not src.is_file():
                continue
            dst = self.root / rel
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(src, dst)
        for rel in SUPPORT_DIRS:
            shutil.copytree(ROOT / rel, self.root / rel, dirs_exist_ok=True)

        boot = json.loads((self.root / POINTER).read_text(encoding="utf-8"))["boot_requirements"]
        for key, declared in boot.items():
            if not key.endswith("_path") or not isinstance(declared, str):
                continue
            src = ROOT / declared
            if src.is_file() and not (self.root / declared).exists():
                dst = self.root / declared
                dst.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(src, dst)

    def tearDown(self):
        self.tmp.cleanup()

    def read(self, rel):
        return json.loads((self.root / rel).read_text(encoding="utf-8"))

    def write(self, rel, payload):
        (self.root / rel).write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")

    def run_tool(self, **kwargs):
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            code = reconcile(self.root, **kwargs)
        return code, out.getvalue()

    def seed_stale_mirrors(self):
        pointer = self.read(POINTER)
        pointer["current_frontier"]["critical_blocker"] = STALE_BLOCKER
        pointer["current_frontier"]["next_step"] = STALE_ACTION
        self.write(POINTER, pointer)

        queue = self.read(QUEUE)
        queue["immediate_frontier"]["exact_blocker"] = STALE_BLOCKER
        queue["immediate_frontier"]["next_action"] = STALE_ACTION
        self.write(QUEUE, queue)

        scoreboard = self.read(SCOREBOARD)
        scoreboard["next_progress_event_target"] = STALE_ACTION
        scoreboard["active_frontier_accounting"]["residual_gap"] = STALE_BLOCKER
        scoreboard["active_frontier_accounting"]["next_required_action"] = STALE_ACTION
        if "next_required_action" in scoreboard:
            scoreboard["next_required_action"] = STALE_ACTION
        self.write(SCOREBOARD, scoreboard)

        record_rel = f"canonical/capabilities/frontier/{self.target}.json"
        record = self.read(record_rel)
        record["residual_gap"] = STALE_BLOCKER
        record["next_action"] = STALE_ACTION
        # enforce_goal_hierarchy.py checks the target record's atomic pair, so the
        # tool must maintain it as well as residual_gap/next_action. Seeded only
        # where the live record carries those keys.
        for key, stale in (("current_atomic_blocker", STALE_BLOCKER),
                           ("current_atomic_next_action", STALE_ACTION)):
            if key in record:
                record[key] = stale
        self.write(record_rel, record)

    def mirror_values(self):
        pointer, queue = self.read(POINTER), self.read(QUEUE)
        scoreboard = self.read(SCOREBOARD)
        record = self.read(f"canonical/capabilities/frontier/{self.target}.json")
        values = {
            "pointer.critical_blocker": pointer["current_frontier"]["critical_blocker"],
            "pointer.next_step": pointer["current_frontier"]["next_step"],
            "queue.exact_blocker": queue["immediate_frontier"]["exact_blocker"],
            "queue.next_action": queue["immediate_frontier"]["next_action"],
            "scoreboard.next_progress_event_target": scoreboard["next_progress_event_target"],
            **({"scoreboard.next_required_action": scoreboard["next_required_action"]}
               if "next_required_action" in scoreboard else {}),
            "scoreboard.afa.residual_gap": scoreboard["active_frontier_accounting"]["residual_gap"],
            "scoreboard.afa.next_required_action": scoreboard["active_frontier_accounting"][
                "next_required_action"
            ],
            "record.residual_gap": record["residual_gap"],
            "record.next_action": record["next_action"],
        }
        for key in ("current_atomic_blocker", "current_atomic_next_action"):
            if key in record:
                values["record." + key] = record[key]
        return values

    # --- detection and repair ----------------------------------------------
    def test_live_repository_is_reconciled(self):
        # Standing regression: mirror rot must fail a test, not only the guard.
        # This covers the mirror fields, pointer control-path currency AND the
        # hierarchy's own next_progress_event_target, because a run that reports
        # unrepaired drift now fails closed instead of exiting 0.
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            code = reconcile(ROOT, write=False, fix_control_paths=False)
        self.assertEqual(code, 0, out.getvalue())
        self.assertIn("MIRRORS_CONSISTENT", out.getvalue())

    def test_report_only_drift_fails_the_check(self):
        # Regression: the verdict was once driven only by pending mirror changes,
        # so a report -- identity drift, stale control paths -- printed and then
        # exited 0. That is fail-open: the
        # standing oracle above stayed green while enforce_goal_hierarchy.py
        # failed the same tree.
        record_rel = f"canonical/capabilities/frontier/{self.target}.json"
        record = self.read(record_rel)
        record["capability_id"] = "SOME_OTHER_CAPABILITY_V1"
        self.write(record_rel, record)
        code, out = self.run_tool(write=False, fix_control_paths=False)
        self.assertIn("IDENTITY_DRIFT", out)
        self.assertIn("UNREPAIRED_DRIFT_PRESENT", out)
        self.assertNotIn("MIRRORS_CONSISTENT", out)
        self.assertEqual(code, 1, "a report is unrepaired drift and must fail closed")

    def test_seeded_drift_is_detected_without_writing(self):
        self.seed_stale_mirrors()
        before = self.mirror_values()
        code, out = self.run_tool(write=False, fix_control_paths=False)
        self.assertEqual(code, 1)
        self.assertIn("MIRROR_DRIFT", out)
        self.assertEqual(self.mirror_values(), before, "--check must not write")

    def test_seeded_drift_is_repaired_to_the_authority(self):
        self.seed_stale_mirrors()
        code, out = self.run_tool(write=True, fix_control_paths=False)
        self.assertEqual(code, 0, out)
        self.assertIn("MIRROR_CHANGES", out)
        values = self.mirror_values()
        for key, value in values.items():
            if key.endswith("next_progress_event_target"):
                expected = self.progress_event
            elif "blocker" in key or "residual_gap" in key:
                expected = self.blocker
            else:
                expected = self.action
            self.assertEqual(value, expected, key)

    def test_progress_event_mirror_follows_the_field_the_guard_reads(self):
        # enforce_goal_hierarchy.py compares scoreboard.next_progress_event_target
        # to hierarchy.next_progress_event_target, not to next_required_action_class.
        # Mirroring the action class would manufacture the mismatch the guard
        # reports whenever the authority itself is unaligned.
        hierarchy = self.read(HIERARCHY)
        hierarchy["next_progress_event_target"] = "SOME_DISTINCT_EVENT_NAME"
        self.write(HIERARCHY, hierarchy)
        code, out = self.run_tool(write=True, fix_control_paths=False)
        self.assertNotIn("HIERARCHY_PROGRESS_EVENT_DRIFT", out)
        self.assertEqual(code, 0, out)
        self.assertEqual(
            self.read(SCOREBOARD)["next_progress_event_target"], "SOME_DISTINCT_EVENT_NAME",
            "the mirror must follow the field the guard compares against, and a "
            "value distinct from next_required_action_class is legitimate",
        )

    def test_top_level_scoreboard_action_mirror_is_maintained(self):
        # The guard reads the scoreboard's top-level next_required_action; a tool
        # that maintained only the nested active_frontier_accounting copy would
        # report MIRRORS_CONSISTENT on a tree the guard fails.
        scoreboard = self.read(SCOREBOARD)
        if "next_required_action" not in scoreboard:
            self.skipTest("live scoreboard carries no top-level next_required_action")
        scoreboard["next_required_action"] = STALE_ACTION
        self.write(SCOREBOARD, scoreboard)
        code, out = self.run_tool(write=False, fix_control_paths=False)
        self.assertEqual(code, 1, out)
        self.assertIn("next_required_action", out)
        code, out = self.run_tool(write=True, fix_control_paths=False)
        self.assertEqual(code, 0, out)
        self.assertEqual(self.read(SCOREBOARD)["next_required_action"], self.action)

    def test_atomic_pair_drift_alone_is_detected_and_repaired(self):
        # The guard checks the target record's current_atomic_* pair. A tool that
        # maintained only residual_gap/next_action would report MIRRORS_CONSISTENT
        # on a tree enforce_goal_hierarchy.py fails, which is the fail-open shape
        # this suite exists to prevent.
        record_rel = f"canonical/capabilities/frontier/{self.target}.json"
        record = self.read(record_rel)
        if "current_atomic_blocker" not in record:
            self.skipTest("live target record carries no atomic pair")
        record["current_atomic_blocker"] = STALE_BLOCKER
        record["current_atomic_next_action"] = STALE_ACTION
        self.write(record_rel, record)
        code, out = self.run_tool(write=False, fix_control_paths=False)
        self.assertEqual(code, 1, out)
        self.assertIn("current_atomic_blocker", out)
        code, out = self.run_tool(write=True, fix_control_paths=False)
        self.assertEqual(code, 0, out)
        repaired = self.read(record_rel)
        self.assertEqual(repaired["current_atomic_blocker"], self.blocker)
        self.assertEqual(repaired["current_atomic_next_action"], self.action)

    def test_repair_is_idempotent(self):
        self.seed_stale_mirrors()
        self.run_tool(write=True, fix_control_paths=False)
        code, out = self.run_tool(write=True, fix_control_paths=False)
        self.assertEqual(code, 0, out)
        self.assertIn("MIRRORS_CONSISTENT", out)

    def test_repair_preserves_byte_formatting_of_untouched_files(self):
        # Start from a queue whose mirrors already equal the authority, so this
        # test measures formatting preservation rather than live-tree drift,
        # which test_live_repository_is_reconciled covers explicitly.
        queue = self.read(QUEUE)
        queue["immediate_frontier"]["exact_blocker"] = self.blocker
        queue["immediate_frontier"]["next_action"] = self.action
        self.write(QUEUE, queue)
        queue_before = (self.root / QUEUE).read_text(encoding="utf-8")
        pointer = self.read(POINTER)
        pointer["current_frontier"]["critical_blocker"] = STALE_BLOCKER
        self.write(POINTER, pointer)
        self.run_tool(write=True, fix_control_paths=False)
        self.assertEqual(
            (self.root / QUEUE).read_text(encoding="utf-8"), queue_before,
            "an untouched mirror file must not be rewritten",
        )

    # --- authority boundaries ----------------------------------------------
    def test_scoreboard_counters_never_move(self):
        before = self.read(SCOREBOARD)["counters_since_epoch_start"]
        self.seed_stale_mirrors()
        self.run_tool(write=True, fix_control_paths=False)
        self.assertEqual(self.read(SCOREBOARD)["counters_since_epoch_start"], before)

    def test_the_tool_never_edits_the_authority(self):
        # next_progress_event_target is not a mirror of next_required_action_class.
        # enforce_goal_hierarchy.py once required them to be equal (added 44d6a09)
        # and that requirement was repealed in d32bf4d; upstream's live value is a
        # distinct event name such as RANK22_BUILDER_ARTIFACT_FREEZE. Aligning them
        # under the repealed law overwrote that event name with the action class,
        # so the capability is removed rather than defaulted off, and a distinct
        # value is no longer drift at all.
        hierarchy = self.read(HIERARCHY)
        hierarchy["next_progress_event_target"] = "SOME_DISTINCT_EVENT_NAME"
        self.write(HIERARCHY, hierarchy)
        self.seed_stale_mirrors()
        seeded = (self.root / HIERARCHY).read_text(encoding="utf-8")
        code, out = self.run_tool(write=True, fix_control_paths=False)
        self.assertNotIn("HIERARCHY_PROGRESS_EVENT_DRIFT", out)
        self.assertEqual(
            (self.root / HIERARCHY).read_text(encoding="utf-8"), seeded,
            "the authoritative file must be byte-identical after any run",
        )
        self.assertEqual(self.read(HIERARCHY)["next_progress_event_target"],
                         "SOME_DISTINCT_EVENT_NAME")

    def test_capability_identity_drift_is_reported_not_rewritten(self):
        record_rel = f"canonical/capabilities/frontier/{self.target}.json"
        record = self.read(record_rel)
        record["capability_id"] = "SOME_OTHER_CAPABILITY_V1"
        self.write(record_rel, record)
        code, out = self.run_tool(write=True, fix_control_paths=False)
        self.assertIn("IDENTITY_DRIFT", out)
        self.assertIn("RECONCILE_FRONTIER", out)
        self.assertEqual(code, 1, "a frontier redefinition is never a silent success")
        self.assertEqual(
            self.read(record_rel)["capability_id"], "SOME_OTHER_CAPABILITY_V1",
            "changing the active target is a frontier redefinition, not a mirror repair",
        )

    # --- control-path currency ---------------------------------------------
    def test_stale_control_path_is_reported_then_advanced(self):
        pointer = self.read(POINTER)
        stale = "canonical/gates/GOAL_HIERARCHY_ACTION_GATE_V10.json"
        pointer["boot_requirements"]["goal_hierarchy_action_gate_path"] = stale
        # A non-boot mirror reference must not be left contradicting boot.
        pointer["current_frontier"]["goal_hierarchy_action_gate"] = stale
        self.write(POINTER, pointer)

        code, out = self.run_tool(write=False, fix_control_paths=False)
        self.assertIn("CONTROL_PATH_NOT_CURRENT", out)
        self.assertEqual(code, 1, "stale control paths must fail closed until advanced")
        self.assertEqual(
            self.read(POINTER)["boot_requirements"]["goal_hierarchy_action_gate_path"], stale,
            "reporting must not write",
        )

        code, out = self.run_tool(write=True, fix_control_paths=True)
        self.assertEqual(code, 0, out)
        repaired = self.read(POINTER)
        self.assertEqual(
            repaired["boot_requirements"]["goal_hierarchy_action_gate_path"],
            "canonical/gates/GOAL_HIERARCHY_ACTION_GATE_V11.json",
        )
        self.assertEqual(
            repaired["current_frontier"]["goal_hierarchy_action_gate"],
            "canonical/gates/GOAL_HIERARCHY_ACTION_GATE_V11.json",
            "mirror references must follow boot",
        )

    def test_missing_control_path_file_is_reported(self):
        pointer = self.read(POINTER)
        pointer["boot_requirements"]["white_box_capability_capsule_schema_path"] = (
            "canonical/governance/DOES_NOT_EXIST_V1.json"
        )
        self.write(POINTER, pointer)
        code, out = self.run_tool(write=True, fix_control_paths=True)
        self.assertIn("CONTROL_PATH_FILE_MISSING", out)

    # --- fail-closed refusals ----------------------------------------------
    def test_refuses_when_authority_blocker_is_missing(self):
        hierarchy = self.read(HIERARCHY)
        hierarchy["current_parent_blocker"] = ""
        self.write(HIERARCHY, hierarchy)
        code, out = self.run_tool(write=True, fix_control_paths=False)
        self.assertEqual(code, 2)
        self.assertIn("REFUSED", out)

    def test_refuses_when_target_record_is_absent(self):
        (self.root / f"canonical/capabilities/frontier/{self.target}.json").unlink()
        code, out = self.run_tool(write=True, fix_control_paths=False)
        self.assertEqual(code, 2)
        self.assertIn("REFUSED", out)

    def test_refuses_when_identity_mirror_file_is_absent(self):
        (self.root / QUEUE).unlink()
        code, out = self.run_tool(write=True, fix_control_paths=False)
        self.assertEqual(code, 2)
        self.assertIn("REFUSED", out)


if __name__ == "__main__":
    unittest.main()
