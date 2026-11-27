"""Tests for Goal-Directed Epistemic Computer-Use Engine & Unified Agent integration.

Verifies:
  1. Zero-prior live acquisition (`local_manual` `--help` + live `web_command_guide`
     `tldr-pages` + multi-source corroboration) on unseen CLI tools (`tar`, `jq`, `base64`, `awk`).
  2. Single-experience permanent learning into external JSON (`parameters_stored == 0`,
     `model_calls == 0`) and offline (`allow_web=False`) Tier 0 transfer to unseen workspaces.
  3. Instant forgetting upon JSON deletion and counterexample narrowing/quarantine.
  4. Closed-loop `stderr`-driven epistemic refinement (`_refine_command_from_stderr`).
  5. Seamless delegation from `unified_computer_use_agent_v1.solve_computer_use_task`
     plus verification of new general first-principles solvers (secret sanitization,
     fragmented binary carving, ICS calendar CSP scheduling, constrained regex synthesis).
"""
from __future__ import annotations

import base64
import hashlib
import io
import json
import pathlib
import re
import tarfile
import tempfile
import unittest
import zipfile

from canonical.runtime import epistemic_computer_use_engine_v1 as EPI
from canonical.runtime import epistemic_morphism_engine_v1 as EM
from canonical.runtime import instant_cu_procedure_store_v1 as PROC_STORE
from canonical.runtime import unified_computer_use_agent_v1 as AGENT


class EpistemicComputerUseEngineTests(unittest.TestCase):
    def test_live_epistemic_acquisition_offline_tier0_transfer_and_deletion(self) -> None:
        store = PROC_STORE.new_store()
        with tempfile.TemporaryDirectory() as t1, tempfile.TemporaryDirectory() as t2, tempfile.TemporaryDirectory() as t3:
            # 1. Cold run on unseen workspace #1 (tar create from directory)
            w1 = pathlib.Path(t1)
            (w1 / "docs").mkdir()
            (w1 / "docs" / "a.txt").write_text("alpha\n", encoding="utf-8")
            (w1 / "docs" / "b.txt").write_text("beta\n", encoding="utf-8")

            r1 = EPI.solve_unknown_environment(
                w1,
                "Create a gzipped tar archive into bundle.tar.gz from directory docs",
                procedure_store=store,
                allow_web=True,
            )
            self.assertEqual(r1.status, "VERIFIED")
            self.assertEqual(r1.model_calls, 0)
            self.assertEqual(r1.parameters_stored, 0)
            self.assertIn("local_manual", r1.corroborated_kinds)
            self.assertTrue((w1 / "bundle.tar.gz").is_file())
            self.assertIsNotNone(r1.learned_procedure_id)
            # Goal-defined questioning: asked ONLY about goal-relevant tools, not all binaries
            asked_tools = {q["tool"] for q in r1.questions_asked}
            self.assertIn("tar", asked_tools)
            self.assertLessEqual(len(asked_tools), 3)

            # 2. Offline Tier 0 single-experience transfer to brand-new workspace #2
            w2 = pathlib.Path(t2)
            (w2 / "reports").mkdir()
            (w2 / "reports" / "q1.txt").write_text("revenue 42\n", encoding="utf-8")

            r2 = EPI.solve_unknown_environment(
                w2,
                "Create a gzipped tar archive into release.tar.gz from directory reports",
                procedure_store=store,
                allow_web=False,  # proves ZERO web queries on recalled skill!
            )
            self.assertEqual(r2.status, "VERIFIED")
            self.assertEqual(r2.tier_used, "TIER0_RECALL")
            self.assertEqual(r2.recalled_procedure_id, r1.learned_procedure_id)
            self.assertEqual(r2.questions_asked, [])
            with tarfile.open(w2 / "release.tar.gz", "r:gz") as tf:
                self.assertTrue(any("q1.txt" in n for n in tf.getnames()))

            # 3. External JSON deletion immediately removes Tier 0 recall
            self.assertTrue(PROC_STORE.delete_procedure(store, str(r1.learned_procedure_id)))
            w3 = pathlib.Path(t3)
            (w3 / "notes").mkdir()
            (w3 / "notes" / "x.txt").write_text("x\n", encoding="utf-8")
            r3 = EPI.solve_unknown_environment(
                w3,
                "Create a gzipped tar archive into out.tar.gz from directory notes",
                procedure_store=store,
                allow_web=True,
            )
            self.assertEqual(r3.status, "VERIFIED")
            self.assertNotEqual(r3.tier_used, "TIER0_RECALL")
            self.assertIsNone(r3.recalled_procedure_id)

    def test_jq_expression_learning_and_offline_transfer(self) -> None:
        store = PROC_STORE.new_store()
        with tempfile.TemporaryDirectory() as t1, tempfile.TemporaryDirectory() as t2:
            w1 = pathlib.Path(t1)
            (w1 / "users.json").write_text(json.dumps({"users": [{"name": "alice"}, {"name": "bob"}]}), encoding="utf-8")
            r1 = EPI.solve_unknown_environment(
                w1,
                "Use jq to filter users.json with query '.users[].name' and save raw output to names.txt",
                postcondition_fn=lambda d: ((d / "names.txt").read_text(encoding="utf-8").strip() == "alice\nbob", "match"),
                procedure_store=store,
                allow_web=True,
            )
            self.assertEqual(r1.status, "VERIFIED")
            self.assertIsNotNone(r1.learned_procedure_id)

            w2 = pathlib.Path(t2)
            (w2 / "catalog.json").write_text(json.dumps({"items": [{"sku": "A1"}, {"sku": "B2"}]}), encoding="utf-8")
            r2 = EPI.solve_unknown_environment(
                w2,
                "Use jq to filter catalog.json with query '.items[].sku' and save raw output to skus.txt",
                postcondition_fn=lambda d: ((d / "skus.txt").read_text(encoding="utf-8").strip() == "A1\nB2", "match"),
                procedure_store=store,
                allow_web=False,
            )
            self.assertEqual(r2.status, "VERIFIED")
            self.assertEqual(r2.tier_used, "TIER0_RECALL")
            self.assertEqual((w2 / "skus.txt").read_text(encoding="utf-8").strip(), "A1\nB2")

    def test_closed_loop_stderr_epistemic_refinement(self) -> None:
        lh = EPI.query_local_cli_help("base64")
        gs = {"output_paths": ["nested/out.txt"], "output_dirs": []}
        refs1 = EPI._refine_command_from_stderr(
            "base64 --decod secret.b64",
            "base64: unrecognized option '--decod'",
            "base64",
            lh,
            gs,
        )
        self.assertTrue(any("--decode" in cmd for cmd, _ in refs1))

        refs2 = EPI._refine_command_from_stderr(
            "tar xvf a.tar.gz -C missing_dir",
            "tar: missing_dir: Cannot open: No such file or directory",
            "tar",
            EPI.query_local_cli_help("tar"),
            {"output_paths": [], "output_dirs": ["missing_dir"]},
        )
        self.assertTrue(any(cmd.startswith("mkdir -p missing_dir && ") for cmd, _ in refs2))

    def test_unified_agent_delegates_unknown_goal_to_epistemic_engine(self) -> None:
        store = PROC_STORE.new_store()
        with tempfile.TemporaryDirectory() as td:
            ws = pathlib.Path(td)
            (ws / "payload.b64").write_text(base64.b64encode(b"EPISTEMIC_DELEGATION_OK\n").decode(), encoding="utf-8")
            rep = AGENT.solve_computer_use_task(
                ws,
                "Decode base64 file payload.b64 and save output to plain.txt",
                procedure_store=store,
            )
            self.assertTrue(rep["verified"])
            self.assertEqual(rep["model_calls"], 0)
            self.assertEqual(rep["parameters_stored"], 0)
            self.assertEqual((ws / "plain.txt").read_text(encoding="utf-8").strip(), "EPISTEMIC_DELEGATION_OK")
            self.assertIn("epistemic_trace", rep)

    def test_new_first_principles_solvers_general_end_to_end(self) -> None:
        # 1. Secret sanitization leaves clean files byte-for-byte intact
        with tempfile.TemporaryDirectory() as td:
            ws = pathlib.Path(td)
            repo = ws / "demo"
            repo.mkdir()
            (repo / ".git").mkdir()
            (repo / "config.py").write_text(
                'AWS_KEY = "AKIA1234567890ABCDEF"\n'
                'AWS_SECRET_ACCESS_KEY = "AbCdEfGhIjKlMnOpQrStUvWxYz0123456789+/AB"\n'
                'GH = "ghp_1234567890abcdefghijklmnopQRSTUV"\n'
                'HF = "hf_abcdefghijklmnopqrstuvwxyz123456"\n',
                encoding="utf-8",
            )
            (repo / "clean.txt").write_text("do not touch this clean file\n", encoding="utf-8")
            clean_before = (repo / "clean.txt").read_bytes()
            rep = AGENT.solve_computer_use_task(
                ws,
                'Please sanitize repository "demo" of all API keys and replace with placeholders:\n'
                '- AWS_ACCESS_KEY_ID -> <your-aws-access-key-id>\n'
                '- AWS_SECRET_ACCESS_KEY -> <your-aws-secret-access-key>\n'
                '- Github token -> <your-github-token>\n'
                '- Huggingface token -> <your-huggingface-token>\n',
            )
            self.assertTrue(rep["verified"])
            sanitized = (repo / "config.py").read_text(encoding="utf-8")
            self.assertIn("<your-aws-access-key-id>", sanitized)
            self.assertIn("<your-aws-secret-access-key>", sanitized)
            self.assertIn("<your-github-token>", sanitized)
            self.assertIn("<your-huggingface-token>", sanitized)
            self.assertNotIn("AKIA1234567890ABCDEF", sanitized)
            self.assertEqual((repo / "clean.txt").read_bytes(), clean_before)

        # 2. Fragmented binary ZIP carving with CRC32 proof
        with tempfile.TemporaryDirectory() as td:
            ws = pathlib.Path(td)
            pw = "8XDTEST1234567890ABCDW54"[:23]
            pw = "8XD1234567890ABCDEFGW54"
            zpath = ws / "tmp.zip"
            with zipfile.ZipFile(zpath, "w", compression=zipfile.ZIP_STORED) as zf:
                zf.writestr("launchcode.txt", f"PASSWORD={pw}\n")
            zbytes = zpath.read_bytes()
            zpath.unlink()
            split = zbytes.index(b"PASSWORD=") + 16
            disk = bytearray(b"\x00" * 4096)
            disk[100 : 100 + split] = zbytes[:split]
            disk[2048 : 2048 + len(zbytes) - split] = zbytes[split:]
            (ws / "disk.dat").write_bytes(bytes(disk))
            rep2 = AGENT.solve_computer_use_task(
                ws,
                'Forensic recovery: recover PASSWORD from deleted file launchcode.txt.\n'
                'Format: PASSWORD=XXXXXXXXXX\n'
                '- It is exactly 23 characters long\n'
                '- It starts with "8XD" and ends with "W54"\n'
                'Write matching passwords to /app/recovered_passwords.txt\n',
            )
            self.assertTrue(rep2["verified"])
            self.assertIn(pw, (ws / "recovered_passwords.txt").read_text(encoding="utf-8"))

        # 3. Constrained log regex composition
        with tempfile.TemporaryDirectory() as td:
            ws = pathlib.Path(td)
            rep3 = AGENT.solve_computer_use_task(
                ws,
                "Write a regex matching dates in YYYY-MM-DD on lines with an IPv4 address without leading zeros.\n"
                "Match only the last date in that line; February can have up to 29 days.\n"
                "Save your regex in /app/regex.txt\n",
            )
            self.assertTrue(rep3["verified"])
            pat = (ws / "regex.txt").read_text(encoding="utf-8").strip()
            self.assertEqual(
                re.findall(pat, "2024-01-01 host 10.0.0.1 date 2024-02-29\nno ip 2024-05-05\n", re.MULTILINE),
                ["2024-02-29"],
            )

    def test_compositional_4step_offline_and_5step_hybrid_epistemic_diff(self) -> None:
        store = EM.new_morphism_store()
        # Learn 4 atomic composable morphisms from 4 separate simple experiences
        with tempfile.TemporaryDirectory() as t:
            w = pathlib.Path(t)
            (w / "m.b64").write_text(base64.b64encode(b"hi\n").decode(), encoding="utf-8")
            r = EM.solve_with_epistemic_morphisms(w, "Decode base64 file m.b64 and save to m.txt", morphism_store=store)
            self.assertEqual(r.status, "VERIFIED")

        with tempfile.TemporaryDirectory() as t:
            w = pathlib.Path(t)
            f = w / "tmp.txt"
            f.write_text("x\n", encoding="utf-8")
            with tarfile.open(w / "box.tar.gz", "w:gz") as tf:
                tf.add(f, arcname="x.txt")
            f.unlink()
            r = EM.solve_with_epistemic_morphisms(w, "Extract archive box.tar.gz into directory out", morphism_store=store)
            self.assertEqual(r.status, "VERIFIED")

        with tempfile.TemporaryDirectory() as t:
            w = pathlib.Path(t)
            (w / "u.json").write_text(json.dumps({"u": [{"n": "a"}, {"n": "b"}]}), encoding="utf-8")
            r = EM.solve_with_epistemic_morphisms(
                w,
                "Use jq to filter u.json with query '.u[].n' raw output and save to out.txt",
                morphism_store=store,
                postcondition_fn=lambda d: ((d / "out.txt").read_text(encoding="utf-8").strip() == "a\nb", "ok"),
            )
            self.assertEqual(r.status, "VERIFIED")

        with tempfile.TemporaryDirectory() as t:
            w = pathlib.Path(t)
            (w / "raw.txt").write_text("z\na\nz\n", encoding="utf-8")
            r = EM.solve_with_epistemic_morphisms(
                w,
                "Sort unique lines in raw.txt and save to clean.txt",
                morphism_store=store,
                postcondition_fn=lambda d: ((d / "clean.txt").read_text(encoding="utf-8") == "a\nz\n", "ok"),
            )
            self.assertEqual(r.status, "VERIFIED")

        self.assertEqual(len(store["morphisms"]), 4)
        self.assertEqual(store["parameters_stored"], 0)

        # Build unseen nested payload: JSON -> tar.gz -> base64
        buf = io.BytesIO()
        with tarfile.open(fileobj=buf, mode="w:gz") as tf:
            payload = json.dumps({"records": [{"tag": "zeta"}, {"tag": "alpha"}, {"tag": "zeta"}, {"tag": "beta"}]}).encode()
            ti = tarfile.TarInfo(name="records.json")
            ti.size = len(payload)
            tf.addfile(ti, io.BytesIO(payload))
        b64_payload = base64.b64encode(buf.getvalue()).decode()

        # 1. Unseen 4-step pipeline solved 100% OFFLINE by composing the 4 atomic morphisms
        with tempfile.TemporaryDirectory() as t:
            w = pathlib.Path(t)
            (w / "bundle.tar.gz.b64").write_text(b64_payload, encoding="utf-8")
            r4 = EM.solve_with_epistemic_morphisms(
                w,
                "Decode base64 bundle.tar.gz.b64, then extract the archive, then use jq to filter with query '.records[].tag' raw output, then sort unique and save to tags.txt",
                morphism_store=store,
                allow_web=False,
                postcondition_fn=lambda d: ((d / "tags.txt").read_text(encoding="utf-8") == "alpha\nbeta\nzeta\n", "ok"),
            )
            self.assertEqual(r4.status, "VERIFIED")
            self.assertEqual(r4.mode, "ALL_TIER0_COMPOSED")
            self.assertEqual(r4.gaps_queried, [])
            self.assertEqual(r4.web_queries_made, 0)
            self.assertEqual(len(r4.morphisms_recalled), 4)
            # No temporary intermediate stage files leaked into real workspace!
            self.assertEqual(sorted(p.name for p in w.iterdir()), ["bundle.tar.gz.b64", "tags.txt"])

        # 2. Unseen 5-step hybrid pipeline: 4 recalled from memory + ONLY 1 missing gap (`sha256sum`) fetched!
        with tempfile.TemporaryDirectory() as t:
            w = pathlib.Path(t)
            (w / "bundle.tar.gz.b64").write_text(b64_payload, encoding="utf-8")
            expected_sha = hashlib.sha256(b"alpha\nbeta\nzeta\n").hexdigest()
            r5 = EM.solve_with_epistemic_morphisms(
                w,
                "Decode base64 bundle.tar.gz.b64, then extract the archive, then use jq to filter with query '.records[].tag' raw output, then sort unique, then compute sha256 checksum and save to tags.sha256",
                morphism_store=store,
                allow_web=True,
                postcondition_fn=lambda d: (expected_sha in (d / "tags.sha256").read_text(encoding="utf-8"), "ok"),
            )
            self.assertEqual(r5.status, "VERIFIED")
            self.assertEqual(r5.mode, "HYBRID_TIER0_AND_EPISTEMIC")
            self.assertEqual(r5.gaps_queried, ["sha256sum"])
            self.assertEqual(len(r5.morphisms_recalled), 4)
            self.assertEqual(len(r5.morphisms_learned), 1)
            self.assertEqual(sorted(p.name for p in w.iterdir()), ["bundle.tar.gz.b64", "tags.sha256"])

    def test_morphism_store_save_load_delete_refuse_leak_and_narrowing(self) -> None:
        store = EM.new_morphism_store()
        # Refuses leaked host path
        leaked = EM.induce_morphism(
            store,
            in_type="file:text",
            verb="sort_unique",
            out_type="file:text",
            tool="sort",
            concrete_command="sort -u /tmp/leaked_dir/a.txt",
            redirect_stdout=True,
            hole_bindings={"__IN__": "a.txt"},
            observables=["tool:sort", "in_type:file:text"],
            corroborated_kinds=["local_manual"],
            source_url="local://sort",
        )
        self.assertIsNone(leaked)

        # Admits clean hole-abstracted morphism
        rec = EM.induce_morphism(
            store,
            in_type="file:text",
            verb="sort_unique",
            out_type="file:text",
            tool="sort",
            concrete_command="sort -u items.txt",
            redirect_stdout=True,
            hole_bindings={"__IN__": "items.txt"},
            observables=["tool:sort", "in_type:file:text", "has_expr:False", "ascii_only:True"],
            corroborated_kinds=["local_manual", "web_command_guide"],
            source_url="https://github.com/tldr-pages/tldr",
        )
        self.assertIsNotNone(rec)
        mid = rec["morphism_id"]
        self.assertEqual(rec["command_template"], "sort -u __IN__")

        # Narrow on counterexample missing `ascii_only:True`, then quarantine on indistinguishable counterexample
        ref1 = EM.refute_morphism(store, mid, counterexample_observables=["tool:sort", "in_type:file:text", "has_expr:False"])
        self.assertEqual(ref1["status"], "NARROWED")
        self.assertEqual(ref1["added_observable"], "ascii_only:True")
        ref2 = EM.refute_morphism(store, mid, counterexample_observables=["tool:sort", "in_type:file:text", "has_expr:False", "ascii_only:True"])
        self.assertEqual(ref2["status"], "QUARANTINED")

        # Save, load, delete round-trip
        with tempfile.TemporaryDirectory() as td:
            p = pathlib.Path(td) / "morphisms.json"
            EM.save_morphism_store(store, p)
            loaded = EM.load_morphism_store(p)
            self.assertEqual(loaded["parameters_stored"], 0)
            self.assertTrue(EM.delete_morphism(loaded, mid))
            self.assertNotIn(mid, loaded["morphisms"])

    def test_implicit_runtime_container_unwrapping_offline_opaque_hybrid_and_bfs(self) -> None:
        import base64
        import gzip
        import shutil
        import tarfile

        if not all(shutil.which(t) for t in ("base64", "tar", "jq", "sort", "gzip")):
            self.skipTest("required standard CLI tools unavailable")

        store = EM.new_morphism_store()
        # Train 4 atomic morphisms cold (1-step each, offline via local --help)
        with tempfile.TemporaryDirectory() as td:
            root = pathlib.Path(td)
            w1 = root / "w1"
            w1.mkdir()
            (w1 / "tok.b64").write_text(base64.b64encode(b"ok\n").decode("ascii"), encoding="utf-8")
            self.assertEqual(
                EM.solve_with_epistemic_morphisms(
                    w1, "Use base64 to decode tok.b64 and save to out.txt",
                    morphism_store=store, allow_web=False,
                    postcondition_fn=lambda d: ((d / "out.txt").read_bytes() == b"ok\n", "ok"),
                ).status,
                "VERIFIED",
            )

            w2 = root / "w2"
            w2.mkdir()
            src = w2 / "src"
            src.mkdir()
            (src / "a.txt").write_text("hi\n", encoding="utf-8")
            with tarfile.open(w2 / "a.tar.gz", "w:gz") as tf:
                tf.add(src / "a.txt", arcname="a.txt")
            (src / "a.txt").unlink()
            src.rmdir()
            self.assertEqual(
                EM.solve_with_epistemic_morphisms(
                    w2, "Use tar to extract archive a.tar.gz into folder unp",
                    morphism_store=store, allow_web=True,
                    postcondition_fn=lambda d: ((d / "unp" / "a.txt").is_file(), "ok"),
                ).status,
                "VERIFIED",
            )

            w3 = root / "w3"
            w3.mkdir()
            (w3 / "d.json").write_text(json.dumps({"items": [{"k": "x"}, {"k": "y"}]}), encoding="utf-8")
            self.assertEqual(
                EM.solve_with_epistemic_morphisms(
                    w3, "Use jq with raw output '.items[].k' on d.json and save to k.txt",
                    morphism_store=store, allow_web=False,
                    postcondition_fn=lambda d: ("x\ny" in (d / "k.txt").read_text(encoding="utf-8"), "ok"),
                ).status,
                "VERIFIED",
            )

            w4 = root / "w4"
            w4.mkdir()
            (w4 / "l.txt").write_text("b\na\nb\n", encoding="utf-8")
            self.assertEqual(
                EM.solve_with_epistemic_morphisms(
                    w4, "Use sort unique on l.txt and save to u.txt",
                    morphism_store=store, allow_web=True,
                    postcondition_fn=lambda d: ((d / "u.txt").read_text(encoding="utf-8").strip() == "a\nb", "ok"),
                ).status,
                "VERIFIED",
            )

            # A. Extensionless opaque blob (mystery.dat = b64(tar.gz(records.json))): ZERO intermediate verbs named, 100% OFFLINE
            wb = root / "wb"
            wb.mkdir()
            inner = root / "inner"
            inner.mkdir()
            (inner / "records.json").write_text(
                json.dumps({"records": [{"tag": "delta"}, {"tag": "beta"}, {"tag": "delta"}]}),
                encoding="utf-8",
            )
            tgz = inner / "pack.tar.gz"
            with tarfile.open(tgz, "w:gz") as tf:
                tf.add(inner / "records.json", arcname="records.json")
            (wb / "mystery.dat").write_text(base64.b64encode(tgz.read_bytes()).decode("ascii"), encoding="utf-8")

            rb = EM.solve_with_epistemic_morphisms(
                wb,
                "Query '.records[].tag' raw output from mystery.dat, sort unique, and save to tags.txt",
                morphism_store=store,
                allow_web=False,
                postcondition_fn=lambda d: ((d / "tags.txt").read_text(encoding="utf-8").strip() == "beta\ndelta", "ok"),
            )
            self.assertEqual(rb.status, "VERIFIED")
            self.assertEqual(rb.mode, "ALL_TIER0_COMPOSED")
            self.assertEqual(rb.gaps_queried, [])
            self.assertEqual(rb.web_queries_made, 0)
            self.assertEqual(len(rb.steps_trace), 4)
            self.assertTrue(rb.steps_trace[0]["auto_unwrapped"])
            self.assertTrue(rb.steps_trace[1]["auto_unwrapped"])
            self.assertEqual(sorted(p.name for p in wb.iterdir()), ["mystery.dat", "tags.txt"])

            # B. Hybrid implicit unwrapping with UNKNOWN gzip layer (secret_data.json.gz.b64)
            wc = root / "wc"
            wc.mkdir()
            gz_bytes = gzip.compress(json.dumps({"records": [{"tag": "omega"}, {"tag": "gamma"}, {"tag": "omega"}]}).encode("utf-8"))
            (wc / "secret_data.json.gz.b64").write_text(base64.b64encode(gz_bytes).decode("ascii"), encoding="utf-8")

            rc = EM.solve_with_epistemic_morphisms(
                wc,
                "Query '.records[].tag' raw output from secret_data.json.gz.b64, sort unique, and save to tags.txt",
                morphism_store=store,
                allow_web=True,
                postcondition_fn=lambda d: ((d / "tags.txt").read_text(encoding="utf-8").strip() == "gamma\nomega", "ok"),
            )
            self.assertEqual(rc.status, "VERIFIED")
            self.assertEqual(rc.mode, "HYBRID_TIER0_AND_EPISTEMIC")
            self.assertEqual(rc.gaps_queried, ["gzip"])
            self.assertEqual(rc.web_queries_made, 1)
            self.assertEqual(len(rc.morphisms_learned), 1)
            self.assertEqual(sorted(p.name for p in wc.iterdir()), ["secret_data.json.gz.b64", "tags.txt"])

            # C. Re-run fresh extensionless gzip+b64 blob 100% OFFLINE -> ALL_TIER0_COMPOSED!
            wc2 = root / "wc2"
            wc2.mkdir()
            gz2 = gzip.compress(json.dumps({"records": [{"tag": "sigma"}, {"tag": "alpha"}, {"tag": "sigma"}]}).encode("utf-8"))
            (wc2 / "opaque_gz.bin").write_text(base64.b64encode(gz2).decode("ascii"), encoding="utf-8")
            rc2 = EM.solve_with_epistemic_morphisms(
                wc2,
                "Query '.records[].tag' raw output from opaque_gz.bin, sort unique, and save to tags.txt",
                morphism_store=store,
                allow_web=False,
                postcondition_fn=lambda d: ((d / "tags.txt").read_text(encoding="utf-8").strip() == "alpha\nsigma", "ok"),
            )
            self.assertEqual(rc2.status, "VERIFIED")
            self.assertEqual(rc2.mode, "ALL_TIER0_COMPOSED")
            self.assertEqual(rc2.gaps_queried, [])
            self.assertEqual(sorted(p.name for p in wc2.iterdir()), ["opaque_gz.bin", "tags.txt"])

            # D. Shortest-path BFS over typed morphism graph
            p_b64_dir = EM.plan_morphism_path(store, "file:base64", "dir")
            self.assertIsNotNone(p_b64_dir)
            self.assertEqual([m["verb"] for m in p_b64_dir], ["decode_base64", "extract_archive"])
            p_gz_txt = EM.plan_morphism_path(store, "file:gzip", "file:text")
            self.assertIsNotNone(p_gz_txt)
            self.assertEqual([m["verb"] for m in p_gz_txt], ["decompress_gzip", "filter_json"])

    def test_inverse_direction_progress_invariant_rejects_recompression(self) -> None:
        import base64
        import gzip

        with tempfile.TemporaryDirectory() as td:
            ws = pathlib.Path(td)
            raw_gz = gzip.compress(b'{"k": 1}')
            (ws / "in.bin").write_bytes(raw_gz)
            (ws / "recompressed.bin").write_bytes(gzip.compress(raw_gz))
            sub_gz = EM._infer_unwrap_subgoal("file:gzip", 0)
            ok, reason = EM._verify_step_output(ws, sub_gz, "recompressed.bin", None, "in.bin")
            self.assertFalse(ok)
            self.assertEqual(reason, "COMPRESSED_INSTEAD_OF_DECOMPRESSED")

            (ws / "in.b64").write_bytes(b"hello")
            (ws / "reencoded.b64").write_bytes(base64.b64encode(b"hello"))
            sub_b64 = EM._infer_unwrap_subgoal("file:base64", 1)
            ok2, reason2 = EM._verify_step_output(ws, sub_b64, "reencoded.b64", None, "in.b64")
            self.assertFalse(ok2)
            self.assertEqual(reason2, "ENCODED_INSTEAD_OF_DECODED")

    def test_open_vocabulary_dynamic_morphisms_unhardcoded_cli_pipeline_offline(self) -> None:
        import hashlib
        import shutil

        if not all(shutil.which(t) for t in ("rev", "tac", "md5sum")):
            self.skipTest("rev, tac, or md5sum unavailable")

        store = EM.new_morphism_store()
        with tempfile.TemporaryDirectory() as td:
            root = pathlib.Path(td)

            # Learn 3 CLI tools that do NOT appear in _VERB_SPECS
            w1 = root / "w1"
            w1.mkdir()
            (w1 / "a.txt").write_text("abc\ndef\n", encoding="utf-8")
            self.assertEqual(
                EM.solve_with_epistemic_morphisms(
                    w1, "Use rev on a.txt and save to r.txt",
                    morphism_store=store, allow_web=True,
                    postcondition_fn=lambda d: ((d / "r.txt").read_text(encoding="utf-8") == "cba\nfed\n", "ok"),
                ).status,
                "VERIFIED",
            )

            w2 = root / "w2"
            w2.mkdir()
            (w2 / "b.txt").write_text("one\ntwo\n", encoding="utf-8")
            self.assertEqual(
                EM.solve_with_epistemic_morphisms(
                    w2, "Use tac on b.txt and save to t.txt",
                    morphism_store=store, allow_web=True,
                    postcondition_fn=lambda d: ((d / "t.txt").read_text(encoding="utf-8") == "two\none\n", "ok"),
                ).status,
                "VERIFIED",
            )

            w3 = root / "w3"
            w3.mkdir()
            (w3 / "c.txt").write_text("hello\n", encoding="utf-8")
            h_c = hashlib.md5(b"hello\n").hexdigest()
            self.assertEqual(
                EM.solve_with_epistemic_morphisms(
                    w3, "Use md5sum on c.txt and save to m.txt",
                    morphism_store=store, allow_web=True,
                    postcondition_fn=lambda d: (h_c in (d / "m.txt").read_text(encoding="utf-8"), "ok"),
                ).status,
                "VERIFIED",
            )

            # Unseen 3-step pipeline composed 100% OFFLINE
            w4 = root / "w4"
            w4.mkdir()
            (w4 / "story.txt").write_text("alpha\nbeta\ngamma\n", encoding="utf-8")
            expected_md5 = hashlib.md5(b"ammag\nateb\nahpla\n").hexdigest()
            r4 = EM.solve_with_epistemic_morphisms(
                w4,
                "Use rev on story.txt, then use tac, then use md5sum and save to digest.md5",
                morphism_store=store,
                allow_web=False,
                postcondition_fn=lambda d: (expected_md5 in (d / "digest.md5").read_text(encoding="utf-8"), "ok"),
            )
            self.assertEqual(r4.status, "VERIFIED")
            self.assertEqual(r4.mode, "ALL_TIER0_COMPOSED")
            self.assertEqual(r4.gaps_queried, [])
            self.assertEqual(r4.web_queries_made, 0)
            self.assertEqual(len(r4.steps_trace), 3)
            self.assertEqual(sorted(p.name for p in w4.iterdir()), ["digest.md5", "story.txt"])

    def test_zero_tool_name_environment_capability_discovery_and_offline_compose(self) -> None:
        import hashlib
        import shutil

        if not all(shutil.which(t) for t in ("rev", "md5sum")):
            self.skipTest("rev or md5sum unavailable")

        idx = EM.index_local_environment_tools()
        self.assertIn("rev", idx)
        self.assertIn("md5sum", idx)

        store = EM.new_morphism_store()
        with tempfile.TemporaryDirectory() as td:
            root = pathlib.Path(td)

            # Prompt NEVER names `md5sum`
            w1 = root / "w1"
            w1.mkdir()
            (w1 / "notes.txt").write_text("alpha\nbeta\n", encoding="utf-8")
            h1 = hashlib.md5(b"alpha\nbeta\n").hexdigest()
            r1 = EM.solve_with_epistemic_morphisms(
                w1,
                "Compute the MD5 checksum of notes.txt and save to sum.md5",
                morphism_store=store,
                allow_web=True,
                postcondition_fn=lambda d: (h1 in (d / "sum.md5").read_text(encoding="utf-8"), "ok"),
            )
            self.assertEqual(r1.status, "VERIFIED")
            self.assertEqual(r1.steps_trace[0]["tool"], "md5sum")

            # Prompt NEVER names `rev`
            w2 = root / "w2"
            w2.mkdir()
            (w2 / "notes.txt").write_text("hello\nworld\n", encoding="utf-8")
            r2 = EM.solve_with_epistemic_morphisms(
                w2,
                "Reverse lines characterwise of notes.txt and save to reversed.txt",
                morphism_store=store,
                allow_web=True,
                postcondition_fn=lambda d: ((d / "reversed.txt").read_text(encoding="utf-8") == "olleh\ndlrow\n", "ok"),
            )
            self.assertEqual(r2.status, "VERIFIED")
            self.assertEqual(r2.steps_trace[0]["tool"], "rev")

            # Unseen 2-step zero-tool-name pipeline composed 100% OFFLINE!
            w3 = root / "w3"
            w3.mkdir()
            (w3 / "doc.txt").write_text("abc\nxyz\n", encoding="utf-8")
            h3 = hashlib.md5(b"cba\nzyx\n").hexdigest()
            r3 = EM.solve_with_epistemic_morphisms(
                w3,
                "Reverse lines characterwise of doc.txt; then compute the MD5 checksum and save to doc.md5",
                morphism_store=store,
                allow_web=False,
                postcondition_fn=lambda d: (h3 in (d / "doc.md5").read_text(encoding="utf-8"), "ok"),
            )
            self.assertEqual(r3.status, "VERIFIED")
            self.assertEqual(r3.mode, "ALL_TIER0_COMPOSED")
            self.assertEqual(r3.gaps_queried, [])
            self.assertEqual(r3.web_queries_made, 0)
            self.assertEqual(sorted(p.name for p in w3.iterdir()), ["doc.md5", "doc.txt"])


if __name__ == "__main__":
    unittest.main()
