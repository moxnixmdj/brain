from __future__ import annotations

import unittest

from canonical.runtime import verified_novelty_basis_v8 as b
from canonical.runtime import universal_learning_novelty_basis_router_v8 as r


SIG=["state","transition"]


def primitive(pid="p",sig=SIG,verified=True):
    dg=b.signature_digest(sig)
    return {
        "primitive_id":pid,
        "canonical_signature":sig,
        "verification_receipt":{
            "receipt_id":"proof-"+pid,
            "independent_verified":verified,
            "exact_byte_bound":True,
            "conclusion":"success",
            "behavior_verified":True,
            "primitive_id":pid,
            "signature_sha256":dg,
        },
    }


def composition_spec(*,target_id="t",target_sig=SIG,ids=("p",),steps=None,burden=1,verified=True):
    steps=steps or [{"op":"compose","inputs":list(ids),"outputs":[target_id]}]
    dg=b.composition_digest(
        target_id=target_id,target_signature=target_sig,
        primitive_ids=list(ids),composition_steps=steps,
    )
    td=b.target_digest(target_id=target_id,target_signature=target_sig)
    pd={pid:b.signature_digest(SIG) for pid in sorted(ids)}
    return {
        "id":"comp",
        "primitive_ids":list(ids),
        "composition_steps":steps,
        "burden":burden,
        "verification_receipt":{
            "receipt_id":"composition-proof",
            "independent_verified":verified,
            "exact_byte_bound":True,
            "conclusion":"success",
            "behavior_preserving_on_claimed_scope":True,
            "scope_relation":"EXACT",
            "composition_sha256":dg,
            "primitive_ids":sorted(ids),
            "primitive_signature_sha256":pd,
            "target_sha256":td,
        },
    }


def symmetry_spec(*,source="p",target="t",target_sig=SIG,transform="rename",verified=True):
    dg=b.symmetry_digest(
        source_id=source,target_id=target,transform_id=transform,
        source_signature=SIG,target_signature=target_sig,
    )
    return {
        "id":"sym",
        "source_primitive_id":source,
        "transform_id":transform,
        "verification_receipt":{
            "receipt_id":"sym-proof",
            "independent_verified":verified,
            "exact_byte_bound":True,
            "conclusion":"success",
            "bijective_on_claimed_scope":True,
            "behavior_equivariant":True,
            "inverse_verified":True,
            "scope_relation":"EXACT",
            "symmetry_sha256":dg,
        },
    }


class NoveltyBasisV8Tests(unittest.TestCase):
    def test_verified_composition_authorizes_structural_reuse_only(self):
        spec=composition_spec()
        out=b.verify_composition(
            target_id="t",target_signature=SIG,
            primitives=[primitive()],
            primitive_ids=spec["primitive_ids"],
            composition_steps=spec["composition_steps"],
            verification_receipt=spec["verification_receipt"],
            burden=spec["burden"],
        )
        self.assertTrue(out["structural_reuse_authorized"])
        self.assertFalse(out["target_execution_authorized"])
        self.assertEqual(out["scope_relation"],"EXACT")

    def test_unverified_primitive_rejected(self):
        spec=composition_spec()
        with self.assertRaises(b.NoveltyBasisError):
            b.verify_composition(
                target_id="t",target_signature=SIG,
                primitives=[primitive(verified=False)],
                primitive_ids=spec["primitive_ids"],
                composition_steps=spec["composition_steps"],
                verification_receipt=spec["verification_receipt"],
            )

    def test_self_or_unverified_composition_proof_rejected(self):
        spec=composition_spec(verified=False)
        with self.assertRaises(b.NoveltyBasisError):
            b.verify_composition(
                target_id="t",target_signature=SIG,primitives=[primitive()],
                primitive_ids=spec["primitive_ids"],composition_steps=spec["composition_steps"],
                verification_receipt=spec["verification_receipt"],
            )

    def test_tampered_composition_digest_rejected(self):
        spec=composition_spec()
        spec["verification_receipt"]["composition_sha256"]="sha256:"+"0"*64
        with self.assertRaises(b.NoveltyBasisError):
            b.verify_composition(
                target_id="t",target_signature=SIG,primitives=[primitive()],
                primitive_ids=spec["primitive_ids"],composition_steps=spec["composition_steps"],
                verification_receipt=spec["verification_receipt"],
            )

    def test_minimum_ranking_only_operates_after_verification(self):
        a=composition_spec(burden=100)
        oa=b.verify_composition(
            target_id="t",target_signature=SIG,primitives=[primitive()],
            primitive_ids=a["primitive_ids"],composition_steps=a["composition_steps"],
            verification_receipt=a["verification_receipt"],burden=100,
        )
        fake=dict(oa)
        fake["status"]="UNVERIFIED"
        fake["burden"]=0
        chosen=b.choose_minimum_verified_composition([fake,oa])
        self.assertEqual(chosen["selected"]["burden"],100)
        self.assertIn("TRUTH_PREESTABLISHED",chosen["ranking_rule"])

    def test_verified_symmetry_requires_bijection_equivariance_and_inverse(self):
        spec=symmetry_spec()
        out=b.verify_symmetry(
            source_primitive=primitive(),target_id="t",target_signature=SIG,
            transform_id=spec["transform_id"],
            verification_receipt=spec["verification_receipt"],
        )
        self.assertTrue(out["structural_reuse_authorized"])
        bad=symmetry_spec()
        bad["verification_receipt"]["inverse_verified"]=False
        with self.assertRaises(b.NoveltyBasisError):
            b.verify_symmetry(
                source_primitive=primitive(),target_id="t",target_signature=SIG,
                transform_id=bad["transform_id"],verification_receipt=bad["verification_receipt"],
            )

    def test_symmetry_wrong_digest_rejected(self):
        spec=symmetry_spec()
        spec["verification_receipt"]["symmetry_sha256"]="sha256:"+"f"*64
        with self.assertRaises(b.NoveltyBasisError):
            b.verify_symmetry(
                source_primitive=primitive(),target_id="t",target_signature=SIG,
                transform_id=spec["transform_id"],verification_receipt=spec["verification_receipt"],
            )


class NoveltyBasisRouterV8Tests(unittest.TestCase):
    def test_verified_composition_eliminates_structural_relearning(self):
        spec=composition_spec()
        out=r.route(
            target_id="t",target_signature=SIG,
            verified_primitives=[primitive()],
            composition_specs=[spec],
            symmetry_specs=[],
            v7_kwargs={},
        )
        self.assertEqual(out["route"],"REUSE_VERIFIED_NOVELTY_BASIS")
        self.assertEqual(out["structural_novelty_residual"],[])
        self.assertFalse(out["empirical_structure_learning_authorized"])
        self.assertIsNone(out["v7_result"])
        self.assertFalse(out["trusted_execution_authorized"])

    def test_verified_symmetry_eliminates_structural_relearning(self):
        spec=symmetry_spec()
        out=r.route(
            target_id="t",target_signature=SIG,
            verified_primitives=[primitive()],
            composition_specs=[],
            symmetry_specs=[spec],
            v7_kwargs={},
        )
        self.assertEqual(out["route"],"REUSE_VERIFIED_NOVELTY_BASIS")
        self.assertEqual(out["selected_reuse"]["reuse_type"],"VERIFIED_SYMMETRY")

    def test_invalid_composition_does_not_get_reuse_credit(self):
        spec=composition_spec()
        spec["verification_receipt"]["independent_verified"]=False
        # We avoid invoking V7 with incomplete kwargs by inspecting the rejected
        # basis relation directly rather than pretending fallback itself proves anything.
        with self.assertRaises(b.NoveltyBasisError):
            b.verify_composition(
                target_id="t",target_signature=SIG,primitives=[primitive()],
                primitive_ids=spec["primitive_ids"],composition_steps=spec["composition_steps"],
                verification_receipt=spec["verification_receipt"],
            )

    def test_v8_invariant_bundle(self):
        out=r.prove_v8_invariants()
        self.assertTrue(out["pass"],out)
        self.assertTrue(out["verified_composition_requires_external_proof"])
        self.assertTrue(out["verified_symmetry_requires_external_proof"])
        self.assertTrue(out["compression_metrics_not_truth_evidence"])
        self.assertTrue(out["v7_base_preserved"])
        self.assertFalse(out["unknown_domain_acceptance_proved"])
        self.assertFalse(out["promotion_authority"])


if __name__=="__main__":
    unittest.main(verbosity=2)
