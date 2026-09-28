#!/usr/bin/env python3
import pathlib
import subprocess
import sys
import unittest
from unittest import mock

ROOT=pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"runtime"))
import capability_discovery as d


class BatchedExecutableEvidenceTests(unittest.TestCase):
    def tearDown(self):
        d.set_external_apt_executable_evidence_searcher(None)
        d._MANPAGE_TEXT_CACHE.clear()

    def test_local_acquisition_uses_one_literal_from_file_scan(self):
        calls=[]
        def fake_run(cmd,**kwargs):
            calls.append((list(cmd),dict(kwargs)))
            self.assertEqual(cmd[0],"apt-file")
            return subprocess.CompletedProcess(
                cmd,0,
                "pkg-a: usr/bin/metadata-inspect\n"
                "pkg-b: usr/bin/camera-metadata\n"
                "pkg-c: usr/share/doc/not-an-executable\n",
                ""
            )
        with mock.patch.object(d.shutil,"which",return_value="/usr/bin/apt-file"), \
             mock.patch.object(d.subprocess,"run",side_effect=fake_run), \
             mock.patch.object(d,"_fetch_ubuntu_manpage_text",return_value="camera metadata inspect"):
            out=d._local_apt_executable_evidence(
                "Inspect camera metadata from an image",limit=20
            )
        self.assertEqual(len(calls),1)
        cmd,kwargs=calls[0]
        self.assertIn("--from-file",cmd)
        self.assertIn("--stream-results",cmd)
        self.assertNotIn("-x",cmd)
        self.assertNotIn("--regexp",cmd)
        self.assertEqual(cmd[-2:],[ "search","-" ])
        self.assertIn("metadata",kwargs.get("input",""))
        self.assertTrue(out)
        self.assertTrue(all(x["acquisition_mode"]=="APT_FILE_FROM_FILE_LITERAL_BATCH" for x in out))

    def test_direct_executable_evidence_beats_large_lexical_score(self):
        def evidence_searcher(**kwargs):
            return [{
                "name":"direct-provider",
                "command_paths":["/usr/bin/direct-op"],
                "command_terms":["direct","operation"],
                "manpage_commands":[],
                "semantic_terms":["direct","operation"],
                "semantic_hits":["direct","operation"],
                "semantic_coverage":1.0,
                "acquisition_mode":"TEST",
            }]
        d.set_external_apt_executable_evidence_searcher(evidence_searcher)
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
        self.assertEqual(
            out["candidates"][0]["evidence_tier"],
            "DIRECT_EXECUTABLE_SEMANTIC"
        )

    def test_manpage_enrichment_fanout_is_bounded(self):
        lines=[]
        for i in range(30):
            lines.append(f"pkg-{i}: usr/bin/inspect-{i}")
        calls=[]
        def fake_run(cmd,**kwargs):
            return subprocess.CompletedProcess(cmd,0,"\n".join(lines)+"\n","")
        def fake_fetch(command,timeout_s=4,opener=None):
            calls.append(command)
            return "inspect metadata"
        with mock.patch.object(d.shutil,"which",return_value="/usr/bin/apt-file"), \
             mock.patch.object(d.subprocess,"run",side_effect=fake_run), \
             mock.patch.object(d,"_fetch_ubuntu_manpage_text",side_effect=fake_fetch):
            d._local_apt_executable_evidence("Inspect metadata",limit=36)
        self.assertLessEqual(len(calls),12)


if __name__=="__main__":
    unittest.main(verbosity=2)
