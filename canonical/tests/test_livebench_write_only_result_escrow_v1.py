import ast
import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from canonical.runtime import livebench_write_only_result_escrow_v1 as escrow

class LiveBenchWriteOnlyResultEscrowTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from cryptography.hazmat.primitives.asymmetric import rsa
        from cryptography.hazmat.primitives import serialization
        cls.private_key=rsa.generate_private_key(public_exponent=65537,key_size=2048)
        cls.public_pem=cls.private_key.public_key().public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo,
        )

    def _decrypt_for_test_only(self,envelope: bytes,lease: str):
        from cryptography.hazmat.primitives import hashes
        from cryptography.hazmat.primitives.asymmetric import padding
        from cryptography.hazmat.primitives.ciphers.aead import AESGCM
        p=len(escrow.MAGIC)
        wrapped=envelope[p:p+escrow.RSA_BYTES]; p+=escrow.RSA_BYTES
        nonce=envelope[p:p+escrow.NONCE_BYTES]; p+=escrow.NONCE_BYTES
        ciphertext=envelope[p:]
        key=self.private_key.decrypt(
            wrapped,
            padding.OAEP(
                mgf=padding.MGF1(algorithm=hashes.SHA256()),
                algorithm=hashes.SHA256(),
                label=None,
            ),
        )
        plain=AESGCM(key).decrypt(nonce,ciphertext,escrow._aad(lease))
        mode=plain[0]
        length=int.from_bytes(plain[1:9],"big")
        digest=plain[9:41]
        body=plain[41:41+length] if mode==0 else b""
        return mode,length,digest,body

    def test_fixed_size_roundtrip_and_no_plaintext_receipt(self):
        lease="a"*64
        low=b'{"score":0.01,"summary":"LOW_SECRET"}'
        high=b'{"score":0.999,"summary":"HIGH_SECRET_WITH_DIFFERENT_LENGTH"}'
        envelopes=[]
        for result in (low,high):
            with tempfile.TemporaryDirectory() as td:
                receipt=escrow.write_result_opaque(
                    result,lease_digest_sha256=lease,
                    public_key_pem=self.public_pem,output_root=td,
                )
                path=Path(td)/receipt["escrow_object_path"]
                envelope=path.read_bytes()
                envelopes.append(envelope)
                self.assertEqual(len(envelope),escrow.EXPECTED_ENVELOPE_BYTES)
                visible=json.dumps(receipt,sort_keys=True)
                self.assertNotIn("LOW_SECRET",visible)
                self.assertNotIn("HIGH_SECRET",visible)
                self.assertNotIn('"score"',visible)
                self.assertFalse(receipt["plaintext_result_fields_visible"])
                self.assertFalse(receipt["plaintext_result_length_visible"])
                self.assertFalse(receipt["plaintext_result_hash_visible"])
                self.assertFalse(receipt["decrypt_capability_present"])
                mode,length,digest,body=self._decrypt_for_test_only(envelope,lease)
                self.assertEqual(mode,0)
                self.assertEqual(length,len(result))
                self.assertEqual(digest,hashlib.sha256(result).digest())
                self.assertEqual(body,result)
        self.assertEqual(len(envelopes[0]),len(envelopes[1]))

    def test_overflow_is_also_fixed_size_and_opaque(self):
        lease="b"*64
        result=b"x"*(escrow.MAX_STORED_RESULT_BYTES+123)
        envelope=escrow.seal_result_bytes(result,lease_digest_sha256=lease,public_key_pem=self.public_pem)
        self.assertEqual(len(envelope),escrow.EXPECTED_ENVELOPE_BYTES)
        mode,length,digest,body=self._decrypt_for_test_only(envelope,lease)
        self.assertEqual(mode,1)
        self.assertEqual(length,len(result))
        self.assertEqual(digest,hashlib.sha256(result).digest())
        self.assertEqual(body,b"")

    def test_output_path_depends_only_on_lease(self):
        lease="c"*64
        path=escrow.escrow_object_relpath(lease)
        self.assertEqual(path,f"livebench-shadow-escrow/{lease}.bin")
        self.assertNotIn("score",path.lower())

    def test_duplicate_write_fails_before_any_result_release(self):
        lease="d"*64
        with tempfile.TemporaryDirectory() as td:
            escrow.write_result_opaque(b"first",lease_digest_sha256=lease,public_key_pem=self.public_pem,output_root=td)
            with self.assertRaises(FileExistsError):
                escrow.write_result_opaque(b"second",lease_digest_sha256=lease,public_key_pem=self.public_pem,output_root=td)

    def test_pre_fixed_point_completion_surface_is_constant_and_opaque(self):
        a=escrow.opaque_completion({"schema":escrow.RECEIPT_SCHEMA,"status":"OPAQUE_ESCROW_COMMITTED"})
        b=escrow.opaque_completion({"schema":escrow.RECEIPT_SCHEMA,"status":"OPAQUE_ESCROW_COMMITTED","score":99})
        self.assertEqual(a,b)
        self.assertEqual(a["status"],"OPAQUE_COMPLETION")
        self.assertFalse(a["result_visible"])
        self.assertFalse(a["score_visible"])
        self.assertFalse(a["summary_visible"])

    def test_production_module_has_no_decrypt_or_private_key_loader_call(self):
        source=Path(escrow.__file__).read_text()
        tree=ast.parse(source)
        attrs={n.attr for n in ast.walk(tree) if isinstance(n,ast.Attribute)}
        names={n.name for n in ast.walk(tree) if isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef))}
        self.assertNotIn("decrypt",attrs)
        self.assertNotIn("load_pem_private_key",attrs)
        self.assertFalse(any("decrypt" in name.lower() or "reveal" in name.lower() for name in names))

if __name__=="__main__":
    unittest.main()
