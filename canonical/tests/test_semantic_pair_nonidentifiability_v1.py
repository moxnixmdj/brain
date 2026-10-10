from __future__ import annotations

from hashlib import sha256
import io
import json
import unittest
from unittest.mock import patch
import zipfile

from canonical.runtime import semantic_pair_nonidentifiability_v1 as kernel
from canonical.runtime import margin_bare_nonidentifiability_v1 as margin
from canonical.runtime import oewn_release_sense_universe_v1 as oewn


SOURCE_ID = "doc:test"
SOURCE = "ambiguous source"


def h(text):
    return sha256(text.encode()).hexdigest()


def compat_result(source_id, source_text, iid, sem):
    return {
        "pass": True,
        "schema": kernel.COMPATIBILITY_SCHEMA,
        "source_id": source_id,
        "source_sha256": h(source_text),
        "interpretation_id": iid,
        "interpretation_semantics_sha256": sem,
        "source_compatible": True,
        "verification_authority_mutated": False,
        "receipt_sha256": h("compat:" + iid + ":" + sem),
    }


def distinct_result(left_id, left_sem, right_id, right_sem):
    return {
        "pass": True,
        "schema": kernel.DISTINCTNESS_SCHEMA,
        "left_interpretation_id": left_id,
        "left_semantics_sha256": left_sem,
        "right_interpretation_id": right_id,
        "right_semantics_sha256": right_sem,
        "semantically_distinct": True,
        "verification_authority_mutated": False,
        "receipt_sha256": h("distinct:" + left_id + ":" + right_id),
    }


def valid_call(**overrides):
    sem_a = h("sem-a")
    sem_b = h("sem-b")
    comp = {
        "a": compat_result(SOURCE_ID, SOURCE, "interpretation:a", sem_a),
        "b": compat_result(SOURCE_ID, SOURCE, "interpretation:b", sem_b),
    }
    distinct = distinct_result(
        "interpretation:a", sem_a, "interpretation:b", sem_b
    )

    def compat_verifier(raw):
        return comp.get(raw.get("slot"))

    def distinct_verifier(_raw):
        return dict(distinct)

    args = {
        "source_id": SOURCE_ID,
        "source_text": SOURCE,
        "compatibility_receipts": [{"slot": "a"}, {"slot": "b"}],
        "compatibility_verifier": compat_verifier,
        "distinctness_receipt": {"pair": "ab"},
        "distinctness_verifier": distinct_verifier,
    }
    args.update(overrides)
    return kernel.prove(**args)


def margin_zip():
    entries = {
        "margin": {
            "n": {
                "sense": [
                    {"id": margin.COLLATERAL_SENSE, "synset": margin.COLLATERAL_SYNSET},
                    {"id": margin.PROFIT_SENSE, "synset": margin.PROFIT_SYNSET},
                ]
            }
        }
    }
    noun = {
        margin.COLLATERAL_SYNSET: {
            "definition": [margin.COLLATERAL_DEFINITION],
            "members": ["margin", "security deposit"],
            "partOfSpeech": "n",
        },
        margin.PROFIT_SYNSET: {
            "definition": [margin.PROFIT_DEFINITION],
            "members": ["margin", "gross profit margin"],
            "partOfSpeech": "n",
        },
    }
    bio = io.BytesIO()
    with zipfile.ZipFile(bio, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("entries-m.json", json.dumps(entries))
        zf.writestr("noun.possession.json", json.dumps(noun))
        zf.writestr("frames.json", "{}")
    return bio.getvalue()


class Tests(unittest.TestCase):
    def test_two_verified_distinct_compatible_interpretations_refute_unique_identity(self):
        out = valid_call()
        self.assertTrue(out["pass"], out)
        self.assertEqual(
            out["status"],
            "PASS__PAIRWISE_SEMANTIC_NONIDENTIFIABILITY_PROVED",
        )
        self.assertTrue(out["semantic_nonidentifiability_authority"])
        self.assertFalse(out["unique_semantic_identity_identified"])
        self.assertFalse(
            out["unique_semantic_identity_identifiable_from_source_alone"]
        )

    def test_hypothesis_space_completeness_is_not_required_for_negative_result(self):
        out = valid_call()
        self.assertTrue(out["pass"])
        self.assertFalse(out["hypothesis_space_completeness_required"])
        self.assertFalse(out["open_world_semantic_completeness_claimed"])
        self.assertTrue(out["additional_information_required_for_unique_identity"])

    def test_source_hash_mismatch_fails_closed(self):
        bad = compat_result(SOURCE_ID, "different source", "interpretation:a", h("a"))
        good = compat_result(SOURCE_ID, SOURCE, "interpretation:b", h("b"))

        def verifier(raw):
            return bad if raw["slot"] == "a" else good

        out = kernel.prove(
            source_id=SOURCE_ID,
            source_text=SOURCE,
            compatibility_receipts=[{"slot": "a"}, {"slot": "b"}],
            compatibility_verifier=verifier,
            distinctness_receipt={"x": 1},
            distinctness_verifier=lambda _x: {},
        )
        self.assertFalse(out["pass"])
        self.assertIn("COMPATIBILITY_RECEIPT_INVALID", out["reason"])

    def test_source_incompatible_receipt_fails_closed(self):
        sem_a, sem_b = h("a"), h("b")
        a = compat_result(SOURCE_ID, SOURCE, "a", sem_a)
        a["source_compatible"] = False
        b = compat_result(SOURCE_ID, SOURCE, "b", sem_b)
        out = kernel.prove(
            source_id=SOURCE_ID,
            source_text=SOURCE,
            compatibility_receipts=[{"slot": "a"}, {"slot": "b"}],
            compatibility_verifier=lambda raw: a if raw["slot"] == "a" else b,
            distinctness_receipt={"x": 1},
            distinctness_verifier=lambda _x: {},
        )
        self.assertFalse(out["pass"])
        self.assertIn("COMPATIBILITY_RECEIPT_INVALID", out["reason"])

    def test_same_interpretation_id_cannot_prove_nonidentifiability(self):
        sem_a, sem_b = h("a"), h("b")
        a = compat_result(SOURCE_ID, SOURCE, "same", sem_a)
        b = compat_result(SOURCE_ID, SOURCE, "same", sem_b)
        dist = distinct_result("same", sem_a, "same", sem_b)
        out = kernel.prove(
            source_id=SOURCE_ID,
            source_text=SOURCE,
            compatibility_receipts=[{"slot": "a"}, {"slot": "b"}],
            compatibility_verifier=lambda raw: a if raw["slot"] == "a" else b,
            distinctness_receipt={"x": 1},
            distinctness_verifier=lambda _x: dist,
        )
        self.assertFalse(out["pass"])
        self.assertIn("interpretation_ids_not_distinct", out["reason"])

    def test_same_semantics_hash_cannot_be_declared_distinct(self):
        sem = h("same-sem")
        a = compat_result(SOURCE_ID, SOURCE, "a", sem)
        b = compat_result(SOURCE_ID, SOURCE, "b", sem)
        dist = distinct_result("a", sem, "b", sem)
        out = kernel.prove(
            source_id=SOURCE_ID,
            source_text=SOURCE,
            compatibility_receipts=[{"slot": "a"}, {"slot": "b"}],
            compatibility_verifier=lambda raw: a if raw["slot"] == "a" else b,
            distinctness_receipt={"x": 1},
            distinctness_verifier=lambda _x: dist,
        )
        self.assertFalse(out["pass"])
        self.assertIn("interpretation_semantics_not_distinct", out["reason"])

    def test_distinctness_pair_must_bind_exact_compatibility_semantics(self):
        sem_a, sem_b = h("a"), h("b")
        a = compat_result(SOURCE_ID, SOURCE, "a", sem_a)
        b = compat_result(SOURCE_ID, SOURCE, "b", sem_b)
        dist = distinct_result("a", h("wrong"), "b", sem_b)
        out = kernel.prove(
            source_id=SOURCE_ID,
            source_text=SOURCE,
            compatibility_receipts=[{"slot": "a"}, {"slot": "b"}],
            compatibility_verifier=lambda raw: a if raw["slot"] == "a" else b,
            distinctness_receipt={"x": 1},
            distinctness_verifier=lambda _x: dist,
        )
        self.assertFalse(out["pass"])
        self.assertIn("interpretation_pair_binding", out["reason"])

    def test_exactly_two_compatibility_receipts_required_in_v1(self):
        out = valid_call(compatibility_receipts=[{"slot": "a"}])
        self.assertFalse(out["pass"])
        self.assertEqual(
            out["reason"],
            "EXACTLY_TWO_COMPATIBILITY_RECEIPTS_REQUIRED",
        )

    def test_margin_certificate_replays_through_generic_theorem(self):
        raw = margin_zip()
        digest = sha256(raw).hexdigest()
        source = "Margin increased."
        source_id = "doc:margin"
        with patch.object(oewn, "RELEASE_SHA256", digest):
            concrete = margin.prove(source, oewn_archive=raw)
        self.assertTrue(concrete["pass"], concrete)

        sem = {
            margin.COLLATERAL_SENSE: h(
                margin.COLLATERAL_SENSE + ":" + margin.COLLATERAL_SYNSET
            ),
            margin.PROFIT_SENSE: h(
                margin.PROFIT_SENSE + ":" + margin.PROFIT_SYNSET
            ),
        }

        def compat_verifier(raw_receipt):
            sid = raw_receipt["sense_id"]
            with patch.object(oewn, "RELEASE_SHA256", digest):
                replay = margin.prove(source, oewn_archive=raw)
            if sid not in replay["witness_sense_ids"]:
                return None
            return compat_result(
                source_id,
                source,
                sid,
                sem[sid],
            )

        def distinct_verifier(_raw_receipt):
            with patch.object(oewn, "RELEASE_SHA256", digest):
                replay = margin.prove(source, oewn_archive=raw)
            if set(replay["witness_sense_ids"]) != {
                margin.COLLATERAL_SENSE,
                margin.PROFIT_SENSE,
            }:
                return None
            return distinct_result(
                margin.COLLATERAL_SENSE,
                sem[margin.COLLATERAL_SENSE],
                margin.PROFIT_SENSE,
                sem[margin.PROFIT_SENSE],
            )

        out = kernel.prove(
            source_id=source_id,
            source_text=source,
            compatibility_receipts=[
                {"sense_id": margin.COLLATERAL_SENSE},
                {"sense_id": margin.PROFIT_SENSE},
            ],
            compatibility_verifier=compat_verifier,
            distinctness_receipt={"pair": "margin-witnesses"},
            distinctness_verifier=distinct_verifier,
        )
        self.assertTrue(out["pass"], out)
        self.assertEqual(
            set(out["witness_interpretation_ids"]),
            {margin.COLLATERAL_SENSE, margin.PROFIT_SENSE},
        )

    def test_no_semantic_identity_or_terminal_authority(self):
        out = valid_call()
        self.assertTrue(out["pass"])
        self.assertFalse(out["semantic_truth_authority"])
        self.assertFalse(out["execution_authority"])
        self.assertFalse(out["acceptance_authority"])
        self.assertFalse(out["promotion_authority"])
        self.assertFalse(out["terminal_authority"])
        self.assertEqual(out["terminal_credit_delta"], 0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
