import unittest

from canonical.runtime import astra_runtime as astra


def _receipt(*, admitted=True, context="ctx", route="route-a", cell="cell-a", a="1", q="2", r="3"):
    return {
        "context_digest": context,
        "cell_id": cell,
        "route_id": route,
        "route_blob_sha": r * 40,
        "adequacy_certificate_blob_sha": q * 40,
        "admission_certificate_blob_sha": a * 40,
        "admitted": admitted,
    }


class CertificateGatedAstraBindingTests(unittest.TestCase):
    def test_astra_step_selects_only_matching_positive_certificate(self):
        step = {
            "id": "route-select",
            "adapter": "certificate_gated_route_select",
            "actual_context_digest": "ctx",
            "admission_receipts": [
                _receipt(admitted=False, a="0"),
                _receipt(route="route-b", cell="cell-b", a="4", q="5", r="6"),
                _receipt(route="route-a", cell="cell-a", a="1", q="2", r="3"),
            ],
        }
        out = astra.execute_step(step, mission={})
        self.assertEqual(out["schema"], "PROJECT_BRAIN_CERTIFICATE_GATED_DEPLOYED_ROUTE_SELECTION_V1")
        self.assertEqual(out["route_id"], "route-a")
        self.assertTrue(out["admitted"])
        self.assertTrue(out["selection_only"])
        self.assertFalse(out["downstream_route_execution_performed"])
        self.assertFalse(out["execution_authority"])
        self.assertFalse(out["promotion_authority"])
        self.assertEqual(out["terminal_results_observed"], 0)
        self.assertEqual(out["terminal_credit_delta"], 0)

    def test_astra_step_fails_closed_for_uncovered_context(self):
        step = {
            "id": "route-select",
            "adapter": "certificate_gated_route_select",
            "actual_context_digest": "uncovered",
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
            "admission_receipts": [row],
        }
        with self.assertRaisesRegex(astra.Blocker, "ADMISSION_NOT_LITERAL_BOOL"):
            astra.execute_step(step, mission={})


if __name__ == "__main__":
    unittest.main()
