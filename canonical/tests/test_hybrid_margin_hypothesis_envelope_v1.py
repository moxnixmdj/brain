from __future__ import annotations

import json
from pathlib import Path
import tempfile
import unittest

from canonical.runtime import hybrid_margin_hypothesis_envelope_v1 as hybrid
from canonical.runtime import oewn_release_sense_universe_v1 as oewn

ROOT = Path(__file__).resolve().parents[2]


def sense(sid, synset, definition):
    return {
        "sense_id": sid,
        "synset_id": synset,
        "part_of_speech": "n",
        "lexname": "noun.test",
        "members": ["margin"],
        "definitions": [definition],
        "examples": [],
        "relations": {},
    }


def universe():
    rows = [
        sense("margin%1:07:00::", "05127983-n", "an amount beyond the minimum necessary"),
        sense("margin%1:07:01::", "04757264-n", "a permissible difference"),
        sense("margin%1:10:00::", "06401041-n", "blank space around page text"),
        sense("margin%1:21:01::", "13372293-n", "collateral deposited with a broker"),
        sense("margin%1:21:02::", "13281661-n", "gross profit"),
        sense("margin%1:25:00::", "13926393-n", "boundary line"),
    ]
    return {
        "schema": oewn.SCHEMA,
        "status": "PASS__OEWN_2025_RELEASE_RELATIVE_SENSE_UNIVERSE_ENUMERATED",
        "pass": True,
        "release_id": oewn.RELEASE_ID,
        "archive_sha256": oewn.RELEASE_SHA256,
        "lemma": "margin",
        "requested_part_of_speech": "n",
        "senses": rows,
        "sense_count": len(rows),
        "candidate_set_complete_relative_to_release": True,
        "intended_sense_identified": False,
        "open_world_english_sense_completeness_claimed": False,
    }


def fake_projection(pack):
    return {
        "pass": True,
        "receipt": {
            "fragment_ids": ["FIBO_MARGIN_CLASS"],
            "receipt_sha256": "a" * 64,
        },
        "source_fragment_authority": True,
        "terminal_authority": False,
    }


class Tests(unittest.TestCase):
    def test_real_shape_contains_six_oewn_plus_fibo_plus_remainder(self):
        out = hybrid.build(
            universe(),
            repo_root=ROOT,
            projection_verifier=fake_projection,
        )
        self.assertTrue(out["pass"], out)
        self.assertEqual(out["oewn_release_sense_count"], 6)
        self.assertEqual(out["hypothesis_count"], 8)
        ids = {x["hypothesis_id"] for x in out["hypotheses"]}
        self.assertIn("FIBO::" + hybrid.FIBO_MARGIN_ID, ids)
        self.assertIn("OPEN_WORLD_REMAINDER::margin:n", ids)

    def test_fibo_rate_margin_is_not_erased_by_oewn_release_completeness(self):
        out = hybrid.build(
            universe(),
            repo_root=ROOT,
            projection_verifier=fake_projection,
        )
        fibo = next(
            x for x in out["hypotheses"]
            if x["source_family"] == "FIBO_Q2_2026_PINNED_CONCEPT"
        )
        self.assertEqual(fibo["concept_id"], hybrid.FIBO_MARGIN_ID)
        self.assertEqual(fibo["synonym"], "spread")
        self.assertIn("specified index rate", fibo["definition"])
        self.assertTrue(fibo["candidate_only"])

    def test_oewn_completeness_does_not_become_finance_completeness(self):
        out = hybrid.build(
            universe(),
            repo_root=ROOT,
            projection_verifier=fake_projection,
        )
        self.assertTrue(out["oewn_release_sense_set_complete"])
        self.assertFalse(out["explicit_hypothesis_set_complete"])
        self.assertFalse(out["open_world_finance_semantics_complete"])
        self.assertFalse(out["hypotheses_mutually_exclusive_proved"])
        self.assertFalse(out["safe_for_exact_minimax_world_solver"])

    def test_no_intended_sense_is_selected(self):
        out = hybrid.build(
            universe(),
            repo_root=ROOT,
            projection_verifier=fake_projection,
        )
        self.assertFalse(out["intended_sense_identified"])
        self.assertFalse(out["semantic_truth_authority"])
        self.assertTrue(out["candidate_generation_authority"])

    def test_open_world_remainder_is_mandatory(self):
        out = hybrid.build(
            universe(),
            repo_root=ROOT,
            projection_verifier=fake_projection,
        )
        self.assertTrue(out["open_world_remainder_required"])
        self.assertTrue(out["open_world_remainder_present"])
        remainder = [
            x for x in out["hypotheses"]
            if x["source_family"] == "OPEN_WORLD_REMAINDER"
        ]
        self.assertEqual(len(remainder), 1)

    def test_wrong_oewn_release_hash_fails_closed(self):
        u = universe()
        u["archive_sha256"] = "0" * 64
        out = hybrid.build(
            u,
            repo_root=ROOT,
            projection_verifier=fake_projection,
        )
        self.assertFalse(out["pass"])
        self.assertEqual(out["status"], "FAIL_CLOSED")
        self.assertIn("OEWN_UNIVERSE_BINDING_INVALID", out["reason"])

    def test_missing_oewn_sense_fails_closed_instead_of_shrinking_universe(self):
        u = universe()
        u["senses"] = u["senses"][:-1]
        out = hybrid.build(
            u,
            repo_root=ROOT,
            projection_verifier=fake_projection,
        )
        self.assertFalse(out["pass"])
        self.assertIn("OEWN_MARGIN_SENSE_COUNT_INVALID", out["reason"])

    def test_changed_oewn_sense_binding_fails_closed(self):
        u = universe()
        u["senses"][0]["synset_id"] = "99999999-n"
        out = hybrid.build(
            u,
            repo_root=ROOT,
            projection_verifier=fake_projection,
        )
        self.assertFalse(out["pass"])
        self.assertIn("OEWN_MARGIN_RELEASE_SENSE_SET_MISMATCH", out["reason"])

    def test_fibo_source_authority_failure_fails_closed(self):
        out = hybrid.build(
            universe(),
            repo_root=ROOT,
            projection_verifier=lambda _pack: {"pass": False},
        )
        self.assertFalse(out["pass"])
        self.assertEqual(out["reason"], "FIBO_MARGIN_SOURCE_AUTHORITY_FAILED")

    def test_missing_authenticated_fibo_fragment_fails_closed(self):
        def bad_projection(_pack):
            return {
                "pass": True,
                "receipt": {
                    "fragment_ids": [],
                    "receipt_sha256": "b" * 64,
                },
            }

        out = hybrid.build(
            universe(),
            repo_root=ROOT,
            projection_verifier=bad_projection,
        )
        self.assertFalse(out["pass"])
        self.assertEqual(out["reason"], "FIBO_MARGIN_FRAGMENT_NOT_AUTHENTICATED")

    def test_pack_drift_fails_closed(self):
        source = ROOT / hybrid.PACK_PATH
        doc = json.loads(source.read_text(encoding="utf-8"))
        doc["source_id"] = "tampered"
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            target = root / hybrid.PACK_PATH
            target.parent.mkdir(parents=True)
            target.write_text(json.dumps(doc), encoding="utf-8")
            out = hybrid.build(
                universe(),
                repo_root=root,
                projection_verifier=fake_projection,
            )
        self.assertFalse(out["pass"])
        self.assertIn("FIBO_MARGIN_PACK_GIT_BLOB_DRIFT", out["reason"])

    def test_zero_terminal_promotion_or_acceptance_authority(self):
        out = hybrid.build(
            universe(),
            repo_root=ROOT,
            projection_verifier=fake_projection,
        )
        self.assertTrue(out["pass"], out)
        self.assertFalse(out["execution_authority"])
        self.assertFalse(out["acceptance_authority"])
        self.assertFalse(out["promotion_authority"])
        self.assertFalse(out["terminal_authority"])
        self.assertEqual(out["terminal_credit_delta"], 0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
