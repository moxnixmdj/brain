"""Synthetic contract tests for the fail-closed Jev decision adapter.

These tests never load project evaluation cases or call a model endpoint.
"""

from __future__ import annotations

import json
import sys
import unittest
import urllib.error
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from canonical.runtime import cognitive_decision_kernel as kernel  # noqa: E402


class _Response:
    def __init__(self, payload):
        self.payload = json.dumps(payload).encode("utf-8")

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, traceback):
        return False

    def read(self):
        return self.payload


def _payload(probability):
    return {"answers": {"decision": {"noul": probability}}}


class CognitiveDecisionKernelTests(unittest.TestCase):
    def decide_with_payload(self, payload):
        with patch.object(kernel.urllib.request, "urlopen", return_value=_Response(payload)):
            return kernel.decide(
                endpoint="https://unused.invalid/v1/systemone",
                model="synthetic-canary",
                state={"source": "synthetic"},
                question="Synthetic canary only",
                threshold=0.80,
            )

    def test_confident_positive_at_threshold_is_admitted(self):
        result = self.decide_with_payload(_payload(0.80))
        self.assertEqual((result.status, result.decision), ("ADMIT", True))

    def test_confident_negative_at_threshold_is_admitted_as_false(self):
        result = self.decide_with_payload(_payload(0.20))
        self.assertEqual((result.status, result.decision), ("ADMIT", False))

    def test_below_threshold_escalates_without_decision(self):
        result = self.decide_with_payload(_payload(0.79))
        self.assertEqual((result.status, result.decision), ("ESCALATE", None))
        self.assertEqual(result.reason, "CONFIDENCE_BELOW_FAIL_CLOSED_THRESHOLD")

    def test_boolean_is_not_coerced_to_probability_or_admitted(self):
        result = self.decide_with_payload(_payload(True))
        self.assertEqual((result.status, result.decision), ("ESCALATE", None))
        self.assertEqual(result.reason, "ENDPOINT_OR_RESPONSE_FAILURE_FAIL_CLOSED")

    def test_non_numeric_and_out_of_range_values_escalate(self):
        for probability in ("0.99", -0.01, 1.01, float("nan")):
            with self.subTest(probability=probability):
                result = self.decide_with_payload(_payload(probability))
                self.assertEqual((result.status, result.decision), ("ESCALATE", None))

    def test_unavailable_endpoint_escalates(self):
        with patch.object(
            kernel.urllib.request,
            "urlopen",
            side_effect=urllib.error.URLError("synthetic offline endpoint"),
        ):
            result = kernel.decide(
                endpoint="https://unused.invalid/v1/systemone",
                model="synthetic-canary",
                state={},
                question="Synthetic canary only",
                threshold=0.80,
            )
        self.assertEqual((result.status, result.decision), ("ESCALATE", None))
        self.assertEqual(result.reason, "ENDPOINT_OR_RESPONSE_FAILURE_FAIL_CLOSED")


if __name__ == "__main__":
    unittest.main()
