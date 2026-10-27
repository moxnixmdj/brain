from __future__ import annotations

import base64
import pathlib
import tempfile
import unittest
from unittest.mock import patch

from canonical.runtime import root3_pandoc_artifact_executor_v1 as ex


def ctx(root: pathlib.Path):
    src=root/"in.md"; src.write_text("# Hello\n")
    return {
      "effect_class":"DECLARED_ARTIFACT_PRODUCTION",
      "api":"subprocess.run",
      "args":(["pandoc",str(src),"-o",str(root/"out.pdf"),"--pdf-engine=weasyprint"],),
      "kwargs":{"cwd":root,"text":True,"capture_output":True,"timeout":120},
      "callsite":{"module_path":"canonical/runtime/bound_capabilities/pandoc_weasyprint.py","lineno":24,"process_api":"subprocess.run"},
    }


class PandocArtifactExecutorTests(unittest.TestCase):
    def tools(self,name): return "/usr/bin/"+name

    def test_prepare_exact_current_surface(self):
        with tempfile.TemporaryDirectory() as td:
            root=pathlib.Path(td); c=ctx(root)
            with patch.object(ex,"_resolve_tool",side_effect=lambda n:"/usr/bin/"+n), patch.object(ex.confinement,"_inside_mounts",return_value=[]):
                p=ex._prepare(c)
            self.assertEqual(p["destination"],(root/"out.pdf").resolve())
            self.assertEqual(p["expected_pre_sha256"],"ABSENT")
            self.assertEqual(p["inner_argv"][0],"/usr/bin/pandoc")
            self.assertEqual(p["inner_argv"][-1],"--pdf-engine=/usr/bin/weasyprint")

    def test_wrong_callsite_denies(self):
        with tempfile.TemporaryDirectory() as td:
            root=pathlib.Path(td); c=ctx(root); c["callsite"]["lineno"]=25
            with self.assertRaisesRegex(ex.PandocArtifactDenied,"CALLSITE_NOT_SUPPORTED"):
                ex._prepare(c)

    def test_extra_process_kwarg_denies(self):
        with tempfile.TemporaryDirectory() as td:
            root=pathlib.Path(td); c=ctx(root); c["kwargs"]["check"]=False
            with self.assertRaisesRegex(ex.PandocArtifactDenied,"KWARGS_NOT_EXACT"):
                ex._prepare(c)

    def test_nested_repo_mount_denies(self):
        with tempfile.TemporaryDirectory() as td:
            root=pathlib.Path(td); c=ctx(root)
            with patch.object(ex.confinement,"_inside_mounts",return_value=["nested"]):
                with self.assertRaisesRegex(ex.PandocArtifactDenied,"NESTED_MOUNTS"):
                    ex._prepare(c)

    def test_success_stages_pdf_then_parent_commits(self):
        with tempfile.TemporaryDirectory() as td:
            root=pathlib.Path(td); c=ctx(root); payload=ex.PDF_MAGIC+b"ok"
            def fake(prepared,popen_impl):
                pathlib.Path(prepared["output_dir"],"artifact.pdf").write_bytes(payload)
                return {"timed_out":False,"returncode":0,"stdout_b64":base64.b64encode(b"ok").decode(),"stderr_b64":""}
            with patch.object(ex,"_resolve_tool",side_effect=lambda n:"/usr/bin/"+n), patch.object(ex.confinement,"_inside_mounts",return_value=[]), patch.object(ex.confinement,"_run_confined",side_effect=fake), patch.object(ex.os,"geteuid",create=True,return_value=-1):
                cp=ex.make_executor(popen_impl=lambda *a,**kw:None)(c)
            self.assertEqual(cp.returncode,0)
            self.assertEqual((root/"out.pdf").read_bytes(),payload)

    def test_nonzero_child_does_not_commit(self):
        with tempfile.TemporaryDirectory() as td:
            root=pathlib.Path(td); c=ctx(root); dst=root/"out.pdf"; dst.write_bytes(ex.PDF_MAGIC+b"old")
            def fake(prepared,popen_impl):
                return {"timed_out":False,"returncode":7,"stdout_b64":"","stderr_b64":base64.b64encode(b"bad").decode()}
            with patch.object(ex,"_resolve_tool",side_effect=lambda n:"/usr/bin/"+n), patch.object(ex.confinement,"_inside_mounts",return_value=[]), patch.object(ex.confinement,"_run_confined",side_effect=fake), patch.object(ex.os,"geteuid",create=True,return_value=-1):
                cp=ex.make_executor(popen_impl=lambda *a,**kw:None)(c)
            self.assertEqual(cp.returncode,7)
            self.assertEqual(dst.read_bytes(),ex.PDF_MAGIC+b"old")


if __name__=="__main__":
    unittest.main(verbosity=2)
