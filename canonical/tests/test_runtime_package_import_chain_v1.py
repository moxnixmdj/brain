import ast
import pathlib
import unittest

from canonical.runtime import auto_pypi_library_acquisition as pypi_acq
from canonical.runtime import capability_discovery
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

    def test_pypi_verifier_and_acquirer_use_canonical_runtime_siblings(self):
        self.assertEqual(
            pypi_verifier.pypi_acq.__name__,
            "canonical.runtime.auto_pypi_library_acquisition",
        )
        self.assertEqual(
            pypi_verifier.capability_discovery.__name__,
            "canonical.runtime.capability_discovery",
        )
        self.assertEqual(
            pypi_acq.capability_discovery.__name__,
            "canonical.runtime.capability_discovery",
        )
        self.assertIs(pypi_verifier.capability_discovery, capability_discovery)
        self.assertIs(pypi_acq.capability_discovery, capability_discovery)

    def test_astra_lazy_verifier_imports_are_package_qualified(self):
        runtime_path = (
            pathlib.Path(__file__).resolve().parents[1]
            / "runtime"
            / "astra_runtime.py"
        )
        tree = ast.parse(runtime_path.read_text(encoding="utf-8"))
        unqualified = set()
        canonical = set()
        targets = {
            "independent_pypi_codec_verifier",
            "independent_npm_codec_verifier",
        }
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    if alias.name in targets:
                        unqualified.add(alias.name)
            elif isinstance(node, ast.ImportFrom):
                if node.module == "canonical.runtime":
                    canonical.update(alias.name for alias in node.names if alias.name in targets)
        self.assertEqual(unqualified, set())
        self.assertEqual(canonical, targets)


if __name__ == "__main__":
    unittest.main(verbosity=2)
