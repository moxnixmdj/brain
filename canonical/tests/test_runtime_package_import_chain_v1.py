import unittest

from canonical.runtime import independent_npm_codec_verifier as npm_verifier
from canonical.runtime import independent_pypi_codec_verifier as pypi_verifier


class RuntimePackageImportChainV1Tests(unittest.TestCase):
    def test_npm_verifier_uses_canonical_runtime_siblings(self):
        self.assertEqual(
            npm_verifier.npm_acq.__name__,
            "canonical.runtime.auto_npm_library_acquisition",
        )
        self.assertEqual(
            npm_verifier.astra_runtime.__name__,
            "canonical.runtime.astra_runtime",
        )
        self.assertEqual(
            npm_verifier.npm_package_utils.__name__,
            "canonical.runtime.npm_package_utils",
        )
        self.assertIs(
            npm_verifier.npm_acq.npm_package_utils,
            npm_verifier.npm_package_utils,
        )

    def test_pypi_verifier_uses_canonical_runtime_siblings(self):
        self.assertEqual(
            pypi_verifier.pypi_acq.__name__,
            "canonical.runtime.auto_pypi_library_acquisition",
        )
        self.assertEqual(
            pypi_verifier.capability_discovery.__name__,
            "canonical.runtime.capability_discovery",
        )
        self.assertIs(
            pypi_verifier.pypi_acq.capability_discovery,
            pypi_verifier.capability_discovery,
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
