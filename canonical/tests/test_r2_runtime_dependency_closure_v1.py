from __future__ import annotations

import json
from pathlib import Path
import tempfile
import unittest

from canonical.runtime import r2_runtime_dependency_closure_v1 as closure
from canonical.runtime import r2_direct_route_dynamic_admission_v1 as admission


def write(root:Path,rel:str,text:str)->Path:
    p=root/rel
    p.parent.mkdir(parents=True,exist_ok=True)
    p.write_text(text,encoding="utf-8")
    return p


def write_json(root:Path,rel:str,obj:dict)->Path:
    return write(root,rel,json.dumps(obj,indent=2,sort_keys=True)+"\n")


class RuntimeDependencyClosureV1Tests(unittest.TestCase):
    def test_recursive_absolute_and_relative_imports_are_pinned(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td)
            write(root,"canonical/runtime/__init__.py","")
            write(root,"canonical/runtime/a.py","from canonical.runtime import b\n")
            write(root,"canonical/runtime/b.py","from .c import VALUE\n")
            write(root,"canonical/runtime/c.py","VALUE=1\n")
            out=closure.build(root,"canonical/runtime/a.py")
            self.assertEqual(
                [x["path"] for x in out["files"]],
                [
                    "canonical/runtime/__init__.py",
                    "canonical/runtime/a.py",
                    "canonical/runtime/b.py",
                    "canonical/runtime/c.py",
                ],
            )
            self.assertEqual(out["file_count"],4)
            self.assertEqual(
                closure.validate(root,"canonical/runtime/a.py",out),
                out,
            )

    def test_dependency_content_drift_fails(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td)
            write(root,"canonical/runtime/__init__.py","")
            write(root,"canonical/runtime/a.py","from canonical.runtime import b\n")
            write(root,"canonical/runtime/b.py","VALUE=1\n")
            pinned=closure.build(root,"canonical/runtime/a.py")
            write(root,"canonical/runtime/b.py","VALUE=2\n")
            with self.assertRaisesRegex(
                closure.RuntimeClosureError,
                "RUNTIME_DEPENDENCY_BLOB_DRIFT",
            ):
                closure.validate(root,"canonical/runtime/a.py",pinned)

    def test_dependency_graph_drift_fails(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td)
            write(root,"canonical/runtime/__init__.py","")
            write(root,"canonical/runtime/a.py","from canonical.runtime import b\n")
            write(root,"canonical/runtime/b.py","VALUE=1\n")
            write(root,"canonical/runtime/c.py","VALUE=3\n")
            pinned=closure.build(root,"canonical/runtime/a.py")
            write(
                root,
                "canonical/runtime/b.py",
                "from canonical.runtime import c\nVALUE=1\n",
            )
            with self.assertRaisesRegex(
                closure.RuntimeClosureError,
                "RUNTIME_DEPENDENCY_GRAPH_DRIFT",
            ):
                closure.validate(root,"canonical/runtime/a.py",pinned)

    def test_unresolved_dynamic_import_fails_closed(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td)
            write(root,"canonical/runtime/__init__.py","")
            write(
                root,
                "canonical/runtime/a.py",
                "import importlib\nname='canonical.runtime.b'\n"
                "x=importlib.import_module(name)\n",
            )
            write(root,"canonical/runtime/b.py","VALUE=1\n")
            with self.assertRaisesRegex(
                closure.RuntimeClosureError,
                "RUNTIME_DYNAMIC_IMPORT_UNRESOLVED",
            ):
                closure.build(root,"canonical/runtime/a.py")

    def test_external_imports_do_not_pollute_closure(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td)
            write(root,"canonical/runtime/__init__.py","")
            write(root,"canonical/runtime/a.py","import json\nfrom pathlib import Path\n")
            out=closure.build(root,"canonical/runtime/a.py")
            self.assertEqual(
                [x["path"] for x in out["files"]],
                ["canonical/runtime/a.py"],
            )


class DynamicAdmissionClosureBindingTests(unittest.TestCase):
    def _fixture(self,root:Path):
        write(root,"canonical/runtime/__init__.py","")
        runtime=write(
            root,
            "canonical/runtime/route.py",
            "from canonical.runtime import dep\n"
            "def preflight(request,repo_root=None): return {'matched':False}\n"
            "def run(request,repo_root=None): return {'matched':False}\n",
        )
        write(root,"canonical/runtime/dep.py","VALUE=1\n")
        verification=write_json(
            root,
            "canonical/verification/verify.json",
            {"schema":"FIXTURE_VERIFY","status":"PASS"},
        )
        candidate={
            "schema":admission.CANDIDATE_SCHEMA,
            "route_id":"DIRECT_ADEQUACY::FIXTURE",
            "capability_id":"fixture",
            "deployment_requested":True,
            "selection_class":admission.SELECTION_CLASS,
            "runtime_path":"canonical/runtime/route.py",
            "runtime_git_blob_sha":admission.git_blob_sha(runtime),
            "preflight_callable":"preflight",
            "run_callable":"run",
            "route_verification_path":"canonical/verification/verify.json",
            "route_verification_git_blob_sha":admission.git_blob_sha(verification),
            "scope":"FIXTURE",
            "incremental_spend_usd":0,
            "terminal_authority":False,
        }
        cp=write_json(
            root,
            "canonical/governance/candidate.json",
            candidate,
        )
        receipt={
            "schema":admission.RECEIPT_SCHEMA,
            "status":"INDEPENDENT_PASS__R2_DIRECT_ROUTE_DEPLOYMENT",
            "candidate_path":"canonical/governance/candidate.json",
            "candidate_git_blob_sha":admission.git_blob_sha(cp),
            "route_id":candidate["route_id"],
            "runtime_path":candidate["runtime_path"],
            "runtime_git_blob_sha":candidate["runtime_git_blob_sha"],
            "route_verification_path":candidate["route_verification_path"],
            "route_verification_git_blob_sha":candidate["route_verification_git_blob_sha"],
            "selection_class":admission.SELECTION_CLASS,
            "independent_verified":True,
            "preflight_pure_no_effect":True,
            "matched_route_failure_no_fallthrough":True,
            "producer_independent_acceptance":True,
            "exact_raw_obligation_acceptance":True,
            "deployment_eligible":True,
            "verification_authority_mutated":False,
            "promotion_authority":False,
            "terminal_authority":False,
            "incremental_spend_usd":0,
        }
        write_json(
            root,
            "canonical/verification/receipt.json",
            receipt,
        )
        manifest={
            "schema":admission.MANIFEST_SCHEMA,
            "status":"ACTIVE_DYNAMIC_ADMISSIONS__EMPTY",
            "selection_class":admission.SELECTION_CLASS,
            "collision_policy":"FAIL_CLOSED_ON_ANY_OTHER_DYNAMIC_OR_LEGACY_MATCH",
            "admission_count":0,
            "admissions":[],
            "terminal_authority":False,
        }
        return manifest

    def test_compile_admission_pins_recursive_runtime_closure(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td)
            manifest=self._fixture(root)
            out=admission.compile_admission(
                repo_root=root,
                current_manifest=manifest,
                candidate_path="canonical/governance/candidate.json",
                receipt_path="canonical/verification/receipt.json",
            )
            self.assertTrue(out["pass"],out)
            row=out["admission_row"]
            paths=[x["path"] for x in row["runtime_dependency_closure"]["files"]]
            self.assertIn("canonical/runtime/route.py",paths)
            self.assertIn("canonical/runtime/dep.py",paths)
            admission.validate_manifest(root,out["manifest"])

    def test_manifest_rejects_dependency_drift_after_admission(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td)
            manifest=self._fixture(root)
            out=admission.compile_admission(
                repo_root=root,
                current_manifest=manifest,
                candidate_path="canonical/governance/candidate.json",
                receipt_path="canonical/verification/receipt.json",
            )
            write(root,"canonical/runtime/dep.py","VALUE=9\n")
            with self.assertRaisesRegex(
                admission.DynamicAdmissionError,
                "RUNTIME_DEPENDENCY_CLOSURE_INVALID",
            ):
                admission.validate_manifest(root,out["manifest"])


if __name__=="__main__":
    unittest.main(verbosity=2)
