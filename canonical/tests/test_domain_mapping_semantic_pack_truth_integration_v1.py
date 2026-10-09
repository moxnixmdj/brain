from __future__ import annotations

from hashlib import sha1
import json
from pathlib import Path
import unittest

from canonical.runtime.domain_mapping_truth_certificate_v1 import (
    checked_predicate_id,
    evaluate,
)


ROOT = Path(__file__).resolve().parents[2]
PACK_PATH = "canonical/evidence/FINANCE_REGULATORY_LOSS_ABSORPTION_SEMANTIC_PACK_20261009_V1.json"
VERIFY_PATH = "canonical/verification/FINANCE_REGULATORY_LOSS_ABSORPTION_SEMANTIC_PACK_VERIFY_20261009_V1.json"
SCOPE = "finance:global-standard-terminology:basel-rbc30-fsb-tlac:2026-10-09"
CCOB = "BASEL::CAPITAL_CONSERVATION_BUFFER"
TLAC = "FSB::TLAC"


def _blob(raw: bytes) -> str:
    return sha1(b"blob " + str(len(raw)).encode() + b"\0" + raw).hexdigest()


def pack_payload():
    pack = json.loads((ROOT / PACK_PATH).read_text(encoding="utf-8"))
    raw = (ROOT / VERIFY_PATH).read_bytes()
    return pack, {"path": VERIFY_PATH, "git_blob_sha": _blob(raw)}


def candidate(concept_id):
    return {
        "concept_id": concept_id,
        "surface": concept_id,
        "required_atoms": [],
        "forbidden_atoms": [],
    }


def payload(text, target):
    pack, ref = pack_payload()
    checked = checked_predicate_id(
        source_id="case",
        raw_span=text,
        scope_id=SCOPE,
        target_concept_id=target,
        required_relation="LEFT_ENTAILS_RIGHT",
    )
    return {
        "truth_kind": "DOMAIN_MAPPING_RELATION",
        "predicate_id": checked,
        "raw_span": text,
        "source_id": "case",
        "scope_id": SCOPE,
        "target_concept_id": target,
        "required_relation": "LEFT_ENTAILS_RIGHT",
        "candidate_concepts": [candidate(CCOB), candidate(TLAC)],
        "semantic_pack": pack,
        "semantic_pack_verification_ref": ref,
    }


class Tests(unittest.TestCase):
    def test_verified_pack_synthesizes_ccob_entailment_without_prebuilt_relation_problem(self):
        text = (
            "The buffer is 2.5% of RWA, comprised of Common Equity Tier 1 (CET1), "
            "above the regulatory minimum capital requirement, and can be drawn "
            "down as losses are incurred."
        )
        out = evaluate(payload(text, CCOB))
        self.assertTrue(out["pass"], out)
        self.assertEqual(out["predicate_truth"], "TRUE")
        self.assertEqual(out["required_relation"], "LEFT_ENTAILS_RIGHT")
        self.assertEqual(out["target_concept_id"], CCOB)
        self.assertTrue(out["semantic_truth_authority"])
        self.assertFalse(out["terminal_authority"])

    def test_verified_pack_synthesizes_tlac_entailment(self):
        text = (
            "Global systemically important banks (G-SIBs) require loss-absorbing "
            "and recapitalisation capacity available in resolution through "
            "instruments and liabilities."
        )
        out = evaluate(payload(text, TLAC))
        self.assertTrue(out["pass"], out)
        self.assertEqual(out["predicate_truth"], "TRUE")
        self.assertEqual(out["target_concept_id"], TLAC)

    def test_naked_phrase_remains_unknown_even_with_verified_pack(self):
        out = evaluate(payload("loss-absorbing cushion", CCOB))
        self.assertFalse(out["pass"], out)
        self.assertEqual(out["predicate_truth"], "UNKNOWN")
        self.assertFalse(out["semantic_truth_authority"])

    def test_pack_does_not_turn_missing_tlac_features_into_false(self):
        text = (
            "The buffer is 2.5% of RWA, comprised of Common Equity Tier 1 (CET1), "
            "above the regulatory minimum capital requirement, and can be drawn "
            "down as losses are incurred."
        )
        out = evaluate(payload(text, TLAC))
        self.assertFalse(out["pass"], out)
        self.assertEqual(out["predicate_truth"], "UNKNOWN")

    def test_wrong_pack_verification_blob_fails_closed(self):
        p = payload("loss-absorbing cushion", CCOB)
        p["semantic_pack_verification_ref"]["git_blob_sha"] = "0" * 40
        out = evaluate(p)
        self.assertFalse(out["pass"])
        self.assertEqual(out["status"], "FAIL_CLOSED")
        self.assertIn("SEMANTIC_PACK", out["reason"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
