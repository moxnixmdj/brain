from __future__ import annotations
import json,math
from pathlib import Path
import tempfile,unittest
from canonical.runtime import scientific_numeric_task_compiler_v1 as c
from canonical.runtime import scientific_numeric_pipeline_v1 as p

class ScientificNumericTaskPipelineV1Tests(unittest.TestCase):
 def test_symbolic_instruction_and_schema_compile(self):
  rows=[{"x":x,"z":2*x,"y":3*x+2} for x in range(-8,9)]
  out=c.compile_numeric_task("Predict y from the observed numeric inputs.",rows)
  self.assertEqual(out["status"],"COMPILED",out)
  self.assertEqual(out["family"],"SYMBOLIC_REGRESSION")
  self.assertEqual(out["task_problem"]["target"],"y")
  self.assertIn("x",out["task_problem"]["inputs"])

 def test_periodic_instruction_discovers_time_and_ignores_error_column(self):
  rows=[]
  period=7.5
  for i in range(100):
   t=i*.3
   rows.append({"time":t,"flux":2+math.sin(2*math.pi*t/period),"flux_error":.05})
  out=c.compile_numeric_task("Estimate the dominant period of the periodic signal.",rows)
  self.assertEqual(out["status"],"COMPILED",out)
  self.assertEqual(out["family"],"SHARED_PERIOD_FITTING")
  self.assertEqual(out["provenance"]["time_column"],"time")
  self.assertEqual(out["provenance"]["signal_columns"],["flux"])

 def test_ambiguous_symbolic_and_periodic_intent_fails_closed(self):
  rows=[{"time":i*.2,"y":math.sin(i*.2)} for i in range(20)]
  out=c.compile_numeric_task("Predict y and estimate its period.",rows)
  self.assertEqual((out["status"],out["reason"]),("FAIL_CLOSED","AMBIGUOUS_SYMBOLIC_AND_PERIODIC_INTENT"))

 def test_unsupported_vague_instruction_fails_closed(self):
  rows=[{"x":i,"y":2*i} for i in range(12)]
  out=c.compile_numeric_task("Analyze this dataset thoroughly.",rows)
  self.assertEqual((out["status"],out["reason"]),("FAIL_CLOSED","NO_SUPPORTED_NUMERIC_SCIENCE_INTENT"))

 def test_sparse_rows_are_dropped_but_bounded(self):
  rows=[{"x":i,"y":2*i if i%5 else None} for i in range(30)]
  out=c.compile_numeric_task("Target y",rows)
  self.assertEqual(out["status"],"COMPILED",out)
  self.assertGreater(out["provenance"]["rows_dropped"],0)
  self.assertGreaterEqual(out["provenance"]["rows_used"],8)

 def test_end_to_end_symbolic_solve_and_artifact_materialization(self):
  rows=[{"x":float(x),"y":4.0*x-3.0} for x in range(-10,11)]
  specs=[
   {"relative_path":"solution.json","format":"json","value_path":"result"},
   {"relative_path":"report.md","format":"markdown","title":"Scientific result",
    "fields":[{"label":"Family","path":"family"},{"label":"Verified","path":"verification.pass"}]},
  ]
  with tempfile.TemporaryDirectory() as td:
   out=p.solve_and_materialize("Predict y from x.",rows,specs,td)
   self.assertEqual(out["status"],"PASS__NUMERIC_TASK_SOLVED_AND_ARTIFACTS_VERIFIED",out)
   self.assertTrue((Path(td)/"solution.json").is_file())
   self.assertTrue((Path(td)/"report.md").is_file())
   payload=json.loads((Path(td)/"solution.json").read_text(encoding="utf-8"))
   self.assertEqual(payload["status"],"EXACT_CANDIDATE_FOUND")

 def test_end_to_end_periodic_solve(self):
  period=8.0
  rows=[]
  for i in range(120):
   t=i*.29
   rows.append({"time":t,"signal":1+2.5*math.sin(2*math.pi*t/period+.3)})
  out=p.solve_numeric_task("Find the periodicity of the signal.",rows)
  self.assertEqual(out["status"],"PASS__NUMERIC_TASK_COMPILED_AND_VERIFIED",out)
  self.assertLess(abs(out["solution"]["result"]["period"]-period)/period,.02,out)

 def test_sources_do_not_route_on_benchmark_identifiers(self):
  text=(Path(c.__file__).read_text(encoding="utf-8")+"\n"+Path(p.__file__).read_text(encoding="utf-8")).lower()
  for token in ("rank21","rank22","rank23","dna-storage","rv-astrometry","terminal-bench"):
   self.assertNotIn(token,text)

if __name__=="__main__":
 unittest.main(verbosity=2)
