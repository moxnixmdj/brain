import unittest

from canonical.runtime import independent_npm_codec_verifier as verifier


class RuntimePackageImportChainV1Tests(unittest.TestCase):
    def test_npm_verifier_uses_canonical_runtime_siblings(self):
        self.assertEqual(
            verifier.npm_acq.__name__,
            "canonical.runtime.auto_npm_library_acquisition",
        )
        self.assertEqual(
            verifier.astra_runtime.__name__,
            "canonical.runtime.astra_runtime",
        )
        self.assertEqual(
            verifier.npm_package_utils.__name__,
            "canonical.runtime.npm_package_utils",
        )
        self.assertIs(
            verifier.npm_acq.npm_package_utils,
            verifier.npm_package_utils,
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
