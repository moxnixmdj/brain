from __future__ import annotations

import ast
import json
import math
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from canonical.runtime import tb_science_zero_model_scientific_kernel_v1 as k
from canonical.runtime import harbor_science_zero_model_agent_v1 as a


class ZeroModelScienceKernelV1Tests(unittest.TestCase):
    def test_rank22_visible_family_name_routes_without_task_read(self):
        out=k.classify(
            "",
            "terminal-bench-science/rv-astrometry-fitting::trial-0",
        )
        self.assertEqual(out["route"],"SHARED_PERIOD_HARMONIC_FITTING")
        self.assertEqual(out["model_dependency_count"],0)

    def test_unrelated_family_fails_closed(self):
        out=k.classify("Summarize a qualitative manuscript.","synthetic")
        self.assertIsNone(out["route"])

    def test_exact_sources_import_no_model_runtime(self):
        forbidden={
            "openai","anthropic","transformers","torch","llama_cpp",
            "google.generativeai","vllm","litellm","ollama",
        }
        for module in (k,a):
            path=Path(module.__file__)
            tree=ast.parse(path.read_text(encoding="utf-8"),filename=str(path))
            imported=set()
            for node in ast.walk(tree):
                if isinstance(node,ast.Import):
                    imported.update(x.name for x in node.names)
                elif isinstance(node,ast.ImportFrom) and node.module:
                    imported.add(node.module)
            self.assertFalse(
                any(any(name==bad or name.startswith(bad+".") for bad in forbidden) for name in imported),
                (path,sorted(imported)),
            )

    def test_transfer_commands_are_bounded_and_network_free(self):
        data=Path(k.__file__).read_bytes()
        commands=a._append_commands("/tmp/kernel.py",data)
        self.assertGreater(len(commands),1)
        for command in commands:
            self.assertLessEqual(len(command),12000)
            low=command.lower()
            for token in ("curl ","wget ","git clone","git fetch","pip install","apt install"):
                self.assertNotIn(token,low)

    def test_synthetic_shared_period_fit_materializes_all_artifacts(self):
        true_period=12.5
        with tempfile.TemporaryDirectory() as td:
            root=Path(td)
            data=root/"observations.csv"
            with data.open("w",encoding="utf-8",newline="") as fh:
                fh.write("time,rv,ra\n")
                for i in range(160):
                    t=i*0.37
                    rv=20.0+4.5*math.sin(2*math.pi*t/true_period+0.3)+0.7*math.cos(4*math.pi*t/true_period)
                    ra=-2.0+1.8*math.sin(2*math.pi*t/true_period-0.6)+0.3*math.cos(4*math.pi*t/true_period)
                    fh.write(f"{t:.8f},{rv:.12f},{ra:.12f}\n")
            outputs=[root/"orbit.json",root/"predictions.csv",root/"report.md"]
            payload={
                "route":"SHARED_PERIOD_HARMONIC_FITTING",
                "instruction":"Fit radial velocity and astrometry and write required outputs.",
                "roots":[str(root)],
                "artifacts":[str(x) for x in outputs],
            }
            out=k.run_payload(payload)
            self.assertTrue(out["status"].startswith("PASS__"),out)
            self.assertEqual(out["model_dependency_count"],0)
            self.assertLess(abs(out["period"]-true_period)/true_period,0.02,out)
            for path in outputs:
                self.assertTrue(path.is_file() and path.stat().st_size>0,path)
            result=json.loads(outputs[0].read_text(encoding="utf-8"))
            self.assertEqual(result["model_dependency_count"],0)
            self.assertIn("K",result)
            self.assertIn("astrometric_amplitude",result)

    def test_agent_payload_uses_authoritative_artifacts_and_zero_model(self):
        env={
            "BRAIN_SLOT_ID":"terminal-bench-science/rv-astrometry-fitting::trial-0",
            "BRAIN_TASK_ARTIFACTS_JSON":json.dumps([
                "/results/orbit.json",
                "/results/predictions.csv",
                "/results/report.md",
            ]),
        }
        with patch.dict(os.environ,env,clear=False):
            out=a.build_payload("Fit RV and astrometry using /app/observations.csv.")
        self.assertEqual(out["route"],"SHARED_PERIOD_HARMONIC_FITTING")
        self.assertEqual(out["model_dependency_count"],0)
        self.assertEqual(out["artifacts"][0],"/results/orbit.json")
        self.assertIn("/app",out["roots"])


if __name__=="__main__":
    unittest.main(verbosity=2)
