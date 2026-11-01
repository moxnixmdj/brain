"""A destination the rule could not see: a source file nobody named as a source.

The write-authority rule refuses a write when the destination IS a source the action
also handed the capability.  Measured on main ``f4e6cdb``, 2026-11-01, that leaves one
shape completely open -- a destination that is a source file but was never bound as
one, which is exactly what the binder produces when a sentence names a file and the row
declares both ``output_path`` and ``source_root``:

    run_adapter_locally("software.hardcore.kernel.orchestrate.v1",
                        {"args": {"output_path": "…/u.py"}})
      -> RAN, and u.py (51 bytes of Python) is now 1,134 bytes of JSON report

The pre-check cannot see it, because no source slot was filled.  The bytes can.

Parsing is not enough, and that was measured too: the report the orchestrator writes is
``{"capability_id": …}``, which ``compile()`` accepts happily as a dict literal.  A
module has definitions, imports, assignments or calls at top level; a report is one
bare expression.  So the destination is watched across the run and, if a module became
a non-module, the original bytes are put back and the call fails.
"""
import pathlib
import sys
import tempfile
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from canonical.runtime import write_authority_v1 as wa  # noqa: E402

SOURCE = "import os\nimport sys\n\ndef f():\n    return sys.argv\n"
REPORT = '{"capability_id":"software.hardcore.kernel.orchestrate.v1","verified":true}'


class ADestinationNobodyNamedAsASource(unittest.TestCase):

    def setUp(self) -> None:
        self.root = pathlib.Path(tempfile.mkdtemp(prefix="brain-unnamed-source-"))
        (self.root / "u.py").write_text(SOURCE, encoding="utf-8")

    # -- the watch -------------------------------------------------------- #

    def test_a_python_destination_is_watched(self) -> None:
        watched = wa.watch_destinations(self.root, {"output_path": "u.py"})
        self.assertIn(str((self.root / "u.py").resolve()), watched)

    def test_a_report_that_parses_as_a_dict_is_still_not_a_module(self) -> None:
        self.assertFalse(wa._parses_as_a_module(REPORT.encode()),
                         "a bare JSON object parses as a dict literal and was called a module")
        self.assertTrue(wa._parses_as_a_module(SOURCE.encode()))

    def test_a_source_replaced_by_a_report_is_restored_and_refused(self) -> None:
        watched = wa.watch_destinations(self.root, {"output_path": "u.py"})
        (self.root / "u.py").write_text(REPORT, encoding="utf-8")
        with self.assertRaises(wa.WriteAuthorityViolation) as caught:
            wa.restore_if_a_source_was_replaced(self.root, watched)
        self.assertIn("OUTPUT_REPLACED_A_SOURCE_WITH_NON_SOURCE", str(caught.exception))
        self.assertEqual((self.root / "u.py").read_text(encoding="utf-8"), SOURCE,
                         "the file was reported about but not put back")

    # -- and it does not get in the way of real edits --------------------- #

    def test_an_edit_that_leaves_a_module_is_allowed(self) -> None:
        watched = wa.watch_destinations(self.root, {"output_path": "u.py"})
        better = "import sys\n\n\ndef f():\n    return sys.argv\n"
        (self.root / "u.py").write_text(better, encoding="utf-8")
        wa.restore_if_a_source_was_replaced(self.root, watched)   # must not raise
        self.assertEqual((self.root / "u.py").read_text(encoding="utf-8"), better)

    def test_a_new_file_is_not_watched_and_cannot_be_restored_over(self) -> None:
        watched = wa.watch_destinations(self.root, {"output_path": "brand_new.py"})
        self.assertEqual(watched, {})


if __name__ == "__main__":
    unittest.main()
