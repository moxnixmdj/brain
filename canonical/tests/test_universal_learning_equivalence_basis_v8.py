from __future__ import annotations

import unittest

from canonical.runtime import equivalence_compression_v8 as eq
from canonical.runtime import novelty_basis_v8 as nb
from canonical.runtime import residual_priority_v8 as rp
from canonical.runtime import universal_learning_equivalence_basis_router_v8 as v8


def obj(oid, sig, scope="g"):
    digest=eq.object_digest(object_id=oid,behavior_signature=sig,goal_scope=scope)
    return {
        "object_id":oid,"goal_scope":scope,"behavior_signature":sig,
        "verification_receipt":{
            "receipt_id":"obj-"+oid,"independent_verified":True,"exact_byte_bound":True,
            "conclusion":"success","object_id":oid,"goal_scope":scope,"object_sha256":digest,
        },
    }


def mapping(source, representative, source_obj, rep_obj, basis="FORMAL_ISOMORPHISM", relation="EXACT"):
    digest=eq.mapping_digest(
        source_sha256=source_obj["verification_receipt"]["object_sha256"],
        representative_sha256=rep_obj["verification_receipt"]["object_sha256"],
        goal_scope=source_obj["goal_scope"],basis=basis,relation=relation,
    )
    return {
        "source_id":source,"representative_id":representative,"basis":basis,"relation":relation,
        "verification_receipt":{
            "receipt_id":"map-"+source+"-"+representative,
            "independent_verified":True,"exact_byte_bound":True,"conclusion":"success",
            "behavior_equivalent_on_claimed_scope":True,
            "source_id":source,"representative_id":representative,
            "goal_scope":source_obj["goal_scope"],"basis":basis,"relation":relation,
            "mapping_sha256":digest,
        },
    }


def primitive(pid, atoms, cost):
    digest=nb.primitive_digest(primitive_id=pid,covers_atoms=atoms,description_cost=cost)
    return {
        "primitive_id":pid,"covers_atoms":atoms,"description_cost":cost,
        "verification_receipt":{
            "receipt_id":"p-"+pid,"independent_verified":True,"exact_byte_bound":True,
            "conclusion":"success","primitive_id":pid,"primitive_sha256":digest,
        },
    }


def target(tid, atoms):
    digest=nb.target_digest(target_id=tid,required_atoms=atoms)
    return {
        "target_id":tid,"required_atoms":atoms,
        "verification_receipt":{
            "receipt_id":"t-"+tid,"independent_verified":True,"exact_byte_bound":True,
            "conclusion":"success","required_atom_set_complete":True,
            "target_id":tid,"target_sha256":digest,
        },
    }


def residual(rid, critical, mass, fals, transfer, cost):
    digest=rp.residual_digest(
        residual_id=rid,decision_critical=critical,residual_mass_ub=mass,
        falsification_value_lcb=fals,future_transfer_lcb=transfer,acquisition_cost_ub=cost,
    )
    return {
        "residual_id":rid,"decision_critical":critical,"residual_mass_ub":mass,
        "falsification_value_lcb":fals,"future_transfer_lcb":transfer,"acquisition_cost_ub":cost,
        "verification_receipt":{
            "receipt_id":"r-"+rid,"independent_verified":True,"exact_byte_bound":True,
            "conclusion":"success","residual_id":rid,"residual_sha256":digest,
        },
    }


class EquivalenceCompressionV8Tests(unittest.TestCase):
    def test_verified_equivalence_compresses(self):
        a=obj("a",["x"]); b=obj("b",["y"])
        out=eq.compress(objects=[a,b],mappings=[mapping("b","a",b,a)])
        self.assertEqual(out["object_count_before"],2)
        self.assertEqual(out["representative_count_after"],1)
        self.assertEqual(out["compression_savings"],1)
        self.assertFalse(out["open_world_equivalence_claimed"])

    def test_similarity_without_receipt_cannot_compress(self):
        a=obj("a",["same"]); b=obj("b",["same"])
        bad={"source_id":"b","representative_id":"a","basis":"FORMAL_ISOMORPHISM","relation":"EXACT"}
        with self.assertRaises(eq.EquivalenceCompressionError):
            eq.compress(objects=[a,b],mappings=[bad])

    def test_scope_mismatch_rejected(self):
        a=obj("a",["x"],"g1"); b=obj("b",["x"],"g2")
        # Make a syntactically valid receipt anyway; scope mismatch must fail earlier.
        fake={
            "source_id":"b","representative_id":"a","basis":"FORMAL_ISOMORPHISM","relation":"EXACT",
            "verification_receipt":{},
        }
        with self.assertRaises(eq.EquivalenceCompressionError):
            eq.compress(objects=[a,b],mappings=[fake])

    def test_chained_equivalence_requires_direct_receipt(self):
        a=obj("a",["x"]); b=obj("b",["y"]); c=obj("c",["z"])
        m1=mapping("b","a",b,a)
        m2=mapping("c","b",c,b)
        with self.assertRaises(eq.EquivalenceCompressionError):
            eq.compress(objects=[a,b,c],mappings=[m1,m2])

    def test_tampered_mapping_digest_rejected(self):
        a=obj("a",["x"]); b=obj("b",["y"])
        m=mapping("b","a",b,a)
        m["verification_receipt"]["mapping_sha256"]="sha256:bad"
        with self.assertRaises(eq.EquivalenceCompressionError):
            eq.compress(objects=[a,b],mappings=[m])


class NoveltyBasisV8Tests(unittest.TestCase):
    def test_exact_minimum_cost_beats_smaller_but_costlier_basis(self):
        out=nb.exact_basis(
            primitives=[
                primitive("wide",["a","b"],10),
                primitive("a",["a"],2),
                primitive("b",["b"],2),
            ],
            targets=[target("task",["a","b"])],
        )
        self.assertEqual(out["selected_primitive_ids"],["a","b"])
        self.assertEqual(out["total_description_cost"],"4")
        self.assertFalse(out["open_world_basis_claimed"])

    def test_incomplete_target_receipt_rejected(self):
        t=target("task",["a"])
        t["verification_receipt"]["required_atom_set_complete"]=False
        with self.assertRaises(nb.NoveltyBasisError):
            nb.exact_basis(primitives=[primitive("a",["a"],1)],targets=[t])

    def test_uncovered_required_atom_rejected(self):
        with self.assertRaises(nb.NoveltyBasisError):
            nb.exact_basis(
                primitives=[primitive("a",["a"],1)],
                targets=[target("task",["a","b"])],
            )

    def test_exact_search_bound_fails_closed(self):
        ps=[primitive(f"p{i}",[f"a{i}"],1) for i in range(nb.MAX_EXACT_PRIMITIVES+1)]
        with self.assertRaises(nb.NoveltyBasisError):
            nb.exact_basis(primitives=ps,targets=[target("t",["a0"])])

    def test_tie_break_is_deterministic(self):
        out=nb.exact_basis(
            primitives=[primitive("z",["a"],1),primitive("a",["a"],1)],
            targets=[target("t",["a"])],
        )
        self.assertEqual(out["selected_primitive_ids"],["a"])


class ResidualPriorityV8Tests(unittest.TestCase):
    def test_decision_critical_beats_flashy_noncritical(self):
        out=rp.rank([
            residual("flashy",False,100,100,100,0),
            residual("critical",True,1,1,0,100),
        ])
        self.assertEqual(out["ranked"][0]["residual_id"],"critical")
        self.assertFalse(out["execution_authority"])

    def test_mass_then_falsification_then_transfer_then_cost(self):
        out=rp.rank([
            residual("a",True,5,1,1,5),
            residual("b",True,6,0,0,100),
            residual("c",True,5,2,0,100),
        ])
        self.assertEqual([x["residual_id"] for x in out["ranked"]],["b","c","a"])

    def test_tampered_metrics_rejected(self):
        r=residual("r",True,1,1,1,1)
        r["residual_mass_ub"]=2
        with self.assertRaises(rp.ResidualPriorityError):
            rp.rank([r])

    def test_empty_residuals_safe(self):
        out=rp.rank([])
        self.assertEqual(out["ranked"],[])
        self.assertFalse(out["execution_authority"])


class UniversalLearningV8Tests(unittest.TestCase):
    def test_invariant_bundle(self):
        out=v8.prove_v8_invariants()
        self.assertTrue(out["pass"],out)
        self.assertTrue(out["v7_base_preserved"])
        self.assertFalse(out["unknown_domain_acceptance_proved"])
        self.assertFalse(out["universal_novelty_basis_proved"])
        self.assertEqual(out["acceptance_credit_delta"],0)
        self.assertFalse(out["execution_authority"])
        self.assertFalse(out["promotion_authority"])
        self.assertFalse(out["fresh_reality_authority"])


if __name__=="__main__":
    unittest.main(verbosity=2)
