from __future__ import annotations
import math
from pathlib import Path
import tempfile
import unittest

from canonical.runtime.bound_capabilities import general_scientific_raw_resource_v2 as a


def csv(path,header,rows):
    path.write_text(",".join(header)+"\n"+"\n".join(",".join(str(x) for x in r) for r in rows)+"\n",encoding="utf-8")


class BoundGeneralScientificRawResourceV2Tests(unittest.TestCase):
    def test_repo_local_symbolic_executes_verified(self):
        repo=Path(__file__).resolve().parents[2]
        with tempfile.TemporaryDirectory(dir=repo/"canonical/astra_runtime/tmp") as td:
            root=Path(td)
            csv(root/"d.csv",["x","y"],[[x,3*x+2] for x in range(-9,10)])
            rel=root.relative_to(repo).as_posix()
            out=a.run({"instruction":"Predict y from x.","roots":[rel]},repo)
            self.assertTrue(out["verified"],out)
            self.assertEqual(out["family"],"SYMBOLIC_REGRESSION")
            self.assertEqual(out["model_dependency_count"],0)

    def test_repo_local_paraphrase_executes_verified(self):
        repo=Path(__file__).resolve().parents[2]
        with tempfile.TemporaryDirectory(dir=repo/"canonical/astra_runtime/tmp") as td:
            root=Path(td)
            csv(root/"d.csv",["dose","yield"],[[x,4*x-1] for x in range(-9,10)])
            rel=root.relative_to(repo).as_posix()
            out=a.run({"instruction":"Inputs: dose; outcome: yield.","roots":[rel]},repo)
            self.assertTrue(out["verified"],out)

    def test_absolute_root_forbidden(self):
        repo=Path(__file__).resolve().parents[2]
        with self.assertRaisesRegex(RuntimeError,"ABSOLUTE_SCIENCE_ROOT_FORBIDDEN"):
            a.run({"instruction":"Predict y from x.","roots":[str(repo)]},repo)

    def test_parent_escape_forbidden(self):
        repo=Path(__file__).resolve().parents[2]
        with self.assertRaisesRegex(RuntimeError,"SCIENCE_ROOT_OUTSIDE_REPOSITORY"):
            a.run({"instruction":"Predict y from x.","roots":["../"]},repo)

    def test_missing_root_forbidden(self):
        repo=Path(__file__).resolve().parents[2]
        with self.assertRaisesRegex(RuntimeError,"SCIENCE_ROOT_MISSING"):
            a.run({"instruction":"Predict y from x.","roots":["canonical/astra_runtime/tmp/definitely-missing-science-root"]},repo)

    def test_source_has_no_model_network_or_benchmark_identity(self):
        text=Path(a.__file__).read_text(encoding="utf-8").lower()
        for token in ("openai","anthropic","transformers","llama_cpp","ollama","vllm","litellm",
                      "rank21","rank22","rank23","terminal-bench","dna-storage","rv-astrometry"):
            self.assertNotIn(token,text)


if __name__=="__main__":
    unittest.main(verbosity=2)
