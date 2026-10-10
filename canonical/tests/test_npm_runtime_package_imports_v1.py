from __future__ import annotations

import unittest


class NpmRuntimePackageImportTests(unittest.TestCase):
    def test_auto_npm_library_acquisition_imports_as_canonical_package(self):
        from canonical.runtime import auto_npm_library_acquisition as mod
        self.assertTrue(hasattr(mod, "_search_registry"))

    def test_independent_npm_codec_verifier_imports_as_canonical_package(self):
        from canonical.runtime import independent_npm_codec_verifier as mod
        self.assertTrue(hasattr(mod, "verify"))


if __name__ == "__main__":
    unittest.main(verbosity=2)
