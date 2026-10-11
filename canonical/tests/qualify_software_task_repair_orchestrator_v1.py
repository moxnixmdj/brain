import importlib.util, json, pathlib, sys, tempfile, textwrap, hashlib

ROOT=pathlib.Path("/home/sprite/coding-fresh-qualification-v1")
P=ROOT/"canonical/runtime/bound_capabilities/software_task_repair_orchestrator_v1.py"
spec=importlib.util.spec_from_file_location("orch_qual",P)
orch=importlib.util.module_from_spec(spec); spec.loader.exec_module(orch)

def run_case(case):
    with tempfile.TemporaryDirectory(prefix="qual_") as td:
        r=pathlib.Path(td)
        for name,content in case["files"].items():
            (r/name).write_text(content,encoding="utf-8")
        (r/"test_app.py").write_text(textwrap.dedent(case["test"]),encoding="utf-8")
        before={name:(r/name).read_bytes() for name in case["files"]}
        args={
            "task_text":case["task"],
            "test_paths":["test_app.py"],
            "test_argv":[sys.executable,"test_app.py"],
            "output_path":"result.json",
            "max_candidates":1000,
            "beam_width":24,
            "max_edits":2,
            "timeout_s":5,
        }
        if case.get("source_paths") is not None:
            args["source_paths"]=case["source_paths"]
        out=orch.run(args,r)
        restored=all((r/name).read_bytes()==raw for name,raw in before.items())
        observed={
            "name":case["name"],
            "expected_class":case["expected_class"],
            "status":out["status"],
            "pass":out["pass"],
            "acceptance_complete":out["acceptance_complete"],
            "repair_executed":out["repair_executed"],
            "source_restored":restored,
            "winning_edit_count":out.get("winning_edit_count"),
            "repair_source_selection":out.get("repair_source_selection"),
            "model_dependency_count":out["model_dependency_count"],
            "incremental_spend_usd":out["incremental_spend_usd"],
            "unified_diff":out.get("unified_diff"),
        }
        ok=restored and out["model_dependency_count"]==0 and out["incremental_spend_usd"]==0
        cls=case["expected_class"]
        if cls=="REPAIRED":
            ok=ok and out["pass"] and out["acceptance_complete"] and out["repair_executed"] and bool(out.get("unified_diff"))
        elif cls=="BLOCKED_UNBOUND":
            ok=ok and (not out["pass"]) and (not out["acceptance_complete"]) and (not out["repair_executed"]) and not out.get("unified_diff")
        elif cls=="ALREADY_SATISFIED":
            ok=ok and out["pass"] and out["acceptance_complete"] and out["status"]=="PASS__EXPLICIT_TASK_ALREADY_SATISFIED_BY_BOUND_TESTS"
        elif cls=="BOUNDED_NO_SOLUTION":
            ok=ok and (not out["pass"]) and out["acceptance_complete"] and out["repair_executed"] and out["status"]=="OPEN__EXPLICIT_TASK_BOUND__NO_VERIFIED_CANDIDATE_IN_BOUNDED_REPAIR"
        observed["qualification_pass"]=bool(ok)
        return observed

cases=[
 {
  "name":"fresh_binop_floor_div",
  "expected_class":"REPAIRED",
  "files":{"mathbox.py":"def quotient():\n    return 12 * 3\n"},
  "test":"""import unittest
from mathbox import quotient
class Q(unittest.TestCase):
 def test_q(self): self.assertEqual(quotient(),4)
if __name__=='__main__': unittest.main()
""",
  "task":"quotient must return 4.",
 },
 {
  "name":"fresh_two_file_bool_string",
  "expected_class":"REPAIRED",
  "files":{"flags.py":"def enabled():\n    return False\n","labels.py":"def label():\n    return 'old'\n"},
  "test":"""import unittest
from flags import enabled
from labels import label
class Q(unittest.TestCase):
 def test_enabled(self): self.assertEqual(enabled(),True)
 def test_label(self): self.assertEqual(label(),'new')
if __name__=='__main__': unittest.main()
""",
  "task":"enabled must return true and label must return 'new'.",
  "source_paths":["flags.py","labels.py"],
 },
 {
  "name":"fresh_auto_localized_sub_to_add",
  "expected_class":"REPAIRED",
  "files":{"aggregate.py":"def sum_values():\n    return 10 - 3\n"},
  "test":"""import unittest
from aggregate import sum_values
class Q(unittest.TestCase):
 def test_sum(self): self.assertEqual(sum_values(),13)
if __name__=='__main__': unittest.main()
""",
  "task":"sum_values must return 13.",
 },
 {
  "name":"fresh_unbound_semantics_refusal",
  "expected_class":"BLOCKED_UNBOUND",
  "files":{"mathbox.py":"def quotient():\n    return 12 * 3\n"},
  "test":"""import unittest
from mathbox import quotient
class Q(unittest.TestCase):
 def test_q(self): self.assertEqual(quotient(),4)
if __name__=='__main__': unittest.main()
""",
  "task":"quotient must return 4 without changing performance.",
  "source_paths":["mathbox.py"],
 },
 {
  "name":"fresh_already_satisfied",
  "expected_class":"ALREADY_SATISFIED",
  "files":{"labels.py":"def label():\n    return 'ready'\n"},
  "test":"""import unittest
from labels import label
class Q(unittest.TestCase):
 def test_label(self): self.assertEqual(label(),'ready')
if __name__=='__main__': unittest.main()
""",
  "task":"label must return 'ready'.",
  "source_paths":["labels.py"],
 },
 {
  "name":"fresh_bounded_no_solution",
  "expected_class":"BOUNDED_NO_SOLUTION",
  "files":{"scale.py":"def double(x):\n    return x\n"},
  "test":"""import unittest
from scale import double
class Q(unittest.TestCase):
 def test_double(self): self.assertEqual(double(3),6)
if __name__=='__main__': unittest.main()
""",
  "task":"double must return 6.",
  "source_paths":["scale.py"],
 }
]
results=[run_case(c) for c in cases]
summary={
 "schema":"PROJECT_BRAIN_FRESH_NON_BENCHMARK_SOFTWARE_TASK_QUALIFICATION_V1_RUNTIME",
 "case_count":len(results),
 "passed_count":sum(x["qualification_pass"] for x in results),
 "failed_count":sum(not x["qualification_pass"] for x in results),
 "all_pass":all(x["qualification_pass"] for x in results),
 "results":results,
}
print(json.dumps(summary,indent=2,sort_keys=True))
if not summary["all_pass"]:
    raise SystemExit(1)
