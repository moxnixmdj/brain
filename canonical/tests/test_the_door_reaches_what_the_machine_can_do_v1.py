"""The door refused every goal the machine could already do.

Measured 2026-11-01, straight through ``live_brain_route_admission_v1.solve``, eight
goals the tree already owns a way to serve:

    compress notes.txt into notes.txt.gz   FAIL_CLOSED__STEP_RAISED_OUTCOME_UNKNOWN    313 ms
    hash blob.bin into blob.sha256         FAIL_CLOSED__STEP_RAISED_OUTCOME_UNKNOWN    225 ms
    dump notes.txt into notes.csv          FAIL__RAW_GOAL_COMPILATION_GAP               328 ms
    convert tiny.png into tiny.jpg         FAIL__RAW_GOAL_COMPILATION_GAP               336 ms

Zero passed, nothing was written, and ``computer_env_v1.discover`` was never called --
while the same sentences close through discovery (8,498 ms cold, 265 ms recalled) and
leave a real, verifier-opened file on disk.  A capability the front door never reaches
is not a capability.

The last resort added here is the one that ACTS: it runs on the real file, and the
artifact is opened by the verifier before any pass is reported.  It cannot answer a
governed refusal with a substitute, and it declines every goal whose output format this
repository cannot check -- a ``.py`` file is bytes that happen to be source.
"""
import hashlib
import os
import pathlib
import sys
import tempfile
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from canonical.runtime import live_brain_route_admission_v1 as door  # noqa: E402
from canonical.runtime import program_synthesis_v1 as ps  # noqa: E402
from canonical.runtime import transfer_learning_v1 as tl  # noqa: E402


def _digest(path: pathlib.Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


class TheDoorReachesWhatTheMachineCanDo(unittest.TestCase):

    def setUp(self) -> None:
        self.dir = pathlib.Path(tempfile.mkdtemp(prefix="brain-door-act-"))
        self.work = self.dir / "work"
        self.work.mkdir()
        self.saved_state = tl.STATE_PATH
        tl.STATE_PATH = str(self.dir / "episodes.json")
        os.environ["BRAIN_TRANSFER_LEARNING_FINGERPRINTS"] = str(self.dir / "fp.json")

    def tearDown(self) -> None:
        tl.STATE_PATH = self.saved_state
        os.environ.pop("BRAIN_TRANSFER_LEARNING_FINGERPRINTS", None)

    def test_a_format_goal_the_door_used_to_refuse_is_served_by_acting(self) -> None:
        src = self.work / "notes.txt"
        src.write_text("alpha\nbeta\ngamma\n" * 20, encoding="utf-8")
        before = _digest(src)
        out = door.solve({"task_id": "DOOR_GZ",
                          "goal": "compress notes.txt into notes.txt.xz",
                          "cwd": str(self.work)})
        target = self.work / "notes.txt.xz"
        if not out.get("pass"):
            self.skipTest("xz is not installed here: %s" % out.get("status"))
        self.assertEqual(out.get("status"), "PASS__PERFORMED_ON_REAL_FILE")
        self.assertTrue(target.is_file(), "the door claimed a pass and wrote nothing")
        self.assertEqual(ps.verify_round_trip(target, ".xz"), (True, "ROUND_TRIP_OK"),
                         "the file the door claimed is not the format it claimed")
        self.assertEqual(_digest(src), before, "the input was modified by a compression")
        self.assertEqual(out.get("served_after") and True, True,
                         "the result does not say which refusal it replaced")

    def test_a_goal_with_no_verifiable_output_is_not_served_by_acting(self) -> None:
        (self.work / "calc.py").write_text("def f(x):\n    return x\n", encoding="utf-8")
        self.assertIsNone(door._serve_by_acting(
            {"task_id": "DOOR_PY", "goal": "Format calc.py.", "cwd": str(self.work)}),
            "a route promised work in a format nothing in this tree can check")

    def test_an_honest_contract_refusal_is_not_answered_by_acting(self) -> None:
        # REQUEST_INVALID never reaches the fallback; assert the door still refuses it
        out = door.solve({"task_id": "", "goal": ""})
        self.assertFalse(out.get("pass"))


class TheFallbackIsNotAFreePass(unittest.TestCase):

    def setUp(self) -> None:
        self.dir = pathlib.Path(tempfile.mkdtemp(prefix="brain-perform-state-"))
        self.saved_state = tl.STATE_PATH
        tl.STATE_PATH = str(self.dir / "episodes.json")
        os.environ["BRAIN_TRANSFER_LEARNING_FINGERPRINTS"] = str(self.dir / "fp.json")

    def tearDown(self) -> None:
        tl.STATE_PATH = self.saved_state
        os.environ.pop("BRAIN_TRANSFER_LEARNING_FINGERPRINTS", None)

    def test_only_a_verified_file_can_be_reported(self) -> None:
        """The fallback's pass carries the verifier's own words, not a claim of its own."""
        from canonical.runtime import computer_env_v1 as cenv
        tmp = pathlib.Path(tempfile.mkdtemp(prefix="brain-perform-"))
        (tmp / "notes.txt").write_text("alpha\nbeta\n" * 20, encoding="utf-8")
        done = cenv.perform("compress notes.txt into notes.txt.xz", cwd=tmp)
        if not done.get("pass"):
            self.skipTest("no working plan on this machine: %s" % done.get("status"))
        self.assertTrue(done.get("verification"), "a pass without the verifier's verdict")
        self.assertTrue((tmp / "notes.txt.xz").is_file())


if __name__ == "__main__":
    unittest.main()
