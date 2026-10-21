"""An apt-declared pure-Python dependency may fall back to a pinned wheel.

Three capabilities were declared against Debian packages that are nothing more
than a pure-Python library in a .deb -- ``python3-xlsxwriter``,
``python3-docx``, ``python3-openpyxl``. On a host whose apt metadata does not
carry that exact name/version/sha256 the gate correctly refused, and the
capability was unusable even though the identical code is a published,
hash-pinned wheel that the runtime already knows how to acquire and verify for
its ``pypi``-typed capabilities.

Measured: with the fallback in place, ``Create an xlsx table from JSON records``
goes from ``BOUND_APT_METADATA_NOT_FOUND:python3-xlsxwriter`` to passing end to
end, taking goals that execute from 8 of 23 to 9 of 23.

The fallback is deliberately narrow, and these tests pin every edge of it.
"""

import json
import pathlib
import unittest

REPO_ROOT=pathlib.Path(__file__).resolve().parents[2]

import sys
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0,str(REPO_ROOT))

from canonical.runtime import astra_runtime as ar  # noqa: E402

REGISTRY=json.loads(
    (REPO_ROOT/"canonical/runtime/BOUND_CAPABILITY_REGISTRY_V1.json").read_text(encoding="utf-8")
)
CAPS=REGISTRY["capabilities"]

APT_WITH_FALLBACK=[
    "xlsx.table.create_from_json_records",
    "docx.document.create_from_json_record",
    "xlsx.table.verify_against_json_records",
]

GOOD_FALLBACK={
    "project":"xlsxwriter",
    "version":"3.2.9",
    "wheel_filename":"xlsxwriter-3.2.9-py3-none-any.whl",
    "wheel_sha256":"9a5db42bc5dff014806c58a20b9eae7322a134abb6fce3c92c181bfb275ec5b3",
    "metadata_url":"https://pypi.org/pypi/xlsxwriter/3.2.9/json",
}


def _apt_source(**extra):
    src={
        "type":"apt",
        "packages":[{"name":"python3-xlsxwriter","version":"3.1.9-1","sha256":"a"*64}],
    }
    src.update(extra)
    return src


class AFallbackOnlyFiresWhenThePackageIsAbsentFromThisHost(unittest.TestCase):
    def test_no_fallback_declared_behaves_exactly_as_before(self):
        with self.assertRaises(ar.Blocker) as ctx:
            ar._apt_then_pinned_pypi_fallback({},_apt_source())
        self.assertTrue(str(ctx.exception).startswith("BOUND_APT_METADATA_NOT_FOUND"))

    def test_an_integrity_failure_never_falls_back(self):
        # A package that IS in the metadata but hashes differently is an
        # integrity event. Serving a wheel instead would hide it.
        def boom(source):
            raise ar.Blocker("BOUND_APT_PACKAGE_HASH_MISMATCH:python3-xlsxwriter")
        original=ar._ensure_apt_dependencies
        ar._ensure_apt_dependencies=boom
        try:
            with self.assertRaises(ar.Blocker) as ctx:
                ar._apt_then_pinned_pypi_fallback({},_apt_source(pypi_fallback=dict(GOOD_FALLBACK)))
            self.assertIn("HASH_MISMATCH",str(ctx.exception))
        finally:
            ar._ensure_apt_dependencies=original

    def test_an_incomplete_fallback_is_refused_not_guessed(self):
        partial={k:v for k,v in GOOD_FALLBACK.items() if k!="wheel_sha256"}
        def boom(source):
            raise ar.Blocker("BOUND_APT_METADATA_NOT_FOUND:python3-xlsxwriter")
        original=ar._ensure_apt_dependencies
        ar._ensure_apt_dependencies=boom
        try:
            with self.assertRaises(ar.Blocker) as ctx:
                ar._apt_then_pinned_pypi_fallback({},_apt_source(pypi_fallback=partial))
            self.assertEqual(str(ctx.exception),"BOUND_PYPI_SOURCE_INCOMPLETE")
        finally:
            ar._ensure_apt_dependencies=original

    def test_the_fallback_labels_its_own_provenance(self):
        def boom(source):
            raise ar.Blocker("BOUND_APT_METADATA_NOT_FOUND:python3-xlsxwriter")
        sentinel={"status":"INSTALLED_VERIFIED","project":"xlsxwriter","version":"3.2.9"}
        original_apt=ar._ensure_apt_dependencies
        original_pypi=ar._ensure_pypi_dependency
        ar._ensure_apt_dependencies=boom
        ar._ensure_pypi_dependency=lambda source: dict(sentinel)
        try:
            out=ar._apt_then_pinned_pypi_fallback({},_apt_source(pypi_fallback=dict(GOOD_FALLBACK)))
        finally:
            ar._ensure_apt_dependencies=original_apt
            ar._ensure_pypi_dependency=original_pypi
        self.assertEqual(
            out["acquired_via"],
            "PINNED_PYPI_FALLBACK_FOR_APT_DECLARED_PURE_PYTHON_PACKAGE",
        )
        self.assertEqual(out["apt_package_declared"],"python3-xlsxwriter")
        self.assertEqual(out["status"],"INSTALLED_VERIFIED")


class TheRegistryDeclarationsAreCompleteAndPinned(unittest.TestCase):
    def test_the_three_pure_python_capabilities_declare_a_full_pinned_wheel(self):
        for cid in APT_WITH_FALLBACK:
            with self.subTest(capability=cid):
                src=CAPS[cid]["source"]
                self.assertEqual(src["type"],"apt")
                fb=src.get("pypi_fallback")
                self.assertIsInstance(fb,dict,cid)
                for key in ("project","version","wheel_filename","wheel_sha256","metadata_url"):
                    self.assertTrue(str(fb.get(key) or "").strip(),f"{cid}:{key}")
                self.assertEqual(len(fb["wheel_sha256"]),64,cid)
                int(fb["wheel_sha256"],16)  # raises if not hex
                self.assertTrue(fb["metadata_url"].startswith("https://pypi.org/pypi/"),cid)
                self.assertTrue(fb["wheel_filename"].endswith(".whl"),cid)

    def test_no_other_apt_capability_was_touched(self):
        # The other apt capabilities are real C binaries; there is no wheel to
        # fall back to and none may be invented.
        for cid,entry in CAPS.items():
            src=entry.get("source") or {}
            if src.get("type")!="apt" or cid in APT_WITH_FALLBACK:
                continue
            with self.subTest(capability=cid):
                self.assertNotIn("pypi_fallback",src)

    def test_the_apt_declaration_is_still_the_primary_claim(self):
        for cid in APT_WITH_FALLBACK:
            with self.subTest(capability=cid):
                src=CAPS[cid]["source"]
                self.assertEqual(src["type"],"apt")
                pkgs=src.get("packages")
                self.assertIsInstance(pkgs,list)
                self.assertTrue(pkgs)
                self.assertEqual(len(pkgs[0]["sha256"]),64)


class TheDispatchUsesTheFallback(unittest.TestCase):
    def test_the_apt_branch_calls_the_fallback_helper(self):
        import inspect
        src=inspect.getsource(ar)
        self.assertIn("_apt_then_pinned_pypi_fallback(entry,source)",src)
        # apt must still be tried first, inside the helper
        helper=inspect.getsource(ar._apt_then_pinned_pypi_fallback)
        self.assertLess(
            helper.index("_ensure_apt_dependencies(source)"),
            helper.index('_ensure_pypi_dependency(fallback)'),
        )


if __name__=="__main__":
    unittest.main()
