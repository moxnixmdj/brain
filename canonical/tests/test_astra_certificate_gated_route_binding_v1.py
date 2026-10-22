import hashlib
from pathlib import Path
import unittest

from canonical.runtime import astra_runtime as astra

ROOT = Path(__file__).resolve().parents[2]
ROUTE_PATH = "canonical/runtime/certificate_gated_selected_route_router_v1.py"
ADEQUACY_PATH = "canonical/governance/K6_POSITIVE_ADEQUACY_COVER_CERTIFICATE_THEOREM_20261006_V1.json"
ADMISSION_PATH = "canonical/governance/CERTIFICATE_GATED_SELECTED_ROUTE_ROUTER_SOUNDNESS_REDUCTION_20261007_V1.json"


def _git_blob_sha(rel):
    raw = (ROOT / rel).read_bytes()
    return hashlib.sha1(b"blob " + str(len(raw)).encode("ascii") + b"\x00" + raw).hexdigest()


def _shas():
    return _git_blob_sha(ROUTE_PATH), _git_blob_sha(ADEQUACY_PATH), _git_blob_sha(ADMISSION_PATH)


def _bindings():
    route_sha, adequacy_sha, admission_sha = _shas()
    return {
        route_sha: ROUTE_PATH,
        adequacy_sha: ADEQUACY_PATH,
        admission_sha: ADMISSION_PATH,
    }


def _receipt(*, admitted=True, context="ctx", route="route-a", cell="cell-a",
             route_sha=None, adequacy_sha=None, admission_sha=None):
    default_route, default_adequacy, default_admission = _shas()
    return {
        "context_digest": context,
        "cell_id": cell,
        "route_id": route,
        "route_blob_sha": route_sha or default_route,
        "adequacy_certificate_blob_sha": adequacy_sha or default_adequacy,
        "admission_certificate_blob_sha": admission_sha or default_admission,
        "admitted": admitted,
    }


class CertificateGatedAstraBindingTests(unittest.TestCase):
    def test_astra_step_selects_only_matching_positive_content_bound_certificate(self):
        step = {
            "id": "route-select",
            "adapter": "certificate_gated_route_select",
            "actual_context_digest": "ctx",
            "content_address_bindings": _bindings(),
            "admission_receipts": [
                # The negative receipt must differ in identity, not just in
                # `admitted`. The router's identity tuple deliberately excludes
                # `admitted`, because the same certified route in the same
                # context cannot be both admitted and not admitted -- so a pair
                # that differs only in that flag is a contradiction and the
                # router fails closed on it. This fixture used to supply exactly
                # that, and the test errored with DUPLICATE_RECEIPT instead of
                # testing selection.
                _receipt(admitted=False, route="route-c", cell="cell-c"),
                _receipt(route="route-b", cell="cell-b"),
                _receipt(route="route-a", cell="cell-a"),
            ],
        }
        out = astra.execute_step(step, mission={})
        self.assertEqual(out["schema"], "PROJECT_BRAIN_CERTIFICATE_GATED_DEPLOYED_ROUTE_SELECTION_V1")
        self.assertEqual(out["route_id"], "route-a")
        self.assertTrue(out["admitted"])
        self.assertTrue(out["content_address_binding_verified"])
        self.assertEqual(out["route_path"], ROUTE_PATH)
        self.assertEqual(out["adequacy_certificate_path"], ADEQUACY_PATH)
        self.assertEqual(out["admission_certificate_path"], ADMISSION_PATH)
        self.assertTrue(out["selection_only"])
        self.assertFalse(out["downstream_route_execution_performed"])
        self.assertFalse(out["execution_authority"])
        self.assertFalse(out["promotion_authority"])
        self.assertEqual(out["terminal_results_observed"], 0)
        self.assertEqual(out["terminal_credit_delta"], 0)

    def test_astra_step_rejects_contradictory_admission_for_one_certified_route(self):
        """Two receipts for one route that disagree about admission must not be
        resolved by picking one.

        The router's identity tuple excludes ``admitted`` on purpose: the same
        certified route, in the same context, bound to the same three blobs,
        cannot be both admitted and not admitted. That is a contradiction in the
        evidence, not a choice to be made, so it fails closed. This was only
        exercised by accident before -- a stale fixture tripped it while trying
        to test selection -- so nothing pinned the behaviour.
        """
        step = {
            "id": "route-select",
            "adapter": "certificate_gated_route_select",
            "actual_context_digest": "ctx",
            "content_address_bindings": _bindings(),
            "admission_receipts": [
                _receipt(admitted=False),
                _receipt(admitted=True),
            ],
        }
        with self.assertRaisesRegex(astra.Blocker, "DUPLICATE_RECEIPT"):
            astra.execute_step(step, mission={})

    def test_identical_receipts_repeated_are_still_a_duplicate(self):
        """Even two receipts that agree are a duplicate identity, so the guard
        is about identity and not about disagreement."""
        step = {
            "id": "route-select",
            "adapter": "certificate_gated_route_select",
            "actual_context_digest": "ctx",
            "content_address_bindings": _bindings(),
            "admission_receipts": [_receipt(), _receipt()],
        }
        with self.assertRaisesRegex(astra.Blocker, "DUPLICATE_RECEIPT"):
            astra.execute_step(step, mission={})

    def test_astra_step_fails_closed_for_uncovered_context(self):
        step = {
            "id": "route-select",
            "adapter": "certificate_gated_route_select",
            "actual_context_digest": "uncovered",
            "content_address_bindings": _bindings(),
            "admission_receipts": [_receipt(context="ctx")],
        }
        with self.assertRaisesRegex(astra.Blocker, "NO_CERTIFIED_ROUTE_FOR_ACTUAL_CONTEXT"):
            astra.execute_step(step, mission={})

    def test_astra_step_rejects_non_boolean_admission_before_router(self):
        row = _receipt()
        row["admitted"] = "false"
        step = {
            "id": "route-select",
            "adapter": "certificate_gated_route_select",
            "actual_context_digest": "ctx",
            "content_address_bindings": _bindings(),
            "admission_receipts": [row],
        }
        with self.assertRaisesRegex(astra.Blocker, "ADMISSION_NOT_LITERAL_BOOL"):
            astra.execute_step(step, mission={})

    def test_astra_step_rejects_missing_content_address_bindings(self):
        step = {
            "id": "route-select",
            "adapter": "certificate_gated_route_select",
            "actual_context_digest": "ctx",
            "admission_receipts": [_receipt()],
        }
        with self.assertRaisesRegex(astra.Blocker, "CONTENT_ADDRESS_BINDINGS_REQUIRED"):
            astra.execute_step(step, mission={})

    def test_astra_step_rejects_forged_git_blob_binding(self):
        _, adequacy_sha, admission_sha = _shas()
        forged = "a" * 40
        bindings = {
            forged: ROUTE_PATH,
            adequacy_sha: ADEQUACY_PATH,
            admission_sha: ADMISSION_PATH,
        }
        step = {
            "id": "route-select",
            "adapter": "certificate_gated_route_select",
            "actual_context_digest": "ctx",
            "content_address_bindings": bindings,
            "admission_receipts": [_receipt(route_sha=forged)],
        }
        with self.assertRaisesRegex(astra.Blocker, "GIT_BLOB_SHA_MISMATCH"):
            astra.execute_step(step, mission={})


if __name__ == "__main__":
    unittest.main()
