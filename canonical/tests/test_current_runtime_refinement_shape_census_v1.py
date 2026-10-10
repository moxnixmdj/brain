from __future__ import annotations

import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from canonical.runtime.current_runtime_refinement_shape_census_v1 import run


def blob(path: Path) -> str:
    data=path.read_bytes()
    return hashlib.sha1(b"blob "+str(len(data)).encode("ascii")+b"\0"+data).hexdigest()


class CurrentRuntimeRefinementShapeCensusTests(unittest.TestCase):
    def fixture(self, sources):
        td=tempfile.TemporaryDirectory()
        root=Path(td.name)
        (root/"canonical/runtime").mkdir(parents=True)
        (root/"canonical/governance").mkdir(parents=True)
        obligations=[]
        for name,source in sources.items():
            p=root/"canonical/runtime"/name
            p.write_text(source,encoding="utf-8")
            obligations.append({
                "path":"canonical/runtime/"+name,
                "git_blob_sha":blob(p),
                "refinement_obligation_present":True,
            })
        snapshot={
            "coverage_complete":True,
            "obligations":obligations,
        }
        (root/"canonical/governance/CURRENT_AUTHORITY_RUNTIME_REFINEMENT_OBLIGATION_SNAPSHOT_20261010_V1.json").write_text(
            json.dumps(snapshot),encoding="utf-8"
        )
        return td,root

    def test_self_contained_module_is_lowest_direct_risk_class(self):
        td,root=self.fixture({"a.py":"def f(x):\n    return x+1\n"})
        try:
            out=run(root)
            self.assertEqual(out["rows"][0]["category"],"SELF_CONTAINED_NO_DIRECT_EFFECT")
        finally: td.cleanup()

    def test_canonical_runtime_import_is_transitive_dependency(self):
        td,root=self.fixture({"a.py":"from canonical.runtime.foo import bar\ndef f(x): return bar(x)\n"})
        try:
            out=run(root)
            self.assertEqual(out["rows"][0]["category"],"TRANSITIVE_RUNTIME_DEPENDENT")
        finally: td.cleanup()

    def test_process_or_io_surface_is_high_risk(self):
        td,root=self.fixture({"a.py":"import subprocess\ndef f(): return subprocess.run(['x'])\n"})
        try:
            out=run(root)
            self.assertEqual(out["rows"][0]["category"],"AUTHORITY_EFFECT_OR_DYNAMIC")
            self.assertTrue(out["rows"][0]["direct_dynamic_or_effect_surface"])
        finally: td.cleanup()

    def test_literal_authority_true_is_high_risk(self):
        td,root=self.fixture({"a.py":"def f(): return {'terminal_authority': True}\n"})
        try:
            out=run(root)
            self.assertEqual(out["rows"][0]["category"],"AUTHORITY_EFFECT_OR_DYNAMIC")
            self.assertTrue(out["rows"][0]["literal_authority_true_surface"])
        finally: td.cleanup()

    def test_incomplete_snapshot_is_rejected(self):
        td,root=self.fixture({"a.py":"X=1\n"})
        try:
            p=root/"canonical/governance/CURRENT_AUTHORITY_RUNTIME_REFINEMENT_OBLIGATION_SNAPSHOT_20261010_V1.json"
            raw=json.loads(p.read_text())
            raw["coverage_complete"]=False
            p.write_text(json.dumps(raw))
            with self.assertRaisesRegex(ValueError,"OBLIGATION_SNAPSHOT_NOT_COMPLETE"):
                run(root)
        finally: td.cleanup()

    def test_census_never_claims_semantic_or_terminal_authority(self):
        td,root=self.fixture({"a.py":"X=1\n"})
        try:
            out=run(root)
            self.assertFalse(out["semantic_refinement_proved"])
            self.assertFalse(out["terminal_authority"])
            self.assertEqual(out["terminal_credit_delta"],0)
        finally: td.cleanup()


if __name__=="__main__":
    unittest.main(verbosity=2)
