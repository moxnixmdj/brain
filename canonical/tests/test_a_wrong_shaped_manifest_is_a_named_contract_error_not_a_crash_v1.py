"""A wrong-shaped manifest is a named contract error, not an uncaught traceback.

The tar.gz producer and its GNU-tar verifier both read a manifest as
``manifest.get("records")``.  Both validate the input PATHS carefully
(``MANIFEST_INPUT_REQUIRED``, ``TAR_GZ_OUTPUT_REQUIRED``) and neither validated the
STRUCTURE, so a manifest whose top level is a bare JSON array -- the first shape a
caller reaches for -- died with::

    AttributeError: 'list' object has no attribute 'get'
        archive_verify_gnu_tar.py:15, in _manifest_paths

Reproduced live through ``solve()`` on 911cc62 as ``archive.verify.tar_gz.gnu`` with
``failure_class = LIVE_CONTROLLER_EXECUTION_OR_VERIFICATION_FAILURE`` and the
AttributeError buried in the reason: the caller got a Python traceback where every
other rejection in the same file gives a name.

Measured across the adapter layer: 18 of 92 bound-capability adapters call ``.get()``
on a parsed JSON document with no ``isinstance`` guard.  These two are the pair with
a reproduced crash on the live path.

``records`` absent or null stays legal and yields no paths, exactly as before, and a
genuinely mismatched archive still reports ``ARCHIVE_MEMBER_SET_MISMATCH``.
"""
import importlib.util
import json
import pathlib
import tarfile
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[2]
WORK = ROOT / "canonical/astra_runtime/tmp/manifest_shape_probe"
REL = "canonical/astra_runtime/tmp/manifest_shape_probe"


def _load(name):
    path = ROOT / "canonical/runtime/bound_capabilities" / ("%s.py" % name)
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class WrongShapedManifestIsANamedErrorTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        WORK.mkdir(parents=True, exist_ok=True)
        (WORK / "list_manifest.json").write_text(
            json.dumps([{"path": "sample.txt", "sha256": "x"}]))
        (WORK / "dict_manifest.json").write_text(
            json.dumps({"records": [{"verification_paths": []}]}))
        (WORK / "nullrec_manifest.json").write_text(json.dumps({"records": None}))
        (WORK / "badrec_manifest.json").write_text(json.dumps({"records": ["nope"]}))
        (WORK / "sample.txt").write_text("hello\n")
        with tarfile.open(WORK / "a.tar.gz", "w:gz") as tar:
            tar.add(WORK / "sample.txt", arcname="sample.txt")

    def _run(self, module, manifest, **extra):
        args = {"manifest_path": "%s/%s" % (REL, manifest)}
        args.update(extra)
        return module.run(args, str(ROOT))

    def test_producer_names_the_contract_instead_of_crashing(self):
        with self.assertRaises(RuntimeError) as ctx:
            self._run(_load("archive_tarfile"), "list_manifest.json",
                      output_path="%s/a.tar.gz" % REL)
        self.assertEqual(str(ctx.exception), "MANIFEST_RECORDS_REQUIRED")

    def test_verifier_names_the_contract_instead_of_crashing(self):
        with self.assertRaises(RuntimeError) as ctx:
            self._run(_load("archive_verify_gnu_tar"), "list_manifest.json",
                      archive_path="%s/a.tar.gz" % REL)
        self.assertEqual(str(ctx.exception), "MANIFEST_RECORDS_REQUIRED")

    def test_the_hazard_is_real_and_the_guard_is_what_stops_it(self):
        """Names the underlying hazard without asserting the shipped function is
        broken.  A list genuinely has no .get, which is why the old body died with
        AttributeError; the guard is what converts that into a name.  If someone
        removes the guard this still passes on the first assert and fails on the
        second, which is the point."""
        with self.assertRaises(AttributeError):
            [{"path": "x"}].get("records")
        for module in (_load("archive_tarfile"), _load("archive_verify_gnu_tar")):
            with self.assertRaises(RuntimeError) as ctx:
                module._manifest_paths([{"path": "x"}])
            self.assertEqual(str(ctx.exception), "MANIFEST_RECORDS_REQUIRED")

    def test_a_records_free_manifest_is_still_legal(self):
        """No regression on the shapes that always worked."""
        for manifest in ("dict_manifest.json", "nullrec_manifest.json"):
            self.assertEqual(_load("archive_tarfile")._manifest_paths(
                json.loads((WORK / manifest).read_text())), [])

    def test_a_record_that_is_not_a_mapping_is_also_named(self):
        with self.assertRaises(RuntimeError) as ctx:
            _load("archive_tarfile")._manifest_paths({"records": ["nope"]})
        self.assertEqual(str(ctx.exception), "MANIFEST_RECORDS_REQUIRED")

    def test_the_two_adapters_still_agree_on_the_shape(self):
        """They are a producer/verifier pair; if one accepts a shape the other
        rejects, nothing the producer makes can ever be verified."""
        producer = _load("archive_tarfile")
        verifier = _load("archive_verify_gnu_tar")
        for payload in ([{"path": "x"}], {"records": None}, {"records": []},
                        {"records": [{"verification_paths": ["canonical/x.py"]}]}):
            try:
                left = producer._manifest_paths(payload)
            except Exception as exc:            # noqa: BLE001
                left = type(exc).__name__ + ":" + str(exc)
            try:
                right = verifier._manifest_paths(payload)
            except Exception as exc:            # noqa: BLE001
                right = type(exc).__name__ + ":" + str(exc)
            self.assertEqual(left, right, "producer and verifier disagree on %r" % (payload,))

    def test_a_real_archive_still_verifies(self):
        """The fix must not turn the working path into a refusal."""
        (WORK / "self_manifest.json").write_text(json.dumps({"records": []}))
        with tarfile.open(WORK / "self.tar.gz", "w:gz") as tar:
            tar.add(WORK / "self_manifest.json",
                    arcname="%s/self_manifest.json" % REL)
        result = _load("archive_verify_gnu_tar").run(
            {"manifest_path": "%s/self_manifest.json" % REL,
             "archive_path": "%s/self.tar.gz" % REL}, str(ROOT))
        self.assertIs(result.get("verified"), True)


if __name__ == "__main__":
    unittest.main(verbosity=2)
