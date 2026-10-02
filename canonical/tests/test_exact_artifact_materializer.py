import hashlib,tempfile,unittest
from pathlib import Path
from canonical.runtime.exact_artifact_materializer import materialize_exact_artifact

class Tests(unittest.TestCase):
    def test_exact_materialization(self):
        with tempfile.TemporaryDirectory() as td:
            data=b"native-artifact\x00bytes"
            sha=hashlib.sha256(data).hexdigest()
            out=Path(td)/"x.bin"
            r=materialize_exact_artifact(out,target_bytes=data,expected_target_sha256=sha)
            self.assertEqual(r["status"],"PASS",r)
            self.assertEqual(out.read_bytes(),data)

    def test_target_sha_guard(self):
        with tempfile.TemporaryDirectory() as td:
            out=Path(td)/"x.bin"
            r=materialize_exact_artifact(out,target_bytes=b"x",expected_target_sha256="0"*64)
            self.assertEqual(r["status"],"FAIL_CLOSED")
            self.assertFalse(out.exists())

    def test_source_precondition(self):
        with tempfile.TemporaryDirectory() as td:
            src=Path(td)/"src"; src.write_bytes(b"old")
            out=Path(td)/"out"
            good=hashlib.sha256(b"old").hexdigest()
            target=b"new"; target_sha=hashlib.sha256(target).hexdigest()
            r=materialize_exact_artifact(out,target_bytes=target,expected_target_sha256=target_sha,source_path=src,expected_source_sha256=good)
            self.assertEqual(r["status"],"PASS",r)

    def test_wrong_source_aborts(self):
        with tempfile.TemporaryDirectory() as td:
            src=Path(td)/"src"; src.write_bytes(b"old")
            out=Path(td)/"out"
            target=b"new"; target_sha=hashlib.sha256(target).hexdigest()
            r=materialize_exact_artifact(out,target_bytes=target,expected_target_sha256=target_sha,source_path=src,expected_source_sha256="0"*64)
            self.assertEqual(r["status"],"FAIL_CLOSED")
            self.assertFalse(out.exists())

if __name__=="__main__": unittest.main()
