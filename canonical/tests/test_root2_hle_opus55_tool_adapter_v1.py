from __future__ import annotations

import unittest
from canonical.runtime import root2_hle_opus55_tool_adapter_v1 as a

POLICY={
    "schema":"PROJECT_BRAIN_HLE_OPUS55_TOOL_POLICY_V1",
    "blocklist_patterns":["blocked.example","last-exam"],
}

class Tests(unittest.TestCase):
    def test_blocklist_normalization_matches_reference_semantics(self):
        self.assertEqual(a.block_match("HTTPS://Blocked.Example/path",POLICY),"blocked.example")
        self.assertEqual(a.block_match("https://safe.example/last-exam",POLICY),"last-exam")
        self.assertIsNone(a.block_match("https://safe.example/reference",POLICY))

    def test_search_filters_blocked_results(self):
        html=b"""<html>
          <a href="https://blocked.example/answer">bad</a>
          <a href="https://safe.example/paper">good</a>
        </html>"""
        def fetcher(url,**kwargs):
            return {"status":200,"final_url":url,"body":html}
        out=a.search_web("synthetic query",limit=1,policy=POLICY,fetcher=fetcher)
        self.assertEqual(out["status"],"PASS")
        self.assertEqual(out["results"][0]["url"],"https://safe.example/paper")
        self.assertGreaterEqual(out["blocked_result_count"],1)

    def test_fetch_rejects_blocked_initial_url(self):
        with self.assertRaises(a.HLEToolBlocked):
            a.fetch_web("https://blocked.example/a",policy=POLICY,fetcher=lambda *x,**k: {})

    def test_fetch_rejects_blocked_redirect(self):
        def fetcher(url,**kwargs):
            return {"status":200,"final_url":"https://blocked.example/answer","body":b"x"}
        with self.assertRaises(a.HLEToolBlocked):
            a.fetch_web("https://safe.example/start",policy=POLICY,fetcher=fetcher)

    def test_fetch_safe_records_hash_and_excerpt(self):
        def fetcher(url,**kwargs):
            return {"status":200,"final_url":"https://safe.example/final","body":b"hello"}
        out=a.fetch_web("https://safe.example/start",policy=POLICY,fetcher=fetcher)
        self.assertEqual(out["status"],"PASS")
        self.assertEqual(out["body_excerpt"],"hello")
        self.assertEqual(len(out["body_sha256"]),64)

    def test_code_math_executes(self):
        out=a.execute_code("import math\nprint(math.sqrt(81))")
        self.assertEqual(out["status"],"PASS")
        self.assertIn("9.0",out["stdout"])

    def test_code_network_import_rejected(self):
        for source in ("import socket","import urllib.request","import subprocess"):
            with self.assertRaises(a.HLEToolBlocked):
                a.execute_code(source)

    def test_code_dangerous_builtin_rejected(self):
        with self.assertRaises(a.HLEToolBlocked):
            a.execute_code("print(open('/etc/passwd').read())")

    def test_real_policy_loads_exact_count(self):
        policy=a.load_policy()
        self.assertEqual(len(policy["blocklist_patterns"]),153)
        self.assertIn("huggingface.co",policy["blocklist_patterns"])
        self.assertIn("shashankskagnihotri/Humanitys_Second_Last_Exam",policy["blocklist_patterns"])

    def test_result_redirect_parser(self):
        u=a._normalize_result_href("google","/url?q=https%3A%2F%2Fsafe.example%2Fx")
        self.assertEqual(u,"https://safe.example/x")

if __name__=="__main__":
    unittest.main(verbosity=2)
