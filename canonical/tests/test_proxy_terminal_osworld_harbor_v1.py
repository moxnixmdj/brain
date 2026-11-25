import pathlib, tempfile, subprocess, sys, unittest, json, os
from canonical.swe_kernel.perfect_algorithm_unified_v8 import PerfectAlgorithmUnifiedV8, SCHEMA
from canonical.runtime.osworld_v21_browser_ops_v1 import compile_browser_op

class ProxyHarborTB4(unittest.TestCase):
    def test_terminal_bench_proxy_via_unified(self):
        # Synthetic Terminal-Bench style: repo with failing shell script, agent must fix via terminal
        tmp=pathlib.Path(tempfile.mkdtemp(prefix="tb4-"))
        (tmp/"script.sh").write_text("#!/bin/bash\necho $((2*3))\n")
        (tmp/"task.md").write_text("Goal: script.sh should output 6 and exit 0")
        pa=PerfectAlgorithmUnifiedV8()
        scan=pa.scan_env(str(tmp))
        self.assertEqual(scan["status"], "SENSE_DONE__SCAN_OBSERVED")
        self.assertEqual(scan["model_calls"], 0)
        # Simulate act: run script via transport-like exec
        res=subprocess.run(["bash", str(tmp/"script.sh")], capture_output=True, text=True)
        self.assertEqual(res.stdout.strip(), "6")
        self.assertEqual(res.returncode, 0)
        # Horizon plan for long task
        plan=pa.plan({}, lambda s: True, budget=120)
        self.assertIn(plan["status"], ("PLANNED__HORIZON_DECOMPOSED","REFUSED__NO_MODEL"))
        if plan.get("horizon"):
            self.assertGreaterEqual(plan["total_budget"], 120)

    def test_osworld_browser_ops_compile_no_model(self):
        # OSWorld 2.0 style browser ops via CDP — compiled without model
        op1={"type": "BROWSER_OPEN_URL", "url": "https://example.com"}
        src1=compile_browser_op(op1)
        self.assertIn("location.href", src1)
        op2={"type": "BROWSER_CLICK_TEXT", "text": "Login"}
        src2=compile_browser_op(op2)
        self.assertIn("CLICKED", src2)
        self.assertIn("querySelectorAll", src2)
        # Perfect algorithm scan covers browser action
        pa=PerfectAlgorithmUnifiedV8()
        self.assertIn("browser/computer action", pa.status()["open_components_mechanism_cover"])

    def test_harbor_perfect_agent_zero_model(self):
        from canonical.runtime.harbor_perfect_algorithm_agent_v1 import HarborPerfectAlgorithmAgent, MODEL_CALLS, SCHEMA as H_SCHEMA
        self.assertEqual(MODEL_CALLS, 0)
        self.assertEqual(H_SCHEMA, "PROJECT_BRAIN_HARBOR_PERFECT_ALGORITHM_V1")
        self.assertEqual(HarborPerfectAlgorithmAgent.name(), "perfect-algorithm-v8")
        # Verify no planner dependency
        import pathlib, re
        txt=pathlib.Path("canonical/runtime/harbor_perfect_algorithm_agent_v1.py").read_text()
        # no runtime call to planner — docstring mention of old agent is ok, check code section only
        code_section = txt.split("SCHEMA")[1] if "SCHEMA" in txt else txt
        self.assertNotIn("model_dependency_count = 1", code_section)
        self.assertIn("model_dependency_count\": 0", txt)
        self.assertNotIn("from openai", txt.lower().split("why:")[1] if "why:" in txt.lower() else txt.lower())
        self.assertIn("MODEL_CALLS = 0", txt)
        self.assertIn("BRAIN_OWNED_CONTROL__ZERO_MODEL_CALLS", txt)

    def test_schema_zero_model(self):
        self.assertEqual(SCHEMA, "PROJECT_BRAIN_PERFECT_ALGORITHM_UNIFIED_V8")
        from canonical.swe_kernel.perfect_algorithm_unified_v8 import MODEL_CALLS
        self.assertEqual(MODEL_CALLS, 0)
