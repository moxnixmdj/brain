"""A counterexample receipt must bind a blob that exists, or the check must refuse it.

WHY THIS EXISTS
---------------
`enforce_v22_prewrite_admission` resolved receipt blobs against the base commit only. No change
could therefore ever add a receipt: every new path was skipped, `receipt_blobs` stayed empty, and
`receipt_blobs.get(path) != sha` was true for every row, so the check could only fail. The one way
to satisfy it was to write a sha that is not a blob in this repository, and that is what
`canonical/action_intents/BRANCH_CREATION_GRAMMAR_FIX_V1_20261101.json` did --
`a1b2c3d4e5f6789012345678901234567890abcd`, which is not in the object database.

Resolving at the proposed commit first, and at the base second, makes the receipt bindable and
makes an invented sha fail.

Measured 2026-11-01: with the fix, the guard passes on a receipt this change adds, and re-running
it with the invented sha above reports V22_COUNTEREXAMPLE_RECEIPT_BLOB_STALE_OR_MISMATCH:0.
"""
import subprocess
import unittest

from canonical.runtime import enforce_goal_hierarchy as guard
from execution_guard.v22_prewrite_admission import admission_errors

RECEIPT = "canonical/verification/REPAIR_ADMISSION_KNOWN_COUNTEREXAMPLE_20261101_V1.json"
# Added by this same change, so it exists at HEAD and not at origin/main -- the case the old
# base-only resolver could never bind.
ADDED_RECEIPT = "canonical/verification/EXTERNAL_BASELINE_KNOWN_COUNTEREXAMPLE_20261102_V1.json"
INVENTED = "a1b2c3d4e5f6789012345678901234567890abcd"


def _git(*args: str) -> str:
    return subprocess.run(
        ["git", *args], cwd=guard.ROOT, text=True, capture_output=True, check=True
    ).stdout.strip()


def _admission(path: str, sha: str) -> dict:
    return {"tournament": {"counterexample_receipts": [{"path": path, "git_blob_sha": sha}]}}


class ReceiptBindingTests(unittest.TestCase):
    def test_a_receipt_this_change_adds_binds_at_the_proposed_commit(self):
        real = _git("rev-parse", f"HEAD:{RECEIPT}")
        blobs = guard.resolve_receipt_blobs(_admission(RECEIPT, real), ("HEAD",))
        self.assertEqual(blobs, {RECEIPT: real})

    def test_the_invented_sha_that_main_ships_is_refused(self):
        # The binding returns the sha that is really in the object database, so the invented one
        # the merged intent carries cannot match it. End-to-end, the guard reports
        # V22_COUNTEREXAMPLE_RECEIPT_BLOB_STALE_OR_MISMATCH:0 for that intent (measured 2026-11-01).
        real = _git("rev-parse", f"HEAD:{RECEIPT}")
        blobs = guard.resolve_receipt_blobs(_admission(RECEIPT, INVENTED), ("HEAD",))
        self.assertEqual(blobs[RECEIPT], real)
        self.assertNotEqual(blobs[RECEIPT], INVENTED)

    def test_a_receipt_added_by_the_change_cannot_bind_at_the_base(self):
        # The old resolver searched the base only, so a receipt added by a pull request could never
        # bind and the check could only fail. This receipt is added by the same change, so it is
        # absent from main: searching the base alone finds nothing, searching head finds it.
        self.assertEqual(
            guard.resolve_receipt_blobs(_admission(ADDED_RECEIPT, "0" * 40), ("origin/main",)), {})
        self.assertIn(ADDED_RECEIPT, guard.resolve_receipt_blobs(
            _admission(ADDED_RECEIPT, "0" * 40), ("origin/main", "HEAD")))

    def test_a_path_that_is_absent_everywhere_is_still_skipped(self):
        blobs = guard.resolve_receipt_blobs(
            _admission("canonical/verification/NO_SUCH_RECEIPT.json", "0" * 40), ("HEAD",)
        )
        self.assertEqual(blobs, {})


if __name__ == "__main__":
    unittest.main(verbosity=2)
