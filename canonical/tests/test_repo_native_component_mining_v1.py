"""Pure checks for repository-native operand harvesting."""
import pathlib
import sys
import tempfile
import textwrap
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "canonical" / "swe_kernel"))

import repo_native_component_mining_v1 as mine  # noqa: E402


class MiningTests(unittest.TestCase):
    def test_symbols_include_class_methods_and_constants(self):
        source = textwrap.dedent('''
            LIMIT = 3
            def helper(x): return x
            class Box:
                def drive(self): return True
        ''')
        found = mine.symbols(source)
        self.assertIn("LIMIT", found)
        self.assertIn("helper", found)
        self.assertIn("Box.drive", found)

    def test_package_modules_exclude_the_target(self):
        with tempfile.TemporaryDirectory() as where:
            tree = pathlib.Path(where)
            (tree / "pkg").mkdir()
            (tree / "pkg" / "__init__.py").write_text("")
            (tree / "pkg" / "target.py").write_text("x=1\n")
            (tree / "pkg" / "sibling.py").write_text("class C: pass\n")
            found = mine.package_modules(tree, "pkg/target.py")
            self.assertIn("pkg.sibling", found)
            self.assertNotIn("pkg.target", found)

    def test_add_import_goes_after_future_import(self):
        source = '"""doc"""\nfrom __future__ import annotations\n\nx = 1\n'
        patched = mine.add_import(source, "pkg.sibling", "C")
        self.assertIn("from pkg.sibling import C as _brain_mined", patched)
        self.assertLess(patched.index("from __future__"), patched.index("from pkg.sibling"))

    def test_sibling_values_uses_only_the_same_parametrized_table(self):
        source = textwrap.dedent('''
            import pytest
            @pytest.mark.parametrize("x", ["a", "b", "c"])
            def test_x(x): pass
        ''')
        values = mine.sibling_values(source, ["tests/test_x.py::test_x[b]"])
        self.assertEqual(sorted(v for v in values if isinstance(v, str)), ["a", "c"])


if __name__ == "__main__":
    unittest.main()


class AcquisitionTests(unittest.TestCase):
    def test_contrast_splits_pytest_parameters_without_id_parsing(self):
        import pytest_contrast_acquisition_v1 as acq
        params = {
            "tests/test_x.py::test_x[custom-id-a]": {"value": "'a'", "flag": "True"},
            "tests/test_x.py::test_x[custom-id-b]": {"value": "'b'", "flag": "False"},
        }
        row = acq.contrast(params, ["tests/test_x.py::test_x[custom-id-a]"])
        self.assertIn("a", row["failing"])
        self.assertIn("b", row["passing"])
        self.assertNotIn("a", row["passing"])
        self.assertEqual(row["parameters"], ["value"])
