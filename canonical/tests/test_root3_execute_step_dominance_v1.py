from __future__ import annotations
import pathlib
import tempfile
import unittest

from canonical.runtime.root3_execute_step_dominance_v1 import audit, TARGET


class ExecuteStepDominanceTests(unittest.TestCase):
    def test_current_runtime_passes(self):
        root=pathlib.Path(__file__).resolve().parents[2]
        out=audit(root)
        self.assertEqual(out["status"],"PASS",out)
        self.assertEqual(out["adapter_set"],["goal","http","shell"])
        self.assertEqual(out["accounting"]["acceptance_credit_delta"],0)

    def test_synthetic_direct_capability_bypass_fails_closed(self):
        source=pathlib.Path(__file__).resolve().parents[2]/TARGET
        raw=source.read_text(encoding="utf-8")
        with tempfile.TemporaryDirectory() as td:
            root=pathlib.Path(td)
            dst=root/TARGET
            dst.parent.mkdir(parents=True,exist_ok=True)
            dst.write_text(
                raw+"\n\ndef synthetic_bypass():\n    return _invoke_bound_capability({})\n",
                encoding="utf-8",
            )
            out=audit(root)
            self.assertEqual(out["status"],"FAIL_CLOSED")
            self.assertTrue(
                any(
                    e.get("type")=="CALLER_SET_DRIFT"
                    and e.get("callee")=="_invoke_bound_capability"
                    for e in out["errors"]
                ),
                out,
            )

    def test_synthetic_new_adapter_fails_closed(self):
        source=pathlib.Path(__file__).resolve().parents[2]/TARGET
        raw=source.read_text(encoding="utf-8")
        needle='    if adapter=="goal":\n        return run_goal(step, mission or {})\n'
        self.assertIn(needle,raw)
        modified=raw.replace(
            needle,
            needle+'    if adapter=="new_effectful_adapter":\n        return {}\n',
            1,
        )
        with tempfile.TemporaryDirectory() as td:
            root=pathlib.Path(td)
            dst=root/TARGET
            dst.parent.mkdir(parents=True,exist_ok=True)
            dst.write_text(modified,encoding="utf-8")
            out=audit(root)
            self.assertEqual(out["status"],"FAIL_CLOSED")
            self.assertTrue(
                any(e.get("type")=="ADAPTER_SET_DRIFT" for e in out["errors"]),
                out,
            )


if __name__=="__main__":
    unittest.main(verbosity=2)
