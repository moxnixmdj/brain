from __future__ import annotations
import base64
from copy import deepcopy
import inspect
import unittest
import zipfile
from io import BytesIO

from canonical.runtime import native_artifact_cross_format_candidate_v1 as candidate
from canonical.runtime import native_artifact_cross_format_proof_v1 as proof

class NativeArtifactCrossFormatPreflightTests(unittest.TestCase):
    def test_information_boundary(self):
        case=proof.generate_case("docx",101)
        public=proof.public_task(case)
        self.assertNotIn("_oracle",public)
        src=inspect.getsource(candidate)
        self.assertNotIn("native_artifact_cross_format_proof_v1",src)
        self.assertNotIn("_oracle",src)

    def test_cross_format_population(self):
        for fmt in proof.FORMATS:
            for seed in range(101,106):
                case=proof.generate_case(fmt,seed)
                out=candidate.solve(proof.public_task(case))
                verdict=proof.score_case(case,out)
                self.assertTrue(verdict["pass"],(fmt,seed,out,verdict))

    def test_unchanged_source_is_rejected(self):
        case=proof.generate_case("xlsx",777)
        bad={"status":"OK","output_b64":case["task"]["document_b64"]}
        self.assertFalse(proof.score_case(case,bad)["pass"])

    def test_unrelated_ooxml_mutation_is_rejected(self):
        case=proof.generate_case("docx",888)
        out=candidate.solve(proof.public_task(case))
        self.assertTrue(proof.score_case(case,out)["pass"])
        data=base64.b64decode(out["output_b64"])
        src=BytesIO(data); dst=BytesIO()
        with zipfile.ZipFile(src,"r") as zin, zipfile.ZipFile(dst,"w") as zout:
            for info in zin.infolist():
                payload=zin.read(info.filename)
                if info.filename=="docProps/core.xml":
                    payload=payload+b" "
                zout.writestr(info,payload)
        bad=dict(out); bad["output_b64"]=base64.b64encode(dst.getvalue()).decode("ascii")
        self.assertFalse(proof.score_case(case,bad)["pass"])

    def test_unsupported_format_fails_closed(self):
        out=candidate.solve({"task":{"format":"odt","document_b64":"AA==","edit":{"kind":"X"}}})
        self.assertEqual(out["status"],"FAIL_CLOSED")

if __name__=="__main__":
    unittest.main(verbosity=2)
