import base64
import hashlib
import subprocess
import tempfile
import unittest
from pathlib import Path

from canonical.runtime.aa_briefcase_owner_signature_verifier_v1 import (
    OwnerSignatureError,
    SIGNATURE_SCHEME,
    canonical_statement_bytes,
    verify_owner_signature,
)


def statement():
    return {
        "_type": "https://in-toto.io/Statement/v1",
        "subject": [{"name": "brain-aa-briefcase-candidate", "digest": {"sha256": "a" * 64}}],
        "predicateType": "https://project-brain.local/attestation/aa-briefcase-current-epoch-noninferiority/v1",
        "predicate": {
            "benchmark": "AA-Briefcase v1.1",
            "brain_weakly_dominates_current_opus55": True,
        },
    }


def make_signed(s):
    with tempfile.TemporaryDirectory(prefix="aa_sig_test_") as tmp:
        root = Path(tmp)
        priv = root / "private.pem"
        pub = root / "public.pem"
        msg = root / "statement.json"
        sig = root / "statement.sig"
        subprocess.run(
            ["openssl", "genpkey", "-algorithm", "ED25519", "-out", str(priv)],
            check=True,
            capture_output=True,
        )
        subprocess.run(
            ["openssl", "pkey", "-in", str(priv), "-pubout", "-out", str(pub)],
            check=True,
            capture_output=True,
        )
        msg.write_bytes(canonical_statement_bytes(s))
        subprocess.run(
            [
                "openssl", "pkeyutl", "-sign", "-inkey", str(priv),
                "-rawin", "-in", str(msg), "-out", str(sig),
            ],
            check=True,
            capture_output=True,
        )
        public_key_pem = pub.read_text(encoding="utf-8")
        signature_base64 = base64.b64encode(sig.read_bytes()).decode("ascii")
    bundle = {
        "scheme": SIGNATURE_SCHEME,
        "public_key_pem": public_key_pem,
        "signature_base64": signature_base64,
    }
    binding = {
        "status": "VERIFIED_OWNER_KEY_BINDING",
        "benchmark_owner": "Artificial Analysis",
        "authorized_for": "AA-Briefcase v1.1",
        "signature_scheme": SIGNATURE_SCHEME,
        "identity_verified": True,
        "public_key_pem_sha256": hashlib.sha256(public_key_pem.encode("utf-8")).hexdigest(),
        "binding_receipt_sha256": "b" * 64,
    }
    return bundle, binding


class T(unittest.TestCase):
    def test_real_signature_passes(self):
        s = statement()
        bundle, binding = make_signed(s)
        out = verify_owner_signature(s, bundle, binding)
        self.assertEqual(out["status"], "VERIFIED")
        self.assertTrue(out["attestor_is_benchmark_owner_or_authorized_operator"])

    def test_modified_statement_fails(self):
        s = statement()
        bundle, binding = make_signed(s)
        s["predicate"]["brain_weakly_dominates_current_opus55"] = False
        with self.assertRaisesRegex(OwnerSignatureError, "CRYPTOGRAPHIC_SIGNATURE_INVALID"):
            verify_owner_signature(s, bundle, binding)

    def test_wrong_public_key_binding_fails(self):
        s = statement()
        bundle, binding = make_signed(s)
        binding["public_key_pem_sha256"] = "0" * 64
        with self.assertRaisesRegex(OwnerSignatureError, "OWNER_PUBLIC_KEY_MISMATCH"):
            verify_owner_signature(s, bundle, binding)

    def test_unverified_key_identity_fails(self):
        s = statement()
        bundle, binding = make_signed(s)
        binding["identity_verified"] = False
        with self.assertRaisesRegex(OwnerSignatureError, "OWNER_KEY_IDENTITY_UNVERIFIED"):
            verify_owner_signature(s, bundle, binding)

    def test_wrong_benchmark_authorization_fails(self):
        s = statement()
        bundle, binding = make_signed(s)
        binding["authorized_for"] = "Other Benchmark"
        with self.assertRaisesRegex(OwnerSignatureError, "OWNER_KEY_NOT_AUTHORIZED_FOR_AA_BRIEFCASE"):
            verify_owner_signature(s, bundle, binding)

    def test_bad_signature_bytes_fail(self):
        s = statement()
        bundle, binding = make_signed(s)
        raw = bytearray(base64.b64decode(bundle["signature_base64"]))
        raw[0] ^= 1
        bundle["signature_base64"] = base64.b64encode(bytes(raw)).decode("ascii")
        with self.assertRaisesRegex(OwnerSignatureError, "CRYPTOGRAPHIC_SIGNATURE_INVALID"):
            verify_owner_signature(s, bundle, binding)
