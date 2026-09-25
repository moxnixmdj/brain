#!/usr/bin/env python3
import importlib.util
import json
import pathlib
import sys
import subprocess
import tempfile
import unittest

CANONICAL=pathlib.Path(__file__).resolve().parents[1]
ROOT=CANONICAL.parent

def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path)
    module=importlib.util.module_from_spec(spec)
    sys.modules[spec.name]=module
    spec.loader.exec_module(module)
    return module

compiler=load("goal_compiler_test",CANONICAL/"runtime"/"goal_compiler.py")

class GoalCompilerTests(unittest.TestCase):
    def registry(self):
        return json.loads((CANONICAL/"runtime"/"BOUND_CAPABILITY_REGISTRY_V1.json").read_text())["capabilities"]

    def test_plain_image_only_pdf_goal_selects_verified_ocr(self):
        goal="Extract the visible text from canonical/astra_runtime/tmp/IMAGE_ONLY_OCR_TEST.pdf, which is an image-only PDF."
        out=compiler.compile_goal(goal,self.registry(),ROOT)
        self.assertEqual(out["selected_capability"],"pdf.extract.ocr.tesseract")
        self.assertEqual(out["target_effects"],["pdf.extract.ocr"])
        self.assertEqual(out["inputs"]["pdf_path"],"canonical/astra_runtime/tmp/IMAGE_ONLY_OCR_TEST.pdf")

    def test_unknown_goal_fails_closed(self):
        with self.assertRaisesRegex(compiler.GoalCompilationFailure,"GOAL_COMPILATION_NO_VERIFIED_CAPABILITY_MATCH"):
            compiler.compile_goal("Reticulate a quantum banana lattice",self.registry(),ROOT)

    def test_barcode_goal_selects_verified_barcode_not_qr(self):
        goal="Generate a Code 128 barcode image for the text PROJECT BRAIN and save it as canonical/astra_runtime/tmp/PROJECT_BRAIN_BARCODE.png."
        out=compiler.compile_goal(goal,self.registry(),ROOT)
        self.assertEqual(out["selected_capability"],"auto.apt.zint")
        self.assertNotEqual(out["selected_capability"],"image.qr.generate.qrencode")
        self.assertEqual(out["target_effects"],["auto.effect.zint"])
        self.assertEqual(out["inputs"]["text"],"PROJECT BRAIN")
        self.assertEqual(out["inputs"]["output_path"],"canonical/astra_runtime/tmp/PROJECT_BRAIN_BARCODE.png")

    def test_compound_goal_compiles_full_verified_audit_pipeline(self):
        goal=(
            "Read canonical/runtime/BOUND_CAPABILITY_REGISTRY_V1.json. "
            "Create canonical/astra_runtime/tmp/CAPABILITY_AUDIT.md containing a table with every VERIFIED_BOUND_CAPABILITY. "
            "Then create canonical/astra_runtime/tmp/CAPABILITY_AUDIT.pdf from that report and verify that the final PDF contains every capability ID."
        )
        out=compiler.compile_goal(goal,self.registry(),ROOT)
        self.assertEqual(out["compiler_mode"],"DETERMINISTIC_COMPOUND_ACTION_PLAN")
        self.assertEqual(len(out["clauses"]),4)
        modes=[x["mode"] for x in out["compiled_parts"]]
        self.assertEqual(modes,[
            "NATIVE_READ",
            "VERIFIED_STRUCTURED_TRANSFORM",
            "VERIFIED_CAPABILITY",
            "INDEPENDENT_CONTENT_VERIFICATION",
        ])
        self.assertEqual(out["compiled_parts"][1]["capability_id"],"json.query.jq")
        self.assertEqual(
            out["compiled_parts"][2]["selected_capability"],
            "document.convert.markdown_pdf.pandoc_weasyprint",
        )
        self.assertEqual(
            out["compiled_parts"][2]["inputs"]["markdown_path"],
            "canonical/astra_runtime/tmp/CAPABILITY_AUDIT.md",
        )
        self.assertEqual(
            out["compiled_parts"][2]["inputs"]["output_path"],
            "canonical/astra_runtime/tmp/CAPABILITY_AUDIT.pdf",
        )
        actions=out["controller_actions"]
        self.assertEqual([x["type"] for x in actions],[
            "read_file","invoke_capability","invoke_capability",
            "invoke_capability","assert_text_contains_json_keys","finish",
        ])
        ref=actions[4]["args"]["text"]["$result"]
        self.assertEqual(ref,{"cycle":3,"field":"text"})
        jq_action=actions[1]
        proc=subprocess.run(
            ["jq","-r",jq_action["args"]["filter"],
             str(ROOT/jq_action["args"]["input_path"])],
            text=True,capture_output=True,timeout=20,
        )
        self.assertEqual(proc.returncode,0,proc.stderr)
        self.assertIn("auto.apt.zint",proc.stdout)
        self.assertIn("| id |",proc.stdout)

    def test_replay_prefers_typed_context_over_stale_later_output(self):
        entry=self.registry()["document.convert.markdown_pdf.pandoc_weasyprint"]
        tmp_root=CANONICAL/"astra_runtime"/"tmp"
        tmp_root.mkdir(parents=True,exist_ok=True)
        with tempfile.TemporaryDirectory(dir=tmp_root) as td:
            td=pathlib.Path(td)
            md=td/"REPORT.md"
            pdf=td/"REPORT.pdf"
            md.write_text("# report\n",encoding="utf-8")
            pdf.write_bytes(b"%PDF-stale-output")
            md_rel=str(md.relative_to(ROOT)).replace("\\","/")
            pdf_rel=str(pdf.relative_to(ROOT)).replace("\\","/")
            goal=f"create {pdf_rel} from that report"
            inputs=compiler._bind_inputs(goal,ROOT,entry,context_paths=[md_rel])
            self.assertEqual(inputs["markdown_path"],md_rel)
            self.assertEqual(inputs["output_path"],pdf_rel)

    def test_json_status_manifest_compiles_and_executes(self):
        subgoal=(
            "Create canonical/astra_runtime/tmp/VERIFIED_EVIDENCE_MANIFEST.json "
            "containing one record for every VERIFIED_BOUND_CAPABILITY with its capability ID, "
            "verification mission ID, repository-local verification evidence or receipt paths when present, "
            "and source dependency names, versions, and hashes"
        )
        out=compiler._compile_json_status_manifest(
            subgoal,
            ["canonical/runtime/BOUND_CAPABILITY_REGISTRY_V1.json"],
            self.registry(),
            ROOT,
        )
        self.assertIsNotNone(out)
        action=out["action"]
        self.assertEqual(action["args"]["capability_id"],"json.query.jq")
        self.assertFalse(action["args"]["raw_output"])
        proc=subprocess.run(
            ["jq",action["args"]["filter"],str(ROOT/action["args"]["input_path"])],
            text=True,capture_output=True,timeout=20,
        )
        self.assertEqual(proc.returncode,0,proc.stderr)
        manifest=json.loads(proc.stdout)
        self.assertEqual(manifest["schema"],"PROJECT_BRAIN_STATUS_MANIFEST_V1")
        self.assertEqual(manifest["status_value"],"VERIFIED_BOUND_CAPABILITY")
        ids={x["capability_id"] for x in manifest["records"]}
        self.assertIn("auto.apt.zint",ids)
        zint=next(x for x in manifest["records"] if x["capability_id"]=="auto.apt.zint")
        self.assertEqual(zint["verification_mission_id"],"ASTRA-AUTO-VERIFY-ZINT-85BC9CD2C9A4")
        self.assertIsInstance(zint["source"],dict)

    def test_compound_evidence_bundle_compiles_manifest_archive_and_verifier(self):
        goal=(
            "Read canonical/runtime/BOUND_CAPABILITY_REGISTRY_V1.json. "
            "Create canonical/astra_runtime/tmp/VERIFIED_EVIDENCE_MANIFEST.json containing one record for every VERIFIED_BOUND_CAPABILITY "
            "with its capability ID, verification mission ID, repository-local verification evidence or receipt paths when present, "
            "and source dependency names, versions, and hashes. "
            "Then create canonical/astra_runtime/tmp/VERIFIED_EVIDENCE_BUNDLE.tar.gz containing that manifest and every repository-local "
            "verification evidence or receipt file referenced by the manifest. "
            "Finally verify independently that the archive contains the manifest plus every referenced repository-local evidence file "
            "and that the archived bytes hash exactly to the source bytes."
        )
        out=compiler.compile_goal(goal,self.registry(),ROOT)
        self.assertEqual(out["compiler_mode"],"DETERMINISTIC_COMPOUND_ACTION_PLAN")
        modes=[x["mode"] for x in out["compiled_parts"]]
        self.assertEqual(modes,[
            "NATIVE_READ",
            "VERIFIED_STRUCTURED_MANIFEST",
            "VERIFIED_CAPABILITY",
            "VERIFIED_CAPABILITY",
        ])
        self.assertEqual(out["compiled_parts"][2]["selected_capability"],"archive.tar_gz.create_from_manifest")
        self.assertEqual(out["compiled_parts"][3]["selected_capability"],"archive.verify.tar_gz.gnu")
        self.assertEqual(
            out["compiled_parts"][3]["inputs"]["manifest_path"],
            "canonical/astra_runtime/tmp/VERIFIED_EVIDENCE_MANIFEST.json",
        )
        self.assertEqual(
            out["compiled_parts"][3]["inputs"]["archive_path"],
            "canonical/astra_runtime/tmp/VERIFIED_EVIDENCE_BUNDLE.tar.gz",
        )

    def test_plain_qr_goal_selects_verified_qr_and_binds_arguments(self):
        goal="Generate a QR code image for the text PROJECT BRAIN and save it as canonical/astra_runtime/tmp/PROJECT_BRAIN_QR.png."
        out=compiler.compile_goal(goal,self.registry(),ROOT)
        self.assertEqual(out["selected_capability"],"image.qr.generate.qrencode")
        self.assertEqual(out["target_effects"],["image.qr.generate"])
        self.assertEqual(out["inputs"]["text"],"PROJECT BRAIN")
        self.assertEqual(out["inputs"]["output_path"],"canonical/astra_runtime/tmp/PROJECT_BRAIN_QR.png")

if __name__=="__main__":
    unittest.main(verbosity=2)
