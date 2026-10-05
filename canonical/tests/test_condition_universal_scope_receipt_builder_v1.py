from __future__ import annotations
import tempfile, unittest
from pathlib import Path
from canonical.runtime.condition_universal_scope_receipt_builder_v1 import build_universal_receipts
from canonical.runtime.terminal_condition_restriction_cell_compiler_v2 import git_blob_sha_bytes

MATRIX={"shared_condition_matrix":[
 {"condition":"CYBERSECURITY","mapped_family_union":["TOOLS","OTHER"]},
 {"condition":"BIOLOGY","mapped_family_union":["TOOLS"]},
 {"condition":"LONG_CONTEXT","mapped_family_union":["MEMORY"]},
]}

class UniversalScopeReceiptBuilderTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(); self.root=Path(self.tmp.name)
        p=self.root/"canonical/verification/u.json"; p.parent.mkdir(parents=True)
        self.payload=b'{"independent":true}\n'; p.write_bytes(self.payload)
        self.sha=git_blob_sha_bytes(self.payload)
    def tearDown(self): self.tmp.cleanup()
    def claim(self,**kw):
        c={"predicate_id":"TOOLS_P","state":"PROVED","family":"TOOLS","proof_kind":"ABSOLUTE_CEILING_WITH_UNIVERSAL_FORMAL_SCOPE_COMPLETENESS",
           "scope_complete":True,"independent_or_objective":True,
           "scope_completeness":{"all_admissible_target_inputs_proved":True,"formal_completeness":True},
           "source_path":"canonical/verification/u.json","source_sha":self.sha}
        c.update(kw); return c
    def test_universal_family_emits_all_mapped_conditions_once(self):
        out=build_universal_receipts(MATRIX,{"claims":[self.claim()]},self.root)
        self.assertEqual(out["emitted_receipt_count"],1)
        self.assertEqual(out["covered_cell_count"],2)
        self.assertEqual(out["proofs"][0]["covered_conditions"],["CYBERSECURITY","BIOLOGY"])
    def test_nonuniversal_claim_emits_nothing(self):
        c=self.claim(scope_completeness={"all_admissible_target_inputs_proved":False,"formal_completeness":True})
        self.assertEqual(build_universal_receipts(MATRIX,{"claims":[c]},self.root)["emitted_receipt_count"],0)
    def test_scope_incomplete_emits_nothing(self):
        self.assertEqual(build_universal_receipts(MATRIX,{"claims":[self.claim(scope_complete=False)]},self.root)["emitted_receipt_count"],0)
    def test_nonindependent_emits_nothing(self):
        self.assertEqual(build_universal_receipts(MATRIX,{"claims":[self.claim(independent_or_objective=False)]},self.root)["emitted_receipt_count"],0)
    def test_forged_source_sha_emits_nothing(self):
        self.assertEqual(build_universal_receipts(MATRIX,{"claims":[self.claim(source_sha="1"*40)]},self.root)["emitted_receipt_count"],0)
    def test_unmapped_universal_family_is_not_emitted(self):
        self.assertEqual(build_universal_receipts(MATRIX,{"claims":[self.claim(family="DELEGATION")]},self.root)["emitted_receipt_count"],0)
    def test_memory_without_universal_quantifier_is_excluded(self):
        c=self.claim(family="MEMORY",scope_completeness={})
        self.assertEqual(build_universal_receipts(MATRIX,{"claims":[c]},self.root)["emitted_receipt_count"],0)

if __name__=="__main__": unittest.main(verbosity=2)
