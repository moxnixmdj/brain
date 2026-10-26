#!/usr/bin/env python3
"""Tests for bridge_enumeration_v1 -- the machine-derived verified bridge table.

Standing rule for this file: every passing world is paired with the nearest world
in which it must fail.  The enumeration is judged by re-running its claims against
the world's bytes, not by trusting its rows; tampering with the source fixture after
a real archive is produced must make the consumer refuse.  Nothing is skipped to be
kind: environment-gated producers are asserted absent-or-classified, never silently
present.
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
import pathlib
import shutil
import sys
import tarfile
import tempfile
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from canonical.runtime import bridge_enumeration_v1 as be  # noqa: E402


def _have_yaml():
    return importlib.util.find_spec("yaml") is not None or shutil.which("yq") is not None


def _have_xlsxwriter():
    return importlib.util.find_spec("xlsxwriter") is not None


def _have_tar():
    return shutil.which("tar") is not None


class _EnumerationBase(unittest.TestCase):
    # One paid enumeration per class: the candidates execute for real, so a second
    # run is a determinism check, not a way to amortize the first into decoration.
    @classmethod
    def setUpClass(cls):
        cls.scratch = ROOT / "canonical" / "runtime" / "state" / f"tmp_test_bridge_enum_{cls.__name__}"
        shutil.rmtree(cls.scratch, ignore_errors=True)
        cls.report = be.enumerate_bridges(scratch=cls.scratch)
        cls.report2 = be.enumerate_bridges(scratch=cls.scratch)

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.scratch, ignore_errors=True)

    def rows(self):
        return {(r["capability"], r["emits_type"]) for r in self.report["emits_verified"]}

    def bridge_rows(self):
        return {(b["producer"], b["emits_type"], b["consumer"], b["satisfies"])
                for b in self.report["bridge_verified"]}


class ArchiveBridgeTests(_EnumerationBase):
    def test_archive_create_to_verify_bridge_is_derived_by_execution(self):
        row = ("archive.tar_gz.create_from_manifest", "tar.gz",
               "archive.verify.tar_gz.gnu", "archive.tar_gz.available")
        if _have_tar():
            self.assertIn(row, self.bridge_rows(),
                          "the archive bridge must be derived wherever tar exists")
        else:
            self.assertNotIn(row, self.bridge_rows())
    def test_the_emitted_archive_contains_exactly_the_declared_world(self):
        # the container on disk is from the LAST enumeration (gzip embeds mtime),
        # so byte-level file claims are checked against report2's row
        rows = [r for r in self.report2["emits_verified"]
                if r["capability"] == "archive.tar_gz.create_from_manifest"]
        self.assertEqual(len(rows), 1, "the archive producer must emit exactly one real type")
        artifact = ROOT / rows[0]["artifact"]
        declared = set(rows[0].keys())
        self.assertIn("artifact_sha256", declared)
        member_bytes = {}
        with tarfile.open(artifact, "r:gz") as tf:
            for m in tf.getmembers():
                if m.isfile():
                    member_bytes[m.name.rstrip("/")] = tf.extractfile(m).read()
        manifest = json.loads((self.scratch / "fixtures" / "manifest.json").read_text())
        listed = {str((self.scratch / "fixtures" / "manifest.json").relative_to(ROOT))}
        for record in manifest["records"]:
            listed.update(record["verification_paths"])
        self.assertEqual(set(member_bytes), listed,
                         "archive members must equal the manifest's world, nothing extra")
        for rel, data in member_bytes.items():
            src = (ROOT / rel).read_bytes()
            self.assertEqual(hashlib.sha256(data).hexdigest(),
                             hashlib.sha256(src).hexdigest(),
                             f"member {rel} must byte-match the source world")
        # the reported digest must be of these bytes, not of a claim about them
        self.assertEqual(rows[0]["artifact_sha256"],
                         hashlib.sha256(artifact.read_bytes()).hexdigest())


class TamperWorldTests(_EnumerationBase):
    def test_tampered_source_breaks_the_bridge(self):
        if not _have_tar():
            self.skipTest("no tar executable: the paired failure world needs the consumer")
        rows = [r for r in self.report["emits_verified"]
                if r["capability"] == "archive.tar_gz.create_from_manifest"]
        self.assertEqual(len(rows), 1)
        artifact = rows[0]["artifact"]
        sys.path.insert(0, str(ROOT))
        from canonical.runtime import live_brain_route_admission_v1 as ra
        reg = json.loads((ROOT / be.DEFAULT_REGISTRY).read_text())["capabilities"]
        centry = reg["archive.verify.tar_gz.gnu"]
        manifest_rel = str((self.scratch / "fixtures" / "manifest.json").relative_to(ROOT))
        good = {"type": "invoke_capability",
                "args": {"archive_path": artifact, "manifest_path": manifest_rel,
                         "timeout_s": 8},
                "expect": (centry.get("action_template") or {}).get("expect")}
        ra.run_adapter_locally(centry, good)  # passing world
        # nearest failing world: the source moved after the archive was sealed
        (self.scratch / "fixtures" / "a.txt").write_text("tampered\n", "utf-8")
        with self.assertRaises(Exception) as ctx:
            ra.run_adapter_locally(centry, good)
        self.assertIn("ARCHIVE_HASH_MISMATCH", str(ctx.exception),
                      "hash-verified archive world must fail when sources move")


class OracleDisciplineTests(_EnumerationBase):
    def test_every_emits_row_reproves_its_claim_from_bytes(self):
        self.assertGreater(len(self.report["emits_verified"]), 8,
                           "the enumeration must find real rows in a healthy tree")
        for r in self.report["emits_verified"]:
            self.assertTrue(be.oracle_bytes_of(r["emits_type"], ROOT, r["artifact"]),
                            f"{r['capability']} claimed {r['emits_type']}; bytes disagree")
    def test_no_type_laundering_rows_survive(self):
        rows = self.rows()
        impossible = [
            ("json.file.write", "pdf"), ("json.file.write", "png"),
            ("json.file.write", "tar.gz"), ("json.file.write", "sqlite"),
            ("json.file.write", "xlsx"), ("json.file.write", "docx"),
            ("text.file.write", "pdf"), ("text.file.write", "png"),
            ("text.file.write", "tar.gz"), ("text.file.write", "sqlite"),
            ("text.file.write", "xlsx"), ("text.file.write", "docx"),
            ("text.file.write", "json"),
            ("yaml.to_json.yq", "pdf"), ("yaml.to_json.yq", "yaml"),
            ("yaml.to_json.yq", "xlsx"), ("yaml.to_json.yq", "docx"),
            ("archive.tar_gz.create_from_manifest", "json"),
            ("archive.tar_gz.create_from_manifest", "xlsx"),
            ("xlsx.table.create_from_json_records", "docx"),
            ("sqlite.table.create_from_json_records", "xlsx"),
        ]
        for pair in impossible:
            self.assertNotIn(pair, rows, f"{pair} is a laundering row and must not survive")
        # a refused row is either oracle-caught (TYPE_MISMATCH) or adapter-caught
        # (ADAPTER_REFUSED -- the writer refused the extension itself, an even
        # stronger proof); both are classified refusals, never silent absence
        refused = {(f["capability"], f["type"]) for f in self.report["failures"]
                   if f["class"] in ("TYPE_MISMATCH", "ADAPTER_REFUSED")}
        must_be_caught = {("json.file.write", "pdf"), ("text.file.write", "json"),
                          ("yaml.to_json.yq", "xlsx"),
                          ("archive.tar_gz.create_from_manifest", "pdf")}
        missing = must_be_caught - refused
        self.assertEqual(missing, set(),
                         f"impossible rows that were never refused confuse absence with silence: {missing}")

    def test_xlsx_writer_never_impersonates_a_document(self):
        if not _have_xlsxwriter():
            self.assertFalse(any(r["capability"] == "xlsx.table.create_from_json_records"
                                 for r in self.report["emits_verified"]),
                             "an unrunnable producer must emit no rows")
            return
        rows = [r["emits_type"] for r in self.report["emits_verified"]
                if r["capability"] == "xlsx.table.create_from_json_records"]
        self.assertEqual(rows, ["xlsx"], f"xlsx writer must emit exactly xlsx, got {rows}")


class EnvironmentHonestyTests(_EnumerationBase):
    def test_unrunnable_producers_are_classified_not_credited(self):
        reg = json.loads((ROOT / be.DEFAULT_REGISTRY).read_text())["capabilities"]
        imported_missing = set()
        for cid, entry in reg.items():
            src = entry.get("source") or {}
            mods = src.get("modules") or []
            if mods and any(importlib.util.find_spec(str(m).split(".")[0]) is None
                            for m in mods):
                if "output_path" in ((entry.get("action_template") or {}).get("args") or {}):
                    imported_missing.add(cid)
        emitted = {r["capability"] for r in self.report["emits_verified"]}
        lying = imported_missing & emitted
        self.assertEqual(lying, set(),
                         f"producers whose declared modules cannot import must not emit: {lying}")
    def test_yaml_rows_exist_exactly_where_a_yaml_engine_exists(self):
        rows = self.rows()
        yaml_row = ("yaml.to_json.yq", "json")
        if _have_yaml():
            self.assertIn(yaml_row, rows)
        else:
            self.assertNotIn(yaml_row, rows)


class ReportHonestyTests(_EnumerationBase):
    def test_report_fields_fail_closed(self):
        self.assertEqual(self.report["authority"], "NONE")
        self.assertEqual(self.report["capability_credit"], 0)
        self.assertEqual(self.report["incremental_spend_usd"], 0)
        self.assertEqual(self.report["producer_cognition_model_dependency_count"], 0)
        c = self.report["counts"]
        self.assertEqual(c["registry_entries"], 73)  # the registry under test, exactly
        self.assertEqual(c["emits_verified"], len(self.report["emits_verified"]))
        self.assertEqual(c["bridge_verified"], len(self.report["bridge_verified"]))
    def test_deterministic_on_one_environment(self):
        self.assertEqual(self.rows(), { (r["capability"], r["emits_type"])
                                        for r in self.report2["emits_verified"]})
        self.assertEqual(self.bridge_rows(), {(b["producer"], b["emits_type"],
                                               b["consumer"], b["satisfies"])
                                              for b in self.report2["bridge_verified"]})


class FailClosedRegistryTests(unittest.TestCase):
    def test_a_garbage_adapter_is_refused_and_the_rest_still_enumerate(self):
        scratch = ROOT / "canonical" / "runtime" / "state" / "tmp_test_bridge_enum_garbage"
        shutil.rmtree(scratch, ignore_errors=True)
        try:
            reg = json.loads((ROOT / be.DEFAULT_REGISTRY).read_text())
            cid = "archive.tar_gz.create_from_manifest"
            reg["capabilities"]["garbage.broken.adapter"] = {
                "adapter_module": "does_not_exist_anywhere_v9",
                "status": "VERIFIED_BOUND_CAPABILITY",
                "provides": ["garbage"], "requires": [],
                "incremental_spend_usd": 0,
                "action_template": {"type": "invoke_capability",
                                    "args": {"capability_id": "garbage.broken.adapter",
                                             "output_path": "${input.output_path}"}},
            }
            reg_path = str((scratch / "reg.json").relative_to(ROOT))
            scratch.mkdir(parents=True, exist_ok=True)
            (scratch / "reg.json").write_text(json.dumps(reg))
            report = be.enumerate_bridges(reg_path, scratch=scratch)
            bad = [f for f in report["failures"] if f["capability"] == "garbage.broken.adapter"]
            self.assertTrue(bad, "the broken adapter must appear as a classified failure")
            self.assertTrue(all(f["class"] == "ADAPTER_REFUSED" for f in bad))
            self.assertNotIn("garbage.broken.adapter",
                             {r["capability"] for r in report["emits_verified"]})
            self.assertIn(("archive.tar_gz.create_from_manifest", "tar.gz"),
                          {(r["capability"], r["emits_type"])
                           for r in report["emits_verified"]},
                          "one broken entry must not sink the enumeration")
        finally:
            shutil.rmtree(scratch, ignore_errors=True)


if __name__ == "__main__":
    unittest.main()
