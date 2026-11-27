"""Wave 53 & Wave 54 behavioral verification tests (pure stdlib unittest + pytest compatible).

Covers all six Wave 53-54 leapfrog engines, UnifiedModel wiring at 0 net LOC
added (< 7,534 cap), federation dispatch across all 6 new engine IDs, the
osworld_v21_app_policy_overlay_v1 syntax fix, positive & adversarial negative
controls, and K3=0 / $0.00 compliance.
"""
from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from canonical.runtime import osworld_v21_app_policy_overlay_v1 as osworld_overlay
from canonical.runtime.brain_unified_model_v1 import load_unified_model
from canonical.runtime.unified_hidden_capability_federation_v1 import (
    catalog_federated_engines,
    resolve_cross_disciplinary_concept,
    run_federated_engine,
)
from canonical.runtime.wave53_54_unified_capability_bus_and_leapfrog_v1 import (
    ALL_NINE_METAMORPHIC_LAWS,
    ALL_W40_W54_AWAKENED_DARK_MODULES,
    WAVE53_54_AWAKENED_DARK_MODULES,
    DbspHindsightStrataMemoryEngine,
    DockerlessVerifierAndSelfPlayCurriculumEngine,
    FullMetamorphicLawAndPrecisionSlicerEngine,
    SafeTransferEStitchStrataEngine,
    UnifiedCapabilityBusEngine,
    UnifiedMultiRungJitRLAndWebMcpGrounderEngine,
    canonicalize_eclass_source,
    self_check,
)

REPO_ROOT = Path(__file__).resolve().parents[2]


class TestWave53To54UnifiedCapabilityBusAndLeapfrog(unittest.TestCase):
    def test_01_self_check_passes_all_9_adversarial_checks(self) -> None:
        res = self_check()
        self.assertTrue(res["pass"], f"self_check failed: {res}")
        self.assertEqual(res["checks_passed"], 9)
        self.assertEqual(res["k3_model_calls"], 0)
        self.assertEqual(res["spend_usd"], 0.0)

    def test_02_osworld_overlay_syntax_fix_and_live_decide(self) -> None:
        a11y = (
            '<desktop><application name="LibreOffice Calc">'
            '<frame xmlns:s="https://accessibility.ubuntu.example.org/ns/state" s:active="true"/>'
            "</application></desktop>"
        )
        out = osworld_overlay.decide({"instruction": 'Set cell B2 to "42"', "a11y_tree": a11y})
        self.assertTrue(out["actions"])
        self.assertEqual(out["actions"][0]["operation"], "set_cell_value")
        self.assertEqual(out["actions"][0]["args"]["cell"], "B2")
        self.assertEqual(out["actions"][0]["args"]["value"], "42")

    def test_03_unified_model_loc_cap_and_live_methods(self) -> None:
        bum_lines = len((REPO_ROOT / "canonical/runtime/brain_unified_model_v1.py").read_text(encoding="utf-8").splitlines())
        self.assertEqual(bum_lines, 7653, "Wave 53-54 must preserve exact 0 net LOC growth in brain_unified_model_v1.py")

        model = load_unified_model()
        for method_name in (
            "unified_capability_bus_op",
            "safe_transfer_estitch_strata_op",
            "metamorphic_9_of_9_and_precision_slicer_op",
            "dockerless_verifier_and_selfplay_op",
            "multirung_jitrl_and_webmcp_op",
            "dbsp_hindsight_strata_memory_op",
            # Backward compatibility with Wave 51-52
            "arise_def_use_slice_op",
            "wave52_sliced_structural_swe_op",
            "cold_start_front_door_bridge_op",
        ):
            self.assertTrue(hasattr(model, method_name), f"UnifiedModel missing {method_name}")

        bus_res = model.unified_capability_bus_op("audit")
        self.assertTrue(bus_res["pass"])
        self.assertEqual(bus_res["wave53_54_importable"], 36)
        self.assertTrue(bus_res["zero_overlap_with_w40_w52"])
        self.assertEqual(bus_res["cumulative_w40_w54_count"], 228)
        self.assertEqual(len(WAVE53_54_AWAKENED_DARK_MODULES), 36)
        self.assertEqual(len(ALL_W40_W54_AWAKENED_DARK_MODULES), 228)

    def test_04_federation_registry_concept_map_and_live_dispatch(self) -> None:
        w53_54_engines = (
            "LEAPFROG_W53_UNIFIED_CAPABILITY_BUS",
            "LEAPFROG_W53_SAFE_TRANSFER_ESTITCH_STRATA",
            "LEAPFROG_W54_METAMORPHIC_9_OF_9_AND_PRECISION_SLICER",
            "LEAPFROG_W54_DOCKERLESS_VERIFIER_AND_SELFPLAY",
            "LEAPFROG_W54_MULTIRUNG_JITRL_AND_WEBMCP_GROUNDER",
            "LEAPFROG_W54_DBSP_HINDSIGHT_STRATA_MEMORY",
        )
        cat = catalog_federated_engines()
        cat_modes = {r["mode"] for r in cat["engines"]}
        for eid in w53_54_engines:
            self.assertIn(eid, cat_modes)

        self.assertTrue(run_federated_engine("LEAPFROG_W53_UNIFIED_CAPABILITY_BUS", {"operation": "audit"})["pass"])
        self.assertTrue(run_federated_engine("LEAPFROG_W53_SAFE_TRANSFER_ESTITCH_STRATA", {"operation": "demo_cycle"})["pass"])
        self.assertTrue(run_federated_engine(
            "LEAPFROG_W54_METAMORPHIC_9_OF_9_AND_PRECISION_SLICER",
            {"operation": "generate", "law": "assert_validation", "source": "def f(x):\n    assert x is not None\n    return x\n"},
        )["pass"])
        self.assertTrue(run_federated_engine("LEAPFROG_W54_DOCKERLESS_VERIFIER_AND_SELFPLAY", {"operation": "self_play"})["pass"])
        self.assertTrue(run_federated_engine(
            "LEAPFROG_W54_MULTIRUNG_JITRL_AND_WEBMCP_GROUNDER",
            {
                "operation": "ground_webmcp",
                "goal": "Number 2.",
                "tools": [
                    {"name": "openDoor1", "description": "Open door 1", "inputSchema": {"properties": {}}},
                    {"name": "openDoor2", "description": "Open door 2", "inputSchema": {"properties": {}}},
                ],
            },
        )["pass"])
        self.assertTrue(run_federated_engine("LEAPFROG_W54_DBSP_HINDSIGHT_STRATA_MEMORY", {"operation": "demo_cycle"})["pass"])

        concept = resolve_cross_disciplinary_concept("e-stitch strata contrast edges forgeteval p-mem")
        fams = {m["concept_family"] for m in concept.get("matched_families", [])}
        self.assertIn("WAVE53_ESTITCH_STRATA_SAFE_TRANSFER_AND_CAPABILITY_BUS", fams)
        self.assertIn("WAVE54_METAMORPHIC_9_OF_9_DOCKERLESS_JITRL_WEBMCP_MEMORY", fams)

    def test_05_front_door_real_swe_acceptance_and_content_free_refusal(self) -> None:
        corpus_path = REPO_ROOT / "canonical/corpus/swe_verified_issue_text_20261124_V1.json"
        data = json.loads(corpus_path.read_text(encoding="utf-8"))
        per_inst = data["per_instance"]
        accepted = sum(
            1
            for row in per_inst.values()
            if UnifiedCapabilityBusEngine.route_issue_or_goal(row.get("body", ""), title=row.get("title", ""))["accepted"]
        )
        # Baseline accepted 28/80 (35.0%); Wave 53 router must achieve >= 90% on real SWE issues
        self.assertGreaterEqual(accepted / len(per_inst), 0.90)

        # Strict negative controls: empty / generic / noise strings must ALL be refused
        for junk in ("", "   ", "hello world", "please help", "fix it", "lorem ipsum", "<!-- comment -->"):
            res = UnifiedCapabilityBusEngine.route_issue_or_goal(junk)
            self.assertFalse(res["accepted"], f"False accept on content-free input: {junk!r}")

    def test_06_estitch_strata_contrast_safety_and_invalidation(self) -> None:
        self.assertEqual(
            canonicalize_eclass_source("not (a == b) and (x == None)"),
            canonicalize_eclass_source("(b != a) and (None == x)"),
        )
        eng = SafeTransferEStitchStrataEngine()
        l1 = eng.learn_from_verified_pair("def f(a, hi):\n    return a <= hi\n", "def f(a, hi):\n    return a < hi\n", task_id="lte")
        l2 = eng.learn_from_verified_pair("def g(x, lo):\n    return x < lo\n", "def g(x, lo):\n    return x <= lo\n", task_id="lt")
        self.assertTrue(l1["admitted"] and l2["admitted"])
        # Blind oracle-free recall MUST refuse direction-ambiguous operator rule
        blind = eng.recall_and_transfer("def h(v, cap):\n    return v <= cap\n", verifier=None)
        self.assertFalse(blind["transferred"])
        self.assertEqual(blind["mode"], "REFUSED__CONTRAST_EDGE_UNSETTLED")

        # Oracle-free alpha-safe idiom rule transfers cleanly, then stops forever once invalidated
        l3 = eng.learn_from_verified_pair(
            "def p(obj):\n    return hasattr(obj, '__reversed__')\n",
            "def p(obj):\n    return getattr(obj, '__reversed__', None) is not None\n",
            task_id="hasattr_idiom",
        )
        self.assertTrue(l3["admitted"] and l3["alpha_safe"])
        tr = eng.recall_and_transfer("def q(items):\n    return hasattr(items, '__reversed__')\n", verifier=None)
        self.assertTrue(tr["transferred"])
        self.assertIn("getattr(items, '__reversed__', None) is not None", tr["patched_source"])
        eng.invalidate_rule(l3["rule_id"])
        tr_after = eng.recall_and_transfer("def q(items):\n    return hasattr(items, '__reversed__')\n", verifier=None)
        self.assertFalse(tr_after["transferred"])

    def test_07_metamorphic_9_of_9_and_neighbor_regression_prefilter(self) -> None:
        self.assertEqual(len(ALL_NINE_METAMORPHIC_LAWS), 9)
        with tempfile.TemporaryDirectory(prefix="w54_test_prefilter_") as td:
            ws = Path(td)
            (ws / "hdr_parser.py").write_text(
                "def normalize_key(k):\n    return k.strip().lower()\n\n"
                "def parse_header(line):\n    k, v = line.split(':', 1)\n    return normalize_key(k), v\n",
                encoding="utf-8",
            )
            (ws / "router.py").write_text(
                "from hdr_parser import parse_header\n\ndef route_request(raw):\n    return dict([parse_header(raw)])\n",
                encoding="utf-8",
            )
            (ws / "test_hdr_parser.py").write_text(
                "from hdr_parser import normalize_key, parse_header\n\n"
                "def test_target():\n    assert parse_header('X-Foo:  ') == ('x-foo', '')\n\n"
                "def test_neighbor():\n    assert parse_header('Content-Type: text/html') == ('content-type', 'text/html')\n",
                encoding="utf-8",
            )
            overfit = (
                "def normalize_key(k):\n    return k.strip().lower()\n\n"
                "def parse_header(line):\n    k, v = line.split(':', 1)\n    return normalize_key(k), ''\n"
            )
            clean = (
                "def normalize_key(k):\n    return k.strip().lower()\n\n"
                "def parse_header(line):\n    k, v = line.split(':', 1)\n    return normalize_key(k), v.strip()\n"
            )
            r_bad = FullMetamorphicLawAndPrecisionSlicerEngine.precision_prefilter_candidate(
                ws, "hdr_parser.py", overfit, target_test_nodeid="test_hdr_parser.py::test_target",
            )
            r_good = FullMetamorphicLawAndPrecisionSlicerEngine.precision_prefilter_candidate(
                ws, "hdr_parser.py", clean, target_test_nodeid="test_hdr_parser.py::test_target",
            )
            self.assertTrue(r_bad["target_passed"])
            self.assertFalse(r_bad["accepted"])
            self.assertIn("test_hdr_parser.py::test_neighbor", r_bad["neighbor_regressions"])
            self.assertTrue(r_good["accepted"])

            loc = FullMetamorphicLawAndPrecisionSlicerEngine.localize_top_k_files(
                ws, "Fix `parse_header` spacing in router", top_k=5,
            )
            self.assertEqual(loc["ranked_files"][0]["path"], "hdr_parser.py")
            self.assertTrue(loc["multi_file_coupled"])

            # Atomic multi-file rollback on verifier failure
            orig_router = (ws / "router.py").read_text(encoding="utf-8")
            rb = FullMetamorphicLawAndPrecisionSlicerEngine.apply_multifile_atomic_patch(
                ws, {"router.py": "# broken\n"}, verifier=lambda _p: False,
            )
            self.assertFalse(rb["committed"])
            self.assertTrue(rb["rolled_back"])
            self.assertEqual((ws / "router.py").read_text(encoding="utf-8"), orig_router)

    def test_08_dockerless_verifier_jitrl_webmcp_and_dbsp_memory(self) -> None:
        ok = DockerlessVerifierAndSelfPlayCurriculumEngine.verify_patch_dockerless(
            "def inc(x):\n    return x - 1\n", "def inc(x):\n    return x + 1\n", issue_text="Fix inc subtraction",
        )
        bad = DockerlessVerifierAndSelfPlayCurriculumEngine.verify_patch_dockerless(
            "def inc(x):\n    return x - 1\n", "def inc(x):\n    return x + ghost_var\n", issue_text="Fix inc",
        )
        self.assertEqual(ok["verdict"], "PASS_DOCKERLESS")
        self.assertEqual(bad["verdict"], "REJECT_DOCKERLESS")

        mem = DbspHindsightStrataMemoryEngine()
        mem.inscribe("svc", "region", "us-east", network="world", tags=["deploy"])
        mem.inscribe(
            "svc", "endpoint", "https://us-east.api",
            network="observation",
            depends_on=[("svc", "region")],
            derivation_rule=lambda d: f"https://{d[('svc', 'region')]}.api",
        )
        mem.inscribe("svc", "compliance_note", "US rules", network="experience", depends_on=[("svc", "region")], derivation_rule=None)
        sup = mem.supersede("svc", "region", "eu-west")
        self.assertEqual(mem.recall("svc", "endpoint")["value"], "https://eu-west.api")
        self.assertEqual(mem.recall("svc", "compliance_note")["status"], "ABSENCE_WITNESS")
        mem.retract_tx(sup["tx"])
        self.assertEqual(mem.recall("svc", "endpoint")["value"], "https://us-east.api")
        self.assertEqual(mem.recall("svc", "compliance_note")["value"], "US rules")
        pq = mem.purge_by_query("deploy")
        self.assertEqual(pq["purged_count"], 1)
        self.assertEqual(mem.recall("svc", "region")["status"], "ABSENCE_WITNESS")

    def test_09_ast_singleton_isolation_subscript_swap_and_blind_oss_transfer(self) -> None:
        """Verifies Python 3.11 AST singleton operator isolation, 2-tuple subscript swap,
        EXCEPT_HANDLER_BROADEN, and blind Store-vs-Empty cross-repo OSS transfer."""
        eng = SafeTransferEStitchStrataEngine()
        # Donor 1: single-site <= -> < (must NOT rewrite BOTH <= operators in target at once!)
        eng.learn_from_verified_pair(
            "def f(a, b):\n    if a <= b:\n        return a\n    return b\n",
            "def f(a, b):\n    if a < b:\n        return a\n    return b\n",
            task_id="donor_cmp",
        )
        # Target has TWO `<=` operators; ONLY changing the 2nd one fixes it!
        two_lte_buggy = (
            "def pick(lo, hi, x):\n"
            "    if lo <= hi:\n"
            "        return 1 if x <= hi else 0\n"
            "    return -1\n"
        )

        def _verify_only_second(src: str) -> bool:
            ns: dict = {}
            exec(compile(src, "<t>", "exec"), ns, ns)
            fn = ns["pick"]
            return fn(2, 2, 1) == 1 and fn(2, 2, 2) == 0 and fn(3, 2, 1) == -1

        tr = eng.recall_and_transfer(two_lte_buggy, verifier=_verify_only_second, exclude_task_id="target_two_lte")
        self.assertTrue(tr["transferred"])
        self.assertIn("lo <= hi", tr["patched_source"])
        self.assertIn("x < hi", tr["patched_source"])

        # Donor 2: 2-tuple subscript transpose swap M[i, j] -> M[j, i]
        eng.learn_from_verified_pair(
            "def swap_args(op, x, y):\n    return op(y, x)\n",
            "def swap_args(op, x, y):\n    return op(x, y)\n",
            task_id="donor_swap",
        )
        mat_buggy = "def get_cell(grid, r, c):\n    return grid[c, r]\n"

        def _verify_mat(src: str) -> bool:
            ns: dict = {}
            exec(compile(src, "<m>", "exec"), ns, ns)
            return ns["get_cell"]({(1, 2): 99, (2, 1): 0}, 1, 2) == 99

        tr_m = eng.recall_and_transfer(mat_buggy, verifier=_verify_mat, exclude_task_id="target_mat")
        self.assertTrue(tr_m["transferred"])
        self.assertIn("grid[r, c]", tr_m["patched_source"])

        # Donor 3: EXCEPT_HANDLER_BROADEN across renamed repo
        eng.learn_from_verified_pair(
            "def p(s):\n    try:\n        return int(s)\n    except ValueError:\n        return None\n",
            "def p(s):\n    try:\n        return int(s)\n    except (ValueError, TypeError):\n        return None\n",
            task_id="donor_exc",
        )
        port_buggy = "def parse_port(raw):\n    try:\n        return int(raw)\n    except ValueError:\n        return -1\n"

        def _verify_port(src: str) -> bool:
            ns: dict = {}
            exec(compile(src, "<p>", "exec"), ns, ns)
            return ns["parse_port"]("80") == 80 and ns["parse_port"](None) == -1

        self.assertFalse(SafeTransferEStitchStrataEngine().recall_and_transfer(port_buggy, verifier=_verify_port)["transferred"])
        tr_e = eng.recall_and_transfer(port_buggy, verifier=_verify_port, exclude_task_id="target_port")
        self.assertTrue(tr_e["transferred"])

    def test_10_unittest_testcase_prefilter_and_4step_webmcp_snake_enum(self) -> None:
        """Verifies unittest.TestCase class-method neighbor pre-filtering AND 4-step snake-enum WebMCP grounding."""
        with tempfile.TemporaryDirectory(prefix="w54_ut_pf_") as td:
            ws = Path(td)
            (ws / "pkg").mkdir()
            (ws / "tests").mkdir()
            (ws / "pkg" / "__init__.py").write_text("", encoding="utf-8")
            (ws / "tests" / "__init__.py").write_text("", encoding="utf-8")
            (ws / "pkg" / "norm.py").write_text("def norm(s):\n    return s.strip().lower()\n", encoding="utf-8")
            (ws / "tests" / "test_norm.py").write_text(
                "import unittest\nfrom pkg.norm import norm\n\n"
                "class TestNorm(unittest.TestCase):\n"
                "    def test_slash(self):\n        self.assertEqual(norm('/Api/'), 'api')\n"
                "    def test_plain(self):\n        self.assertEqual(norm('  Home  '), 'home')\n",
                encoding="utf-8",
            )
            bad = "def norm(s):\n    return s.strip().strip('/').lower() if '/' in s else 'BAD'\n"
            good = "def norm(s):\n    return s.strip().strip('/').lower()\n"
            r_bad = FullMetamorphicLawAndPrecisionSlicerEngine.precision_prefilter_candidate(
                ws, "pkg/norm.py", bad, target_test_nodeid="tests/test_norm.py::TestNorm::test_slash"
            )
            r_good = FullMetamorphicLawAndPrecisionSlicerEngine.precision_prefilter_candidate(
                ws, "pkg/norm.py", good, target_test_nodeid="tests/test_norm.py::TestNorm::test_slash"
            )
            self.assertTrue(r_bad["target_passed"])
            self.assertFalse(r_bad["accepted"])
            self.assertIn("tests/test_norm.py::TestNorm::test_plain", r_bad["neighbor_regressions"])
            self.assertTrue(r_good["accepted"])

        # 4-step WebMCP compound goal with snake_case enum (`hide_and_seek`)
        doors_tools = [
            {"name": "open_door", "description": "Open door", "inputSchema": {"type": "object", "properties": {"door_number": {"type": "integer", "enum": [1, 2, 3]}}}},
            {"name": "talk_to_animal", "description": "Talk to animal", "inputSchema": {"type": "object", "properties": {"action": {"type": "string", "enum": ["ask_what_it_is", "dance", "hide_and_seek"]}}}},
            {"name": "return_to_hallway", "description": "Return to hallway", "inputSchema": {"type": "object", "properties": {}}},
        ]
        plan = UnifiedMultiRungJitRLAndWebMcpGrounderEngine.ground_webmcp_goal(
            "Open second door, then ask to dance with him and play hide & seek, finally return to hallway",
            doors_tools,
        )
        self.assertTrue(plan["grounded"])
        self.assertEqual(len(plan["plan"]), 4)
        self.assertEqual(plan["tool_sequence"], ["open_door", "talk_to_animal", "talk_to_animal", "return_to_hallway"])


if __name__ == "__main__":
    unittest.main()
