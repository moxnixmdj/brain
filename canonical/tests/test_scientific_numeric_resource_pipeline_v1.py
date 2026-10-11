from __future__ import annotations
import json,math
from pathlib import Path
import tempfile,unittest

from canonical.runtime import scientific_numeric_resource_pipeline_v1 as p


class ScientificNumericResourcePipelineV1Tests(unittest.TestCase):
    def test_symbolic_csv_resource_end_to_end(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td)
            f=root/"experiment.csv"
            f.write_text("x,y\n"+"\n".join(f"{x},{4*x+3}" for x in range(-10,11))+"\n",encoding="utf-8")
            out=p.execute("Predict y from x.",[root])
            self.assertTrue(out["verified"],out)
            self.assertEqual(out["scientific_pipeline"]["family"],"SYMBOLIC_REGRESSION")
            self.assertEqual(Path(out["resource_binding"]["selected_path"]).name,"experiment.csv")

    def test_periodic_tsv_resource_end_to_end(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td); f=root/"series.tsv"; period=6.4
            rows=["time\tflux\tflux_error"]
            for i in range(140):
                t=i*.21; rows.append(f"{t}\t{2+3*math.sin(2*math.pi*t/period+.2)}\t0.02")
            f.write_text("\n".join(rows)+"\n",encoding="utf-8")
            out=p.execute("Estimate the dominant periodicity.",[root])
            self.assertTrue(out["verified"],out)
            got=out["scientific_pipeline"]["scientific_result"]["result"]["period"]
            self.assertLess(abs(got-period)/period,.02,out)

    def test_json_records_resource_end_to_end(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td); f=root/"rows.json"
            f.write_text(json.dumps({"records":[{"x":x,"y":2*x-1} for x in range(-9,10)]}),encoding="utf-8")
            out=p.execute("Target y",[f])
            self.assertTrue(out["verified"],out)

    def test_irrelevant_table_is_ignored_when_one_table_compiles(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td)
            (root/"irrelevant.csv").write_text("a,b\n"+"\n".join(f"{i},{i+1}" for i in range(12))+"\n",encoding="utf-8")
            (root/"target.csv").write_text("x,y\n"+"\n".join(f"{i},{3*i}" for i in range(12))+"\n",encoding="utf-8")
            out=p.execute("Predict y from x.",[root])
            self.assertTrue(out["verified"],out)
            self.assertTrue(out["resource_binding"]["selected_path"].endswith("target.csv"))

    def test_multiple_compilable_tables_fail_closed(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td)
            for name,m in (("a.csv",2),("b.csv",3)):
                (root/name).write_text("x,y\n"+"\n".join(f"{i},{m*i}" for i in range(12))+"\n",encoding="utf-8")
            out=p.execute("Predict y from x.",[root])
            self.assertFalse(out["pass"])
            self.assertEqual(out["reason"],"AMBIGUOUS_MULTIPLE_COMPILABLE_NUMERIC_RESOURCES")

    def test_no_compilable_resource_fails_closed(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td)
            (root/"data.csv").write_text("a,b\n"+"\n".join(f"{i},{i+1}" for i in range(12))+"\n",encoding="utf-8")
            out=p.execute("Predict y from x.",[root])
            self.assertFalse(out["pass"])
            self.assertEqual(out["reason"],"NO_COMPILABLE_NUMERIC_RESOURCE")

    def test_output_root_is_excluded_from_future_resource_binding(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td); data=root/"data"; outdir=root/"out"; data.mkdir(); outdir.mkdir()
            (data/"d.csv").write_text("x,y\n"+"\n".join(f"{i},{5*i}" for i in range(12))+"\n",encoding="utf-8")
            specs=[{"relative_path":"solution.json","format":"json","value_path":"result"}]
            first=p.execute("Predict y from x.",[root],artifact_specs=specs,output_root=outdir)
            second=p.execute("Predict y from x.",[root],artifact_specs=specs,output_root=outdir)
            self.assertTrue(first["verified"] and second["verified"],(first,second))
            self.assertEqual(first["resource_binding"]["selected_path"],second["resource_binding"]["selected_path"])

    def test_deterministic_binding_and_execution(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td)
            (root/"d.csv").write_text("x,y\n"+"\n".join(f"{i},{i*i}" for i in range(-8,9))+"\n",encoding="utf-8")
            a=p.execute("Model y using x.",[root])
            b=p.execute("Model y using x.",[root])
            self.assertEqual(a,b)

    def test_source_has_no_model_or_benchmark_routing(self):
        text=Path(p.__file__).read_text(encoding="utf-8").lower()
        for token in ("openai","anthropic","transformers","llama_cpp","ollama","vllm","litellm",
                      "rank21","rank22","rank23","terminal-bench","rv-astrometry","dna-storage"):
            self.assertNotIn(token,text)
        self.assertEqual(p.MODEL_DEPENDENCY_COUNT,0)
        self.assertEqual(p.EXTERNAL_MODEL_RUNTIME_CALLS,0)
        self.assertEqual(p.NETWORK_DEPENDENCY_COUNT,0)


if __name__=="__main__":
    unittest.main(verbosity=2)
