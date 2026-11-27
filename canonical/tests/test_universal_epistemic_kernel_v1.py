"""Tests for Universal Epistemic Kernel v1 (canonical/runtime/universal_epistemic_kernel_v1.py).

Verifies ONE minimal zero-LLM (`model_calls == 0`), zero-weight (`parameters_stored == 0`)
epistemic-diff algorithm across:
  1. SWE Epistemic Diff: live runtime introspection (`AttributeError`, `TypeError` kwarg,
     `ImportError` relocation + live PyPI/GitHub corroboration) and Tier 0 offline transfer.
  2. Local Repo Sibling-Pattern Epistemic Oracle (mines recurring helper/guard idioms).
  3. Cross-Modal Opaque-Bundle-to-SWE Composition (extensionless `.bin` -> auto-unwrap ->
     SWE repair -> pytest verify) + 100% offline Tier 0 unwrap on a second unseen bundle.
  4. Unified external inspectable/editable/deletable JSON memory (zero weights, zero raw
     prose, refuses leaked host paths, fail-closed quarantine on refutation).
  5. Observable Browser/DOM stepping through the same universal front door.
"""
from __future__ import annotations

import base64
import pathlib
import shutil
import sys
import tarfile
import tempfile
import unittest

from canonical.runtime import universal_epistemic_kernel_v1 as UEK


class UniversalEpistemicKernelTests(unittest.TestCase):
    def test_swe_epistemic_diff_attribute_kwarg_import_and_tier0_offline_transfer(self) -> None:
        mem = UEK.new_universal_memory()
        py = sys.executable
        with tempfile.TemporaryDirectory() as td:
            root = pathlib.Path(td)

            # 1. AttributeError on stdlib module
            e1 = root / "env1_attr"
            e1.mkdir()
            (e1 / "url_util.py").write_text(
                "import urllib.parse\n"
                "def encode_q(s: str) -> str:\n"
                "    return urllib.parse.quote_pluss(s)\n",
                encoding="utf-8",
            )
            (e1 / "test_url_util.py").write_text(
                "from url_util import encode_q\n"
                "def test_encode():\n"
                "    assert encode_q('a b') == 'a+b'\n",
                encoding="utf-8",
            )
            r1 = UEK.solve_arbitrary_environment(e1, "Fix the failing pytest tests", memory=mem, python_exe=py, allow_web=False)
            self.assertEqual(r1["status"], "VERIFIED")
            self.assertEqual(r1["mode"], "TIER1_SWE_EPISTEMIC_INTROSPECTION")
            self.assertEqual(r1["model_calls"], 0)
            self.assertEqual(r1["parameters_stored"], 0)
            self.assertIn("quote_plus", (e1 / "url_util.py").read_text(encoding="utf-8"))

            # 2. TypeError unexpected keyword argument
            e2 = root / "env2_kwarg"
            e2.mkdir()
            (e2 / "client.py").write_text(
                "def fetch(url: str, timeout: float = 5.0) -> tuple:\n"
                "    return (url, timeout)\n"
                "def call_api() -> tuple:\n"
                "    return fetch('https://example.com', timeout_sec=2.5)\n",
                encoding="utf-8",
            )
            (e2 / "test_client.py").write_text(
                "from client import call_api\n"
                "def test_call():\n"
                "    assert call_api() == ('https://example.com', 2.5)\n",
                encoding="utf-8",
            )
            r2 = UEK.solve_arbitrary_environment(e2, "Fix the failing pytest tests", memory=mem, python_exe=py, allow_web=False)
            self.assertEqual(r2["status"], "VERIFIED")
            self.assertEqual(r2["mode"], "TIER1_SWE_EPISTEMIC_INTROSPECTION")
            self.assertIn("timeout=2.5", (e2 / "client.py").read_text(encoding="utf-8"))

            # 3. ImportError relocated symbol on stdlib/3rd-party package (`urllib` -> `urllib.parse`)
            e3 = root / "env3_import"
            e3.mkdir()
            (e3 / "link_util.py").write_text(
                "from urllib import urlparse\n"
                "def host_of(u: str) -> str:\n"
                "    return urlparse(u).netloc\n",
                encoding="utf-8",
            )
            (e3 / "test_link_util.py").write_text(
                "from link_util import host_of\n"
                "def test_host():\n"
                "    assert host_of('https://example.com/a') == 'example.com'\n",
                encoding="utf-8",
            )
            r3 = UEK.solve_arbitrary_environment(e3, "Fix the failing pytest tests", memory=mem, python_exe=py, allow_web=False)
            self.assertEqual(r3["status"], "VERIFIED")
            self.assertEqual(r3["mode"], "TIER1_SWE_EPISTEMIC_INTROSPECTION")
            self.assertIn("from urllib.parse import urlparse", (e3 / "link_util.py").read_text(encoding="utf-8"))

            # 4. Unseen second repo hitting SAME import bug -> TIER 0 OFFLINE RECALL (zero gaps queried!)
            e3b = root / "env3b_transfer"
            e3b.mkdir()
            (e3b / "router.py").write_text(
                "from urllib import urlparse\n"
                "def path_of(u: str) -> str:\n"
                "    return urlparse(u).path\n",
                encoding="utf-8",
            )
            (e3b / "test_router.py").write_text(
                "from router import path_of\n"
                "def test_path():\n"
                "    assert path_of('https://example.com/x/y') == '/x/y'\n",
                encoding="utf-8",
            )
            r3b = UEK.solve_arbitrary_environment(e3b, "Fix the failing pytest tests", memory=mem, python_exe=py, allow_web=False)
            self.assertEqual(r3b["status"], "VERIFIED")
            self.assertEqual(r3b["mode"], "TIER0_API_CONTRACT_RECALL")
            self.assertEqual(r3b["gaps_queried"], [])
            self.assertEqual(len(r3b["swe_result"]["contracts_recalled"]), 1)

    def test_repo_sibling_pattern_epistemic_oracle(self) -> None:
        mem = UEK.new_universal_memory()
        py = sys.executable
        with tempfile.TemporaryDirectory() as td:
            e4 = pathlib.Path(td) / "env4_sibling"
            e4.mkdir()
            (e4 / "kv.py").write_text(
                "class CaseInsensitiveStore:\n"
                "    def __init__(self):\n"
                "        self._data = {}\n"
                "    def _norm(self, key: str) -> str:\n"
                "        return key.strip().lower()\n"
                "    def put(self, key: str, value: int) -> None:\n"
                "        key = self._norm(key)\n"
                "        self._data[key] = value\n"
                "    def has(self, key: str) -> bool:\n"
                "        key = self._norm(key)\n"
                "        return key in self._data\n"
                "    def get(self, key: str):\n"
                "        return self._data[key]\n",
                encoding="utf-8",
            )
            (e4 / "test_kv.py").write_text(
                "from kv import CaseInsensitiveStore\n"
                "def test_case_insensitive():\n"
                "    s = CaseInsensitiveStore()\n"
                "    s.put('  Alpha ', 42)\n"
                "    assert s.has('ALPHA')\n"
                "    assert s.get('alpha') == 42\n"
                "    assert s.get('  ALPHA  ') == 42\n",
                encoding="utf-8",
            )
            r4 = UEK.solve_arbitrary_environment(e4, "Fix the failing pytest tests", memory=mem, python_exe=py, allow_web=False)
            self.assertEqual(r4["status"], "VERIFIED")
            self.assertEqual(r4["mode"], "TIER1_REPO_SIBLING_ORACLE")
            self.assertEqual(r4["swe_result"]["fix"], "key = self._norm(key)")

    def test_cross_modal_opaque_bundle_unwrap_to_swe_and_offline_second_bundle(self) -> None:
        if not all(shutil.which(t) for t in ("base64", "tar")):
            self.skipTest("base64 or tar unavailable")

        mem = UEK.new_universal_memory()
        py = sys.executable

        def _make_opaque_bundle(out_path: pathlib.Path, files: dict[str, str]) -> None:
            with tempfile.TemporaryDirectory() as td2:
                p2 = pathlib.Path(td2)
                for fn, content in files.items():
                    (p2 / fn).write_text(content, encoding="utf-8")
                tgz = p2 / "pack.tar.gz"
                with tarfile.open(tgz, "w:gz") as tf:
                    for fn in files:
                        tf.add(p2 / fn, arcname=fn)
                out_path.write_text(base64.b64encode(tgz.read_bytes()).decode("ascii"), encoding="utf-8")

        with tempfile.TemporaryDirectory() as td:
            root = pathlib.Path(td)

            # First unseen opaque bundle -> acquires unwrap morphisms live + repairs broken Python code
            ws1 = root / "ws1"
            ws1.mkdir()
            _make_opaque_bundle(
                ws1 / "submission.bin",
                {
                    "calc.py": "def clamp_positive(x: int) -> int:\n    if x > 0:\n        return 0\n    return x\n",
                    "test_calc.py": (
                        "from calc import clamp_positive\n"
                        "def test_clamp():\n"
                        "    assert clamp_positive(-5) == 0\n"
                        "    assert clamp_positive(7) == 7\n"
                        "    assert clamp_positive(0) == 0\n"
                    ),
                },
            )
            r1 = UEK.solve_arbitrary_environment(
                ws1,
                "Fix the failing tests in submission.bin and extract the repaired project into fixed_repo",
                memory=mem,
                python_exe=py,
                allow_web=True,
            )
            self.assertEqual(r1["status"], "VERIFIED")
            self.assertEqual(r1["modality"], "cross_modal_bundle_swe")
            self.assertEqual(sorted(p.name for p in ws1.iterdir()), ["fixed_repo", "submission.bin"])

            # Second unseen opaque bundle -> 100% OFFLINE Tier 0 unwrap + SWE epistemic repair!
            ws2 = root / "ws2"
            ws2.mkdir()
            _make_opaque_bundle(
                ws2 / "archive_blob.dat",
                {
                    "api.py": (
                        "def ping(host: str, retries: int = 3) -> tuple:\n"
                        "    return (host, retries)\n"
                        "def run_ping() -> tuple:\n"
                        "    return ping('db.local', retry_count=2)\n"
                    ),
                    "test_api.py": (
                        "from api import run_ping\n"
                        "def test_ping():\n"
                        "    assert run_ping() == ('db.local', 2)\n"
                    ),
                },
            )
            r2 = UEK.solve_arbitrary_environment(
                ws2,
                "Fix the failing tests in archive_blob.dat and extract the repaired project into repaired_app",
                memory=mem,
                python_exe=py,
                allow_web=False,
            )
            self.assertEqual(r2["status"], "VERIFIED")
            self.assertEqual(r2["web_queries_made"], 0)
            self.assertTrue(r2["mode"].startswith("CROSS_MODAL_ALL_TIER0_COMPOSED_THEN_TIER1_SWE_EPISTEMIC"))
            self.assertEqual(sorted(p.name for p in ws2.iterdir()), ["archive_blob.dat", "repaired_app"])

    def test_unified_memory_inspectable_deletable_zero_weights_and_leak_refusal(self) -> None:
        mem = UEK.new_universal_memory()
        # Refuses leaked host path
        self.assertIsNone(
            UEK.record_api_contract(
                mem,
                defect_kind="attribute_rename",
                owner_type="/tmp/evil/mod",
                bad_symbol="foo",
                good_symbol="bar",
            )
        )
        rec = UEK.record_api_contract(
            mem,
            defect_kind="attribute_rename",
            owner_type="module:urllib.parse",
            bad_symbol="quote_pluss",
            good_symbol="quote_plus",
            corroborated_kinds=("runtime_introspection", "web_package_docs"),
        )
        self.assertIsNotNone(rec)
        cid = rec["contract_id"]

        with tempfile.TemporaryDirectory() as td:
            mp = pathlib.Path(td) / "mem.json"
            UEK.save_universal_memory(mem, mp)
            raw = mp.read_text(encoding="utf-8")
            self.assertNotIn("/tmp/", raw)
            loaded = UEK.load_universal_memory(mp)
            self.assertEqual(loaded["parameters_stored"], 0)
            self.assertEqual(loaded["model_calls"], 0)
            self.assertEqual(len(UEK.recall_api_contracts(loaded, defect_kind="attribute_rename", bad_symbol="quote_pluss")), 1)

            # Fail-closed quarantine on refutation
            ref = UEK.refute_api_contract(loaded, cid, reason="COUNTEREXAMPLE")
            self.assertEqual(ref["status"], UEK.STATUS_QUARANTINED)
            self.assertEqual(UEK.recall_api_contracts(loaded, defect_kind="attribute_rename", bad_symbol="quote_pluss"), [])

            # Deletion removes entry cleanly
            self.assertTrue(UEK.delete_memory_entry(loaded, cid))
            self.assertNotIn(cid, loaded["api_contracts"])

    def test_browser_dom_modality_routing(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            dom = [
                {"id": "nav-home", "tag": "a", "role": "link", "text": "Home"},
                {"id": "btn-deploy", "tag": "button", "role": "button", "text": "Deploy Release"},
            ]
            r = UEK.solve_arbitrary_environment(
                td,
                "Click the Deploy Release button",
                dom_nodes=dom,
            )
            self.assertEqual(r["status"], "VERIFIED")
            self.assertEqual(r["modality"], "browser_dom")
            self.assertEqual(r["dom_action"]["action"]["selector"], "btn-deploy")

    def test_brain_unified_model_one_front_door_epistemic_solve(self) -> None:
        from canonical.runtime import brain_unified_model_v1 as BUM

        model = BUM.open_model()
        py = sys.executable

        # Negative control: unknown goal with NO workspace still fails closed
        neg = model.solve("frobnicate imaginary quantum widget 9999")
        self.assertFalse(neg.get("pass"))
        self.assertEqual(neg.get("reason"), "GOAL_NOT_REPRESENTED_IN_MODEL__FAIL_CLOSED")

        with tempfile.TemporaryDirectory() as td:
            root = pathlib.Path(td)
            mem_file = root / "front_door_memory.json"

            # 1. Front door solves unseen SWE environment via mode="EPISTEMIC" and persists generalized memory
            repo1 = root / "repo1"
            repo1.mkdir()
            (repo1 / "mod_a.py").write_text(
                "from urllib import urlparse\n"
                "def get_host(u: str) -> str:\n"
                "    return urlparse(u).netloc\n",
                encoding="utf-8",
            )
            (repo1 / "test_mod_a.py").write_text(
                "from mod_a import get_host\n"
                "def test_h():\n"
                "    assert get_host('https://brain.dev/x') == 'brain.dev'\n",
                encoding="utf-8",
            )
            out1 = model.solve(
                "Fix the failing pytest tests",
                inputs={"workspace": str(repo1), "memory_path": str(mem_file), "python_exe": py, "allow_web": False},
                mode="EPISTEMIC",
            )
            self.assertTrue(out1["pass"])
            self.assertEqual(out1["model_calls"], 0)
            self.assertEqual(out1["parameters_stored"], 0)
            self.assertTrue(mem_file.is_file())

            # 2. Front door solves unseen 2nd repo OFFLINE via Tier 0 recall from persisted external JSON memory
            repo2 = root / "repo2"
            repo2.mkdir()
            (repo2 / "mod_b.py").write_text(
                "from urllib import urlparse\n"
                "def get_path(u: str) -> str:\n"
                "    return urlparse(u).path\n",
                encoding="utf-8",
            )
            (repo2 / "test_mod_b.py").write_text(
                "from mod_b import get_path\n"
                "def test_p():\n"
                "    assert get_path('https://brain.dev/a/b') == '/a/b'\n",
                encoding="utf-8",
            )
            out2 = model.solve(
                "Fix the failing pytest tests",
                inputs={"workspace": str(repo2), "memory_path": str(mem_file), "python_exe": py, "allow_web": False},
                mode="EPISTEMIC",
            )
            self.assertTrue(out2["pass"])
            self.assertEqual(out2["epistemic_result"]["mode"], "TIER0_API_CONTRACT_RECALL")
            self.assertEqual(out2["epistemic_result"]["gaps_queried"], [])

    def test_plotkin_anti_unification_cli_ast_refutation_narrowing_and_epistemic_diff(self) -> None:
        """Prove Plotkin Least General Generalization (CLI & AST), Anti-Overgeneralization
        Guards, Refutation Narrowing, Tier-0 offline AST law application, and unified
        Shallow-Scan -> Goal-Pruned Epistemic Diff (0 web calls in scan, 0 weights).
        """
        import json
        import sqlite3

        mem = UEK.new_universal_memory()

        # 1. Plotkin CLI Anti-Unification lifts paths & differing args while keeping rigid flags
        cli_law = UEK.anti_unify_command_templates(
            "jq -r '.users[].email' /tmp/env_a/staff.json > /tmp/env_a/emails.txt",
            "jq -r '.orders[].id' /tmp/env_b/sales.json > /tmp/env_b/ids.txt",
        )
        self.assertEqual(cli_law["status"], "VERIFIED")
        self.assertEqual(cli_law["template"], "jq -r __ARG_0__ __INPUT_PATH__ > __OUTPUT_PATH__")
        self.assertNotIn("/tmp/", json.dumps(cli_law))
        stored_cli = UEK.record_generalized_law(mem, cli_law)
        self.assertIsNotNone(stored_cli)
        rendered = UEK.instantiate_anti_unified_command(
            cli_law,
            {"__ARG_0__": ".items[].sku", "__INPUT_PATH__": "inv.json", "__OUTPUT_PATH__": "skus.txt"},
        )
        self.assertIsNotNone(rendered)
        self.assertIn("jq -r", rendered)
        self.assertIn("inv.json", rendered)
        self.assertIn("> skus.txt", rendered)

        # 2. Anti-Overgeneralization Guards (explicitly proves what must NOT be generalized)
        self.assertEqual(
            UEK.anti_unify_command_templates("gzip -d a.gz", "tar -xf b.tar")["status"],
            "REFUSED_HEAD_MISMATCH",
        )
        self.assertEqual(
            UEK.anti_unify_command_templates("sort -u a.txt", "sort -r b.txt")["status"],
            "REFUSED_FLAG_MISMATCH",
        )
        self.assertEqual(
            UEK.anti_unify_ast_edits("a + b", "a - b", "x.split(',')", "x.rsplit(',')")["status"],
            "REFUSED_AST_ROOT_MISMATCH",
        )

        # 3. Plotkin AST Anti-Unification -> Tier-0 offline solve on unseen 3rd repo!
        ast_law = UEK.anti_unify_ast_edits(
            "netloc.split('@', 1)",
            "netloc.rsplit('@', 1)",
            "path.split('/', 1)",
            "path.rsplit('/', 1)",
        )
        self.assertEqual(ast_law["status"], "VERIFIED")
        self.assertEqual(ast_law["before_pattern"], "__HOLE_0__.split(__HOLE_1__, 1)")
        self.assertEqual(ast_law["after_pattern"], "__HOLE_0__.rsplit(__HOLE_1__, 1)")
        self.assertEqual(ast_law["parameters_stored"], 0)
        self.assertEqual(ast_law["raw_prose_stored"], 0)
        self.assertIsNotNone(UEK.record_generalized_law(mem, ast_law))

        with tempfile.TemporaryDirectory() as tmp:
            root = pathlib.Path(tmp)
            # 3a. Unseen 3rd repo solved OFFLINE at Tier 0 using the Plotkin anti-unified AST law
            repo3 = root / "repo3"
            repo3.mkdir()
            (repo3 / "hdr.py").write_text(
                "def extract_tail(header: str) -> str:\n"
                "    _, tail = header.split(':', 1)\n"
                "    return tail\n",
                encoding="utf-8",
            )
            (repo3 / "test_hdr.py").write_text(
                "from hdr import extract_tail\n"
                "def test_multi_colon():\n"
                "    assert extract_tail('a:b:final') == 'final'\n"
                "    assert extract_tail('x:y') == 'y'\n",
                encoding="utf-8",
            )
            res3 = UEK.solve_arbitrary_environment(
                repo3,
                "Fix the failing pytest tests",
                memory=mem,
                python_exe=sys.executable,
                allow_web=False,
            )
            self.assertEqual(res3["status"], "VERIFIED")
            self.assertEqual(res3["mode"], "TIER0_ANTI_UNIFIED_AST_LAW")
            self.assertEqual(res3["gaps_queried"], [])
            self.assertEqual(res3["epistemic_diff"]["web_calls_in_scan"], 0)

            # 3b. Refutation Narrowing: forbid a discriminating fact and confirm selective refusal
            nar = UEK.narrow_law_on_refutation(
                mem,
                ast_law["law_id"],
                positive_facts=["delimiter_from_right"],
                negative_facts=["delimiter_from_right", "prefix_header_parse"],
            )
            self.assertEqual(nar["status"], "NARROWED")
            self.assertEqual(nar["added_forbid_fact"], "prefix_header_parse")
            self.assertIsNone(
                UEK.apply_anti_unified_ast_law(
                    "a, b = s.split(':', 1)\n",
                    mem["generalized_laws"][ast_law["law_id"]],
                    observed_facts=["prefix_header_parse"],
                )
            )
            self.assertIsNotNone(
                UEK.apply_anti_unified_ast_law(
                    "a, b = s.split(':', 1)\n",
                    mem["generalized_laws"][ast_law["law_id"]],
                    observed_facts=["delimiter_from_right"],
                )
            )

            # 4. Unified Shallow-Scan -> Goal-Pruned Epistemic Diff on a multi-artifact workspace
            ws_multi = root / "multi_env"
            ws_multi.mkdir()
            (ws_multi / "users.json").write_text('{"users": [{"email": "a@b.com"}]}\n', encoding="utf-8")
            (ws_multi / "metrics.csv").write_text("ts,latency_ms\n1,4.2\n", encoding="utf-8")
            (ws_multi / "notes.txt").write_text("hello world\n", encoding="utf-8")
            con = sqlite3.connect(str(ws_multi / "app.db"))
            con.execute("CREATE TABLE orders (id INT, total REAL)")
            con.commit()
            con.close()

            diff = UEK.compute_epistemic_diff(
                ws_multi,
                "Compute the SHA256 hash of notes.txt into notes.sha256",
                memory=mem,
            )
            self.assertEqual(diff["web_calls_in_scan"], 0)
            self.assertGreater(diff["pruned_irrelevant_count"], 0)
            self.assertTrue(any(a.startswith("schema:json:users.json:") for a in diff["affordances_scanned"]))
            self.assertTrue(any(a.startswith("schema:csv:metrics.csv:") for a in diff["affordances_scanned"]))
            self.assertTrue(any(a.startswith("schema:sqlite:app.db:orders") for a in diff["affordances_scanned"]))
            self.assertTrue(any("hash_sha256" in g for g in diff["epistemic_delta"]))
            self.assertTrue(UEK.delete_memory_entry(mem, ast_law["law_id"]))

    def test_automatic_online_self_compressing_anti_unification_and_nameerror_import_resolution(self) -> None:
        """Prove fully AUTOMATIC online self-compressing Plotkin anti-unification across
        3 unseen repos (ZERO manual `anti_unify` calls!) AND live `NameError` missing-import
        epistemic resolution + Tier-0 offline transfer.
        """
        mem = UEK.new_universal_memory()
        py = sys.executable

        with tempfile.TemporaryDirectory() as tmp:
            root = pathlib.Path(tmp)

            # Repo 1: `netloc.split('@', 1)` -> buffered as 1 concrete exemplar
            r1 = root / "r1"
            r1.mkdir()
            (r1 / "net.py").write_text(
                "def host_of(netloc: str) -> str:\n"
                "    _, host = netloc.split('@', 1)\n"
                "    return host\n",
                encoding="utf-8",
            )
            (r1 / "test_net.py").write_text(
                "from net import host_of\n"
                "def test_ok():\n"
                "    assert host_of('u:p@corp.org') == 'corp.org'\n"
                "    assert host_of('u:p@ss@example.com') == 'example.com'\n",
                encoding="utf-8",
            )
            res1 = UEK.solve_arbitrary_environment(r1, "Fix the failing pytest tests", memory=mem, python_exe=py, allow_web=False)
            self.assertEqual(res1["status"], "VERIFIED")
            self.assertEqual(len(mem["generalized_laws"]), 0)
            self.assertEqual(len(mem["pending_exemplars"]), 1)

            # Repo 2: `path.split('/', 1)` -> AUTOMATIC Plotkin anti-unification + exemplar compression!
            r2 = root / "r2"
            r2.mkdir()
            (r2 / "fs.py").write_text(
                "def leaf_of(path: str) -> str:\n"
                "    _, leaf = path.split('/', 1)\n"
                "    return leaf\n",
                encoding="utf-8",
            )
            (r2 / "test_fs.py").write_text(
                "from fs import leaf_of\n"
                "def test_ok():\n"
                "    assert leaf_of('a/b') == 'b'\n"
                "    assert leaf_of('a/b/final.txt') == 'final.txt'\n",
                encoding="utf-8",
            )
            res2 = UEK.solve_arbitrary_environment(r2, "Fix the failing pytest tests", memory=mem, python_exe=py, allow_web=False)
            self.assertEqual(res2["status"], "VERIFIED")
            self.assertEqual(res2["swe_result"]["consolidation"]["status"], "PROMOTED_ANTI_UNIFIED_LAW")
            self.assertEqual(len(mem["generalized_laws"]), 1)
            self.assertEqual(len(mem["pending_exemplars"]), 0)  # Self-compressed!

            # Repo 3: unseen `header.split(':', 1)` -> AUTOMATIC Tier-0 offline solve!
            r3 = root / "r3"
            r3.mkdir()
            (r3 / "hdr.py").write_text(
                "def tail_of(header: str) -> str:\n"
                "    _, tail = header.split(':', 1)\n"
                "    return tail\n",
                encoding="utf-8",
            )
            (r3 / "test_hdr.py").write_text(
                "from hdr import tail_of\n"
                "def test_ok():\n"
                "    assert tail_of('k:v') == 'v'\n"
                "    assert tail_of('a:b:end') == 'end'\n",
                encoding="utf-8",
            )
            res3 = UEK.solve_arbitrary_environment(r3, "Fix the failing pytest tests", memory=mem, python_exe=py, allow_web=False)
            self.assertEqual(res3["status"], "VERIFIED")
            self.assertEqual(res3["mode"], "TIER0_ANTI_UNIFIED_AST_LAW")
            self.assertEqual(res3["gaps_queried"], [])

            # Repo 4 & 5: Live `NameError` missing-import epistemic resolution -> Tier-0 recall!
            r4 = root / "r4"
            r4.mkdir()
            (r4 / "stemmer.py").write_text(
                "def get_stem(p: str) -> str:\n"
                "    return Path(p).stem\n",
                encoding="utf-8",
            )
            (r4 / "test_stemmer.py").write_text(
                "from stemmer import get_stem\n"
                "def test_s():\n"
                "    assert get_stem('/x/y/report.pdf') == 'report'\n",
                encoding="utf-8",
            )
            res4 = UEK.solve_arbitrary_environment(r4, "Fix the failing pytest tests", memory=mem, python_exe=py, allow_web=False)
            self.assertEqual(res4["status"], "VERIFIED")
            self.assertEqual(res4["mode"], "TIER1_SWE_EPISTEMIC_INTROSPECTION")
            self.assertIn("from pathlib import Path", (r4 / "stemmer.py").read_text(encoding="utf-8"))

            r5 = root / "r5"
            r5.mkdir()
            (r5 / "ext.py").write_text(
                "def get_ext(p: str) -> str:\n"
                "    return Path(p).suffix\n",
                encoding="utf-8",
            )
            (r5 / "test_ext.py").write_text(
                "from ext import get_ext\n"
                "def test_e():\n"
                "    assert get_ext('/x/y/data.csv') == '.csv'\n",
                encoding="utf-8",
            )
            res5 = UEK.solve_arbitrary_environment(r5, "Fix the failing pytest tests", memory=mem, python_exe=py, allow_web=False)
            self.assertEqual(res5["status"], "VERIFIED")
            self.assertEqual(res5["mode"], "TIER0_API_CONTRACT_RECALL")
            self.assertEqual(res5["gaps_queried"], [])

    def test_automatic_online_cli_self_compression_and_tier0_offline_cli_law_recall(self) -> None:
        """Prove automatic online Plotkin CLI anti-unification across 2 unseen CLI environments
        and instant Tier-0 offline execution (`TIER0_ANTI_UNIFIED_CLI_LAW`) on a 3rd unseen workspace.
        """
        mem = UEK.new_universal_memory()
        # Consolidate 2 verified CLI experiences automatically (as emitted by live runs)
        c1 = UEK.auto_consolidate_experience(
            mem, kind="cli", command="jq -r '.users[].email' staff.json > emails.txt",
        )
        self.assertEqual(c1["status"], "BUFFERED_EXEMPLAR")
        self.assertEqual(len(mem["pending_exemplars"]), 1)

        c2 = UEK.auto_consolidate_experience(
            mem, kind="cli", command="jq -r '.orders[].id' sales.json > ids.txt",
        )
        self.assertEqual(c2["status"], "PROMOTED_ANTI_UNIFIED_LAW")
        self.assertEqual(len(mem["pending_exemplars"]), 0)  # Self-compressed!
        self.assertEqual(c2["template"], "jq -r __ARG_0__ __INPUT_PATH__ > __OUTPUT_PATH__")

        # 3rd unseen workspace solved 100% OFFLINE via Tier-0 Plotkin CLI law!
        with tempfile.TemporaryDirectory() as tmp:
            ws3 = pathlib.Path(tmp) / "ws3"
            ws3.mkdir()
            (ws3 / "inv.json").write_text(
                '{"items": [{"sku": "SKU-10"}, {"sku": "SKU-20"}]}\n', encoding="utf-8",
            )
            res3 = UEK.solve_arbitrary_environment(
                ws3,
                "Use jq to extract '.items[].sku' from inv.json into skus.txt",
                memory=mem,
                allow_web=False,
            )
            self.assertEqual(res3["status"], "VERIFIED")
            self.assertEqual(res3["mode"], "TIER0_ANTI_UNIFIED_CLI_LAW")
            self.assertEqual(res3["web_queries_made"], 0)
            self.assertEqual(res3["gaps_queried"], [])
            self.assertEqual((ws3 / "skus.txt").read_text(encoding="utf-8").splitlines(), ["SKU-10", "SKU-20"])

    def test_live_http_web_ui_epistemic_safety_csrf_recovery_and_tier0_cross_app_transfer(self) -> None:
        """Prove live interactive HTTP/HTML Web UI Epistemic Solver via ONE Front Door:
        - App 1 (unseen): rotating CSRF token, destructive `/nuke` trap form (must stay 0 hits),
          hidden conditional field `company` revealed only on HTTP 400 rejection -> solved & distilled
          into a generalized `web_workflow` law (ZERO concrete URLs, tokens, or emails stored!).
        - App 2 (COMPLETELY unseen port, `/register`, `/wipe` trap, new CSRF tokens, new user):
          recalls generalized `web_workflow` law at Tier 0, pre-binds `company` on round 1,
          replays fresh CSRF, refuses `/wipe`, verifies in 1 round-trip!
        """
        import http.server
        import json as _json
        import threading
        import urllib.parse
        from canonical.runtime.brain_unified_model_v1 import open_model

        def _spawn_app(*, form_path: str, trap_path: str, trap_label: str):
            state = {"csrf_seq": 0, "valid_csrf": "", "trap_hits": 0, "accepted": []}

            class _Handler(http.server.BaseHTTPRequestHandler):
                def log_message(self, fmt, *args):
                    pass

                def do_GET(self):
                    state["csrf_seq"] += 1
                    tok = f"tok_{form_path.strip('/')}_{state['csrf_seq']}"
                    state["valid_csrf"] = tok
                    html = (
                        f"<html><body>"
                        f"<form action='{trap_path}' method='post'>"
                        f"<button type='submit'>{trap_label}</button></form>"
                        f"<form action='{form_path}' method='post'>"
                        f"<input type='hidden' name='csrf' value='{tok}'>"
                        f"<input type='text' name='email' required>"
                        f"<select name='plan' required>"
                        f"<option value='free'>free</option><option value='pro'>pro</option></select>"
                        f"<button type='submit'>Continue</button></form></body></html>"
                    ).encode("utf-8")
                    self.send_response(200)
                    self.send_header("Content-Type", "text/html")
                    self.send_header("Content-Length", str(len(html)))
                    self.end_headers()
                    self.wfile.write(html)

                def do_POST(self):
                    length = int(self.headers.get("Content-Length") or 0)
                    raw = self.rfile.read(length).decode("utf-8", errors="replace")
                    fields = {k: v[0] for k, v in urllib.parse.parse_qs(raw).items()}
                    if self.path == trap_path:
                        state["trap_hits"] += 1
                        self.send_response(200)
                        self.end_headers()
                        self.wfile.write(b"DESTROYED")
                        return
                    if fields.get("csrf") != state["valid_csrf"]:
                        msg = b"stale 'csrf' token"
                        self.send_response(400)
                        self.end_headers()
                        self.wfile.write(msg)
                        return
                    if fields.get("plan") == "pro" and not fields.get("company"):
                        msg = b"field 'company' is required when plan is pro"
                        self.send_response(400)
                        self.end_headers()
                        self.wfile.write(msg)
                        return
                    state["accepted"].append(fields)
                    body = _json.dumps({"ok": True, "email": fields.get("email"), "company": fields.get("company")}).encode("utf-8")
                    self.send_response(200)
                    self.send_header("Content-Type", "application/json")
                    self.end_headers()
                    self.wfile.write(body)

            srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), _Handler)
            port = srv.server_address[1]
            t = threading.Thread(target=srv.serve_forever, daemon=True)
            t.start()
            return srv, port, state

        srv1, port1, st1 = _spawn_app(form_path="/apply", trap_path="/nuke", trap_label="Delete account")
        srv2, port2, st2 = _spawn_app(form_path="/register", trap_path="/wipe", trap_label="Wipe workspace")
        try:
            with tempfile.TemporaryDirectory() as tmp:
                mem_file = pathlib.Path(tmp) / "web_mem.json"
                model = open_model()

                # App 1: Cold epistemic solve (discovers conditional `company`, refuses `/nuke`, replays fresh CSRF)
                out1 = model.solve(
                    f"Submit the signup form at http://127.0.0.1:{port1}/apply with email=ada@example.org, plan=pro, company=AnalyticalEngines",
                    inputs={"web_url": f"http://127.0.0.1:{port1}/apply", "memory_path": str(mem_file)},
                    mode="EPISTEMIC",
                )
                self.assertTrue(out1["pass"])
                er1 = out1["epistemic_result"]
                self.assertEqual(er1["modality"], "live_http_web_ui")
                self.assertEqual(er1["mode"], "EPISTEMIC_WEB_UI_SOLVED")
                self.assertEqual(er1["rounds"], 2)
                self.assertEqual(st1["trap_hits"], 0)
                self.assertIn("/nuke", er1["blocked_destructive_forms"])
                self.assertEqual(st1["accepted"][0]["company"], "AnalyticalEngines")

                # Verify generalized law stores ZERO concrete URLs, ports, CSRF tokens, or user emails!
                mem_text = mem_file.read_text(encoding="utf-8")
                self.assertNotIn(str(port1), mem_text)
                self.assertNotIn("ada@example.org", mem_text)
                self.assertNotIn("tok_apply", mem_text)
                self.assertNotIn("AnalyticalEngines", mem_text)

                # App 2: Completely unseen port/action/trap/user -> Tier-0 1-round transfer!
                out2 = model.solve(
                    f"Submit the form at http://127.0.0.1:{port2}/register with email=grace@navy.mil, plan=pro, company=COBOLCorp",
                    inputs={"web_url": f"http://127.0.0.1:{port2}/register", "memory_path": str(mem_file)},
                    mode="EPISTEMIC",
                )
                self.assertTrue(out2["pass"])
                er2 = out2["epistemic_result"]
                self.assertEqual(er2["mode"], "TIER0_WEB_WORKFLOW_LAW")
                self.assertEqual(er2["rounds"], 1)  # Solved on FIRST attempt — zero wasted error round-trip!
                self.assertEqual(st2["trap_hits"], 0)
                self.assertIn("/wipe", er2["blocked_destructive_forms"])
                self.assertEqual(st2["accepted"][0]["company"], "COBOLCorp")
                self.assertEqual(er2["model_calls"], 0)
                self.assertEqual(er2["parameters_stored"], 0)
        finally:
            srv1.shutdown()
            srv1.server_close()
            srv2.shutdown()
            srv2.server_close()

    def test_swe_ifexp_truthiness_sibling_regex_and_str_explosion_laws(self) -> None:
        """Verify 3 general zero-LLM SWE laws (IfExp truthiness->is_not_none, sibling-import
        regex `$`->`\\Z`, and character-exploded `list(s)`->`s` unwrap) on clean synthetic repos.
        """
        from canonical.runtime.causal_angelic_swe_engine_v1 import solve_repository

        py = sys.executable
        with tempfile.TemporaryDirectory() as tmp:
            root = pathlib.Path(tmp)

            # 1. ast.IfExp truthiness vs None (`map(key, items) if key else items`)
            r1 = root / "ifexp_repo"
            r1.mkdir()
            (r1 / "uniq.py").write_text(
                "def all_unique(items, key=None):\n"
                "    seen = set()\n"
                "    for x in (map(key, items) if key else items):\n"
                "        if x in seen:\n"
                "            return False\n"
                "        seen.add(x)\n"
                "    return True\n",
                encoding="utf-8",
            )
            (r1 / "test_uniq.py").write_text(
                "from uniq import all_unique\n"
                "class FalseyKey:\n"
                "    def __bool__(self): return False\n"
                "    def __call__(self, x): return x.lower()\n"
                "def test_falsey_key():\n"
                "    assert all_unique(['A', 'B', 'a'], FalseyKey()) is False\n"
                "    assert all_unique(['A', 'B', 'c'], FalseyKey()) is True\n",
                encoding="utf-8",
            )
            res1 = solve_repository(r1, ["test_uniq.py"], python_exe=py, timeout_s=20.0)
            self.assertIsNotNone(res1.get("winner"))
            self.assertEqual(res1["winner"]["tier"], "TIER3_TRUTHINESS_NONE")

            # 2. Sibling-imported module regex `$` -> `\Z`
            r2 = root / "sib_regex_repo"
            (r2 / "pkg").mkdir(parents=True)
            (r2 / "pkg" / "__init__.py").write_text("", encoding="utf-8")
            (r2 / "pkg" / "_tok.py").write_text(
                "import re\n"
                "END_RE = re.compile(r'$')\n",
                encoding="utf-8",
            )
            (r2 / "pkg" / "parser.py").write_text(
                "from ._tok import END_RE\n"
                "def parse_word(s: str) -> str:\n"
                "    i = 0\n"
                "    while i < len(s) and s[i].isalpha():\n"
                "        i += 1\n"
                "    if not END_RE.match(s, i):\n"
                "        raise ValueError('trailing')\n"
                "    return s[:i]\n",
                encoding="utf-8",
            )
            (r2 / "test_parser.py").write_text(
                "import pytest\n"
                "from pkg.parser import parse_word\n"
                "def test_ok():\n"
                "    assert parse_word('hello') == 'hello'\n"
                "def test_trailing_nl():\n"
                "    with pytest.raises(ValueError):\n"
                "        parse_word('hello\\n')\n",
                encoding="utf-8",
            )
            res2 = solve_repository(r2, ["test_parser.py"], python_exe=py, timeout_s=20.0)
            self.assertIsNotNone(res2.get("winner"))
            self.assertEqual(res2["winner"]["tier"], "TIER3_STATIC_REGEX_ANCHOR")
            self.assertEqual(res2["winner"]["file"], "pkg/_tok.py")

            # 3. Character-exploded `list(s)` inside f-string unwrap
            r3 = root / "explode_repo"
            r3.mkdir()
            (r3 / "meta.py").write_text(
                "def check_charset(cs: str) -> str:\n"
                "    if cs != 'UTF-8':\n"
                "        raise ValueError(f'only UTF-8 allowed, not {list(cs)}')\n"
                "    return cs\n",
                encoding="utf-8",
            )
            (r3 / "test_meta.py").write_text(
                "import pytest\n"
                "from meta import check_charset\n"
                "def test_ok():\n"
                "    assert check_charset('UTF-8') == 'UTF-8'\n"
                "def test_bad():\n"
                "    with pytest.raises(ValueError, match='latin-1'):\n"
                "        check_charset('latin-1')\n",
                encoding="utf-8",
            )
            res3 = solve_repository(r3, ["test_meta.py"], python_exe=py, timeout_s=20.0)
            self.assertIsNotNone(res3.get("winner"))
            self.assertEqual(res3["winner"]["tier"], "TIER3_STR_EXPLOSION_UNWRAP")

            # 4. Single-pass iterator/generator exhaustion materialization (`list(...)` / `tuple(...)`)
            r4 = root / "gen_repo"
            r4.mkdir()
            (r4 / "pipe.py").write_text(
                "def process(items, hook):\n"
                "    vals = hook(items)\n"
                "    for v in vals:\n"
                "        if v < 0:\n"
                "            raise ValueError('neg')\n"
                "    return [v * 2 for v in vals]\n",
                encoding="utf-8",
            )
            (r4 / "test_pipe.py").write_text(
                "from pipe import process\n"
                "def test_generator_hook():\n"
                "    assert process([1, 2, 3], lambda xs: (x for x in xs)) == [2, 4, 6]\n"
                "    assert process([4, 5], lambda xs: (x for x in xs)) == [8, 10]\n",
                encoding="utf-8",
            )
            res4 = solve_repository(r4, ["test_pipe.py"], python_exe=py, timeout_s=20.0)
            self.assertIsNotNone(res4.get("winner"))
            self.assertEqual(res4["winner"]["tier"], "TIER3_ITERATOR_MATERIALIZE")

    def test_multi_location_validation_raise_guard_cwe_report_and_arbitrary_ws_path(self) -> None:
        """Verify multi-location `TIER3_VALIDATION_RAISE_GUARD` + first-principles CWE report
        emission via ONE Front Door, plus arbitrary-workspace absolute path relativization.
        """
        import json as _json
        from canonical.runtime.brain_unified_model_v1 import open_model
        from canonical.runtime import unified_computer_use_agent_v1 as CU_AGENT

        py = sys.executable
        with tempfile.TemporaryDirectory() as tmp:
            ws = pathlib.Path(tmp) / "hdr_app"
            ws.mkdir()
            (ws / "headers.py").write_text(
                "def norm_name(k):\n"
                "    k = str(k)\n"
                "    return k.title()\n\n"
                "def norm_val(v):\n"
                "    v = str(v)\n"
                "    return v.strip()\n\n"
                "class HeaderBag(dict):\n"
                "    def put(self, k, v):\n"
                "        self[norm_name(k)] = norm_val(v)\n",
                encoding="utf-8",
            )
            (ws / "test_headers.py").write_text(
                "import pytest\n"
                "from headers import HeaderBag\n"
                "def test_ok():\n"
                "    b = HeaderBag()\n"
                "    b.put('content-type', 'text/plain')\n"
                "    assert b['Content-Type'] == 'text/plain'\n"
                "def test_prevent_control_characters_in_headers():\n"
                "    b = HeaderBag()\n"
                "    for bad in ('a\\nb', 'a\\rb', 'a\\0b'):\n"
                "        with pytest.raises(ValueError):\n"
                "            b.put(bad, 'ok')\n"
                "        with pytest.raises(ValueError):\n"
                "            b.put('X-Test', bad)\n",
                encoding="utf-8",
            )
            model = open_model()
            out = model.solve(
                f"Fix the CRLF / CWE-93 vulnerability in {ws}/headers.py and write {ws}/report.jsonl",
                inputs={"workspace": str(ws), "python_exe": py, "allow_web": False, "timeout_s": 20.0},
                mode="EPISTEMIC",
            )
            self.assertTrue(out["pass"])
            er = out["epistemic_result"]
            self.assertEqual(er["mode"], "CAUSAL_ANGELIC_TIER3_VALIDATION_RAISE_GUARD")
            self.assertEqual(er["model_calls"], 0)
            self.assertEqual(er["parameters_stored"], 0)
            rep = _json.loads((ws / "report.jsonl").read_text(encoding="utf-8").strip())
            self.assertEqual(rep["file_path"], str(ws / "headers.py"))
            self.assertEqual(rep["cwe_id"], ["cwe-93"])

            # Verify arbitrary-workspace absolute path relativization (not only `/app/...`)
            env_obs = {
                "workspace": str(ws),
                "observables": ["has_git_repo"],
                "git_repos": [{"rel_path": "repo"}],
            }
            goal = CU_AGENT.compile_instruction(
                f"Recover the secret from {ws}/repo and write it to {ws}/secret.txt (format secret[...]).",
                env_obs,
            )
            self.assertEqual(goal["output_path"], "secret.txt")

    def test_swe_format_repr_canonical_obj_name_and_subclass_priority_laws(self) -> None:
        """Verify 3 general zero-LLM SWE laws (`TIER3_FORMAT_QUOTED_TO_REPR`,
        `TIER3_CANONICAL_OBJ_NAME`, `TIER3_SUBCLASS_PRIORITY_WEIGHT`) on clean synthetic repos.
        """
        from canonical.runtime.causal_angelic_swe_engine_v1 import solve_repository

        py = sys.executable
        with tempfile.TemporaryDirectory() as tmp:
            root = pathlib.Path(tmp)

            # 1. `'{field}'` -> `{field!r}` format escape law
            r1 = root / "fmt_repo"
            r1.mkdir()
            (r1 / "paths.py").write_text(
                "def fail_dir(p: str) -> str:\n"
                "    return \"File '{fname}' is a directory.\".format(fname=p)\n",
                encoding="utf-8",
            )
            (r1 / "test_paths.py").write_text(
                "from paths import fail_dir\n"
                "def test_esc():\n"
                "    assert 'my\\\\ndir' in fail_dir('/tmp/my\\ndir')\n"
                "    assert 'plain' in fail_dir('plain')\n",
                encoding="utf-8",
            )
            res1 = solve_repository(r1, ["test_paths.py"], python_exe=py, timeout_s=20.0)
            self.assertIsNotNone(res1.get("winner"))
            self.assertEqual(res1["winner"]["tier"], "TIER3_FORMAT_QUOTED_TO_REPR")

            # 2. Canonical object `.name` in tuple return (`return cmd_name, cmd, rest`)
            r2 = root / "alias_repo"
            r2.mkdir()
            (r2 / "cli.py").write_text(
                "class Cmd:\n"
                "    def __init__(self, name): self.name = name\n"
                "class Group:\n"
                "    def __init__(self): self.cmds = {'push': Cmd('push')}\n"
                "    def get_cmd(self, nm):\n"
                "        for k, v in self.cmds.items():\n"
                "            if k.startswith(nm): return v\n"
                "        return None\n"
                "    def resolve(self, args):\n"
                "        cmd_name = args[0]\n"
                "        cmd = self.get_cmd(cmd_name)\n"
                "        return cmd_name, cmd, args[1:]\n"
                "    def usage(self, args):\n"
                "        nm, _, _ = self.resolve(args)\n"
                "        return f'Usage: root {nm}'\n",
                encoding="utf-8",
            )
            (r2 / "test_cli.py").write_text(
                "from cli import Group\n"
                "def test_alias():\n"
                "    g = Group()\n"
                "    assert g.usage(['pu']).startswith('Usage: root push')\n"
                "    assert g.usage(['push']).startswith('Usage: root push')\n",
                encoding="utf-8",
            )
            res2 = solve_repository(r2, ["test_cli.py"], python_exe=py, timeout_s=20.0)
            self.assertIsNotNone(res2.get("winner"))
            self.assertEqual(res2["winner"]["tier"], "TIER3_CANONICAL_OBJ_NAME")

            # 3. Subclass priority weight override
            r3 = root / "prio_repo"
            r3.mkdir()
            (r3 / "conv.py").write_text(
                "class BaseConv:\n"
                "    weight = 100\n"
                "class IntConv(BaseConv):\n"
                "    weight = 50\n"
                "    tag = 'int'\n"
                "class UuidConv(BaseConv):\n"
                "    tag = 'uuid'\n"
                "def match_best():\n"
                "    best = min([IntConv(), UuidConv()], key=lambda c: c.weight)\n"
                "    return (best.tag, 'ok')\n",
                encoding="utf-8",
            )
            (r3 / "test_conv.py").write_text(
                "from conv import match_best\n"
                "def test_weight():\n"
                "    assert match_best() == ('uuid', 'ok')\n",
                encoding="utf-8",
            )
            res3 = solve_repository(r3, ["test_conv.py"], python_exe=py, timeout_s=20.0)
            self.assertIsNotNone(res3.get("winner"))
            self.assertEqual(res3["winner"]["tier"], "TIER3_SUBCLASS_PRIORITY_WEIGHT")

    def test_swe_stale_attr_descriptor_fallback_and_const_default_laws(self) -> None:
        """Verify 3 general Iteration-5 SWE causal AST laws on fresh unseen synthetic repos:
          1. TIER3_STALE_ATTR_TO_COMPUTED_LOCAL (`self.X` -> `X_value` from `self.get_X()`)
          2. TIER3_DESCRIPTOR_UNBOUND_FALLBACK (`__class__ = Desc(fallback=property(type))`)
          3. TIER3_CONST_DEFAULT_ABDUCT (`def f(..., code=302)` -> `code=303`)
        """
        from canonical.runtime.causal_angelic_swe_engine_v1 import solve_repository

        py = sys.executable
        with tempfile.TemporaryDirectory() as tmp:
            root = pathlib.Path(tmp)

            # 1. Stale attribute vs computed local
            r1 = root / "stale_attr_repo"
            r1.mkdir()
            (r1 / "flag.py").write_text(
                "class Flag:\n"
                "    def __init__(self, default=False):\n"
                "        self.default = default\n"
                "        self.opts = ['--on']\n"
                "        self.secondary = ['--off']\n"
                "    def get_default(self, override):\n"
                "        return override if override is not None else self.default\n"
                "    def label(self, override=None):\n"
                "        default_value = self.get_default(override)\n"
                "        chosen = (self.opts if self.default else self.secondary)[0]\n"
                "        return f'default: {chosen}'\n",
                encoding="utf-8",
            )
            (r1 / "test_flag.py").write_text(
                "from flag import Flag\n"
                "def test_override():\n"
                "    f = Flag(default=False)\n"
                "    assert f.label(override=True) == 'default: --on'\n"
                "    assert f.label(override=None) == 'default: --off'\n",
                encoding="utf-8",
            )
            res1 = solve_repository(r1, ["test_flag.py"], python_exe=py, timeout_s=20.0)
            self.assertIsNotNone(res1.get("winner"))
            self.assertEqual(res1["winner"]["tier"], "TIER3_STALE_ATTR_TO_COMPUTED_LOCAL")

            # 2. Unbound descriptor __class__ fallback
            r2 = root / "desc_repo"
            r2.mkdir()
            (r2 / "proxy.py").write_text(
                "class Lookup:\n"
                "    def __init__(self, fallback=None):\n"
                "        self.fallback = fallback\n"
                "    def __set_name__(self, owner, name):\n"
                "        self.name = name\n"
                "    def __get__(self, inst, owner=None):\n"
                "        if inst is None:\n"
                "            return self\n"
                "        try:\n"
                "            obj = inst._current()\n"
                "        except RuntimeError:\n"
                "            if self.fallback is None:\n"
                "                raise\n"
                "            return self.fallback.__get__(inst, owner)\n"
                "        return getattr(obj, self.name)\n"
                "class Proxy:\n"
                "    def _current(self):\n"
                "        raise RuntimeError('unbound')\n"
                "    __class__ = Lookup()\n"
                "    __len__ = Lookup()\n",
                encoding="utf-8",
            )
            (r2 / "test_proxy.py").write_text(
                "import pytest\n"
                "from proxy import Proxy\n"
                "def test_isinstance():\n"
                "    p = Proxy()\n"
                "    assert p.__class__ is Proxy\n"
                "    assert not isinstance(p, dict)\n"
                "def test_len_still_raises():\n"
                "    p = Proxy()\n"
                "    with pytest.raises(RuntimeError):\n"
                "        p.__len__()\n",
                encoding="utf-8",
            )
            res2 = solve_repository(r2, ["test_proxy.py"], python_exe=py, timeout_s=20.0)
            self.assertIsNotNone(res2.get("winner"))
            self.assertEqual(res2["winner"]["tier"], "TIER3_DESCRIPTOR_UNBOUND_FALLBACK")

            # 3. Constant default parameter abduction
            r3 = root / "const_def_repo"
            r3.mkdir()
            (r3 / "http_util.py").write_text(
                "def make_redirect(url: str, code: int = 302) -> dict:\n"
                "    return {'url': url, 'status': code}\n",
                encoding="utf-8",
            )
            (r3 / "test_http_util.py").write_text(
                "from http_util import make_redirect\n"
                "def test_redirect_default():\n"
                "    assert make_redirect('/next')['status'] == 303\n",
                encoding="utf-8",
            )
            res3 = solve_repository(r3, ["test_http_util.py"], python_exe=py, timeout_s=20.0)
            self.assertIsNotNone(res3.get("winner"))
            self.assertEqual(res3["winner"]["tier"], "TIER3_CONST_DEFAULT_ABDUCT")

    def test_swe_iter7_sibling_guard_xfail_map_commute_and_regex_fullmatch(self) -> None:
        """Verify Iteration 7 SWE laws (xfail preservation + inner sibling guard conjunct,
        iterator map-repeat commutation, and static-cone regex fullmatch) on unseen packages.
        """
        from canonical.runtime.causal_angelic_swe_engine_v1 import solve_repository

        py = sys.executable
        with tempfile.TemporaryDirectory(prefix="swe_iter7_a_") as tmp:
            root = pathlib.Path(tmp)

            # 1. Inner sibling guard conjunct + @pytest.mark.xfail preservation
            r1 = root / "guard_repo"
            r1.mkdir()
            (r1 / "model.py").write_text(
                "NOOP = object()\n"
                "def build(items, readonly=False, cls_hook=None):\n"
                "    has_cls = cls_hook is not None and cls_hook is not NOOP\n"
                "    need_cache = readonly\n"
                "    for it in items:\n"
                "        if it['hook'] is not None:\n"
                "            if readonly is True:\n"
                "                raise ValueError('readonly forbids hook')\n"
                "            need_cache = True\n"
                "        elif has_cls and it['hook'] is not NOOP:\n"
                "            need_cache = True\n"
                "    return need_cache\n",
                encoding="utf-8",
            )
            (r1 / "test_model.py").write_text(
                "import pytest\n"
                "from model import NOOP, build\n"
                "def test_readonly_noop_ok():\n"
                "    assert build([{'hook': NOOP}], readonly=True) is True\n"
                "def test_readonly_real_hook_raises():\n"
                "    with pytest.raises(ValueError):\n"
                "        build([{'hook': 'check'}], readonly=True)\n"
                "def test_mutable_noop_still_caches():\n"
                "    assert build([{'hook': NOOP}], readonly=False) is True\n"
                "@pytest.mark.xfail(reason='known expected fail')\n"
                "def test_expected_xfail():\n"
                "    assert False\n",
                encoding="utf-8",
            )
            res1 = solve_repository(r1, ["test_model.py"], python_exe=py, timeout_s=20.0)
            self.assertEqual(res1["status"], "VERIFIED", res1)
            self.assertEqual(res1["winner"]["tier"], "TIER3_SIBLING_GUARD_CONJUNCT")

            # 2. Iterator map-repeat commutation: tuple(map(tuple, streams * copies)) -> tuple(map(tuple, streams)) * copies
            r2 = root / "pool_repo"
            r2.mkdir()
            (r2 / "pool.py").write_text(
                "def sample_pools(*streams, copies=1):\n"
                "    pools = tuple(map(tuple, streams * copies))\n"
                "    return tuple(p[0] for p in pools)\n",
                encoding="utf-8",
            )
            (r2 / "test_pool.py").write_text(
                "from pool import sample_pools\n"
                "def test_iter_copies():\n"
                "    assert sample_pools(iter([1, 2]), iter(['a', 'b']), copies=3) == (1, 'a', 1, 'a', 1, 'a')\n",
                encoding="utf-8",
            )
            res2 = solve_repository(r2, ["test_pool.py"], python_exe=py, timeout_s=20.0)
            self.assertEqual(res2["status"], "VERIFIED", res2)
            self.assertEqual(res2["winner"]["tier"], "TIER3_MAP_REPEAT_COMMUTE")

            # 3. Static-cone regex `.match(` -> `.fullmatch(` (even when called via worker thread)
            r3 = root / "cors_repo"
            r3.mkdir()
            (r3 / "gate.py").write_text(
                "import re\n"
                "class OriginGate:\n"
                "    def __init__(self, pat):\n"
                "        self.origin_regex = re.compile(pat)\n"
                "    def allowed(self, origin):\n"
                "        return bool(self.origin_regex.match(origin))\n",
                encoding="utf-8",
            )
            (r3 / "test_gate.py").write_text(
                "import threading\n"
                "from gate import OriginGate\n"
                "def test_fullmatch_in_thread():\n"
                "    g = OriginGate(r'https://.*\\.example\\.org')\n"
                "    out = []\n"
                "    t = threading.Thread(target=lambda: out.append((g.allowed('https://a.example.org'), g.allowed('https://a.example.org.evil.com'))))\n"
                "    t.start(); t.join()\n"
                "    assert out == [(True, False)]\n",
                encoding="utf-8",
            )
            res3 = solve_repository(r3, ["test_gate.py"], python_exe=py, timeout_s=20.0)
            self.assertEqual(res3["status"], "VERIFIED", res3)
            self.assertEqual(res3["winner"]["tier"], "TIER3_STATIC_REGEX_FULLMATCH")

    def test_swe_iter7_unwrap_unary_default_guard_table_alias_and_replace_narrow(self) -> None:
        """Verify Iteration 7 SWE laws (unary transform unwrap, bool-attr default guard,
        regex dispatch-table alias abduction, and scientific-notation replace context narrowing).
        """
        from canonical.runtime.causal_angelic_swe_engine_v1 import solve_repository

        py = sys.executable
        with tempfile.TemporaryDirectory(prefix="swe_iter7_b_") as tmp:
            root = pathlib.Path(tmp)

            # 1. Over-applied unary unquote unwrap in yield
            r1 = root / "hdr_repo"
            r1.mkdir()
            (r1 / "hdr.py").write_text(
                "def _unquote(s):\n"
                "    return s[1:-1] if len(s) >= 2 and s[0] == '\"' and s[-1] == '\"' else s\n"
                "def parse_pairs(raw):\n"
                "    for part in raw.split(';'):\n"
                "        k, v = part.strip().split('=', 1)\n"
                "        yield _unquote(k), _unquote(v)\n",
                encoding="utf-8",
            )
            (r1 / "test_hdr.py").write_text(
                "from hdr import parse_pairs\n"
                "def test_quoted_key_preserved():\n"
                "    assert dict(parse_pairs('a=\"1\"; \"__k\"=\"v\"')) == {'a': '1', '\"__k\"': 'v'}\n",
                encoding="utf-8",
            )
            res1 = solve_repository(r1, ["test_hdr.py"], python_exe=py, timeout_s=20.0)
            self.assertEqual(res1["status"], "VERIFIED", res1)
            self.assertEqual(res1["winner"]["tier"], "TIER3_UNWRAP_UNARY_CALL_ON_DIFF")

            # 2. Bool-attr default guard strengthening (`and not self.mandatory`)
            r2 = root / "flag_repo"
            r2.mkdir()
            (r2 / "flag.py").write_text(
                "class Opt:\n"
                "    def __init__(self, is_toggle=False, mandatory=False, default=None):\n"
                "        self.mandatory = mandatory\n"
                "        self.default = default\n"
                "        no_def = default is None\n"
                "        if is_toggle and no_def:\n"
                "            self.default = False\n"
                "    def resolve(self, val):\n"
                "        if val is None and self.default is None and self.mandatory:\n"
                "            return 'MISSING'\n"
                "        return self.default if val is None else val\n",
                encoding="utf-8",
            )
            (r2 / "test_flag.py").write_text(
                "from flag import Opt\n"
                "def test_mandatory_toggle():\n"
                "    assert Opt(is_toggle=True, mandatory=True).resolve(None) == 'MISSING'\n"
                "def test_optional_toggle():\n"
                "    assert Opt(is_toggle=True).resolve(None) is False\n",
                encoding="utf-8",
            )
            res2 = solve_repository(r2, ["test_flag.py"], python_exe=py, timeout_s=20.0)
            self.assertEqual(res2["status"], "VERIFIED", res2)
            self.assertEqual(res2["winner"]["tier"], "TIER3_DEFAULT_GUARD_BOOL_ATTR")

            # 3. Regex table alias abduction (`("falcon", "falcon")` -> `("falcon|fal", "falcon")`)
            r3 = root / "ua_repo"
            r3.mkdir()
            (r3 / "agent.py").write_text(
                "import re\n"
                "AGENTS = (('falcon', 'falcon'), ('sparrow', 'sparrow'))\n"
                "def detect(s):\n"
                "    for pat, lbl in AGENTS:\n"
                "        m = re.search(rf'(?:{pat})/(\\d+\\.\\d+)', s, re.I)\n"
                "        if m:\n"
                "            return lbl, m.group(1)\n"
                "    return None, None\n",
                encoding="utf-8",
            )
            (r3 / "test_agent.py").write_text(
                "from agent import detect\n"
                "def test_fal_alias():\n"
                "    assert detect('Sparrow/1.0 Fal/4.2') == ('falcon', '4.2')\n"
                "def test_sparrow():\n"
                "    assert detect('Sparrow/1.0') == ('sparrow', '1.0')\n",
                encoding="utf-8",
            )
            res3 = solve_repository(r3, ["test_agent.py"], python_exe=py, timeout_s=20.0)
            self.assertEqual(res3["status"], "VERIFIED", res3)
            self.assertEqual(res3["winner"]["tier"], "TIER3_REGEX_TABLE_ALIAS_ABDUCT")

            # 4. Scientific-notation `.replace('-0', '-')` -> `.replace('e-0', 'e-')`
            r4 = root / "fmt_repo"
            r4.mkdir()
            (r4 / "fmt.py").write_text(
                "def short_num(n):\n"
                "    f = '{0:.3g}'.format(n).replace('+0', '+').replace('-0', '-')\n"
                "    s = str(n)\n"
                "    return f if len(f) < len(s) else s\n",
                encoding="utf-8",
            )
            (r4 / "test_fmt.py").write_text(
                "from fmt import short_num\n"
                "def test_neg_frac():\n"
                "    assert short_num(-0.1234) == '-0.123'\n"
                "    assert short_num(1e-5) == '1e-5'\n",
                encoding="utf-8",
            )
            res4 = solve_repository(r4, ["test_fmt.py"], python_exe=py, timeout_s=20.0)
            self.assertEqual(res4["status"], "VERIFIED", res4)
            self.assertEqual(res4["winner"]["tier"], "TIER3_REPLACE_CONTEXT_NARROW")

    def test_iter8_unseen_swe_structural_laws_varargs_regex_and_str_diff_abduct(self) -> None:
        """Iter 8 unseen generalization tests for Tier 3b laws #26-#28:
        - #26 TIER3_VARARGS_STAR_PARAM (`def batch(cls, tasks, ...)` -> `*tasks`)
        - #27 TIER3_REGEX_QUANTIFIER_RELAX (`[0-9]{0,5}` -> `0*[0-9]{0,5}` on leading zeros)
        - #28 TIER3_STATIC_STR_DIFF_ABDUCT (unified-diff literal mismatch abduction)
        """
        from canonical.runtime.causal_angelic_swe_engine_v1 import solve_repository

        py = sys.executable
        with tempfile.TemporaryDirectory(prefix="uek_iter8_laws_") as td:
            root = pathlib.Path(td)

            # 1. Varargs `*param` promotion on positional arity mismatch
            r1 = root / "batch_repo"
            r1.mkdir()
            (r1 / "runner.py").write_text(
                "class Runner:\n"
                "    @classmethod\n"
                "    def collect(cls, items, factor=1):\n"
                "        return [x * factor for x in items]\n",
                encoding="utf-8",
            )
            (r1 / "test_runner.py").write_text(
                "from runner import Runner\n"
                "def test_variadic():\n"
                "    assert Runner.collect(2, 3, 4, factor=10) == [20, 30, 40]\n",
                encoding="utf-8",
            )
            res1 = solve_repository(r1, ["test_runner.py"], python_exe=py, timeout_s=20.0)
            self.assertEqual(res1["status"], "VERIFIED", res1)
            self.assertEqual(res1["winner"]["tier"], "TIER3_VARARGS_STAR_PARAM")

            # 2. Leading-zero regex bounded quantifier relaxation
            r2 = root / "addr_repo"
            r2.mkdir()
            (r2 / "addr.py").write_text(
                "import re\n"
                "ADDR_PAT = re.compile(r'^([a-z]+)(?::([0-9]{0,5}))?$')\n"
                "def parse_port(s):\n"
                "    m = ADDR_PAT.match(s)\n"
                "    if not m:\n"
                "        raise ValueError(f'bad addr {s}')\n"
                "    return int(m.group(2)) if m.group(2) else None\n",
                encoding="utf-8",
            )
            (r2 / "test_addr.py").write_text(
                "from addr import parse_port\n"
                "def test_leading_zeros():\n"
                "    assert parse_port('db:000008080') == 8080\n"
                "    assert parse_port('db:443') == 443\n",
                encoding="utf-8",
            )
            res2 = solve_repository(r2, ["test_addr.py"], python_exe=py, timeout_s=20.0)
            self.assertEqual(res2["status"], "VERIFIED", res2)
            self.assertEqual(res2["winner"]["tier"], "TIER3_REGEX_QUANTIFIER_RELAX")

            # 3. Unified-diff static string literal abduction
            r3 = root / "msg_repo"
            r3.mkdir()
            (r3 / "diag.py").write_text(
                "def format_hint(tok):\n"
                "    return f'Expected operator (==, !=, not, not in) near {tok}'\n",
                encoding="utf-8",
            )
            (r3 / "test_diag.py").write_text(
                "from diag import format_hint\n"
                "def test_msg():\n"
                "    assert format_hint('x') == 'Expected operator (==, !=, in, not in) near x'\n",
                encoding="utf-8",
            )
            res3 = solve_repository(r3, ["test_diag.py"], python_exe=py, timeout_s=20.0)
            self.assertEqual(res3["status"], "VERIFIED", res3)
            self.assertEqual(res3["winner"]["tier"], "TIER3_STATIC_STR_DIFF_ABDUCT")

    def test_iter8_online_plotkin_ast_rewrite_single_experience_tier0_transfer_and_deletion(self) -> None:
        """Prove real single-experience Plotkin AST Rewrite Law learning & zero-probe Tier-0 transfer:
        1. Solve Repo A -> automatically distills inspectable Plotkin AST rewrite law (`?0.match -> ?0.fullmatch`)
           into external JSON store (0 weights, 0 LLM calls).
        2. Solve completely unseen Repo B (different file, function, variable names) using that store ->
           VERIFIED via `TIER0_AST_REWRITE_LAW` with `angelic_probes_run == 0`!
        3. Delete the law from the external store -> Tier-0 recall vanishes immediately.
        4. Counterexample quarantine (`refutations >= 2`) disables misapplied laws automatically.
        """
        from canonical.runtime.causal_angelic_swe_engine_v1 import (
            solve_repository,
            _recall_tier0_ast_rewrite_laws,
        )

        py = sys.executable
        store: dict = {}
        with tempfile.TemporaryDirectory(prefix="uek_iter8_ast_transfer_") as td:
            root = pathlib.Path(td)

            # Repo A (experience 1): learns `?0.match -> ?0.fullmatch`
            ra = root / "repo_a"
            ra.mkdir()
            (ra / "guard.py").write_text(
                "import re\n"
                "class Guard:\n"
                "    def __init__(self, regex):\n"
                "        self.origin_regex = re.compile(regex)\n"
                "    def allowed(self, origin):\n"
                "        return bool(self.origin_regex.match(origin))\n",
                encoding="utf-8",
            )
            (ra / "test_guard.py").write_text(
                "from guard import Guard\n"
                "def test_exact():\n"
                "    g = Guard(r'https://good\\.org')\n"
                "    assert g.allowed('https://good.org') is True\n"
                "    assert g.allowed('https://good.org.evil.net') is False\n",
                encoding="utf-8",
            )
            res_a = solve_repository(
                ra, ["test_guard.py"], skill_store=store, learn_into_store=True, python_exe=py, timeout_s=20.0
            )
            self.assertEqual(res_a["status"], "VERIFIED", res_a)
            laws = store.get("ast_rewrite_laws") or {}
            self.assertGreaterEqual(len(laws), 1, f"Expected Plotkin AST rewrite law in store: {store}")
            law = next(iter(laws.values()))
            self.assertEqual(law["pattern_before"], ["Attr", {"$var": 0}, "match"])
            self.assertEqual(law["pattern_after"], ["Attr", {"$var": 0}, "fullmatch"])

            # Repo B (COMPLETELY unseen names `compiled_pat`, `host_str` -> TIER0 with 0 angelic probes!)
            rb = root / "repo_b"
            rb.mkdir()
            (rb / "router.py").write_text(
                "import re\n"
                "def check_host(compiled_pat, host_str):\n"
                "    return bool(compiled_pat.match(host_str))\n",
                encoding="utf-8",
            )
            (rb / "test_router.py").write_text(
                "import re\n"
                "from router import check_host\n"
                "def test_host():\n"
                "    p = re.compile(r'api\\.acme\\.io')\n"
                "    assert check_host(p, 'api.acme.io') is True\n"
                "    assert check_host(p, 'api.acme.io.attacker.net') is False\n",
                encoding="utf-8",
            )
            res_b = solve_repository(
                rb, ["test_router.py"], skill_store=store, learn_into_store=False, python_exe=py, timeout_s=20.0
            )
            self.assertEqual(res_b["status"], "VERIFIED", res_b)
            self.assertEqual(res_b["winner"]["tier"], "TIER0_AST_REWRITE_LAW")
            self.assertEqual(res_b["angelic_probes_run"], 0)

            # Quarantine check: refutations >= 2 disables the law cleanly inside solve_repository
            law["refutations"] = 2
            res_quar = solve_repository(
                rb, ["test_router.py"], skill_store=store, learn_into_store=False, python_exe=py, timeout_s=20.0
            )
            self.assertNotEqual((res_quar.get("winner") or {}).get("tier"), "TIER0_AST_REWRITE_LAW")

            # Delete external store -> zero knowledge in weights (cannot hit TIER0_AST_REWRITE_LAW)
            res_empty = solve_repository(
                rb, ["test_router.py"], skill_store={}, learn_into_store=False, python_exe=py, timeout_s=20.0
            )
            self.assertNotEqual((res_empty.get("winner") or {}).get("tier"), "TIER0_AST_REWRITE_LAW")

    def test_iter14_multipage_web_auth_pagination_rest_poly_skill_cross_site_transfer(self) -> None:
        """Verify live multi-page authenticated web workflow (login session cookie + CSRF replay +
        catalog pagination + item selection + dynamic <script> JSON REST API checkout + destructive
        trap avoidance) and true Poly-Skill Tier-0 cross-site transfer (ICLR 2026 PolySkill/SGDR)
        to an unseen website with different routes, field names, CSRF headers, and traps."""
        import json
        import threading
        import urllib.parse
        from http.server import BaseHTTPRequestHandler, HTTPServer
        from canonical.runtime.brain_unified_model_v1 import open_model

        def _spawn_app(*, routes, fields, csrf_name, meta_csrf_name, csrf_hdr, item_title, item_slug, expected_user, expected_pass, expected_coupon):
            state = {"traps_hit": 0, "orders": [], "cart": [], "authed": set(), "csrf": "tok_a", "meta_csrf": "m_tok_z"}

            class Handler(BaseHTTPRequestHandler):
                def log_message(self, *args):
                    pass

                def _send(self, code, body, ctype="text/html", cookies=None):
                    b = body.encode("utf-8")
                    self.send_response(code)
                    self.send_header("Content-Type", ctype)
                    self.send_header("Content-Length", str(len(b)))
                    if cookies:
                        self.send_header("Set-Cookie", cookies)
                    self.end_headers()
                    self.wfile.write(b)

                def _is_authed(self):
                    return any(f"sid={s}" in self.headers.get("Cookie", "") for s in state["authed"])

                def do_GET(self):
                    p = self.path
                    if any(t in p for t in ("reset", "delete", "wipe", "destroy", "logout")):
                        state["traps_hit"] += 1
                        return self._send(200, "TRAP")
                    if p == "/":
                        return self._send(
                            200,
                            f'<a href="{routes["trap_link"]}">Reset</a>'
                            f'<a href="{routes["login"]}">Sign In</a>'
                            f'<form method="POST" action="{routes["trap_form"]}"><button>Delete</button></form>',
                        )
                    if p == routes["login"]:
                        return self._send(
                            200,
                            f'<form method="POST" action="{routes["login"]}">'
                            f'<input type="hidden" name="{csrf_name}" value="{state["csrf"]}">'
                            f'<input name="{fields["user"]}" required>'
                            f'<input type="password" name="{fields["pass"]}" required>'
                            f'<button>Log In</button></form>',
                        )
                    if p == routes["catalog1"]:
                        if not self._is_authed():
                            return self._send(403, "no")
                        return self._send(200, f'<a href="{routes["trap_link"]}">Logout</a><a href="{routes["catalog2"]}">Next Page</a>')
                    if p == routes["catalog2"]:
                        if not self._is_authed():
                            return self._send(403, "no")
                        return self._send(200, f'<a href="{routes["item"]}">{item_title}</a>')
                    if p == routes["item"]:
                        if not self._is_authed():
                            return self._send(403, "no")
                        return self._send(
                            200,
                            f'<h1>{item_title}</h1>'
                            f'<form method="POST" action="{routes["trap_form"]}"><button>Destroy</button></form>'
                            f'<form method="POST" action="{routes["add"]}">'
                            f'<input type="hidden" name="{csrf_name}" value="{state["csrf"]}">'
                            f'<input type="hidden" name="sku" value="{item_slug}">'
                            f'<button>Add to Cart</button></form>',
                        )
                    if p == routes["checkout"]:
                        if not self._is_authed() or not state["cart"]:
                            return self._send(403, "no")
                        return self._send(
                            200,
                            f'<head><meta name="{meta_csrf_name}" content="{state["meta_csrf"]}"></head>'
                            f'<script>fetch("{routes["api_order"]}",{{method:"POST",headers:{{"{csrf_hdr}":"{state["meta_csrf"]}"}}}})</script>',
                        )
                    return self._send(404, "404")

                def do_POST(self):
                    raw = self.rfile.read(int(self.headers.get("Content-Length", "0"))).decode("utf-8", errors="replace")
                    if any(t in self.path for t in ("reset", "delete", "wipe", "destroy")):
                        state["traps_hit"] += 1
                        return self._send(200, "TRAP")
                    if self.path == routes["login"]:
                        kv = dict(urllib.parse.parse_qsl(raw))
                        if kv.get(csrf_name) == state["csrf"] and kv.get(fields["user"]) == expected_user and kv.get(fields["pass"]) == expected_pass:
                            state["authed"].add("ok")
                            return self._send(200, f'<a href="{routes["catalog1"]}">Products</a>', cookies="sid=ok; Path=/")
                        return self._send(401, "bad")
                    if self.path == routes["add"]:
                        state["cart"].append(item_slug)
                        return self._send(200, f'<a href="{routes["checkout"]}">Checkout</a>')
                    if self.path == routes["api_order"]:
                        if not self._is_authed() or not state["cart"]:
                            return self._send(403, "no", "application/json")
                        if self.headers.get(csrf_hdr) != state["meta_csrf"]:
                            return self._send(403, '{"error":"bad csrf"}', "application/json")
                        d = json.loads(raw or "{}")
                        if not d.get("coupon"):
                            return self._send(400, '{"error":"missing required field: coupon"}', "application/json")
                        if d["coupon"] != expected_coupon:
                            return self._send(400, '{"error":"invalid coupon"}', "application/json")
                        state["orders"].append(d)
                        return self._send(200, json.dumps({"ok": True, "coupon": d["coupon"]}), "application/json")
                    return self._send(404, "404")

            srv = HTTPServer(("127.0.0.1", 0), Handler)
            threading.Thread(target=srv.serve_forever, daemon=True).start()
            return srv, srv.server_address[1], state

        srv_a, port_a, st_a = _spawn_app(
            routes={"login": "/login", "catalog1": "/catalog", "catalog2": "/catalog?page=2", "item": "/item/quantum-mouse", "add": "/cart/add", "checkout": "/checkout", "api_order": "/api/orders", "trap_link": "/reset", "trap_form": "/delete"},
            fields={"user": "username", "pass": "password"},
            csrf_name="csrf_token", meta_csrf_name="csrf-token", csrf_hdr="X-CSRF-Token",
            item_title="Quantum Mouse", item_slug="quantum-mouse",
            expected_user="alice", expected_pass="s3cr3t", expected_coupon="SAVE10",
        )
        srv_b, port_b, st_b = _spawn_app(
            routes={"login": "/signin", "catalog1": "/shop", "catalog2": "/shop?page=2", "item": "/product/photon-pad", "add": "/bag/put", "checkout": "/pay", "api_order": "/api/purchase", "trap_link": "/wipe", "trap_form": "/destroy"},
            fields={"user": "user_id", "pass": "passwd"},
            csrf_name="_xsrf", meta_csrf_name="xsrf-token", csrf_hdr="X-XSRF-Token",
            item_title="Photon Pad", item_slug="photon-pad",
            expected_user="bob", expected_pass="p4ss99", expected_coupon="VIP25",
        )
        try:
            mem = UEK.new_universal_memory()
            model = open_model()
            r1 = model.solve(
                'Log in with username=alice, password=s3cr3t, find "Quantum Mouse", add it to cart, and complete checkout with coupon=SAVE10',
                mode="EPISTEMIC",
                inputs={"web_url": f"http://127.0.0.1:{port_a}/", "memory": mem},
            )
            e1 = r1["epistemic_result"]
            self.assertEqual(r1["status"], "PASS")
            self.assertEqual(e1["mode"], "EPISTEMIC_WEB_POLY_SKILL_SOLVED")
            self.assertEqual(e1["failed_probes"], 1)
            self.assertEqual(st_a["traps_hit"], 0)
            self.assertEqual(st_a["orders"], [{"coupon": "SAVE10"}])
            # Distilled Poly-Skill contains ZERO host URLs, ZERO tokens, ZERO parameter weights!
            law = e1["distilled_law"]
            law_str = json.dumps(law)
            self.assertNotIn("127.0.0.1", law_str)
            self.assertNotIn("SAVE10", law_str)
            self.assertNotIn("s3cr3t", law_str)
            self.assertEqual(law["parameters_stored"], 0)

            r2 = model.solve(
                'Sign in with username=bob, password=p4ss99, find "Photon Pad", add it to bag, and complete checkout with coupon=VIP25',
                mode="EPISTEMIC",
                inputs={"web_url": f"http://127.0.0.1:{port_b}/", "memory": mem},
            )
            e2 = r2["epistemic_result"]
            self.assertEqual(r2["status"], "PASS")
            self.assertEqual(e2["mode"], "TIER0_WEB_POLY_SKILL")
            self.assertEqual(e2["failed_probes"], 0)
            self.assertEqual(e2["recalled_law_id"], law["law_id"])
            self.assertEqual(st_b["traps_hit"], 0)
            self.assertEqual(st_b["orders"], [{"coupon": "VIP25"}])
            self.assertEqual(r2["model_calls"], 0)
            self.assertEqual(r2["parameters_stored"], 0)
        finally:
            srv_a.shutdown()
            srv_b.shutdown()

    def test_iter20_zero_prior_closed_loop_epistemic_api_error_law_transfer_and_structured_data(self) -> None:
        """Verify Iter 20 Step-6 Zero-Prior Closed-Loop Epistemic Solver through ONE Front Door:
        1. EnvAlpha: Unknown local Python module `zephyr_sdk.py` with aliased bad kwarg `limit=2`
           (real param is `max_entries`) -> catches TypeError, introspects signature live, repairs,
           verifies output, and distills a path-free Trace2Skill `error_fix_law` (0 model calls).
        2. EnvBeta: Completely different unknown module `orion_analytics.py` (`cap=2` vs `cap_count`)
           -> recalls distilled `error_fix_law` at Tier-0 with 0 failed executions!
        3. Skill-Pro score-based refutation/quarantine & Plotkin subsumption pruning.
        4. Zero-prior live-schema structured data transform (CSV filter+groupby+sum -> JSON,
           followed by Tier-0 recall on an unseen CSV workspace + SQLite immutable sort+limit).
        """
        import json
        import sqlite3
        from canonical.runtime.brain_unified_model_v1 import open_model

        model = open_model()
        mem = UEK.new_universal_memory()

        with tempfile.TemporaryDirectory(prefix="iter20_zp_") as tmp:
            root = pathlib.Path(tmp)

            # 1. EnvAlpha: Unknown local Python API with wrong kwarg -> closed-loop repair + distillation
            env_a = root / "env_alpha"
            env_a.mkdir()
            (env_a / "zephyr_sdk.py").write_text(
                "def compute_ledger(records, *, max_entries=10, factor=1):\n"
                "    picked = records[:int(max_entries)]\n"
                "    return {'count': len(picked), 'total': sum(r['amt'] for r in picked) * factor}\n",
                encoding="utf-8",
            )
            (env_a / "orders.json").write_text(
                json.dumps([{"amt": 10}, {"amt": 25}, {"amt": 99}]),
                encoding="utf-8",
            )
            r_a = model.solve(
                f"Call compute_ledger from zephyr_sdk.py on orders.json with limit=2 and factor=3 and write result to {env_a}/ledger.json",
                mode="EPISTEMIC",
                inputs={"workspace": str(env_a), "memory": mem, "allow_web": False},
            )
            self.assertEqual(r_a["status"], "PASS", r_a)
            ea = r_a["epistemic_result"]
            self.assertEqual(ea["status"], "VERIFIED")
            self.assertEqual(ea["mode"], "EPISTEMIC_ZERO_PRIOR_API_CEGIS")
            self.assertEqual(ea["model_calls"], 0)
            self.assertEqual(ea["parameters_stored"], 0)
            self.assertEqual(
                json.loads((env_a / "ledger.json").read_text(encoding="utf-8")),
                {"count": 2, "total": 105},
            )
            # Verify Trace2Skill error-fix law distilled with ZERO concrete paths or values!
            self.assertGreaterEqual(len(mem["error_fix_laws"]), 1)
            mem_dump = json.dumps(mem["error_fix_laws"])
            self.assertNotIn("env_alpha", mem_dump)
            self.assertNotIn("zephyr_sdk", mem_dump)
            self.assertNotIn("orders.json", mem_dump)

            # 2. EnvBeta: Completely different unseen module & CSV input -> Tier-0 instant error-law recall (0 failed tries!)
            env_b = root / "env_beta"
            env_b.mkdir()
            (env_b / "orion_analytics.py").write_text(
                "def summarize_events(rows, *, cap_items=10):\n"
                "    top = rows[:int(cap_items)]\n"
                "    return {'n': len(top), 'names': [r['tag'] for r in top]}\n",
                encoding="utf-8",
            )
            (env_b / "events.csv").write_text("tag,score\nred,5\nblue,9\ngreen,2\n", encoding="utf-8")
            r_b = model.solve(
                f"Use summarize_events in orion_analytics.py on events.csv with cap=2 and save to {env_b}/summary.json",
                mode="EPISTEMIC",
                inputs={"workspace": str(env_b), "memory": mem, "allow_web": False},
            )
            self.assertEqual(r_b["status"], "PASS", r_b)
            eb = r_b["epistemic_result"]
            self.assertEqual(eb["status"], "VERIFIED")
            self.assertEqual(eb["mode"], "TIER0_ZERO_PRIOR_API_WITH_ERROR_LAW")
            self.assertEqual(eb["zero_prior_result"]["error_repairs"], [])
            self.assertEqual(
                json.loads((env_b / "summary.json").read_text(encoding="utf-8")),
                {"n": 2, "names": ["red", "blue"]},
            )

            # 3. Skill-Pro score-based refutation, quarantine, and pruning
            bad_rec = UEK.record_error_fix_law(
                mem, error_kind="ValueError", context_shape="bad_demo", repair_op="noop_bad",
            )
            self.assertIsNotNone(bad_rec)
            lid_bad = bad_rec["law_id"]
            UEK.refute_error_fix_law(mem, lid_bad, "falsified_1")
            UEK.refute_error_fix_law(mem, lid_bad, "falsified_2")
            self.assertEqual(UEK.recall_error_fix_laws(mem, error_kind="ValueError", context_shape="bad_demo"), [])
            prune_stats = UEK.compress_and_prune_memory(mem)
            self.assertGreaterEqual(prune_stats["pruned_error_laws"], 1)
            self.assertNotIn(lid_bad, mem["error_fix_laws"])

            # 4. Zero-Prior Live-Schema Structured Data Transform (CSV -> filter + group by + sum -> JSON) + Tier-0 Transfer
            env_c = root / "env_csv1"
            env_c.mkdir()
            (env_c / "sales.csv").write_text(
                "region,status,revenue\nnorth,paid,100\nnorth,open,50\nnorth,paid,40\nsouth,paid,75\n",
                encoding="utf-8",
            )
            r_c = model.solve(
                f"From sales.csv filter where status = paid, group by region and compute sum of revenue, save to {env_c}/totals.json",
                mode="EPISTEMIC",
                inputs={"workspace": str(env_c), "memory": mem, "allow_web": False},
            )
            self.assertEqual(r_c["status"], "PASS", r_c)
            ec = r_c["epistemic_result"]
            self.assertEqual(ec["mode"], "EPISTEMIC_ZERO_PRIOR_DATA_PIPELINE")
            self.assertEqual(json.loads((env_c / "totals.json").read_text(encoding="utf-8")), {"north": 140, "south": 75})

            # Unseen CSV workspace with different schema -> Tier-0 recall (0 schema gaps!)
            env_d = root / "env_csv2"
            env_d.mkdir()
            (env_d / "metrics.csv").write_text(
                "team,active,points\nalpha,yes,12\nbeta,no,99\nalpha,yes,8\n",
                encoding="utf-8",
            )
            r_d = model.solve(
                f"From metrics.csv filter where active = yes, group by team and compute sum of points, write to {env_d}/out.json",
                mode="EPISTEMIC",
                inputs={"workspace": str(env_d), "memory": mem, "allow_web": False},
            )
            self.assertEqual(r_d["status"], "PASS", r_d)
            ed = r_d["epistemic_result"]
            self.assertEqual(ed["mode"], "TIER0_ZERO_PRIOR_DATA_PIPELINE")
            self.assertEqual(ed["gaps_queried"], [])
            self.assertEqual(json.loads((env_d / "out.json").read_text(encoding="utf-8")), {"alpha": 20})

            # SQLite immutable live-schema sort desc + limit -> JSON
            env_sq = root / "env_sqlite"
            env_sq.mkdir()
            con = sqlite3.connect(str(env_sq / "telemetry.db"))
            con.execute("CREATE TABLE sensors (name TEXT, temp REAL)")
            con.executemany("INSERT INTO sensors VALUES (?, ?)", [("s1", 21.5), ("s2", 42.0), ("s3", 33.0)])
            con.commit()
            con.close()
            r_sq = model.solve(
                f"Read telemetry.db sort by temp descending top 2 and write to {env_sq}/hot.json",
                mode="EPISTEMIC",
                inputs={"workspace": str(env_sq), "memory": mem, "allow_web": False},
            )
            self.assertEqual(r_sq["status"], "PASS", r_sq)
            hot = json.loads((env_sq / "hot.json").read_text(encoding="utf-8"))
            self.assertEqual([x["name"] for x in hot], ["s2", "s3"])

    def test_iter21_zero_prior_cli_error_self_heal_and_tier0_transfer(self) -> None:
        """Verify Iter 21 Track C: zero-prior unseen CLI binary/script closed-loop flag error
        self-healing via live `--help` introspection, path-free `CLIFlagError` law distillation,
        and Tier-0 transfer (0 failed executions) to a completely different unseen CLI tool
        through the ONE front door (`open_model().solve(..., mode='EPISTEMIC')`).
        """
        from canonical.runtime.brain_unified_model_v1 import open_model
        import json

        model = open_model()
        mem = UEK.new_universal_memory()
        with tempfile.TemporaryDirectory(prefix="uek_iter21_cli_") as tmp:
            root = pathlib.Path(tmp)

            # 1. Brand-new unseen executable CLI binary (`bin/pulsar_cli`, no .py suffix, chmod +x)
            env_a = root / "cli_alpha"
            (env_a / "bin").mkdir(parents=True)
            cli_a = env_a / "bin" / "pulsar_cli"
            cli_a.write_text(
                f"#!{sys.executable}\n"
                "import argparse, csv, json, pathlib\n"
                "p = argparse.ArgumentParser(prog='pulsar_cli')\n"
                "p.add_argument('--source-file', metavar='PATH', required=True, help='Input CSV data file')\n"
                "p.add_argument('--cap-rows', type=int, metavar='N', required=True, help='Maximum rows limit to emit')\n"
                "p.add_argument('--dest-path', metavar='FILE', required=True, help='Output JSON destination path')\n"
                "args = p.parse_args()\n"
                "rows = list(csv.DictReader(open(args.source_file, encoding='utf-8')))[:args.cap_rows]\n"
                "pathlib.Path(args.dest_path).write_text(json.dumps({'count': len(rows), 'names': [r['name'] for r in rows]}), encoding='utf-8')\n",
                encoding="utf-8",
            )
            cli_a.chmod(0o755)
            (env_a / "items.csv").write_text("name,score\nalpha,90\nbeta,80\ngamma,70\n", encoding="utf-8")

            r_a = model.solve(
                f"Run ./bin/pulsar_cli --input items.csv --limit 2 --output {env_a}/summary.json",
                mode="EPISTEMIC",
                inputs={"workspace": str(env_a), "memory": mem, "allow_web": False},
            )
            self.assertEqual(r_a["status"], "PASS", r_a)
            ea = r_a["epistemic_result"]
            self.assertEqual(ea["model_calls"], 0)
            self.assertEqual(ea["parameters_stored"], 0)
            self.assertEqual(ea["mode"], "EPISTEMIC_ZERO_PRIOR_CLI_ERROR_HEAL")
            zpa = ea["zero_prior_result"]
            self.assertGreaterEqual(len(zpa["error_repairs"]), 3)
            self.assertEqual(zpa["failed_executions"], 1)
            self.assertTrue(zpa["learned_law_ids"])
            self.assertEqual(
                json.loads((env_a / "summary.json").read_text(encoding="utf-8")),
                {"count": 2, "names": ["alpha", "beta"]},
            )
            # Confirm distilled law has ZERO leaked paths, ZERO tool names, ZERO concrete flags
            law_dump = json.dumps(mem["error_fix_laws"])
            self.assertNotIn("pulsar_cli", law_dump)
            self.assertNotIn("cap-rows", law_dump)
            self.assertNotIn(str(root), law_dump)

            # 2. Completely different unseen CLI script (`quasar_tool.py`, different flags, stdout->file!)
            env_b = root / "cli_beta"
            env_b.mkdir()
            (env_b / "quasar_tool.py").write_text(
                "import argparse, json, pathlib\n"
                "p = argparse.ArgumentParser(prog='quasar_tool')\n"
                "p.add_argument('--src-json', metavar='PATH', required=True, help='Input JSON source file')\n"
                "p.add_argument('--max-entries', type=int, metavar='N', required=True, help='Limit number of entries')\n"
                "p.add_argument('--write-to', metavar='FILE', required=True, help='Destination output JSON file')\n"
                "args = p.parse_args()\n"
                "data = json.loads(pathlib.Path(args.src_json).read_text(encoding='utf-8'))[:args.max_entries]\n"
                "pathlib.Path(args.write_to).write_text(json.dumps({'n': len(data), 'ids': [d['id'] for d in data]}), encoding='utf-8')\n",
                encoding="utf-8",
            )
            (env_b / "records.json").write_text(
                json.dumps([{"id": "x1"}, {"id": "x2"}, {"id": "x3"}, {"id": "x4"}]),
                encoding="utf-8",
            )

            r_b = model.solve(
                f"Execute quasar_tool.py --input records.json --limit 3 --out {env_b}/report.json",
                mode="EPISTEMIC",
                inputs={"workspace": str(env_b), "memory": mem, "allow_web": False},
            )
            self.assertEqual(r_b["status"], "PASS", r_b)
            eb = r_b["epistemic_result"]
            self.assertEqual(eb["model_calls"], 0)
            self.assertEqual(eb["parameters_stored"], 0)
            self.assertEqual(eb["mode"], "TIER0_ZERO_PRIOR_CLI_WITH_ERROR_LAW")
            zpb = eb["zero_prior_result"]
            self.assertEqual(zpb["failed_executions"], 0)
            self.assertEqual(zpb["error_repairs"], [])
            self.assertEqual(zpb["gaps_queried"], [])
            self.assertTrue(zpb["recalled_law_ids"])
            self.assertEqual(
                json.loads((env_b / "report.json").read_text(encoding="utf-8")),
                {"n": 3, "ids": ["x1", "x2", "x3"]},
            )

    def test_iter22_interactive_gui_a11y_validation_self_heal_and_cross_app_tier0_transfer(self) -> None:
        """Verify Iter 22 interactive observable GUI / Accessibility-Tree closed-loop workflow engine:
        - AppAlpha (Settings Manager, unseen, empty memory): navigates tabs, avoids destructive traps
          (`Reset All Settings`, `Delete Account`, `Cancel`), self-heals live A11y validation errors
          (prefix `https://`, min-length 12, required checkbox), confirms modal dialog, and distills
          app/ID/coordinate-free Skill-Pro GUI skill + Trace2Skill `GUIValidationError` law.
        - AppBeta (Project Preferences, completely different unseen app): transfers at Tier-0
          (`TIER0_GUI_A11Y_POLY_SKILL`, `failed_submits == 0`, `traps_hit == 0`, `gaps_queried == []`)
          through `open_model().solve(..., mode='EPISTEMIC')` with `model_calls == 0`, `parameters_stored == 0`.
        """
        from canonical.runtime.brain_unified_model_v1 import open_model
        import json

        class _StatefulA11yApp:
            def __init__(self, *, app_kind: str) -> None:
                self.app_kind = app_kind
                self.screen = "home" if app_kind == "alpha" else "dashboard"
                self.vals: dict[str, str] = {}
                self.checked: dict[str, bool] = {}
                self.errors: list[str] = []
                self.done = False
                self.trap_triggered = False

            def observe(self) -> dict[str, Any]:
                if self.app_kind == "alpha":
                    if self.screen == "home":
                        nodes = [
                            {"id": "t_ov", "role": "tab", "name": "Overview", "selected": True, "enabled": True},
                            {"id": "t_sec", "role": "tab", "name": "Security", "selected": False, "enabled": True},
                            {"id": "t_bill", "role": "tab", "name": "Billing", "selected": False, "enabled": True},
                            {"id": "b_rst", "role": "button", "name": "Reset All Settings", "enabled": True},
                        ]
                    elif self.screen == "security":
                        nodes = [
                            {"id": "f_url", "role": "textbox", "name": "Webhook URL", "value": self.vals.get("f_url", ""), "enabled": True},
                            {"id": "f_sec", "role": "textbox", "name": "API Secret", "value": self.vals.get("f_sec", ""), "enabled": True},
                            {"id": "c_aud", "role": "checkbox", "name": "Accept Audit Policy", "checked": self.checked.get("c_aud", False), "required": True, "enabled": True},
                            {"id": "b_del", "role": "button", "name": "Delete Account", "enabled": True},
                            {"id": "b_sav", "role": "button", "name": "Save", "enabled": True},
                        ]
                    else:  # confirm_dialog
                        nodes = [
                            {"id": "dlg", "role": "dialog", "name": "Confirm Security Update", "enabled": True},
                            {"id": "b_can", "role": "button", "name": "Cancel", "enabled": True},
                            {"id": "b_ok", "role": "button", "name": "Confirm", "enabled": True},
                        ]
                else:  # beta: completely different screens, roles, labels, IDs, and constraints
                    if self.screen == "dashboard":
                        nodes = [
                            {"id": "m_gen", "role": "menuitem", "name": "General", "selected": True, "enabled": True},
                            {"id": "m_dep", "role": "menuitem", "name": "Deployments", "selected": False, "enabled": True},
                            {"id": "btn_wipe", "role": "button", "name": "Wipe Workspace", "enabled": True},
                        ]
                    elif self.screen == "deployments":
                        nodes = [
                            {"id": "in_cb", "role": "input", "name": "Callback Endpoint", "hint": "must start with 'https://'", "value": self.vals.get("in_cb", ""), "enabled": True},
                            {"id": "in_tok", "role": "input", "name": "Signing Token", "hint": "minimum length 14 characters", "value": self.vals.get("in_tok", ""), "enabled": True},
                            {"id": "sw_roll", "role": "switch", "name": "Confirm Production Rollout", "checked": self.checked.get("sw_roll", False), "required": True, "enabled": True},
                            {"id": "btn_dest", "role": "button", "name": "Destroy Cluster", "enabled": True},
                            {"id": "btn_app", "role": "button", "name": "Apply", "enabled": True},
                        ]
                    else:  # confirm_modal
                        nodes = [
                            {"id": "mod", "role": "dialog", "name": "Proceed With Rollout", "enabled": True},
                            {"id": "btn_ab", "role": "button", "name": "Abort", "enabled": True},
                            {"id": "btn_pr", "role": "button", "name": "Proceed", "enabled": True},
                        ]
                return {
                    "screen": self.screen,
                    "nodes": nodes,
                    "errors": list(self.errors),
                    "done": self.done,
                    "trap_triggered": self.trap_triggered,
                    "state": {"vals": dict(self.vals), "checked": dict(self.checked)},
                }

            def step(self, action: dict[str, Any]) -> dict[str, Any]:
                atype = action.get("type")
                nid = str(action.get("id") or "")
                self.errors = []
                if nid in ("b_rst", "b_del", "b_can", "btn_wipe", "btn_dest", "btn_ab"):
                    self.trap_triggered = True
                    return self.observe()
                if atype == "type":
                    self.vals[nid] = str(action.get("value") or "")
                elif atype == "toggle":
                    self.checked[nid] = not self.checked.get(nid, False)
                elif atype == "click":
                    if self.app_kind == "alpha":
                        if nid == "t_sec":
                            self.screen = "security"
                        elif nid == "b_sav":
                            if not self.vals.get("f_url", "").startswith("https://"):
                                self.errors.append("Webhook URL must start with 'https://'")
                            if len(self.vals.get("f_sec", "")) < 12:
                                self.errors.append("API Secret must be at least 12 characters")
                            if not self.checked.get("c_aud", False):
                                self.errors.append("Must accept Audit Policy before saving")
                            if not self.errors:
                                self.screen = "confirm_dialog"
                        elif nid == "b_ok" and self.screen == "confirm_dialog":
                            self.done = True
                    else:
                        if nid == "m_dep":
                            self.screen = "deployments"
                        elif nid == "btn_app":
                            if not self.vals.get("in_cb", "").startswith("https://"):
                                self.errors.append("Callback Endpoint must start with 'https://'")
                            if len(self.vals.get("in_tok", "")) < 14:
                                self.errors.append("Signing Token minimum length 14 characters")
                            if not self.checked.get("sw_roll", False):
                                self.errors.append("Must accept Confirm Production Rollout")
                            if not self.errors:
                                self.screen = "confirm_modal"
                        elif nid == "btn_pr" and self.screen == "confirm_modal":
                            self.done = True
                return self.observe()

        model = open_model()
        mem = UEK.new_universal_memory()

        # 1. Cold AppAlpha (empty memory) -> closed-loop A11y validation self-heal + distillation
        app_a = _StatefulA11yApp(app_kind="alpha")
        r_a = model.solve(
            "Open Security settings, configure Webhook URL and API Secret, and save changes",
            mode="EPISTEMIC",
            inputs={
                "gui_env": app_a,
                "field_values": {"webhook url": "hooks.internal/v1", "api secret": "short"},
                "memory": mem,
                "allow_web": False,
            },
        )
        self.assertEqual(r_a["status"], "PASS", r_a)
        ea = r_a["epistemic_result"]
        self.assertEqual(ea["model_calls"], 0)
        self.assertEqual(ea["parameters_stored"], 0)
        self.assertEqual(ea["mode"], "EPISTEMIC_GUI_A11Y_CLOSED_LOOP")
        self.assertEqual(ea["traps_hit"], 0)
        self.assertGreaterEqual(len(ea["validation_repairs"]), 3)
        self.assertTrue(ea["learned_skill_id"])
        self.assertTrue(ea["learned_err_law_id"])
        self.assertTrue(app_a.done)
        self.assertTrue(app_a.vals["f_url"].startswith("https://"))
        self.assertGreaterEqual(len(app_a.vals["f_sec"]), 12)
        # Confirm distilled GUI skill + error law have ZERO app names / element IDs / coordinates
        mem_dump = json.dumps({"g": mem.get("gui_workflow_skills"), "e": mem.get("error_fix_laws")})
        self.assertNotIn("f_url", mem_dump)
        self.assertNotIn("t_sec", mem_dump)
        self.assertNotIn("hooks.internal", mem_dump)

        # 2. Brand-new unseen AppBeta (reusing mem) -> Tier-0 transfer (0 failed submits, 0 traps!)
        app_b = _StatefulA11yApp(app_kind="beta")
        r_b = model.solve(
            "Navigate to Deployments, set Callback Endpoint and Signing Token, and apply",
            mode="EPISTEMIC",
            inputs={
                "gui_env": app_b,
                "field_values": {"callback endpoint": "deploy.prod/cb", "signing token": "tok9"},
                "memory": mem,
                "allow_web": False,
            },
        )
        self.assertEqual(r_b["status"], "PASS", r_b)
        eb = r_b["epistemic_result"]
        self.assertEqual(eb["model_calls"], 0)
        self.assertEqual(eb["parameters_stored"], 0)
        self.assertEqual(eb["mode"], "TIER0_GUI_A11Y_POLY_SKILL")
        self.assertEqual(eb["failed_submits"], 0)
        self.assertEqual(eb["validation_repairs"], [])
        self.assertEqual(eb["traps_hit"], 0)
        self.assertEqual(eb["gaps_queried"], [])
        self.assertTrue(eb["recalled_skill_ids"])
        self.assertTrue(app_b.done)
        self.assertTrue(app_b.vals["in_cb"].startswith("https://"))
        self.assertGreaterEqual(len(app_b.vals["in_tok"]), 14)

    def test_iter64_live_multipage_auth_link_navigation_and_honest_field_completion(self) -> None:
        """Iter 64: After an authenticated login POST redirects to a form-less Dashboard,
        UEK MUST NOT falsely declare VERIFIED while user-supplied goal fields remain unsubmitted;
        it must follow goal-relevant safe `<a href>` links (skipping destructive traps), replay
        fresh hidden CSRF tokens, submit the target form, AND fail closed when no target exists.
        """
        import http.server
        import socketserver
        import threading
        import urllib.parse
        from canonical.runtime import brain_unified_model_v1 as UM

        keys_created: list[str] = []
        mode = {"with_keys": True}

        class _PortalHandler(http.server.BaseHTTPRequestHandler):
            def log_message(self, *args: object) -> None:
                pass

            def _authed(self) -> bool:
                return "sid=ok_sess" in (self.headers.get("Cookie") or "")

            def do_GET(self) -> None:
                if self.path == "/":
                    self.send_response(200)
                    self.send_header("Content-Type", "text/html")
                    self.end_headers()
                    if not self._authed():
                        self.wfile.write(
                            b'<html><body><h1>Portal Login</h1>'
                            b'<form method="POST" action="/login">'
                            b'<input type="hidden" name="csrf" value="tok-77">'
                            b'<input name="username"><input name="password" type="password">'
                            b'<button type="submit">Sign In</button></form></body></html>'
                        )
                    elif mode["with_keys"]:
                        self.wfile.write(
                            b'<html><body><h1>Dashboard</h1>'
                            b'<a href="/profile">Profile</a> '
                            b'<a href="/settings/keys">API Keys</a> '
                            b'<a href="/delete-account">Delete Account</a></body></html>'
                        )
                    else:
                        self.wfile.write(b"<html><body><h1>Dashboard</h1><p>Read-only.</p></body></html>")
                elif self.path == "/settings/keys":
                    if not self._authed():
                        self.send_response(302)
                        self.send_header("Location", "/")
                        self.end_headers()
                        return
                    self.send_response(200)
                    self.send_header("Content-Type", "text/html")
                    self.end_headers()
                    self.wfile.write(
                        b'<html><body><h1>API Keys</h1>'
                        b'<form method="POST" action="/settings/keys">'
                        b'<input type="hidden" name="csrf" value="tok-88">'
                        b'<input name="key_name">'
                        b'<button type="submit">Create Key</button></form></body></html>'
                    )
                else:
                    self.send_response(404)
                    self.end_headers()

            def do_POST(self) -> None:
                ln = int(self.headers.get("Content-Length", "0"))
                form = urllib.parse.parse_qs(self.rfile.read(ln).decode())
                if self.path == "/login":
                    if form.get("csrf") == ["tok-77"] and form.get("username") == ["admin"] and form.get("password") == ["s3cr3t"]:
                        self.send_response(302)
                        self.send_header("Set-Cookie", "sid=ok_sess; Path=/")
                        self.send_header("Location", "/")
                        self.end_headers()
                    else:
                        self.send_response(401)
                        self.end_headers()
                elif self.path == "/settings/keys":
                    if self._authed() and form.get("csrf") == ["tok-88"] and form.get("key_name"):
                        keys_created.append(form["key_name"][0])
                        self.send_response(200)
                        self.send_header("Content-Type", "text/html")
                        self.end_headers()
                        self.wfile.write(b"<html><body><h1>Key Created</h1><code>sk-live-9001</code></body></html>")
                    else:
                        self.send_response(403)
                        self.end_headers()

        srv = socketserver.TCPServer(("127.0.0.1", 0), _PortalHandler)
        port = srv.server_address[1]
        threading.Thread(target=srv.serve_forever, daemon=True).start()
        try:
            with tempfile.TemporaryDirectory(prefix="uek_iter64_web_") as td:
                goal = (
                    f"Log in to http://127.0.0.1:{port} with username=admin password=s3cr3t, "
                    "navigate to API Keys, and create key key_name=prod-sync"
                )
                # 1. Positive multi-page Login -> Dashboard -> API Keys -> Create Key
                r1 = UM.open_model().solve(goal, inputs={"workspace": td}, mode="EPISTEMIC")
                self.assertTrue(r1.get("pass"), r1)
                self.assertEqual(keys_created, ["prod-sync"])
                ep1 = r1.get("epistemic_result") or {}
                self.assertEqual(ep1.get("model_calls"), 0)
                self.assertEqual(ep1.get("parameters_stored"), 0)
                self.assertIn("/settings/keys", [t.get("action") for t in (ep1.get("trace") or [])])

                # 2. Honest fail-closed when Dashboard has NO target link/form
                mode["with_keys"] = False
                keys_created.clear()
                r2 = UM.open_model().solve(goal, inputs={"workspace": td}, mode="EPISTEMIC")
                self.assertFalse(r2.get("pass"), r2)
                self.assertEqual(keys_created, [])
        finally:
            srv.shutdown()
            srv.server_close()


if __name__ == "__main__":
    unittest.main()
