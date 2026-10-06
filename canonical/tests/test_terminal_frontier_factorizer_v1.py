import importlib.util
import pathlib
import unittest

MODULE = pathlib.Path(__file__).resolve().parents[1] / "runtime" / "terminal_frontier_factorizer_v1.py"


class FrontierFactorizerTests(unittest.TestCase):
    def load(self):
        spec = importlib.util.spec_from_file_location("factorizer", MODULE)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod

    def test_repaired_global_basis_preserves_30_current_obligations(self):
        m = self.load()
        out = m.factorize()
        self.assertEqual(out["atomic_count"], 22)
        self.assertEqual(out["meta_count"], 8)
        self.assertEqual(out["truth_obligation_count"], 30)
        self.assertEqual(out["truth_obligations_deleted"], 2)

    def test_four_shared_interfaces_only(self):
        m = self.load()
        out = m.factorize()
        self.assertEqual(set(out["interfaces"]), {
            "TARGET_TUPLE_BINDING",
            "EXTERNAL_RESULT_OR_ACCESS",
            "UNIVERSAL_SCOPE_AND_COMPOSITION",
            "BEHAVIORAL_QUOTIENT_AND_TRANSFER",
        })

    def test_every_obligation_has_a_gate(self):
        m = self.load()
        out = m.factorize()
        self.assertEqual(len(out["obligation_interfaces"]), 30)
        self.assertTrue(all(v for v in out["obligation_interfaces"].values()))

    def test_no_credit_from_factorization(self):
        m = self.load()
        out = m.factorize()
        self.assertEqual(out["acceptance_credit_delta"], 0)
        self.assertEqual(out["ownership_credit_delta"], 0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
