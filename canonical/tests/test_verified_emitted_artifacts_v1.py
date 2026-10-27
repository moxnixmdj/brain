#!/usr/bin/env python3
"""A capability declares the artifact it really writes, and the graph chains it.

MEASURED 2026-10-27 on 65b7c26, before this file existed:

    73 bound capabilities, 96 effect tokens provided, 38 required
    85 of 96 provided tokens are consumed by NOTHING
    16 of 73 capabilities can take another capability's output
    25 capabilities "provide" their own name  (`docx.document.create.python_docx`
      provides `docx.document.create`) -- a label, not a type, so no consumer can
      ever unify with it

The archive pair is the measured example of the cost.  The registry itself says
`archive.tar_gz.create_from_manifest` is independently verified BY
`archive.verify.tar_gz.gnu`, and that verifier requires `archive.tar_gz.available`.
The producer never declared that token, so the edge did not exist:

    plan({'manifest.json.available'}, 'archive.tar_gz.verify_manifest_members')
      before: None
      after : ['archive.tar_gz.create_from_manifest', 'archive.verify.tar_gz.gnu']

Nothing in this file trusts the table.  Every row is re-proven here by running
the producer, re-reading the emitted bytes with the stdlib (independently of the
adapter that wrote them), and handing them to the consumer, which must report
`verified`.  The negative controls matter as much as the proof: a table row no
consumer can use must contribute nothing, and removing the row must remove the
edge -- otherwise the "gain" was never the row.
"""
from __future__ import annotations

import gzip
import hashlib
import importlib
import json
import pathlib
import shutil
import tarfile
import unittest

REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]

import sys

if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from canonical.runtime import capability_composer_v1 as composer  # noqa: E402
from canonical.runtime import live_brain_route_admission_v1 as ra  # noqa: E402

MANIFEST = "canonical/astra_runtime/tmp/ARCHIVE_VERIFY_MANIFEST.json"
CREATE = "archive.tar_gz.create_from_manifest"
VERIFY = "archive.verify.tar_gz.gnu"
EMITTED = "archive.tar_gz.available"
WORK = REPO_ROOT / "canonical/astra_runtime/tmp/verified_emits_unit"


def _registry():
    return composer.load_registry()


def _run(capability_id: str, **args):
    """Execute one bound adapter exactly the way the composer does."""
    entry = dict(_registry()[capability_id])
    entry.setdefault("capability_id", capability_id)
    payload = {"capability_id": capability_id}
    payload.update(args)
    return ra.run_adapter_locally(entry, {"args": payload})


def _manifest_paths():
    data = json.loads((REPO_ROOT / MANIFEST).read_text(encoding="utf-8"))
    paths = []
    for record in data.get("records") or []:
        paths.extend(record.get("verification_paths") or [])
    return paths


class TheProducerReallyEmitsThatType(unittest.TestCase):
    """The row is only allowed to exist if these hold."""

    def setUp(self):
        shutil.rmtree(WORK, ignore_errors=True)
        WORK.mkdir(parents=True, exist_ok=True)
        self.archive = "canonical/astra_runtime/tmp/verified_emits_unit/emitted.tar.gz"

    def tearDown(self):
        shutil.rmtree(WORK, ignore_errors=True)

    def test_the_table_names_the_token_the_consumer_requires(self):
        required = {t for entry in _registry().values()
                    for t in (entry.get("requires") or [])}
        for capability_id, row in composer.VERIFIED_EMITS_V1.items():
            for token in row["tokens"]:
                self.assertIn(token, required,
                              f"{capability_id} claims {token} but nothing requires it")

    def test_every_admitted_row_names_a_real_capability_and_consumer(self):
        registry = _registry()
        report = composer.verified_emits_report(registry)
        self.assertEqual(report["refused"], [], report["refused"])
        for capability_id, row in composer.VERIFIED_EMITS_V1.items():
            self.assertIn(capability_id, registry)
            self.assertIn(row["consumer"], registry)
            self.assertTrue(row["evidence"]["oracle"])

    def test_the_emitted_bytes_are_really_a_tar_gz(self):
        """Re-read the artifact with the stdlib, not with the adapter's report."""
        result = _run(CREATE, manifest_path=MANIFEST, output_path=self.archive)
        self.assertTrue(result.get("output_verified"), result)

        written = REPO_ROOT / self.archive
        raw = written.read_bytes()
        self.assertEqual(raw[:2], b"\x1f\x8b", "gzip magic missing")
        with gzip.open(written, "rb") as handle:
            self.assertTrue(handle.read(1), "gzip stream is empty")

        expected = set(_manifest_paths()) | {MANIFEST}
        with tarfile.open(written, "r:gz") as archive:
            members = {member.name for member in archive.getmembers()}
            self.assertEqual(members, expected, "member set is not the manifest's")
            for name in members:
                extracted = archive.extractfile(name).read()
                on_disk = (REPO_ROOT / name).read_bytes()
                self.assertEqual(
                    hashlib.sha256(extracted).hexdigest(),
                    hashlib.sha256(on_disk).hexdigest(),
                    f"{name} inside the archive is not the file on disk")

    def test_the_consumer_accepts_what_the_producer_wrote(self):
        """The edge is real because this runs, not because the table says so."""
        _run(CREATE, manifest_path=MANIFEST, output_path=self.archive)
        result = _run(VERIFY, manifest_path=MANIFEST, archive_path=self.archive)
        self.assertTrue(result.get("verified"), result)

    def test_a_tampered_archive_is_not_accepted(self):
        """Paired failing world: if this passes, the oracle is not reading bytes."""
        _run(CREATE, manifest_path=MANIFEST, output_path=self.archive)
        written = REPO_ROOT / self.archive
        with tarfile.open(written, "r:gz") as archive:
            buffers = {m.name: archive.extractfile(m).read()
                       for m in archive.getmembers()}
        with tarfile.open(written, "w:gz") as archive:
            for name, payload in buffers.items():
                bad = payload[:-1] + bytes([payload[-1] ^ 0xFF]) if payload else b"x"
                info = tarfile.TarInfo(name)
                info.size = len(bad)
                import io

                archive.addfile(info, io.BytesIO(bad))
        with self.assertRaises(Exception) as caught:
            _run(VERIFY, manifest_path=MANIFEST, archive_path=self.archive)
        self.assertIn("MISMATCH", str(caught.exception).upper()
                      + str(getattr(caught.exception, "code", "")).upper())


class TheGraphChainsWhatTheEvidenceCertifies(unittest.TestCase):
    def test_the_planner_now_finds_the_two_step_chain(self):
        declared = composer.graph(use_verified=False)
        self.assertIsNone(
            composer.plan({"manifest.json.available"},
                          "archive.tar_gz.verify_manifest_members", declared),
            "the declared graph already chained these; the row proves nothing")
        chained = composer.graph()
        self.assertEqual(
            composer.plan({"manifest.json.available"},
                          "archive.tar_gz.verify_manifest_members", chained),
            [CREATE, VERIFY])

    def test_the_edge_comes_from_the_row_and_from_nothing_else(self):
        empty = composer.graph(verified={})
        self.assertNotIn("archive.tar_gz.available",
                         empty[CREATE]["provides"])
        self.assertIsNone(
            composer.plan({"manifest.json.available"},
                          "archive.tar_gz.verify_manifest_members", empty))

    def test_forward_closure_reaches_the_verifier_only_because_of_the_row(self):
        seed = ["manifest.json.available"]
        order, _ = composer.forward_closure(seed, composer.graph())
        self.assertIn(CREATE, order)
        self.assertIn(VERIFY, order)
        declared, _ = composer.forward_closure(seed, composer.graph(use_verified=False))
        self.assertIn(CREATE, declared)
        self.assertNotIn(VERIFY, declared)


class ADeclarationNobodyCanUseIsRefused(unittest.TestCase):
    """Fail-closed: decoration never enters the graph."""

    def test_a_token_no_consumer_requires_is_refused(self):
        registry = _registry()
        table = {CREATE: {"tokens": ["archive.tar_gz.nobody_wants_this"],
                          "consumer": VERIFY,
                          "evidence": {"oracle": "x"}}}
        report = composer.verified_emits_report(registry, table)
        self.assertEqual(report["admitted"], {})
        self.assertEqual(report["refused"][0]["reason"], "TOKEN_NO_CONSUMER")

    def test_a_row_without_an_oracle_is_refused(self):
        registry = _registry()
        table = {CREATE: {"tokens": [EMITTED], "consumer": VERIFY, "evidence": {}}}
        report = composer.verified_emits_report(registry, table)
        self.assertEqual(report["admitted"], {})
        self.assertEqual(report["refused"][0]["reason"], "NO_EXECUTION_EVIDENCE")

    def test_a_row_for_an_unknown_capability_is_refused(self):
        registry = _registry()
        table = {"archive.not.a.capability": {"tokens": [EMITTED],
                                              "consumer": VERIFY,
                                              "evidence": {"oracle": "x"}}}
        report = composer.verified_emits_report(registry, table)
        self.assertEqual(report["admitted"], {})
        self.assertEqual(report["refused"][0]["reason"], "CAPABILITY_NOT_IN_REGISTRY")


if __name__ == "__main__":
    unittest.main()
