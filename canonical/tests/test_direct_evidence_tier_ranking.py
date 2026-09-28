#!/usr/bin/env python3
import pathlib,subprocess,sys,unittest
from unittest import mock
ROOT=pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"runtime"))
import capability_discovery as d

class EvidenceTierRankingTests(unittest.TestCase):
    def tearDown(self):
        d.set_external_apt_executable_evidence_searcher(None)

    def test_direct_executable_semantic_tier_beats_huge_lexical_score(self):
        def searcher(**kwargs):
            return [{
                "name":"direct-provider",
                "command_paths":["/usr/bin/direct-op"],
                "command_terms":["direct"],
                "manpage_commands":["direct-op"],
                "semantic_terms":["direct","operation"],
                "semantic_hits":["direct","operation"],
                "semantic_coverage":1.0,
            }]
        d.set_external_apt_executable_evidence_searcher(searcher)
        noisy="lexical-noise - direct operation direct operation direct operation direct operation\n"
        def fake_run(cmd,**kwargs):
            if cmd[:2]==["apt-cache","search"]:
                return subprocess.CompletedProcess(cmd,0,noisy,"")
            if cmd[:2]==["apt-cache","policy"]:
                return subprocess.CompletedProcess(cmd,0,"Candidate: 1.0\n","")
            if cmd[:2]==["apt-cache","show"]:
                return subprocess.CompletedProcess(cmd,0,"SHA256: "+"a"*64+"\n","")
            raise AssertionError(cmd)
        with mock.patch.object(d.subprocess,"run",side_effect=fake_run):
            out=d.search_apt_packages("Perform direct operation",limit=10)
        self.assertEqual(out["candidates"][0]["name"],"direct-provider")
        self.assertEqual(out["candidates"][0]["evidence_tier"],"DIRECT_EXECUTABLE_SEMANTIC")

if __name__=="__main__":
    unittest.main(verbosity=2)
