from __future__ import annotations

from hashlib import sha256
import json
import unittest

from canonical.runtime import information_theoretic_externality_gate_v1 as gate


def _sha(value):
    return sha256(
        json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        ).encode("utf-8")
    ).hexdigest()


def _receipt(*, verifier_id, statement_sha256, evidence_sha256="e" * 64):
    payload = {
        "verified": True,
        "source_kind": "INDEPENDENT_VERIFIER",
        "verifier_id": verifier_id,
        "statement_sha256": statement_sha256,
        "evidence_sha256": evidence_sha256,
        "verification_authority_mutated": False,
    }
    return {**payload, "receipt_sha256": _sha(payload)}


def _certificate():
    obligation_ids = ["w1"]
    obs = "1" * 64
    act1 = "3" * 64
    act2 = "4" * 64
    world_pair = {
        "world_1": {
            "world_id": "W1",
            "accessible_observation_sha256": obs,
            "required_action_sha256": act1,
        },
        "world_2": {
            "world_id": "W2",
            "accessible_observation_sha256": obs,
            "required_action_sha256": act2,
        },
    }
    ind_statement = _sha({
        "claim": "OBSERVATIONAL_EQUIVALENCE",
        "obligation_ids": obligation_ids,
        "world_ids": ["W1", "W2"],
        "accessible_observation_sha256": obs,
    })
    action_statement = _sha({
        "claim": "ACTION_SEPARATION",
        "obligation_ids": obligation_ids,
        "required_action_sha256_pair": [act1, act2],
    })
    exhaustion_statement = _sha({
        "claim": "INTERNAL_BYPASS_SET_EXHAUSTED",
        "obligation_ids": obligation_ids,
        "required_bypass_classes": list(gate.REQUIRED_BYPASS_CLASSES),
    })
    bypass_rows = []
    for name in gate.REQUIRED_BYPASS_CLASSES:
        statement = _sha({
            "claim": "BYPASS_FALSIFIED",
            "bypass_class": name,
            "obligation_ids": obligation_ids,
        })
        bypass_rows.append({
            "bypass_class": name,
            "verdict": "FALSIFIED",
            "proof": _receipt(
                verifier_id="V:bypass:" + name,
                statement_sha256=statement,
            ),
        })
    cert = {
        "schema": gate.CERTIFICATE_SCHEMA,
        "status": "PROVED_INFORMATION_THEORETICALLY_EXTERNAL",
        "prover_id": "PROVER:externality:1",
        "obligation_ids": obligation_ids,
        "exact_missing_information_sha256": "2" * 64,
        "world_pair": world_pair,
        "indistinguishability_proof": _receipt(
            verifier_id="V:indistinguishability",
            statement_sha256=ind_statement,
        ),
        "action_separation_proof": _receipt(
            verifier_id="V:action-separation",
            statement_sha256=action_statement,
        ),
        "internal_constructive_gap_exhaustion_proof": _receipt(
            verifier_id="V:internal-exhaustion",
            statement_sha256=exhaustion_statement,
        ),
        "bypass_falsification": bypass_rows,
    }
    core = {
        "schema": cert["schema"],
        "status": cert["status"],
        "prover_id": cert["prover_id"],
        "obligation_ids": cert["obligation_ids"],
        "exact_missing_information_sha256": cert["exact_missing_information_sha256"],
        "world_pair": cert["world_pair"],
        "indistinguishability_proof_receipt_sha256": cert["indistinguishability_proof"]["receipt_sha256"],
        "action_separation_proof_receipt_sha256": cert["action_separation_proof"]["receipt_sha256"],
        "internal_constructive_gap_exhaustion_proof_receipt_sha256": cert["internal_constructive_gap_exhaustion_proof"]["receipt_sha256"],
        "bypass_falsification_receipt_sha256": {
            row["bypass_class"]: row["proof"]["receipt_sha256"]
            for row in bypass_rows
        },
    }
    authority_statement = _sha({
        "claim": "EXTERNALITY_CERTIFICATE_VERIFIED",
        "certificate_core_sha256": _sha(core),
    })
    cert["externality_verification_authority"] = _receipt(
        verifier_id="V:externality-authority",
        statement_sha256=authority_statement,
        evidence_sha256=_sha(core),
    )
    return cert


class InformationTheoreticExternalityGateV1Tests(unittest.TestCase):
    def test_no_certificate_never_becomes_external(self):
        out = gate.verify_certificate(None, pending=[{"work_id": "w1"}])
        self.assertFalse(out["pass"])
        self.assertFalse(out["irreducible_external_information_proved"])
        self.assertEqual(
            out["reason"],
            "PROOF_CARRYING_EXTERNALITY_CERTIFICATE_REQUIRED",
        )

    def test_complete_bound_certificate_passes(self):
        cert = _certificate()
        out = gate.verify_certificate(cert, pending=[{"work_id": "w1"}])
        self.assertTrue(out["pass"], out)
        self.assertTrue(out["irreducible_external_information_proved"])
        self.assertEqual(
            out["status"],
            "PROVED_INFORMATION_THEORETICALLY_EXTERNAL",
        )

    def test_same_observation_but_same_action_is_not_external(self):
        cert = _certificate()
        cert["world_pair"]["world_2"]["required_action_sha256"] = (
            cert["world_pair"]["world_1"]["required_action_sha256"]
        )
        out = gate.verify_certificate(cert, pending=[{"work_id": "w1"}])
        self.assertFalse(out["pass"])
        self.assertEqual(
            out["reason"],
            "WORLD_PAIR_DOES_NOT_REQUIRE_DIFFERENT_ACTIONS",
        )

    def test_missing_bypass_class_is_not_external(self):
        cert = _certificate()
        cert["bypass_falsification"].pop()
        out = gate.verify_certificate(cert, pending=[{"work_id": "w1"}])
        self.assertFalse(out["pass"])
        self.assertEqual(out["reason"], "BYPASS_FALSIFICATION_NOT_EXHAUSTIVE")

    def test_forged_receipt_digest_is_rejected(self):
        cert = _certificate()
        cert["indistinguishability_proof"]["receipt_sha256"] = "f" * 64
        out = gate.verify_certificate(cert, pending=[{"work_id": "w1"}])
        self.assertFalse(out["pass"])
        self.assertEqual(
            out["reason"],
            "INDEPENDENT_INDISTINGUISHABILITY_PROOF_REQUIRED",
        )

    def test_receipt_bound_to_wrong_statement_is_rejected(self):
        cert = _certificate()
        proof = cert["indistinguishability_proof"]
        proof["statement_sha256"] = "9" * 64
        payload = {k: v for k, v in proof.items() if k != "receipt_sha256"}
        proof["receipt_sha256"] = _sha(payload)
        out = gate.verify_certificate(cert, pending=[{"work_id": "w1"}])
        self.assertFalse(out["pass"])
        self.assertEqual(
            out["reason"],
            "INDEPENDENT_INDISTINGUISHABILITY_PROOF_REQUIRED",
        )

    def test_prover_cannot_self_verify(self):
        cert = _certificate()
        proof = cert["action_separation_proof"]
        proof["verifier_id"] = cert["prover_id"]
        payload = {k: v for k, v in proof.items() if k != "receipt_sha256"}
        proof["receipt_sha256"] = _sha(payload)
        out = gate.verify_certificate(cert, pending=[{"work_id": "w1"}])
        self.assertFalse(out["pass"])
        self.assertEqual(
            out["reason"],
            "INDEPENDENT_ACTION_SEPARATION_PROOF_REQUIRED",
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
