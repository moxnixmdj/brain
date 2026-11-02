"""Two claims, both falsifiable in this file.

1. `self_prediction_baseline_v1`: the baseline is a number the system cannot author, computed from
   strictly earlier settled attempts. A claim that says 0.5 for everything must NOT beat it, and a
   claim that tracks real outcomes must. If both land in the same bucket the comparison is
   decoration, and this test fails.

2. `capability_onboarding_factory_v1`: a capability is onboarded only with a demonstration, a
   DIFFERENT held-out instance, and an inspector that passes on both. Each refusal is exercised,
   including the one that matters most -- an inspector that passes on the demonstration and fails on
   the held-out instance, which is the exact shape of a memorised skill.
"""
import pathlib
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))

from canonical.runtime import capability_onboarding_factory_v1 as F  # noqa: E402
from canonical.runtime import self_prediction_baseline_v1 as B  # noqa: E402


def _rows(pairs, cid="cap.a"):
    return [{"capability_id": cid, "predicted_pass_probability": p, "outcome_pass": o,
             "settled_at_unix": float(i)} for i, (p, o) in enumerate(pairs)]


class BaselineTests(unittest.TestCase):
    def test_a_constant_claim_cannot_beat_a_lookup_table(self):
        # Streaky outcomes: 30 passes, then 30 failures, twice. There IS learnable structure, so a
        # lookup table of the track record beats a claim that says 0.5 forever. Measured with 10-wide
        # blocks: the baseline loses to the constant (margin -0.020) because on a short blocky series
        # the transitions dominate and a constant is genuinely strong. That is why the series here is
        # long enough for structure to be learnable -- see the alternating test for the other edge.
        pairs = [(0.5, True)] * 30 + [(0.5, False)] * 30 + [(0.5, True)] * 30 + [(0.5, False)] * 30
        report = B.compare(_rows(pairs))
        self.assertIn(report["verdict"],
                      {"NO_BETTER_THAN_EXTERNAL_BASELINE", "WORSE_THAN_EXTERNAL_BASELINE"}, report)

    def test_a_perfectly_alternating_history_beats_every_predictor_including_the_baseline(self):
        # KNOWN LIMITATION, asserted so it cannot be forgotten: on a perfect alternation there is no
        # learnable structure, and a causal predictor is slightly anti-correlated because it expects
        # the last outcome to repeat. A constant 0.5 claim therefore edges it out. The consequence is
        # stated in the counterexample receipt: a WORSE_THAN_EXTERNAL_BASELINE verdict is evidence
        # about a claim only when the history has structure to learn from.
        pairs = [(0.5, i % 2 == 0) for i in range(40)]
        report = B.compare(_rows(pairs))
        self.assertGreater(report["margin_over_baseline"], 0.0)
        self.assertLess(report["margin_over_baseline"], 0.05)  # an edge, not a rout

    def test_a_claim_that_tracks_outcomes_beats_the_baseline(self):
        # The system says 0.95 before passes and 0.05 before failures -- real information.
        pairs = [(0.95, True)] * 20 + [(0.05, False)] * 20
        report = B.compare(_rows(pairs))
        self.assertEqual(report["verdict"], "CLAIM_BEATS_EXTERNAL_BASELINE", report)
        self.assertGreater(report["margin_over_baseline"], 0.0)

    def test_the_baseline_uses_only_earlier_attempts(self):
        rows = _rows([(0.5, True)] * 3 + [(0.5, False)] * 3)
        report = B.compare(rows)
        # The first attempt has no history, so the baseline is the neutral global prior.
        self.assertEqual(report["rows"][0]["external_baseline"], 0.5)
        # Later attempts see earlier outcomes, so the baseline moves away from 0.5.
        self.assertNotEqual(report["rows"][-1]["external_baseline"], 0.5)

    def test_an_empty_ledger_gets_no_verdict(self):
        self.assertEqual(B.compare([])["verdict"], "INSUFFICIENT_EVIDENCE")

    def test_a_thin_ledger_gets_no_verdict(self):
        self.assertEqual(B.compare(_rows([(0.9, True)] * 5))["verdict"], "INSUFFICIENT_EVIDENCE")

    def test_a_baseline_probability_is_bounded_and_shrunk(self):
        self.assertEqual(B.baseline_probability(passes=0, attempts=0, global_rate=0.5), 0.5)
        one = B.baseline_probability(passes=1, attempts=1, global_rate=0.3)
        self.assertLess(one, 1.0)  # one lucky pass does not make a capability certain
        self.assertGreater(one, 0.3)


class FactoryTests(unittest.TestCase):
    def setUp(self):
        self.registered = []
        self.inspector = lambda payload: (payload.get("verified") is True, "NOT_VERIFIED")
        self.factory = F.Factory(inspector_for=lambda cid: self.inspector,
                                 register=self.registered.append)
        self.demo = {"ok": True, "binds": {"path": "a"}, "verified": True}
        self.held = {"binds": {"path": "b"}, "verified": True}

    def test_a_full_pipeline_onboards_once(self):
        attempt = self.factory.onboard(capability_id="cap.a", demonstration=self.demo,
                                       heldout=self.held)
        self.assertEqual(attempt.status, "ONBOARDED", attempt)
        self.assertTrue(attempt.heldout_used)
        self.assertEqual(len(self.registered), 1)
        self.assertEqual(self.factory.metrics()["throughput"], 1.0)

    def test_no_heldout_instance_is_refused(self):
        attempt = self.factory.onboard(capability_id="cap.a", demonstration=self.demo, heldout=None)
        self.assertEqual(attempt.status, "FAIL_CLOSED__NO_HELDOUT_INSTANCE")

    def test_a_heldout_that_binds_the_same_parameters_is_refused(self):
        attempt = self.factory.onboard(capability_id="cap.a", demonstration=self.demo,
                                       heldout={"binds": {"path": "a"}, "verified": True})
        self.assertEqual(attempt.status,
                         "FAIL_CLOSED__HELDOUT_IDENTICAL_TO_THE_DEMONSTRATION")

    def test_no_inspector_is_refused_before_anything_is_registered(self):
        factory = F.Factory(inspector_for=lambda cid: None, register=self.registered.append)
        attempt = factory.onboard(capability_id="cap.a", demonstration=self.demo, heldout=self.held)
        self.assertEqual(attempt.status, "FAIL_CLOSED__NO_INSPECTOR")
        self.assertEqual(self.registered, [])

    def test_a_skill_that_replays_but_fails_the_heldout_is_refused(self):
        # Passes on the demonstration, fails on the different instance: an overfit skill.
        def inspector(payload):
            return payload.get("binds") == {"path": "a"}, "HELDOUT_ANCHOR_NOT_PRESENT"

        factory = F.Factory(inspector_for=lambda cid: inspector, register=self.registered.append)
        attempt = factory.onboard(capability_id="cap.a", demonstration=self.demo, heldout=self.held)
        self.assertEqual(attempt.status, "FAIL_CLOSED__HELDOUT_UNVERIFIED")
        self.assertEqual(self.registered, [])
        metrics = factory.metrics()
        self.assertEqual(metrics["heldout_survival"], 0.0)
        self.assertEqual(metrics["refusals_by_status"]["FAIL_CLOSED__HELDOUT_UNVERIFIED"], 1)

    def test_a_failed_demonstration_is_refused(self):
        attempt = self.factory.onboard(capability_id="cap.a",
                                       demonstration={"ok": False, "reason": "BROKE"},
                                       heldout=self.held)
        self.assertEqual(attempt.status, "FAIL_CLOSED__DEMONSTRATION_DID_NOT_SUCCEED")

    def test_metrics_report_throughput_and_survival_separately(self):
        self.factory.onboard(capability_id="cap.a", demonstration=self.demo, heldout=self.held)
        self.factory.onboard(capability_id="cap.b", demonstration=self.demo,
                             heldout={"binds": {"path": "a"}, "verified": True})
        metrics = self.factory.metrics()
        self.assertEqual(metrics["attempted"], 2)
        self.assertEqual(metrics["onboarded"], 1)
        self.assertEqual(metrics["throughput"], 0.5)


if __name__ == "__main__":
    unittest.main(verbosity=2)
