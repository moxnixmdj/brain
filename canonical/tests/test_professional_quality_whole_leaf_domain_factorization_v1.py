from __future__ import annotations

import unittest

from canonical.runtime.professional_quality_whole_leaf_domain_factorization_v1 import (
    ProfessionalDomainFactorizationError,
    compile_factorization,
)


def manifest():
    roots=[]
    for i in range(1,13):
        rid=f"R{i}_X"
        roots.append({
            "root_id": rid,
            "contract": f"contract-{i}",
            "semantic_leaf":{"id":f"PQ::{rid}::SEMANTIC","obligation":"s","acceptance":"sa"},
            "execution_leaf":{"id":f"PQ::{rid}::EXECUTION","obligation":"e","acceptance":"ea"},
        })
    return {"roots":roots}


def worklist():
    rows=[]
    for i in range(1,13):
        rid=f"R{i}_X"
        for kind in ("SEMANTIC","EXECUTION"):
            lid=f"PQ::{rid}::{kind}"
            rows.append({
                "leaf_id":lid,
                "root_id":rid,
                "uncovered_partition_id":lid+"::UNPROVED_COMPLEMENT",
                "bounded_witness_scope_ids":[lid+"::WITNESS"],
            })
    return {"rows":rows}


class ProfessionalDomainFactorizationTests(unittest.TestCase):
    def test_exact_24_to_12_factorization(self):
        out=compile_factorization(manifest(),worklist())
        self.assertEqual(out["root_count"],12)
        self.assertEqual(out["leaf_count"],24)
        self.assertEqual(out["pair_domain_equivalence_proved_count"],0)
        self.assertEqual(out["pair_domain_equivalence_required_count"],12)

    def test_same_root_pair_never_self_grants_domain_equivalence(self):
        out=compile_factorization(manifest(),worklist())
        for row in out["roots"]:
            self.assertTrue(row["domain_reuse_candidate"])
            self.assertFalse(row["semantic_execution_domain_equivalence_proved"])
            self.assertFalse(row["domain_reuse_authority"])

    def test_missing_complement_fails_closed(self):
        w=worklist()
        w["rows"].pop()
        with self.assertRaisesRegex(
            ProfessionalDomainFactorizationError,
            "COMPLEMENT_UNIVERSE_NOT_24",
        ):
            compile_factorization(manifest(),w)

    def test_root_mismatch_fails_closed(self):
        w=worklist()
        w["rows"][0]["root_id"]="WRONG"
        with self.assertRaisesRegex(
            ProfessionalDomainFactorizationError,
            "COMPLEMENT_ROOT_MISMATCH",
        ):
            compile_factorization(manifest(),w)

    def test_extra_or_wrong_leaf_universe_fails_closed(self):
        w=worklist()
        w["rows"][0]["leaf_id"]="PQ::ALIEN::SEMANTIC"
        with self.assertRaisesRegex(
            ProfessionalDomainFactorizationError,
            "COMPLEMENT_PAIR_MISSING|MANIFEST_COMPLEMENT_LEAF_UNIVERSE_MISMATCH",
        ):
            compile_factorization(manifest(),w)


if __name__=="__main__":
    unittest.main(verbosity=2)
