from __future__ import annotations
import base64,hashlib,tempfile,unittest
from pathlib import Path
from canonical.runtime.apt_metadata_snapshot_v1 import AptSnapshotError,decompress_lz4_frame,iter_lz4_frame_chunks,parse_deb822_records,installed_version,xxh32

LINKED=base64.b64decode("BCJNGEBAwBIBAACPQUJDRDEyMzQIAP/////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////gUEQxMjM0QgAAAA8IAP//////////////////////////////////////////////////////////////////////////pVBUQUlMCgAAAAA=")
CHECKED=base64.b64decode("BCJNGFxAhTgBAAAAAABCEgEAAI9BQkNEMTIzNAgA/////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////+BQRDEyMzQ7sb4EQgAAAA8IAP//////////////////////////////////////////////////////////////////////////pVBUQUlMCuKF6Y4AAAAAri0MlQ==")
EXPECTED_LEN=80005
EXPECTED_SHA="062955c774242f653f1455d7c800f9db5f9e72b11fed8b84b248ce62520dbbbc"

class AptMetadataSnapshotV1Tests(unittest.TestCase):
    def assert_payload(self,raw):
        out=decompress_lz4_frame(raw)
        self.assertEqual(len(out),EXPECTED_LEN)
        self.assertEqual(hashlib.sha256(out).hexdigest(),EXPECTED_SHA)
        return out
    def test_known_xxh32_empty_vector(self):
        self.assertEqual(xxh32(b""),0x02CC5D05)
    def test_linked_block_reference_fixture(self):
        self.assert_payload(LINKED)
    def test_checksummed_reference_fixture(self):
        self.assert_payload(CHECKED)
    def test_streaming_linked_fixture_matches_full_decoder(self):
        self.assertEqual(b"".join(iter_lz4_frame_chunks(LINKED)),self.assert_payload(LINKED))
    def test_corrupt_header_checksum_fails_closed(self):
        raw=bytearray(LINKED); raw[6]^=1
        with self.assertRaises(AptSnapshotError): decompress_lz4_frame(bytes(raw))
    def test_deb822_continuation(self):
        rows=parse_deb822_records("Package: a\nDescription: short\n long\nVersion: 1\n\n")
        self.assertEqual(rows,[{"Package":"a","Description":"short\nlong","Version":"1"}])
    def test_installed_version_from_status_snapshot(self):
        with tempfile.TemporaryDirectory() as td:
            p=Path(td)/"status"
            p.write_text("Package: a\nStatus: install ok installed\nVersion: 1.2-3\n\nPackage: b\nStatus: deinstall ok config-files\nVersion: 9\n\n")
            self.assertEqual(installed_version("a",p),"1.2-3")
            self.assertIsNone(installed_version("b",p))
if __name__=="__main__": unittest.main(verbosity=2)
