from __future__ import annotations

from hashlib import sha1
import json
from pathlib import Path
import unittest

from canonical.runtime.authenticated_source_phrase_atom_bridge_v1 import (
    resolve as resolve_phrases,
    verify_source_atom_receipt,
)
from canonical.runtime.repository_bound_semantic_mapping_pack_v1 import (
    load_verified_pack,
    make_concept_definition_verifier,
    make_lexicon_authority_verifier,
)
from canonical.runtime.source_aligned_definitional_entailment_v1 import prove


ROOT = Path(__file__).resolve().parents[2]
PACK_PATH = "canonical/evidence/FINANCE_REGULATORY_LOSS_ABSORPTION_SEMANTIC_PACK_20261009_V1.json"
VERIFY_PATH = "canonical/verification/FINANCE_REGULATORY_LOSS_ABSORPTION_SEMANTIC_PACK_VERIFY_20261009_V1.json"
EXPECTED_PACK_SHA256 = "52cfe8c6cf354b79983f7c9f40392a3457b7bd9e4a09d2cb841703a3447267f9"
SCOPE = "finance:global-standard-terminology:basel-rbc30-fsb-tlac:2026-10-09"
CCOB = "BASEL::CAPITAL_CONSERVATION_BUFFER"
TLAC = "FSB::TLAC"


def _blob(raw: bytes) -> str:
    return sha1(b"blob " + str(len(raw)).encode() + b"\0" + raw).hexdigest()


def verified_pack():
    pack = json.loads((ROOT / PACK_PATH).read_text(encoding="utf-8"))
    raw = (ROOT / VERIFY_PATH).read_bytes()
    out = load_verified_pack(
        pack,
        {"path": VERIFY_PATH, "git_blob_sha": _blob(raw)},
        repo_root=ROOT,
    )
    if out.get("pass") is not True:
        raise AssertionError(out)
    return out


def phrase_evidence(text: str):
    vp = verified_pack()
    lex_verifier = make_lexicon_authority_verifier(vp)
    out = resolve_phrases(
        raw_span=text,
        source_id="case",
        scope_id=SCOPE,
        lexicon=vp["phrase_lexicon"],
        authority_receipt={"pack": vp["pack_sha256"]},
        authority_verifier=lex_verifier,
    )
    return vp, lex_verifier, out


def prove_concept(text: str, concept_id: str):
    vp, lex_verifier, bridge = phrase_evidence(text)
    receipts = list(bridge.get("source_atom_receipts") or [])

    def atom_verifier(receipt):
        return verify_source_atom_receipt(
            receipt,
            raw_span=text,
            source_id="case",
            scope_id=SCOPE,
            lexicon=vp["phrase_lexicon"],
            authority_receipt={"pack": vp["pack_sha256"]},
            authority_verifier=lex_verifier,
        )

    return prove(
        raw_span=text,
        source_id="case",
        scope_id=SCOPE,
        left_id="mention:test",
        right_id=concept_id,
        source_atom_receipts=receipts,
        source_atom_verifier=atom_verifier,
        concept_definition_receipt={"pack": vp["pack_sha256"]},
        concept_definition_verifier=make_concept_definition_verifier(vp, concept_id),
    )


class Tests(unittest.TestCase):
    def test_real_pack_is_repository_bound_and_primary_source_verified(self):
        vp = verified_pack()
        self.assertEqual(vp["pack_sha256"], EXPECTED_PACK_SHA256)
        self.assertTrue(vp["phrase_lexicon_semantics_authenticated"])
        self.assertTrue(vp["concept_definitions_authenticated"])
        self.assertTrue(vp["source_authority_reviewed"])
        self.assertFalse(vp["terminal_authority"])

    def test_naked_loss_absorbing_cushion_does_not_entail_ccob_or_tlac(self):
        text = "loss-absorbing cushion"
        ccob = prove_concept(text, CCOB)
        tlac = prove_concept(text, TLAC)
        self.assertFalse(ccob["left_entails_right"], ccob)
        self.assertFalse(tlac["left_entails_right"], tlac)
        self.assertEqual(ccob["strongest_proved_relation"], "UNKNOWN")
        self.assertEqual(tlac["strongest_proved_relation"], "UNKNOWN")

    def test_basel_discriminators_entail_ccob_not_tlac(self):
        text = (
            "The buffer is 2.5% of RWA, comprised of Common Equity Tier 1 (CET1), "
            "above the regulatory minimum capital requirement, and can be drawn "
            "down as losses are incurred."
        )
        ccob = prove_concept(text, CCOB)
        tlac = prove_concept(text, TLAC)
        self.assertTrue(ccob["left_entails_right"], ccob)
        self.assertEqual(ccob["strongest_proved_relation"], "LEFT_ENTAILS_RIGHT")
        self.assertFalse(tlac["left_entails_right"], tlac)
        self.assertIn("regime.resolution", tlac["missing_target_atoms"])

    def test_fsb_resolution_discriminators_entail_tlac_not_ccob(self):
        text = (
            "Global systemically important banks (G-SIBs) require loss-absorbing "
            "and recapitalisation capacity available in resolution through "
            "instruments and liabilities."
        )
        tlac = prove_concept(text, TLAC)
        ccob = prove_concept(text, CCOB)
        self.assertTrue(tlac["left_entails_right"], tlac)
        self.assertEqual(tlac["strongest_proved_relation"], "LEFT_ENTAILS_RIGHT")
        self.assertFalse(ccob["left_entails_right"], ccob)
        self.assertIn("composition.CET1", ccob["missing_target_atoms"])

    def test_missing_one_ccob_discriminator_stays_unknown_not_refuted(self):
        text = (
            "The buffer is comprised of Common Equity Tier 1 (CET1), above the "
            "regulatory minimum capital requirement, and can be drawn down as "
            "losses are incurred."
        )
        ccob = prove_concept(text, CCOB)
        self.assertFalse(ccob["left_entails_right"])
        self.assertFalse(ccob["left_entails_right_disproved"])
        self.assertEqual(ccob["missing_target_atoms"], ["quantity.2_5_percent_RWA"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
