"""Hard unseen-environment tests for `epistemic_doc_compiler_agent_v1.py`.

Verifies the 5-stage Goal-Directed Epistemic Algorithm (`SCAN -> PARTITION ->
ACQUIRE -> ACT+VERIFY+REFUSE -> ANTI_UNIFY+PRUNE`) on real installed Linux
binaries, brand-new unseen custom CLIs, multi-step pipelines, live HTTP servers
with stale prose/curl docs, zero-leakage memory governance, and ONE Front Door
(`UnifiedModel.solve(..., mode='EPISTEMIC')`), with `model_calls == 0` and
`parameters_stored == 0`.
"""

from __future__ import annotations

import base64
import gzip
import hashlib
import http.server
import io
import json
import pathlib
import socketserver
import stat
import tarfile
import tempfile
import threading
import unittest

from canonical.runtime import brain_unified_model_v1 as UM
from canonical.runtime import epistemic_doc_compiler_agent_v1 as EDC


class TestEpistemicDocCompilerAgentV1(unittest.TestCase):
    def test_01_real_linux_binaries_zero_hardcoded_rules(self) -> None:
        """Real Linux binaries (`jq`, `base64`, `sort`) compiled purely from live `--help`."""
        with tempfile.TemporaryDirectory(prefix="brain_edc_bins_") as td:
            root = pathlib.Path(td)
            mem = EDC.EpistemicMemoryStore(root / "mem.json")

            # 1. jq
            w1 = root / "jq_ws"
            w1.mkdir()
            (w1 / "items.json").write_text(
                json.dumps(
                    {
                        "users": [
                            {"name": "alice", "active": True},
                            {"name": "bob", "active": False},
                            {"name": "carol", "active": True},
                        ]
                    }
                ),
                encoding="utf-8",
            )
            r1 = EDC.solve_with_instant_knowledge(
                "Use jq with raw output filter '.users[] | select(.active) | .name' on items.json and save to names.txt",
                workspace=w1,
                memory=mem,
                verifier=lambda st: (st["output_text"] == "alice\ncarol\n", f"got={st['output_text']!r}"),
            )
            self.assertEqual(r1["status"], "VERIFIED", r1)
            self.assertEqual(r1["model_calls"], 0)
            self.assertEqual(r1["parameters_stored"], 0)

            # 2. base64
            w2 = root / "b64_ws"
            w2.mkdir()
            (w2 / "secret.b64").write_text("ZXBpc3RlbWljLXplcm8tbGxt\n", encoding="utf-8")
            r2 = EDC.solve_with_instant_knowledge(
                "Use base64 to decode secret.b64 and save to decoded.txt",
                workspace=w2,
                memory=mem,
                verifier=lambda st: (st["output_text"] == "epistemic-zero-llm", f"got={st['output_text']!r}"),
            )
            self.assertEqual(r2["status"], "VERIFIED", r2)
            self.assertEqual(r2["model_calls"], 0)

            # 3. sort
            w3 = root / "sort_ws"
            w3.mkdir()
            (w3 / "nums.txt").write_text("banana\napple\ncherry\napple\nbanana\n", encoding="utf-8")
            r3 = EDC.solve_with_instant_knowledge(
                "Use sort with unique and reverse order on nums.txt and write to sorted.txt",
                workspace=w3,
                memory=mem,
                verifier=lambda st: (st["output_text"] == "cherry\nbanana\napple\n", f"got={st['output_text']!r}"),
            )
            self.assertEqual(r3["status"], "VERIFIED", r3)
            self.assertEqual(r3["model_calls"], 0)

    def test_02_multi_step_real_linux_pipeline_composition(self) -> None:
        """3-step real Linux pipeline (`base64 -> jq -> sort`) composed end-to-end with 0 LLM calls."""
        with tempfile.TemporaryDirectory(prefix="brain_edc_pipe_") as td:
            root = pathlib.Path(td)
            mem = EDC.EpistemicMemoryStore(root / "mem.json")
            payload = json.dumps(
                {
                    "records": [
                        {"tag": "zeta", "ok": True},
                        {"tag": "alpha", "ok": True},
                        {"tag": "zeta", "ok": True},
                        {"tag": "skip", "ok": False},
                        {"tag": "mid", "ok": True},
                    ]
                }
            ).encode("utf-8")
            (root / "bundle.b64").write_text(base64.b64encode(payload).decode("ascii") + "\n", encoding="utf-8")

            goal = (
                "Use base64 to decode bundle.b64 and save to raw.json, "
                "then use jq with raw output filter '.records[] | select(.ok) | .tag' on raw.json and save to tags.txt, "
                "then use sort with unique and reverse order on tags.txt and write to final.txt"
            )
            res = EDC.solve_multi_step_with_instant_knowledge(
                goal,
                workspace=root,
                memory=mem,
                verifier=lambda st: (st["output_text"] == "zeta\nmid\nalpha\n", f"got={st['output_text']!r}"),
            )
            self.assertEqual(res["status"], "VERIFIED", res)
            self.assertEqual(res["steps_completed"], 3)
            self.assertEqual(res["model_calls"], 0)
            self.assertEqual(res["parameters_stored"], 0)

    def test_03_cross_environment_plotkin_anti_unification_and_mdl_pruning(self) -> None:
        """Two brand-new unseen CLIs with disjoint subcommands & flags trigger Plotkin LGG + MDL pruning."""
        with tempfile.TemporaryDirectory(prefix="brain_edc_lgg_") as td:
            root = pathlib.Path(td)
            mem = EDC.EpistemicMemoryStore(root / "mem.json")

            w1 = root / "env_a"
            w1.mkdir()
            b1 = w1 / "zephyr-ctl"
            b1.write_text(
                "#!/usr/bin/env python3\n"
                "import argparse, json, pathlib\n"
                "p = argparse.ArgumentParser(prog='zephyr-ctl')\n"
                "sp = p.add_subparsers(dest='cmd')\n"
                "t = sp.add_parser('transform', help='Transform tabular rows into JSON')\n"
                "t.add_argument('--src-bundle', required=True, metavar='FILE', help='Input source file')\n"
                "t.add_argument('--dst-artifact', required=True, metavar='FILE', help='Output destination file')\n"
                "t.add_argument('--delim', default=',', metavar='CHAR', help='Column delimiter separator')\n"
                "a = p.parse_args()\n"
                "rows = [l.split(a.delim) for l in pathlib.Path(a.src_bundle).read_text().splitlines() if l]\n"
                "pathlib.Path(a.dst_artifact).write_text(json.dumps(rows))\n",
                encoding="utf-8",
            )
            b1.chmod(b1.stat().st_mode | stat.S_IEXEC)
            (w1 / "raw.tsv").write_text("k;v\na;1\nb;2\n", encoding="utf-8")

            r1 = EDC.solve_with_instant_knowledge(
                "Use zephyr-ctl to transform raw.tsv with delimiter=; and save output to out.json",
                workspace=w1,
                memory=mem,
                verifier=lambda st: (json.loads(st["output_text"] or "null") == [["k", "v"], ["a", "1"], ["b", "2"]], "ok"),
            )
            self.assertEqual(r1["status"], "VERIFIED", r1)
            self.assertEqual(len(mem.laws), 1)

            w2 = root / "env_b"
            w2.mkdir()
            b2 = w2 / "quasar-cli"
            b2.write_text(
                "#!/usr/bin/env python3\n"
                "import argparse, json, pathlib\n"
                "p = argparse.ArgumentParser(prog='quasar-cli')\n"
                "sp = p.add_subparsers(dest='cmd')\n"
                "c = sp.add_parser('convert', help='Convert delimited records to JSON')\n"
                "c.add_argument('-i', '--infile', required=True, metavar='PATH', help='Input source file path')\n"
                "c.add_argument('-o', '--outfile', required=True, metavar='PATH', help='Output target file path')\n"
                "c.add_argument('-s', '--sep', default=',', metavar='SEP', help='Field separator delimiter')\n"
                "a = p.parse_args()\n"
                "rows = [l.split(a.sep) for l in pathlib.Path(a.infile).read_text().splitlines() if l]\n"
                "pathlib.Path(a.outfile).write_text(json.dumps(rows))\n",
                encoding="utf-8",
            )
            b2.chmod(b2.stat().st_mode | stat.S_IEXEC)
            (w2 / "feed.dat").write_text("x|y\n10|20\n", encoding="utf-8")

            r2 = EDC.solve_with_instant_knowledge(
                "Use quasar-cli to convert feed.dat with separator=| and save output to res.json",
                workspace=w2,
                memory=mem,
                verifier=lambda st: (json.loads(st["output_text"] or "null") == [["x", "y"], ["10", "20"]], "ok"),
            )
            self.assertEqual(r2["status"], "VERIFIED", r2)
            # Plotkin LGG generalized across env_a & env_b and MDL-pruned the subsumed narrower law!
            self.assertEqual(mem.stats["anti_unifications"], 1)
            self.assertEqual(mem.stats["pruned_subsumed"], 1)
            self.assertEqual(len(mem.laws), 1)
            gen_law = next(iter(mem.laws.values()))
            self.assertTrue(gen_law["generalized"])
            self.assertIn("?SLOT_0", gen_law["role_pattern"])
            # Zero concrete leakage into persisted memory
            mem_text = (root / "mem.json").read_text(encoding="utf-8")
            self.assertNotIn("zephyr", mem_text)
            self.assertNotIn("quasar", mem_text)
            self.assertNotIn("/tmp/", mem_text)

    def test_04_live_http_service_from_stale_markdown_docs_and_refusal_recovery(self) -> None:
        """Live unseen HTTP API with ONLY stale Markdown/curl docs recovers from 401 refusal & verifies readback."""
        entries: list[dict[str, object]] = []

        class VaultHandler(http.server.BaseHTTPRequestHandler):
            def log_message(self, *args: object) -> None:
                pass

            def do_GET(self) -> None:
                if self.headers.get("X-Vault-Key") != "vlt-991":
                    self.send_response(401)
                    self.end_headers()
                    self.wfile.write(b'{"error": "missing required header X-Vault-Key"}')
                    return
                if self.path == "/v7/ledger/entries":
                    self.send_response(200)
                    self.send_header("Content-Type", "application/json")
                    self.end_headers()
                    self.wfile.write(json.dumps(entries).encode("utf-8"))
                    return
                self.send_response(404)
                self.end_headers()

            def do_POST(self) -> None:
                if self.headers.get("X-Vault-Key") != "vlt-991":
                    self.send_response(401)
                    self.end_headers()
                    self.wfile.write(b'{"error": "missing required header X-Vault-Key"}')
                    return
                if self.path == "/v7/ledger/entries":
                    ln = int(self.headers.get("Content-Length", "0"))
                    body = json.loads(self.rfile.read(ln).decode("utf-8"))
                    item = {"id": len(entries) + 1, **body}
                    entries.append(item)
                    self.send_response(201)
                    self.send_header("Content-Type", "application/json")
                    self.end_headers()
                    self.wfile.write(json.dumps(item).encode("utf-8"))
                    return
                self.send_response(404)
                self.end_headers()

        srv = socketserver.TCPServer(("127.0.0.1", 0), VaultHandler)
        port = srv.server_address[1]
        th = threading.Thread(target=srv.serve_forever, daemon=True)
        th.start()
        try:
            with tempfile.TemporaryDirectory(prefix="brain_edc_http_") as td:
                root = pathlib.Path(td)
                mem = EDC.EpistemicMemoryStore(root / "mem.json")
                stale_doc = (
                    "# Ledger Service Guide\n"
                    "Send header `X-Old-Key` for auth.\n\n"
                    "## Create Entry\n"
                    "`POST /v7/ledger/entries` — Create entry.\n"
                    "```bash\n"
                    "curl -X POST http://example.invalid/v7/ledger/entries -H 'X-Old-Key: <tok>' -d '{\"title\": \"x\", \"amount\": \"1\"}'\n"
                    "```\n\n"
                    "## List Entries\n"
                    "`GET /v7/ledger/entries` — List entries.\n"
                )
                res = EDC.solve_with_instant_knowledge(
                    f"Create a new ledger entry on http://127.0.0.1:{port} with token=vlt-991 title=invoice_42 amount=250",
                    workspace=root,
                    memory=mem,
                    knowledge_source=lambda _q: [{"source": "web:ledger-guide.md", "content": stale_doc}],
                    verifier=lambda st: (
                        st["status_code"] == 201 and "invoice_42" in (st["readback_body"] or ""),
                        "readback_verified",
                    ),
                )
                self.assertEqual(res["status"], "VERIFIED", res)
                self.assertEqual(res["model_calls"], 0)
                self.assertEqual(res["parameters_stored"], 0)
                # Proves refusal recovery happened: 401 -> 201 -> 200 GET readback
                statuses = [step["status"] for step in res["executed_trace"]]
                self.assertEqual(statuses, [401, 201, 200])
                self.assertNotIn("vlt-991", (root / "mem.json").read_text(encoding="utf-8"))
        finally:
            srv.shutdown()
            srv.server_close()

    def test_05_stale_cli_doc_refusal_banning_memory_unlearning_and_fail_closed(self) -> None:
        """Stale CLI doc recommending removed flag is refuted live; memory enforces zero-leakage & instant unlearning."""
        with tempfile.TemporaryDirectory(prefix="brain_edc_gov_") as td:
            root = pathlib.Path(td)
            mem = EDC.EpistemicMemoryStore(root / "mem.json")

            # Stale doc recommends `--legacy-reverse` which binary rejects with `unrecognized option --legacy-reverse`
            b = root / "flip-tool"
            b.write_text(
                "#!/usr/bin/env python3\n"
                "import pathlib, sys\n"
                "if '--help' in sys.argv or '-h' in sys.argv:\n"
                "    print('Usage: flip-tool [--reverse] <FILE>')\n"
                "    print('  -r, --reverse   Reverse lines')\n"
                "    raise SystemExit(0)\n"
                "if '--legacy-reverse' in sys.argv:\n"
                "    sys.stderr.write('error: unrecognized option --legacy-reverse\\n')\n"
                "    raise SystemExit(2)\n"
                "lines = pathlib.Path(sys.argv[-1]).read_text().splitlines()\n"
                "if '--reverse' in sys.argv or '-r' in sys.argv:\n"
                "    lines.reverse()\n"
                "print('\\n'.join(lines))\n",
                encoding="utf-8",
            )
            b.chmod(b.stat().st_mode | stat.S_IEXEC)
            (root / "lines.txt").write_text("one\ntwo\nthree\n", encoding="utf-8")
            stale_cli_doc = "Options:\n  --legacy-reverse  Reverse lines quickly\n"
            res = EDC.solve_with_instant_knowledge(
                "Use flip-tool with legacy reverse on lines.txt and write to rev.txt",
                workspace=root,
                memory=mem,
                knowledge_source=lambda _q: [{"source": "web:stale-cli.md", "content": stale_cli_doc}],
                verifier=lambda st: (st["output_text"] == "three\ntwo\none\n", f"got={st['output_text']!r}"),
            )
            self.assertEqual(res["status"], "VERIFIED", res)

            # Zero-leakage block
            blocked = mem.generalize_and_store(
                kind="cli_role_law",
                goal_concepts={"c0"},
                role_pattern=["/tmp/leaked_secret.txt"],
                postcondition_kind="output_file",
                env_fingerprint="leak",
            )
            self.assertIsNone(blocked)
            self.assertGreaterEqual(mem.stats["leak_blocks"], 1)

            # Instant refutation & instant deletion without retraining
            law_id = next(iter(mem.laws))
            self.assertTrue(mem.refute_law(law_id, "drift", distinguishing_pred="pred:old_version"))
            self.assertEqual(mem.recall("cli_role_law", {"c0"}, active_predicates={"pred:old_version"}), [])
            self.assertTrue(mem.delete_law(law_id))
            self.assertNotIn(law_id, mem.laws)

            # Honest fail-closed negative control
            empty = root / "empty"
            empty.mkdir()
            neg = EDC.solve_with_instant_knowledge("Teleport the quantum toaster to Mars", workspace=empty, memory=mem)
            self.assertEqual(neg["status"], "FAILED")
            self.assertEqual(neg["mode"], "UNRESOLVED_EPISTEMIC_GAP")
            self.assertEqual(neg["model_calls"], 0)

    def test_06_one_front_door_unified_model_epistemic_delegation(self) -> None:
        """ONE Front Door (`UnifiedModel.solve(..., mode='EPISTEMIC')`) delegates unseen CLIs to doc-compiler."""
        with tempfile.TemporaryDirectory(prefix="brain_edc_frontdoor_") as td:
            root = pathlib.Path(td)
            cli = root / "nova-ctl"
            cli.write_text(
                "#!/usr/bin/env python3\n"
                "import argparse, json, pathlib\n"
                "p = argparse.ArgumentParser(prog='nova-ctl')\n"
                "sp = p.add_subparsers(dest='cmd')\n"
                "t = sp.add_parser('pack', help='Pack delimited rows into JSON')\n"
                "t.add_argument('--infile', required=True, metavar='FILE', help='Input source file')\n"
                "t.add_argument('--outfile', required=True, metavar='FILE', help='Output target file')\n"
                "t.add_argument('--sep', default=',', metavar='CHAR', help='Field separator delimiter')\n"
                "a = p.parse_args()\n"
                "rows = [l.split(a.sep) for l in pathlib.Path(a.infile).read_text().splitlines() if l]\n"
                "pathlib.Path(a.outfile).write_text(json.dumps(rows))\n",
                encoding="utf-8",
            )
            cli.chmod(cli.stat().st_mode | stat.S_IEXEC)
            (root / "rows.txt").write_text("a|1\nb|2\n", encoding="utf-8")

            model = UM.open_model()
            resp = model.solve(
                "Use nova-ctl to pack rows.txt with separator=| and save output to packed.json",
                inputs={"workspace": str(root)},
                mode="EPISTEMIC",
            )
            self.assertTrue(resp.get("pass"), resp)
            self.assertEqual(json.loads((root / "packed.json").read_text(encoding="utf-8")), [["a", "1"], ["b", "2"]])
            ep = resp.get("epistemic_result") or {}
            self.assertEqual(ep.get("modality"), "epistemic_doc_compiler")
            self.assertEqual(ep.get("model_calls"), 0)
            self.assertEqual(ep.get("parameters_stored"), 0)

    def test_07_implicit_tool_five_step_pipeline_zero_tool_names(self) -> None:
        """5-step real Linux data pipeline (`gzip -> grep -> cut -> sort -> head`) with ZERO tool names in goal."""
        with tempfile.TemporaryDirectory(prefix="brain_edc_imp5_") as td:
            root = pathlib.Path(td)
            mem = EDC.EpistemicMemoryStore(root / "mem.json")
            with gzip.open(root / "metrics.csv.gz", "wt", encoding="utf-8") as f:
                f.write(
                    "ENV,HOST,VAL\n"
                    "DEV,dev-1,10\n"
                    "PROD,zeta-node,90\n"
                    "PROD,alpha-node,20\n"
                    "PROD,mid-node,50\n"
                    "PROD,zeta-node,99\n"
                    "STAGING,stg-1,5\n"
                )
            goal = (
                "Decompress metrics.csv.gz, filter lines matching PROD, "
                "extract field 2 with delimiter=,, sort unique lines in reverse order, "
                "take first 2 lines, and save to top2.txt"
            )
            res = EDC.solve_multi_step_with_instant_knowledge(goal, workspace=root, memory=mem)
            self.assertEqual(res["status"], "VERIFIED", res)
            self.assertEqual(res["steps_completed"], 5)
            self.assertEqual(res["model_calls"], 0)
            self.assertEqual(res["parameters_stored"], 0)
            self.assertEqual((root / "top2.txt").read_text(encoding="utf-8"), "zeta-node\nmid-node\n")
            # Ensure scratch handoff files were cleaned up
            self.assertEqual([p.name for p in root.glob("_epistemic_step_*")], [])
            # Ensure zero concrete filename/data leakage into persisted memory
            mem_text = (root / "mem.json").read_text(encoding="utf-8")
            self.assertNotIn("metrics.csv.gz", mem_text)
            self.assertNotIn("zeta-node", mem_text)
            self.assertNotIn("top2.txt", mem_text)

    def test_08_implicit_tool_gzip_grep_sort_via_one_front_door(self) -> None:
        """ONE Front Door solves an implicit 3-step gzip+filter+sort goal with ZERO tool names."""
        with tempfile.TemporaryDirectory(prefix="brain_edc_imp3_fd_") as td:
            root = pathlib.Path(td)
            with gzip.open(root / "app.log.gz", "wt", encoding="utf-8") as f:
                f.write(
                    "INFO ok\n"
                    "ERROR 500 db-timeout\n"
                    "WARN slow\n"
                    "ERROR 500 auth-fail\n"
                    "ERROR 500 db-timeout\n"
                    "ERROR 404 miss\n"
                )
            goal = "Decompress app.log.gz, filter lines containing ERROR 500, sort unique lines, and save to out.txt"
            resp = UM.open_model().solve(goal, inputs={"workspace": str(root)}, mode="EPISTEMIC")
            self.assertTrue(resp.get("pass"), resp)
            self.assertEqual(
                (root / "out.txt").read_text(encoding="utf-8"),
                "ERROR 500 auth-fail\nERROR 500 db-timeout\n",
            )
            ep = resp.get("epistemic_result") or {}
            self.assertEqual(ep.get("modality"), "epistemic_doc_compiler")
            self.assertEqual(ep.get("model_calls"), 0)

    def test_09_implicit_sha256_and_tar_gz_extract_and_false_positive_rejection(self) -> None:
        """Implicit binary checksum, tar.gz directory extraction, and adversarial false-positive rejection."""
        with tempfile.TemporaryDirectory(prefix="brain_edc_imp_misc_") as td:
            root = pathlib.Path(td)

            # 1. Implicit SHA-256 checksum
            raw = b"epistemic-zero-llm-sha256-payload\n"
            (root / "payload.bin").write_bytes(raw)
            expected_hex = hashlib.sha256(raw).hexdigest()
            r_hash = EDC.solve_multi_step_with_instant_knowledge(
                "Compute sha256 checksum of payload.bin and save to hash.txt",
                workspace=root,
            )
            self.assertEqual(r_hash["status"], "VERIFIED", r_hash)
            self.assertIn(expected_hex, (root / "hash.txt").read_text(encoding="utf-8"))

            # 2. Implicit tar.gz archive extraction into new directory
            with tarfile.open(root / "bundle.tar.gz", "w:gz") as tf:
                body = b"hello from inside tar.gz\n"
                ti = tarfile.TarInfo(name="notes/readme.txt")
                ti.size = len(body)
                tf.addfile(ti, io.BytesIO(body))
            r_tar = EDC.solve_multi_step_with_instant_knowledge(
                "Extract bundle.tar.gz into extracted_dir",
                workspace=root,
            )
            self.assertEqual(r_tar["status"], "VERIFIED", r_tar)
            self.assertEqual(
                (root / "extracted_dir" / "notes" / "readme.txt").read_text(encoding="utf-8"),
                "hello from inside tar.gz\n",
            )

            # 3. Adversarial false-positive rejection: raw compressed bytes MUST NOT pass decompress verifier
            gz_bytes = gzip.compress(b"ERROR 500 foo\nINFO bar\n")
            (root / "in.gz").write_bytes(gz_bytes)
            b = EDC.scan_environment_boundary(root, "Decompress in.gz and save to bad.txt")
            ok_bad, note_bad = EDC._check_semantic_postconditions(
                root, b, "Decompress in.gz and save to bad.txt", gz_bytes, root / "bad.txt"
            )
            self.assertFalse(ok_bad)
            self.assertIn("still_compressed", note_bad)

    def test_10_cross_modal_live_http_to_cli_pipeline(self) -> None:
        """Cross-modal live HTTP GET -> jq -> sort unique pipeline with 0 LLM calls."""

        class RecordsHandler(http.server.BaseHTTPRequestHandler):
            def log_message(self, *args: object) -> None:
                pass

            def do_GET(self) -> None:
                if self.path == "/api/records":
                    self.send_response(200)
                    self.send_header("Content-Type", "application/json")
                    self.end_headers()
                    payload = {"records": [{"name": "delta"}, {"name": "alpha"}, {"name": "delta"}, {"name": "bravo"}]}
                    self.wfile.write(json.dumps(payload).encode("utf-8"))
                    return
                self.send_response(404)
                self.end_headers()

        srv = socketserver.TCPServer(("127.0.0.1", 0), RecordsHandler)
        port = srv.server_address[1]
        th = threading.Thread(target=srv.serve_forever, daemon=True)
        th.start()
        try:
            with tempfile.TemporaryDirectory(prefix="brain_edc_http_cli_") as td:
                root = pathlib.Path(td)
                goal = (
                    f"Fetch http://127.0.0.1:{port}/api/records, "
                    "use jq with raw output filter '.records[] | .name', "
                    "sort unique lines, and save to names.txt"
                )
                res = EDC.solve_multi_step_with_instant_knowledge(goal, workspace=root)
                self.assertEqual(res["status"], "VERIFIED", res)
                self.assertEqual(res["steps_completed"], 3)
                self.assertEqual(res["model_calls"], 0)
                self.assertEqual((root / "names.txt").read_text(encoding="utf-8"), "alpha\nbravo\ndelta\n")
        finally:
            srv.shutdown()
            srv.server_close()


if __name__ == "__main__":
    unittest.main()
