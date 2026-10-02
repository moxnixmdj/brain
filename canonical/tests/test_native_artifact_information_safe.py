from __future__ import annotations
import inspect,unittest
from canonical.runtime import native_artifact_information_safe_candidate as candidate
from canonical.runtime import native_artifact_information_safe_proof as proof

class NativeArtifactInformationSafeTests(unittest.TestCase):
    def test_target_bytes_are_not_public(self):
        case=proof.generate_case(1,0)
        public=proof.public_task(case)
        self.assertNotIn("_oracle",public)
        self.assertNotIn("target_bytes",public)

    def test_candidate_has_no_evaluator_dependency(self):
        src=inspect.getsource(candidate)
        self.assertNotIn("native_artifact_information_safe_proof",src)
        self.assertNotIn("_oracle",src)

    def test_cross_format_grid(self):
        out=proof.run_batch(2026,80,candidate.apply_edit)
        self.assertTrue(out["all_pass"],out)
        self.assertEqual({proof.generate_case(2026,i)["format"] for i in range(4)},set(proof.FORMATS))

    def test_one_byte_unrelated_mutation_fails(self):
        case=proof.generate_case(9,0)
        result=candidate.apply_edit(proof.public_task(case))
        data=bytearray(result["output_bytes"])
        # Truncating any ZIP byte must make package/invariants fail.
        result["output_bytes"]=bytes(data[:-1])
        self.assertFalse(proof.score_case(case,result)["pass"])

if __name__=="__main__":unittest.main(verbosity=2)
