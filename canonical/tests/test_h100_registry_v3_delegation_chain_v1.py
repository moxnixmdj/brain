"""V3 was the broken link in the H100 verified-capability delegation chain.

``v1`` defined ``resolve_verified_capability``, ``v2`` defined it and delegated
to ``v1`` -- and ``v3`` never defined it at all, while ``v4`` through ``v8`` each
delegated down to ``v3.resolve_verified_capability``. Every resolution above V3
therefore died with ``AttributeError`` on the last hop. Thirteen test modules
failed on that single missing function.

These tests pin the restored hop *and* the frozen routing contract that V3 is
the authorization point for, so the chain cannot silently break again and the
four verified patch-transfer families cannot be widened past what the precommit
authorizes.
"""
from __future__ import annotations

import json
import math
import unittest
from pathlib import Path
from unittest import mock

from canonical.runtime import h100_verified_capability_registry_v3 as v3

ROOT = Path(__file__).resolve().parents[2]
PRE = json.loads((ROOT / "canonical/governance/H100_GENERIC_PATCH_SEARCH_TRANSFER_PRECOMMIT_V1.json").read_text())
XS = [float(x) for x in PRE["x_population"]["training_x"]]


def rows(fn):
    return [{"x": x, "y": float(fn(x))} for x in XS]


class DelegationChainTests(unittest.TestCase):
    """The regression itself: no version above V3 may lose the resolver."""

    def test_every_version_in_the_chain_exposes_the_resolver(self):
        for n in range(1, 9):
            mod = __import__(
                f"canonical.runtime.h100_verified_capability_registry_v{n}",
                fromlist=["resolve_verified_capability"],
            )
            self.assertTrue(
                callable(getattr(mod, "resolve_verified_capability", None)),
                f"v{n} lost resolve_verified_capability; every version above it delegates here",
            )

    def test_each_version_resolves_without_delegating_into_a_hole(self):
        # v4..v8 all reach v3 on the last hop, which is where this used to raise.
        for n in range(1, 9):
            mod = __import__(
                f"canonical.runtime.h100_verified_capability_registry_v{n}",
                fromlist=["resolve_verified_capability"],
            )
            out = mod.resolve_verified_capability(
                rows(lambda x: -1.1 + 0.3 * x - 0.02 * x ** 5), target="y", input_name="x")
            self.assertIn(
                out.get("status"),
                {"LIBRARY_HIT__VERIFY_BEFORE_USE", "LIBRARY_MISS__RAW_SYNTHESIS_ALLOWED"},
                f"v{n} returned {out.get('status')!r} instead of a verdict",
            )
            # v1 predates the version stamp; every layer above it must name itself
            # so a caller can tell which registry produced the verdict.
            if n > 1:
                self.assertEqual(
                    out.get("registry_version"), n,
                    f"v{n} did not stamp its own registry_version",
                )

    def test_v3_answer_is_stamped_with_its_own_envelope(self):
        out = v3.resolve_verified_capability(
            rows(lambda x: -0.7 + 0.31 * x + 0.42 * x ** 3), target="y", input_name="x")
        self.assertEqual(out["schema"], v3.SCHEMA)
        self.assertEqual(out["registry_version"], 3)


class AuthorizedFamilyTests(unittest.TestCase):
    def _hit(self, fn, cid):
        out = v3.resolve_verified_capability(rows(fn), target="y", input_name="x")
        self.assertEqual(out["status"], "LIBRARY_HIT__VERIFY_BEFORE_USE", out)
        self.assertEqual(out["match"]["capability_id"], cid, out)
        self.assertEqual(out["raw_synthesis_attempts_before_hit"], 0)
        self.assertEqual(out["persistent_learned_bytes"], 0)
        self.assertEqual(out["external_learned_capability_calls"], 0)
        return out

    def test_four_verified_transfer_families_hit(self):
        self._hit(lambda x: -1.1 + 0.3 * x - 0.02 * x ** 5, "CAP_AFFINE_POWER5_V1")
        self._hit(lambda x: 0.8 - 0.1 * x - 0.6 * max(0.0, x + 0.8), "CAP_AFFINE_HINGE_V1")
        self._hit(lambda x: -0.2 - 0.03 * x + 0.9 * math.exp(-1.3 * x * x), "CAP_AFFINE_GAUSSIAN_V1")
        self._hit(lambda x: -0.5 + 0.15 * x - 0.7 * math.tanh(1.6 * x), "CAP_AFFINE_TANH_V1")

    def test_legacy_cubic_still_routes_through_v2_unchanged(self):
        out = self._hit(lambda x: -0.7 + 0.31 * x + 0.42 * x ** 3, "CAP_AFFINE_CUBIC_V1")
        # the V2 route is untouched; only the envelope is re-stamped
        self.assertEqual(out["match"]["capability_id"], "CAP_AFFINE_CUBIC_V1")

    def test_unverified_rational_grammar_still_routes_to_raw_search(self):
        # RATIONAL_1PX2 is not an authorized family and 1/(1+x^2) is not in the
        # span of {1, x, any authorized basis}, so this must stay a miss.
        out = v3.resolve_verified_capability(
            rows(lambda x: 0.2 + 0.1 * x + 0.7 / (1.0 + x * x)), target="y", input_name="x")
        self.assertEqual(out["status"], "LIBRARY_MISS__RAW_SYNTHESIS_ALLOWED", out)

    def test_abs_shaped_data_routes_through_the_authorized_hinge_not_a_new_family(self):
        # The precommit forbids compiling an ABS grammar, and none is compiled.
        # But |x| = 2*max(0, x) - x, so an absolute-value shape lies exactly in
        # the span of {1, x, max(0, x)} and the authorized HINGE family fits it
        # for real. Routing it through HINGE is correct; adding an ABS family to
        # get there would not be.
        out = v3.resolve_verified_capability(
            rows(lambda x: 0.4 + 0.2 * x + 1.3 * abs(x)), target="y", input_name="x")
        self.assertEqual(out["status"], "LIBRARY_HIT__VERIFY_BEFORE_USE", out)
        self.assertEqual(out["match"]["capability_id"], "CAP_AFFINE_HINGE_V1", out)
        self.assertEqual(out["match"]["family"], "HINGE")
        self.assertNotIn("ABS", out["match"]["family"])
        self.assertLessEqual(out["match"]["candidate"]["train_nrmse"], 1e-8)

    def test_only_the_authorized_power_is_routable(self):
        # shape_policy is FIXED_POWER_5, so the rest of the power grid is not
        # authorized even though the underlying search could fit it.
        out = v3.resolve_verified_capability(
            rows(lambda x: 0.5 - 0.2 * x + 0.11 * x ** 4), target="y", input_name="x")
        self.assertEqual(out["status"], "LIBRARY_MISS__RAW_SYNTHESIS_ALLOWED", out)
        for hit in v3._exact_family_matches(
                rows(lambda x: 0.5 - 0.2 * x + 0.11 * x ** 4),
                v3._authorized_transfer_families()[1], "y", "x", 1e-8):
            self.assertNotEqual(hit["capability_id"], "CAP_AFFINE_POWER5_V1")

    def test_every_authorized_family_comes_from_the_frozen_precommit(self):
        doc, families = v3._authorized_transfer_families()
        self.assertEqual(
            sorted(f["capability_id"] for f in families),
            sorted(a["capability_id"] for a in doc["additions"]),
        )
        self.assertEqual(len(families), 4)


class FailClosedTests(unittest.TestCase):
    def test_two_exact_families_fail_closed_instead_of_picking_one(self):
        doc, families = v3._authorized_transfer_families()
        fn = lambda x: -1.1 + 0.3 * x - 0.02 * x ** 5
        real = v3._exact_family_matches(rows(fn), families, "y", "x", 1e-8)
        self.assertEqual(len(real), 1, "expected exactly one exact family for the power-5 shape")

        # The routing decision under ambiguity is what this pins: given two
        # exact families, resolve must refuse rather than take the first one the
        # grid reached.
        doubled = [dict(real[0]), dict(real[0], capability_id="CAP_AFFINE_TANH_V1", family="TANH")]
        with mock.patch.object(v3, "_exact_family_matches", return_value=doubled):
            out = v3.resolve_verified_capability(rows(fn), target="y", input_name="x")
        self.assertEqual(out["status"], "FAIL_CLOSED__AMBIGUOUS_FAMILY_MATCH", out)
        self.assertIsNone(out["match"])
        self.assertEqual(
            out["candidate_capability_ids"],
            ["CAP_AFFINE_POWER5_V1", "CAP_AFFINE_TANH_V1"],
        )

    def test_helper_returns_every_exact_family_not_just_the_first(self):
        # If this ever collapses to first-match-wins the ambiguity guard above
        # becomes unreachable and silently stops protecting anything.
        doc, families = v3._authorized_transfer_families()
        found = v3._exact_family_matches(
            rows(lambda x: -0.5 + 0.15 * x - 0.7 * math.tanh(1.6 * x)), families, "y", "x", 1e-8)
        self.assertEqual([h["capability_id"] for h in found], ["CAP_AFFINE_TANH_V1"])

    def test_too_few_rows_fails_closed_rather_than_fitting(self):
        doc, families = v3._authorized_transfer_families()
        self.assertEqual(
            v3._exact_family_matches(
                [{"x": 0.0, "y": 1.0}, {"x": 1.0, "y": 2.0}], families, "y", "x", 1e-8),
            [],
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
