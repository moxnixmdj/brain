# PROJECT_BRAIN auto-generated SMOKE scaffolds (python.tests.generate.scaffold.v1)
# Claims only: callable evaluates with deterministic derived fixtures.
import pathlib
import sys
import unittest

sys.path.insert(0, '/home/user/brain/canonical/astra_runtime/tmp/typed_sweep/python_tests_generate_scaffold_v1/swe_repo1022030989/src')


class GeneratedSmoke1(unittest.TestCase):
    def test_smoke_bench(self):
        from bench import bench
        result = bench()
        self.assertNotIsInstance(result, BaseException)


if __name__ == "__main__":
    unittest.main()
