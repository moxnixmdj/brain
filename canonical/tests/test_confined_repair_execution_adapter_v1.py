"""Do not enable repair through the current non-isolating confinement carrier."""
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from canonical.runtime import astra_runtime
from canonical.runtime import computer_execution_boundary_v1 as boundary
from canonical.runtime import confined_dispatch_v1 as confined
from canonical.runtime import verified_bound_capability_execution_adapter_v1 as bound


class RepairFrontDoorSafetyTests(unittest.TestCase):
    def test_repair_still_refuses_even_with_independent_evidence(self):
        # Isolate the post-inspection branch; this mock is not evidence of admission.
        with mock.patch.object(bound, "inspect", return_value={"entry": {}}) as inspect, \
             mock.patch.object(confined, "run_confined_capability") as dispatch, \
             mock.patch.object(bound, "_receipt_backed_execution") as receipt_route, \
             mock.patch.object(astra_runtime, "_invoke_bound_capability") as host:
            result = bound.execute(boundary.REPAIR_CAPABILITY_ID, inputs={"output_path": "report.json"})
        inspect.assert_called_once_with(boundary.REPAIR_CAPABILITY_ID)
        self.assertEqual(result["status"], boundary.STATUS)
        self.assertFalse(result["pass"])
        self.assertFalse(result["executed"])
        self.assertFalse(result["terminal_authority"])
        self.assertEqual(result["capability_credit_delta"], 0)
        self.assertEqual(result["ownership_credit_delta"], 0)
        dispatch.assert_not_called()
        receipt_route.assert_not_called()
        host.assert_not_called()

    def test_missing_independent_evidence_cannot_dispatch(self):
        with mock.patch.object(bound, "inspect", side_effect=bound.BoundExecutionError("evidence missing")), \
             mock.patch.object(confined, "run_confined_capability") as dispatch, \
             mock.patch.object(astra_runtime, "_invoke_bound_capability") as host:
            result = bound.execute(boundary.REPAIR_CAPABILITY_ID, inputs={"output_path": "report.json"})
        self.assertFalse(result["pass"])
        self.assertIn("evidence missing", result["reason"])
        dispatch.assert_not_called()
        host.assert_not_called()

    def test_existing_carrier_does_not_isolate_filesystem(self):
        # Characterization, not approval: a controlled sibling sentinel shows why
        # host_untouched cannot authorize untrusted repair. No real host files.
        from canonical.runtime import confinement_v1

        with tempfile.TemporaryDirectory(prefix="repair_isolation_probe_") as temp:
            root = Path(temp) / "repo"
            root.mkdir()
            subprocess.run(["git", "init", "-q", str(root)], check=True)
            (root / "seed.txt").write_text("seed\n", encoding="utf-8")
            subprocess.run(["git", "-C", str(root), "add", "seed.txt"], check=True)
            subprocess.run(["git", "-C", str(root), "-c", "user.name=Test", "-c",
                            "user.email=test@example.invalid", "commit", "-qm", "seed"], check=True)
            sentinel = Path(temp) / "outside"
            code = ("from pathlib import Path; "
                    f"Path({str(sentinel)!r}).write_text('sentinel'); "
                    "Path('effect.txt').write_text('effect')")
            result = confinement_v1.run_confined(
                root, [sys.executable, "-c", code], budget_s=10,
                declared_effects=["effect.txt"])
            self.assertEqual(sentinel.read_text(encoding="utf-8"), "sentinel")
            self.assertTrue(result["host_untouched"])
            self.assertTrue(result["verified"])


if __name__ == "__main__":
    unittest.main()
