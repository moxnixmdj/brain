#!/usr/bin/env python3
import importlib.util,pathlib,subprocess,sys,unittest
from unittest import mock

ROOT=pathlib.Path(__file__).resolve().parents[1]
RUNTIME=ROOT/"runtime"
sys.path.insert(0,str(RUNTIME))
import capability_discovery as d

class ExecutableSemanticEvidenceTests(unittest.TestCase):
    def tearDown(self):
        d.set_external_apt_executable_evidence_searcher(None)

    def test_external_evidence_can_promote_nonlexical_executable_candidate(self):
        def searcher(**kwargs):
            return [{
                "name":"semantic-tool",
                "command_paths":["/usr/bin/semantic-convert"],
                "command_terms":["semantic","convert"],
                "manpage_commands":["semantic-convert"],
                "semantic_terms":["semantic","format","convert"],
                "semantic_hits":["semantic","format","convert"],
                "semantic_coverage":1.0,
            }]
        d.set_external_apt_executable_evidence_searcher(searcher)

        def fake_run(cmd,**kwargs):
            if cmd[:2]==["apt-cache","search"]:
                return subprocess.CompletedProcess(cmd,0,"noise-package - unrelated semantic helper\n","")
            if cmd[:2]==["apt-cache","policy"]:
                return subprocess.CompletedProcess(cmd,0,"Candidate: 1.0\n","")
            if cmd[:2]==["apt-cache","show"]:
                return subprocess.CompletedProcess(cmd,0,"SHA256: "+"a"*64+"\n","")
            raise AssertionError(cmd)

        with mock.patch.object(d.subprocess,"run",side_effect=fake_run):
            out=d.search_apt_packages("Convert semantic format",limit=10)
        self.assertEqual(out["candidates"][0]["name"],"semantic-tool")
        ev=out["candidates"][0]["executable_semantic_evidence"]
        self.assertEqual(ev["semantic_coverage"],1.0)
        self.assertGreater(ev["evidence_bonus"],0)

if __name__=="__main__":
    unittest.main(verbosity=2)
