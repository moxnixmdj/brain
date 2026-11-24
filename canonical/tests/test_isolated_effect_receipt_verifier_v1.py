"""Integrity tests only; no carrier, trusted collector or independent attestation."""
import copy
import unittest

from canonical.tools import isolated_effect_receipt_verifier_v1 as v


class ReceiptBytesTests(unittest.TestCase):
    def setUp(self):
        self.patch = b'diff --git a/x.py b/x.py\n--- a/x.py\n+++ b/x.py\n@@ -1 +1 @@\n-a\n+b\n'
        self.effects = {"repair.patch": self.patch, "report.json": b'{"result":"ok"}'}
        self.receipt = {
            "schema": v.SCHEMA, "base_commit": "a" * 40, "policy_sha256": "b" * 64,
            "effects": {p: {"sha256": v.digest_bytes(data), "size": len(data)}
                        for p, data in self.effects.items()},
        }
        self.expect = {"expected_receipt_sha256": v.receipt_digest(self.receipt),
                       "expected_base_commit": "a" * 40, "expected_policy_sha256": "b" * 64,
                       "expected_patch_path": "repair.patch",
                       "expected_effect_paths": ("repair.patch", "report.json")}

    def check(self, receipt=None, effects=None, **updates):
        return v.verify_patch(self.receipt if receipt is None else receipt,
                              self.effects if effects is None else effects,
                              **{**self.expect, **updates})

    def test_exact_patch_bytes_are_returned(self):
        self.assertEqual(self.check(), self.patch)
        self.assertEqual(v.digest_bytes(self.check()), self.receipt['effects']['repair.patch']['sha256'])

    def test_effect_bytes_tampering_is_refused(self):
        effects = dict(self.effects, **{'report.json': b'{"result":"NO"}'})
        with self.assertRaisesRegex(v.ReceiptRefused, 'EFFECT_DIGEST_MISMATCH'):
            self.check(effects=effects)

    def test_patch_bytes_tampering_is_refused(self):
        effects = dict(self.effects, **{'repair.patch': self.patch.replace(b'+b', b'+c')})
        with self.assertRaisesRegex(v.ReceiptRefused, 'EFFECT_DIGEST_MISMATCH'):
            self.check(effects=effects)

    def test_effect_path_tampering_is_refused(self):
        receipt = copy.deepcopy(self.receipt)
        receipt['effects']['other.patch'] = receipt['effects'].pop('repair.patch')
        # Even a rehashed receipt cannot change an independently expected path set.
        with self.assertRaisesRegex(v.ReceiptRefused, 'EFFECT_SET_MISMATCH'):
            self.check(receipt=receipt, expected_receipt_sha256=v.receipt_digest(receipt))

    def test_base_commit_tampering_is_refused(self):
        receipt = copy.deepcopy(self.receipt); receipt['base_commit'] = 'c' * 40
        with self.assertRaisesRegex(v.ReceiptRefused, 'BASE_COMMIT_MISMATCH'):
            self.check(receipt=receipt, expected_receipt_sha256=v.receipt_digest(receipt))

    def test_policy_tampering_is_refused(self):
        receipt = copy.deepcopy(self.receipt); receipt['policy_sha256'] = 'd' * 64
        with self.assertRaisesRegex(v.ReceiptRefused, 'POLICY_MISMATCH'):
            self.check(receipt=receipt, expected_receipt_sha256=v.receipt_digest(receipt))

    def test_receipt_digest_tampering_is_refused(self):
        receipt = copy.deepcopy(self.receipt); receipt['base_commit'] = 'c' * 40
        with self.assertRaisesRegex(v.ReceiptRefused, 'RECEIPT_DIGEST_MISMATCH'):
            self.check(receipt=receipt)

    def test_untrusted_or_invalid_effect_paths_are_refused(self):
        for p in ('../evil', '/tmp/evil', 'a/../evil', 'a//b', 'x\\y', '.'):
            with self.subTest(path=p), self.assertRaises(v.ReceiptRefused):
                self.check(expected_patch_path=p, expected_effect_paths=(p,))

    def test_missing_empty_or_extra_effects_are_refused(self):
        for effects in ({}, dict(self.effects, **{'repair.patch': b''}), dict(self.effects, extra=b'x')):
            with self.subTest(effects=list(effects)), self.assertRaises(v.ReceiptRefused):
                self.check(effects=effects)


if __name__ == '__main__':
    unittest.main()
