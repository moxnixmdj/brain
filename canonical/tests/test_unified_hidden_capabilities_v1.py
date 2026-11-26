"""End-to-end verification of the Unified Hidden-Capability Federation in Brain Unified Model V1."""
from __future__ import annotations

import base64
import io
import tempfile
import unittest
import zipfile
from pathlib import Path

from canonical.runtime import brain_unified_model_v1 as model_runtime
from canonical.runtime.unified_hidden_capability_federation_v1 import (
    FEDERATED_KERNEL_DESCRIPTORS,
    catalog_federated_engines,
)


def _make_minimal_docx(text: str) -> tuple[str, bytes]:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr(
            "[Content_Types].xml",
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
            '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
            '<Default Extension="xml" ContentType="application/xml"/>'
            '<Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>'
            "</Types>",
        )
        zf.writestr(
            "_rels/.rels",
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/>'
            "</Relationships>",
        )
        zf.writestr(
            "word/document.xml",
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
            f"<w:body><w:p><w:r><w:t>{text}</w:t></w:r></w:p></w:body></w:document>",
        )
    raw = buf.getvalue()
    return base64.b64encode(raw).decode("ascii"), raw


class UnifiedHiddenCapabilitiesV1Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.model = model_runtime.open_model()

    def test_all_58_federated_kernels_are_compiled_and_self_addressable(self) -> None:
        cat = catalog_federated_engines()
        self.assertEqual(cat["count"], len(FEDERATED_KERNEL_DESCRIPTORS))
        self.assertGreaterEqual(cat["count"], 58)
        expected_domains = {
            "TRUE_CAPABILITIES",
            "SWE_SYNTHESIS_AND_REPAIR",
            "POLYGLOT_REPAIR_AND_BUILD",
            "COMPUTER_USE_PETRI_AND_PROSE",
            "CONTINUAL_LEARNING_AND_ORGANS",
            "FINANCE_VALUATION_AND_REGCAP",
            "VISUAL_3D_CAD_AND_DOCUMENTS",
            "LANGUAGE_SCIENCE_SYMBOLIC_AND_MODULE_SOLVER",
        }
        self.assertEqual(set(cat["domains"].keys()), expected_domains)

        listed = self.model.list_federated_engines()
        self.assertEqual(listed["count"], len(FEDERATED_KERNEL_DESCRIPTORS))

        status = self.model.status()
        self.assertEqual(
            status["counts"]["federated_kernel_engines"],
            len(FEDERATED_KERNEL_DESCRIPTORS),
        )
        self.assertGreaterEqual(status["counts"]["extended_source_index_modules"], 750)

        for mode, spec in FEDERATED_KERNEL_DESCRIPTORS.items():
            eid = "engine:" + mode
            with self.subTest(engine_id=eid):
                self.assertIn(eid, self.model.engines)
                row = self.model.engines[eid]
                self.assertEqual(row["kind"], "FEDERATED_KERNEL_ENGINE")
                self.assertEqual(row["incremental_spend_usd"], 0)
                self.assertEqual(row["model_dependency_count"], 0)
                self.assertTrue((model_runtime.ROOT / spec["source_path"]).is_file())
                routed = self.model.route(eid)
                self.assertTrue(routed["confident"])
                self.assertEqual(routed["best"]["id"], eid)

    def test_cross_tree_extended_source_discovery_reaches_swe_kernel_and_tools(self) -> None:
        swe_hit = self.model.find_any_source("angelic lens cow repair", top_k=5)
        self.assertTrue(swe_hit["candidates"])
        swe_paths = [row["path"] for row in swe_hit["candidates"]]
        self.assertIn("canonical/swe_kernel/angelic_lens_cow_repair_v1.py", swe_paths)
        for row in swe_hit["candidates"]:
            self.assertIs(row["capability"], False)
            self.assertIs(row["executable"], False)

        tool_hit = self.model.find_any_source("right question experiment", top_k=5)
        tool_paths = [row["path"] for row in tool_hit["candidates"]]
        self.assertIn("canonical/tools/the_right_question_is_an_experiment_v1.py", tool_paths)

    def test_true_capabilities_docx_saccr_and_pareto_execute_through_solve(self) -> None:
        docx_b64, _ = _make_minimal_docx("Original Clause Alpha")
        docx_out = self.model.solve(
            "replace unique docx exact edit",
            inputs={
                "docx_b64": docx_b64,
                "old": "Original Clause Alpha",
                "new": "Amended Clause Omega",
            },
        )
        self.assertIs(docx_out["pass"], True)
        self.assertEqual(docx_out["engine_id"], "engine:DOCX_EXACT_TEXT_EDIT")
        edited_bytes = base64.b64decode(docx_out["result"]["output_docx_b64"])
        with zipfile.ZipFile(io.BytesIO(edited_bytes), "r") as zf:
            xml_body = zf.read("word/document.xml").decode("utf-8")
        self.assertIn("Amended Clause Omega", xml_body)
        self.assertNotIn("Original Clause Alpha", xml_body)

        saccr_out = self.model.solve(
            "engine:SACCR_CREDIT_ADDON",
            inputs={
                "trades": [
                    {
                        "notional": 10_000_000,
                        "start": 0.0,
                        "end": 5.0,
                        "direction": 1,
                        "reference": "ACME_CORP",
                        "credit_rating": "BBB",
                        "is_index": False,
                    }
                ]
            },
        )
        self.assertIs(saccr_out["pass"], True)
        self.assertGreater(saccr_out["result"]["credit_addon"], 200_000.0)
        self.assertEqual(len(saccr_out["result"]["traces"]), 1)

        pareto_out = self.model.solve(
            "pareto frontier update fold pareto candidates",
            inputs={
                "candidates": [
                    {
                        "capability_id": "cap.strong",
                        "reusable_capability": True,
                        "independently_verified": True,
                        "capability": "0.9",
                        "generalization": "0.8",
                        "reliability": "0.95",
                        "latency": "1",
                        "compute": "1",
                        "memory": "1",
                        "incremental_spend_usd": "0",
                    },
                    {
                        "capability_id": "cap.dominated",
                        "reusable_capability": True,
                        "independently_verified": True,
                        "capability": "0.3",
                        "generalization": "0.2",
                        "reliability": "0.4",
                        "latency": "5",
                        "compute": "5",
                        "memory": "5",
                        "incremental_spend_usd": "0",
                    },
                ]
            },
        )
        self.assertIs(pareto_out["pass"], True)
        steps = pareto_out["result"]["steps"]
        self.assertIs(steps[0]["admitted"], True)
        self.assertIs(steps[1]["admitted"], False)

    def test_swe_synthesis_splicing_guards_uir_umg_and_rewrites(self) -> None:
        fst_out = self.model.solve(
            "synthesize bidirectional fst lens from transducer witness pairs",
            inputs={
                "witness_pairs": [("a\x01b", "a^Ab"), ("x\x02y", "x^By")],
                "apply_to": ["k\x01m"],
            },
        )
        self.assertIs(fst_out["pass"], True)
        self.assertEqual(fst_out["result"]["transformed_outputs"], ["k^Am"])
        self.assertIs(fst_out["result"]["roundtrip_verified"], True)

        splice_out = self.model.solve(
            "dual program splicing combine partial repairs",
            inputs={
                "parent": "def compute(x):\n    left = x + 1\n    right = x * 2\n    return left + right\n",
                "candidate_a": "def compute(x):\n    left = x + 10\n    right = x * 2\n    return left + right\n",
                "candidate_b": "def compute(x):\n    left = x + 1\n    right = x * 20\n    return left + right\n",
            },
        )
        self.assertIs(splice_out["pass"], True)
        spliced_code = splice_out["result"]["spliced_candidates"][0]
        ns: dict[str, object] = {}
        exec(spliced_code, ns)
        self.assertEqual(ns["compute"](3), (3 + 10) + (3 * 20))

        guard_out = self.model.solve(
            "synthesise separating conjunction distinction guard",
            inputs={
                "positives": [{"empty": True, "count": 0}, {"empty": True, "count": 0}],
                "negatives": [{"empty": False, "count": 2}, {"empty": False, "count": 7}],
            },
        )
        self.assertIs(guard_out["pass"], True)
        self.assertTrue(guard_out["result"]["guard"])

        uir_out = self.model.solve(
            "semantic causal uir equality saturation uir",
            inputs={"code_a": "x + 0", "code_b": "0 + x"},
        )
        self.assertIs(uir_out["pass"], True)
        self.assertIs(uir_out["result"]["equivalent"], True)

        umg_out = self.model.solve(
            "universal meaning graph umg causal lineage",
            inputs={"source": "def f(a):\n    b = a + 2\n    return b * 4\n"},
        )
        self.assertIs(umg_out["pass"], True)
        self.assertGreaterEqual(umg_out["result"]["node_count"], 3)

        cegis_out = self.model.solve(
            "mental cegis egraph canonicalize",
            inputs={"expression": "not (not flag)"},
        )
        self.assertIs(cegis_out["pass"], True)
        self.assertEqual(cegis_out["result"]["canonical_ir"], "IRNode(op='VAR', args=('flag',))")

    def test_polyglot_c_and_javascript_causal_patch_synthesis(self) -> None:
        c_out = self.model.solve(
            "asan cegis c sanitizer patch",
            inputs={
                "source": "int read_ptr(int *p) {\n    if (!p) {\n        return -1;\n    }\n    int v = *q;\n    return v;\n}\n",
                "blame_line": 5,
                "fault_kind": "NULL_DEREF",
            },
        )
        self.assertIs(c_out["pass"], True)
        self.assertGreaterEqual(c_out["result"]["patch_count"], 1)

        js_out = self.model.solve(
            "javascript causal cegis v8 node patch synthesis",
            inputs={
                "source": "function rankItems(items) {\n  return items.sort();\n}\n",
                "candidate_lines": [2],
            },
        )
        self.assertIs(js_out["pass"], True)
        self.assertTrue(
            any("slice().sort(" in patch[2] for patch in js_out["result"]["patches"])
        )

    def test_computer_use_petri_automata_and_prose_claims(self) -> None:
        petri_out = self.model.solve(
            "compute petri dominator cut vertices checkpoint",
            inputs={
                "edges": [
                    ["START", "L1"],
                    ["START", "R1"],
                    ["L1", "GATE"],
                    ["R1", "GATE"],
                    ["GATE", "L2"],
                    ["GATE", "R2"],
                    ["L2", "GOAL"],
                    ["R2", "GOAL"],
                ],
                "start_node": "START",
                "goal_node": "GOAL",
            },
        )
        self.assertIs(petri_out["pass"], True)
        self.assertIn("GATE", petri_out["result"]["ordered_checkpoints"])

        auto_out = self.model.solve(
            "minimal automata experiment separating word",
            inputs={
                "machine_a": {
                    "states": [0, 1],
                    "start": 0,
                    "transitions": {0: {"open": 1}, 1: {"save": 1}},
                    "accepting": [1],
                    "actions": ["open", "save"],
                },
                "machine_b": {
                    "states": [0, 1],
                    "start": 0,
                    "transitions": {0: {"open": 0}, 1: {"save": 1}},
                    "accepting": [1],
                    "actions": ["open", "save"],
                },
            },
        )
        self.assertIs(auto_out["pass"], True)
        self.assertIs(auto_out["result"]["equivalent"], False)
        self.assertEqual(auto_out["result"]["separating_word"], ["open"])

        prose_out = self.model.solve(
            "prose claim experiment manpage claim extractor",
            inputs={
                "text": "Usage: gzip [OPTION]... [FILE]...\nCompress or uncompress FILEs.",
                "subject": "gzip",
            },
        )
        self.assertIs(prose_out["pass"], True)
        self.assertGreaterEqual(prose_out["result"]["claim_count"], 1)

    def test_continual_learning_ir_transfer_skill_crystallizer_and_organs(self) -> None:
        ir_out = self.model.solve(
            "epistemic ir transfer lift_python_to_ir",
            inputs={
                "before_code": "if val == None:\n    return 0\n",
                "after_code": "if val is None:\n    return 0\n",
                "target_snippet": "if record == None:\n    return 0\n",
            },
        )
        self.assertIs(ir_out["pass"], True)
        self.assertIn("record is None", ir_out["result"]["transferred_code"])

        cryst_out = self.model.solve(
            "verified skill crystallizer anti_unify_code_rule",
            inputs={
                "before_snippet": "cleaned = raw_input.strip()",
                "after_snippet": "cleaned = (raw_input or '').strip()",
                "apply_to_source": "title = header_text.strip()",
            },
        )
        self.assertIs(cryst_out["pass"], True)
        self.assertIn("(header_text or '')", cryst_out["result"]["applied_source"])

        organ_out = self.model.solve(
            "meta circular organ induce periodic operator",
            inputs={"examples": [[[n], n % 5] for n in range(18)]},
        )
        self.assertIs(organ_out["pass"], True)
        self.assertEqual(organ_out["result"]["periodic_operator"]["period"], 5)

    def test_finance_visual_hull_language_value_algebra_and_admitted_module_solver(self) -> None:
        with tempfile.TemporaryDirectory() as cog_td:
            bps_out = self.model.act_or_learn(
                "finance quantitative algebra basis points delta",
                cognitive_state_dir=cog_td,
                inputs={
                    "operation": "basis_points_between",
                    "new_percent": "6.25",
                    "old_percent": "4.75",
                },
            )
        self.assertIs(bps_out["pass"], True)
        self.assertEqual(bps_out["result"]["value"], "150.00")

        lbo_out = self.model.solve(
            "simplified lbo leveraged buyout moic irr",
            inputs={
                "workflow": "lbo",
                "parameters": {
                    "share_price": 50,
                    "offer_premium_percent": 20,
                    "basic_shares_million": 100,
                    "transaction_expenses_million": 50,
                    "base_revenue_million": 2000,
                    "base_ebitda_million": 500,
                    "starting_cash_million": 200,
                    "existing_debt_million": 1000,
                    "minimum_cash_million": 100,
                    "entry_leverage_x": 5.0,
                    "debt_interest_rate_percent": 7.0,
                    "cash_interest_rate_percent": 3.0,
                    "tax_rate_percent": 25.0,
                    "revenue_growth_percent": 6.0,
                    "annual_ebitda_margin_expansion_pp": 0.5,
                    "d_and_a_percent_revenue": 3.0,
                    "capex_percent_revenue": 3.5,
                    "hold_years": 5,
                    "exit_multiple_x": 12.0,
                },
            },
        )
        self.assertIs(lbo_out["pass"], True)
        self.assertIn("sponsor_moic_x", lbo_out["result"]["valuation"])
        self.assertIn("sponsor_irr_percent", lbo_out["result"]["valuation"])

        hull_out = self.model.solve(
            "orthographic visual hull 3d voxel silhouette",
            inputs={
                "top": [[1, 0], [1, 1]],
                "front": [[1, 1], [1, 1]],
                "right": [[1, 1], [1, 1]],
            },
        )
        self.assertIs(hull_out["pass"], True)
        self.assertEqual(hull_out["result"]["signature"]["occupied_voxels"], 6)

        _, raw_docx = _make_minimal_docx("Valid OOXML Body")
        with tempfile.NamedTemporaryFile(suffix=".docx") as tf:
            Path(tf.name).write_bytes(raw_docx)
            ooxml_out = self.model.solve(
                "ooxml package integrity validate_ooxml_package",
                inputs={"package_path": tf.name},
            )
        self.assertIs(ooxml_out["pass"], True)

        sum_out = self.model.solve(
            "zero learned extractive summary",
            inputs={
                "text": (
                    "Equality saturation canonicalizes program terms without neural weights. "
                    "Petri dominator checkpoints bound horizon drift across multi-hour workflows. "
                    "Independent postcondition verification prevents silent false positives. "
                    "Exact rational polytopes compute sound interval bounds."
                ),
                "max_sentences": 2,
            },
        )
        self.assertIs(sum_out["pass"], True)
        self.assertTrue(sum_out["result"]["response"])
        self.assertIs(sum_out["result"]["all_output_sentences_verbatim_source_spans"], True)

        alg_out = self.model.solve(
            "value algebra law inducer induce operator algebraic laws",
            inputs={"operator_name": "max"},
        )
        self.assertIs(alg_out["pass"], True)
        self.assertIn("is_one_of_the_inputs", alg_out["result"]["laws"])
        self.assertIn("within_inputs", alg_out["result"]["laws"])

        mod_out = self.model.solve(
            "admitted module solver invoke admitted repository function",
            inputs={
                "query": "orthographic constraint graph",
                "payload": {
                    "top": [[1, 0], [1, 1]],
                    "front": [[1, 1], [1, 1]],
                    "right": [[1, 1], [1, 1]],
                },
            },
        )
        self.assertIs(mod_out["pass"], True)
        self.assertEqual(mod_out["result"]["output"]["status"], "COMPILED")

    def test_missing_inputs_and_absent_optional_dependencies_fail_closed(self) -> None:
        missing_out = self.model.solve("dual program splicing combine partial repairs", inputs={})
        self.assertIs(missing_out["pass"], False)
        self.assertIn("ENGINE_INPUTS_MISSING", missing_out["status"])

        cad_out = self.model.solve(
            "cad partspec cadquery solid generator",
            inputs={"spec": {"shape": "box"}},
        )
        if not cad_out["pass"]:
            self.assertIn("HOST_DEPENDENCY_MISSING:cadquery", cad_out["status"])


if __name__ == "__main__":
    unittest.main()
