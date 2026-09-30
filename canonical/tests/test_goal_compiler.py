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

    def test_decompose_preserves_independent_reread_and_verify_tail(self):
        goal=(
            "Read the UUID from that live result. "
            "Finally independently reread both files and verify the bucket is correct for the actual UUID."
        )
        clauses=compiler.decompose_goal(goal)
        self.assertEqual(clauses,[
            "Read the UUID from that live result",
            "Finally independently reread both files and verify the bucket is correct for the actual UUID",
        ])

    def test_plain_image_only_pdf_goal_selects_verified_ocr(self):
        goal="Extract the visible text from canonical/astra_runtime/tmp/IMAGE_ONLY_OCR_TEST.pdf, which is an image-only PDF."
        out=compiler.compile_goal(goal,self.registry(),ROOT)
        self.assertEqual(out["selected_capability"],"pdf.extract.ocr.tesseract")
        self.assertEqual(out["target_effects"],["pdf.extract.ocr"])
        self.assertEqual(out["inputs"]["pdf_path"],"canonical/astra_runtime/tmp/IMAGE_ONLY_OCR_TEST.pdf")

    def test_unknown_goal_fails_closed(self):
        with self.assertRaisesRegex(compiler.GoalCompilationFailure,"GOAL_COMPILATION_NO_VERIFIED_CAPABILITY_MATCH"):
            compiler.compile_goal("Reticulate a quantum banana lattice",self.registry(),ROOT)

    def test_browser_goal_binds_url_and_typed_future_outputs(self):
        registry={
          "web.browser.rendered.capture.test":{
            "status":"VERIFIED_BOUND_CAPABILITY",
            "provides":["web.browser.rendered.capture"],
            "requires":[],
            "keywords":["browser","rendered","web","screenshot","url"],
            "action_template":{
              "type":"invoke_capability",
              "args":{
                "capability_id":"web.browser.rendered.capture.test",
                "url":"${input.url}",
                "screenshot_path":"${input.screenshot_path}",
                "result_path":"${input.result_path}"
              },
              "expect":{"type":"field_equals","field":"output_verified","value":True}
            }
          }
        }
        goal=("Using a rendered browser, open https://example.com and save a screenshot to "
              "canonical/astra_runtime/tmp/EXAMPLE.png and save the result to "
              "canonical/astra_runtime/tmp/EXAMPLE.json")
        out=compiler.compile_goal(goal,registry,ROOT)
        self.assertEqual(out["selected_capability"],"web.browser.rendered.capture.test")
        self.assertEqual(out["inputs"]["url"],"https://example.com")
        self.assertEqual(out["inputs"]["screenshot_path"],"canonical/astra_runtime/tmp/EXAMPLE.png")
        self.assertEqual(out["inputs"]["result_path"],"canonical/astra_runtime/tmp/EXAMPLE.json")

    def test_repo_path_extraction_ignores_url_path_components(self):
        goal=("Open https://www.python.org/downloads/ and save "
              "canonical/astra_runtime/tmp/REAL.json")
        paths=[raw for raw,_ in compiler._repo_paths(goal,ROOT)]
        self.assertEqual(paths,["canonical/astra_runtime/tmp/REAL.json"])

    def test_browser_clause_binds_outputs_from_future_clause(self):
        registry={
          "web.browser.rendered.capture.test":{
            "status":"VERIFIED_BOUND_CAPABILITY",
            "provides":["web.browser.rendered.capture"],
            "requires":[],
            "keywords":["browser","rendered","web","screenshot","url"],
            "action_template":{
              "type":"invoke_capability",
              "args":{
                "capability_id":"web.browser.rendered.capture.test",
                "url":"${input.url}",
                "screenshot_path":"${input.screenshot_path}",
                "result_path":"${input.result_path}"
              },
              "expect":{"type":"field_equals","field":"output_verified","value":True}
            }
          }
        }
        clause="Using a rendered browser, open https://example.com"
        future=["Save a screenshot to canonical/astra_runtime/tmp/EXAMPLE.png and save canonical/astra_runtime/tmp/EXAMPLE.json"]
        out=compiler._compile_single_goal(clause,registry,ROOT,future_clauses=future)
        self.assertEqual(out["inputs"]["url"],"https://example.com")
        self.assertEqual(out["inputs"]["screenshot_path"],"canonical/astra_runtime/tmp/EXAMPLE.png")
        self.assertEqual(out["inputs"]["result_path"],"canonical/astra_runtime/tmp/EXAMPLE.json")

    def test_browser_capture_then_semver_extraction_compiles(self):
        goal=(
            "Using a real rendered browser, open https://www.python.org/downloads/. "
            "Determine the latest stable Python 3 release shown on the page. "
            "Save a full-page screenshot to canonical/astra_runtime/tmp/PYTHON_DOWNLOADS_TEST.png "
            "and save canonical/astra_runtime/tmp/PYTHON_DOWNLOADS_TEST_RESULT.json containing "
            "source_url, final_url, page_title, latest_stable_python3, and observed_text_evidence."
        )
        out=compiler.compile_goal(goal,self.registry(),ROOT)
        self.assertEqual(out["compiler_mode"],"DETERMINISTIC_COMPOUND_ACTION_PLAN")
        modes=[x["mode"] for x in out["compiled_parts"]]
        self.assertIn("VERIFIED_STRUCTURED_SEMANTIC_EXTRACTION",modes)
        browser=[x for x in out["compiled_parts"] if x.get("selected_capability")=="web.browser.rendered.capture.chromedriver"][0]
        self.assertEqual(browser["inputs"]["screenshot_path"],"canonical/astra_runtime/tmp/PYTHON_DOWNLOADS_TEST.png")
        self.assertEqual(browser["inputs"]["result_path"],"canonical/astra_runtime/tmp/PYTHON_DOWNLOADS_TEST_RESULT.json")
        semantic=[x for x in out["compiled_parts"] if x["mode"]=="VERIFIED_STRUCTURED_SEMANTIC_EXTRACTION"][0]
        self.assertEqual(semantic["field"],"latest_stable_python3")
        self.assertEqual(semantic["product"],"Python")
        self.assertEqual(semantic["major"],"3")

    def test_full_browser_release_goal_compiles_independent_verifier(self):
        goal=(
            "Using a real rendered browser, open https://www.python.org/downloads/. "
            "Determine the latest stable Python 3 release shown on the page. "
            "Save a full-page screenshot to canonical/astra_runtime/tmp/PYTHON_DOWNLOADS_FULL_TEST.png "
            "and save canonical/astra_runtime/tmp/PYTHON_DOWNLOADS_FULL_TEST_RESULT.json containing "
            "source_url, final_url, page_title, latest_stable_python3, and observed_text_evidence. "
            "Finally independently verify from the official Python downloads page, without trusting "
            "the browser extraction, that the claimed latest_stable_python3 string is present and "
            "corresponds to the current stable Python 3 release shown there."
        )
        out=compiler.compile_goal(goal,self.registry(),ROOT)
        self.assertEqual(out["compiler_mode"],"DETERMINISTIC_COMPOUND_ACTION_PLAN")
        modes=[x["mode"] for x in out["compiled_parts"]]
        self.assertIn("VERIFIED_STRUCTURED_SEMANTIC_EXTRACTION",modes)
        self.assertIn("INDEPENDENT_WEB_RELEASE_VERIFICATION",modes)
        verifier=[x for x in out["compiled_parts"] if x["mode"]=="INDEPENDENT_WEB_RELEASE_VERIFICATION"][0]
        self.assertEqual(verifier["capability_id"],"web.release.verify.independent_http")
        self.assertEqual(verifier["version_field"],"latest_stable_python3")
        self.assertEqual(verifier["product"],"Python")
        self.assertEqual(verifier["major"],"3")
        self.assertEqual(verifier["result_path"],"canonical/astra_runtime/tmp/PYTHON_DOWNLOADS_FULL_TEST_RESULT.json")

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

    def test_direct_compound_compiler_uses_effect_result_binding_authority(self):
        registry={
          "decision.producer":{
            "status":"VERIFIED_BOUND_CAPABILITY",
            "incremental_spend_usd":0,
            "cost":1,
            "requires":["structured.decision_evidence.available"],
            "provides":["decision.synthesis.typed"],
            "keywords":["decision","evidence","synthesize"],
            "action_template":{
              "type":"invoke_capability",
              "args":{
                "capability_id":"decision.producer",
                "input_path":"${input.input_path}",
                "output_path":"${input.output_path}",
              },
              "expect":{"type":"field_equals","field":"output_verified","value":True},
            },
            "result_fields":["input_path","output_path","output_verified"],
          },
          "decision.verifier":{
            "status":"VERIFIED_BOUND_CAPABILITY",
            "incremental_spend_usd":0,
            "cost":1,
            "requires":["decision.synthesis.typed"],
            "provides":["decision.synthesis.verified"],
            "keywords":["decision","verify","independent"],
            "action_template":{
              "type":"invoke_capability",
              "args":{
                "capability_id":"decision.verifier",
                "input_path":"${input.input_path}",
                "result_path":"${input.result_path}",
              },
              "expect":{"type":"field_equals","field":"verified","value":True},
            },
            "proposal_bindings":{
              "input_path":{
                "type":"effect_result",
                "effect":"decision.synthesis.typed",
                "field":"input_path",
                "container":"scalar",
              },
              "result_path":{
                "type":"effect_result",
                "effect":"decision.synthesis.typed",
                "field":"output_path",
                "container":"scalar",
              },
            },
            "result_fields":["verified","reason"],
          },
        }
        source="canonical/runtime/BOUND_CAPABILITY_REGISTRY_V1.json"
        output="canonical/astra_runtime/tmp/DIRECT_BINDING_SYNTHETIC.json"
        goal=(
            "Using decision evidence at "+source+", synthesize the decision to "+output+". "
            "Then independently verify the decision result at "+output+"."
        )
        out=compiler.compile_goal(goal,registry,ROOT)
        self.assertEqual(out["compiler_mode"],"DETERMINISTIC_COMPOUND_ACTION_PLAN")
        self.assertEqual(
            [x["selected_capability"] for x in out["compiled_parts"]],
            ["decision.producer","decision.verifier"],
        )
        actions=[x for x in out["controller_actions"] if x["type"]!="finish"]
        self.assertEqual(actions[0]["args"]["input_path"],source)
        self.assertEqual(actions[0]["args"]["output_path"],output)
        self.assertEqual(
            actions[1]["args"]["input_path"],
            {"$result":{"cycle":0,"field":"input_path"}},
        )
        self.assertEqual(
            actions[1]["args"]["result_path"],
            {"$result":{"cycle":0,"field":"output_path"}},
        )
        self.assertNotEqual(
            actions[1]["args"]["input_path"],
            actions[1]["args"]["result_path"],
        )
        self.assertEqual(
            out["compiled_parts"][1]["inputs"]["input_path"],
            {"$result":{"cycle":0,"field":"input_path"}},
        )
        self.assertEqual(
            out["compiled_parts"][1]["inputs"]["result_path"],
            {"$result":{"cycle":0,"field":"output_path"}},
        )

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

    def test_context_url_json_fetch_compiles_from_prior_structured_state(self):
        subgoal="Fetch that project's authoritative live PyPI metadata from the metadata URL recorded in the registry"
        out=compiler._compile_context_url_json_fetch(
            subgoal,
            ["canonical/runtime/BOUND_CAPABILITY_REGISTRY_V1.json","canonical/astra_runtime/tmp/STRUCTURED_SELECTION_TEST.json"],
            self.registry(),
            ROOT,
        )
        self.assertIsNotNone(out)
        action=out["action"]
        self.assertEqual(action["args"]["capability_id"],"http.json.fetch_from_state")
        self.assertEqual(action["args"]["source_json_path"],"canonical/astra_runtime/tmp/STRUCTURED_SELECTION_TEST.json")
        self.assertEqual(action["args"]["url_key"],"metadata_url")
        self.assertTrue(action["args"]["output_path"].endswith(".json"))

    def test_structured_nested_record_selection_compiles_and_executes(self):
        subgoal="Find the VERIFIED_BOUND_CAPABILITY whose source project is pypdf"
        out=compiler._compile_json_record_selection(
            subgoal,
            ["canonical/runtime/BOUND_CAPABILITY_REGISTRY_V1.json"],
            self.registry(),
            ROOT,
        )
        self.assertIsNotNone(out)
        action=out["action"]
        proc=subprocess.run(
            ["jq",action["args"]["filter"],str(ROOT/action["args"]["input_path"])],
            text=True,capture_output=True,timeout=20,
        )
        self.assertEqual(proc.returncode,0,proc.stderr)
        selected=json.loads(proc.stdout)
        self.assertEqual(selected["id"],"pdf.extract.text.pypdf")
        self.assertEqual(selected["record"]["source"]["type"],"pypi")
        self.assertEqual(selected["record"]["source"]["project"],"pypdf")
        self.assertEqual(selected["record"]["status"],"VERIFIED_BOUND_CAPABILITY")

    def test_structured_nested_record_selection_fails_closed_when_not_unique(self):
        subgoal="Find the VERIFIED_BOUND_CAPABILITY whose source type is pypi"
        out=compiler._compile_json_record_selection(
            subgoal,
            ["canonical/runtime/BOUND_CAPABILITY_REGISTRY_V1.json"],
            self.registry(),
            ROOT,
        )
        self.assertIsNotNone(out)
        action=out["action"]
        proc=subprocess.run(
            ["jq",action["args"]["filter"],str(ROOT/action["args"]["input_path"])],
            text=True,capture_output=True,timeout=20,
        )
        self.assertNotEqual(proc.returncode,0)
        self.assertIn("SELECTION_NOT_UNIQUE",proc.stderr)

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

    def test_compound_live_pypi_provenance_compiles_full_verified_pipeline(self):
        goal=(
            "Read canonical/runtime/BOUND_CAPABILITY_REGISTRY_V1.json. "
            "Find the VERIFIED_BOUND_CAPABILITY whose source project is pypdf. "
            "Fetch that project's authoritative live PyPI metadata from the metadata URL recorded in the registry. "
            "Verify that the pinned version and wheel filename still exist in that metadata, download that exact wheel, compute its SHA-256, "
            "and verify it equals the wheel_sha256 recorded in the registry. "
            "Create canonical/astra_runtime/tmp/LIVE_PYPI_PROVENANCE_AUDIT.json containing the capability ID, project, pinned version, wheel filename, recorded hash, live metadata hash, downloaded artifact hash, metadata URL, artifact URL, and a final verified boolean. "
            "Finally independently read the report and fail unless all three hashes are identical and verified is true."
        )
        out=compiler.compile_goal(goal,self.registry(),ROOT)
        self.assertEqual(out["compiler_mode"],"DETERMINISTIC_COMPOUND_ACTION_PLAN")
        self.assertEqual([x["mode"] for x in out["compiled_parts"]],[
            "NATIVE_READ",
            "VERIFIED_STRUCTURED_SELECTION",
            "VERIFIED_LIVE_JSON_FETCH",
            "VERIFIED_PYPI_PROVENANCE",
            "INDEPENDENT_JSON_INTEGRITY_ASSERTION",
            "CAUSAL_ARTIFACT_ALREADY_PRODUCED",
            "INDEPENDENT_JSON_INTEGRITY_ASSERTION",
        ])
        self.assertEqual(out["compiled_parts"][3]["capability_id"],"pypi.provenance.audit_live_artifact")
        self.assertEqual(
            out["compiled_parts"][3]["report_path"],
            "canonical/astra_runtime/tmp/LIVE_PYPI_PROVENANCE_AUDIT.json",
        )
        self.assertEqual(
            out["compiled_parts"][-1]["equal_fields"],
            ["recorded_hash","live_metadata_hash","downloaded_artifact_hash"],
        )

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

    def test_compound_test_audit_keeps_independent_execution_and_verification_together(self):
        goal=(
            "Execute every canonical/tests/test_*.py file. "
            "Create canonical/astra_runtime/tmp/CANONICAL_TEST_AUDIT.json containing one record per test file with repository-relative path, exit code, passed test count, failed test count, error count, skipped count, and duration, plus totals across the corpus. "
            "Fail if any test file exits nonzero. "
            "Finally independently execute the same complete test corpus again and verify that every file in the report still exits zero, "
            "that no canonical test file is missing from the report, and that the report totals are internally consistent."
        )
        out=compiler.compile_goal(goal,self.registry(),ROOT)
        self.assertEqual(out["compiler_mode"],"DETERMINISTIC_COMPOUND_ACTION_PLAN")
        self.assertEqual(len(out["clauses"]),4)
        self.assertEqual([x["mode"] for x in out["compiled_parts"]],[
            "NATIVE_TEST_CORPUS_DISCOVERY",
            "VERIFIED_PYTHON_TEST_AUDIT",
            "PYTHON_TEST_ZERO_FAILURE_ASSERTION",
            "INDEPENDENT_PYTHON_TEST_CORPUS_VERIFICATION",
        ])
        self.assertIn("and verify that every file in the report still exits zero",out["clauses"][-1].lower())

    def test_verified_browser_interaction_compiles_declarative_actions(self):
        goal=(
            "Using a real rendered browser, open https://httpbin.org/forms/post. "
            "Enter PROJECT BRAIN into the customer name field, choose Medium pizza size, "
            "check the Bacon topping, submit the form, and save a full-page screenshot to "
            "canonical/astra_runtime/tmp/HTTPBIN_FORM_SUBMITTED.png and a result JSON to "
            "canonical/astra_runtime/tmp/HTTPBIN_FORM_SUBMITTED.json. "
            "The final rendered page must independently show the submitted customer name PROJECT BRAIN, "
            "size Medium, and topping Bacon; do not count merely opening or screenshotting the form as success."
        )
        out=compiler.compile_goal(goal,self.registry(),ROOT)
        self.assertEqual(out["compiler_mode"],"DETERMINISTIC_COMPOUND_ACTION_PLAN")
        self.assertEqual(out["compiled_parts"][0]["mode"],"VERIFIED_BROWSER_INTERACTION")
        self.assertEqual(
            out["compiled_parts"][0]["selected_capability"],
            "web.browser.rendered.capture.chromedriver",
        )
        actions=out["controller_actions"][0]["args"]["actions"]
        self.assertEqual([x["type"] for x in actions],[
            "set_text","select_option","check","submit",
        ])
        self.assertEqual(actions[0]["value"],"PROJECT BRAIN")
        self.assertEqual(actions[1]["value"],"Medium")
        self.assertEqual(actions[2]["target"],"Bacon")
        self.assertEqual(
            out["controller_actions"][0]["args"]["result_path"],
            "canonical/astra_runtime/tmp/HTTPBIN_FORM_SUBMITTED.json",
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
