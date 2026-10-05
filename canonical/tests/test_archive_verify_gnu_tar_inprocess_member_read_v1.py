from __future__ import annotations
import json, pathlib, subprocess, tarfile, tempfile, unittest
from unittest.mock import patch
from canonical.runtime.bound_capabilities import archive_verify_gnu_tar as m

class ArchiveVerifierInProcessMemberReadTests(unittest.TestCase):
    def _fixture(self, root: pathlib.Path, *, symlink: bool=False):
        (root/"canonical").mkdir()
        (root/"canonical"/"x.txt").write_text("hello\n",encoding="utf-8")
        manifest={"records":[{"verification_paths":["canonical/x.txt"]}]}
        (root/"manifest.json").write_text(json.dumps(manifest),encoding="utf-8")
        arc=root/"a.tar.gz"
        with tarfile.open(arc,"w:gz") as tf:
            tf.add(root/"manifest.json",arcname="manifest.json")
            if symlink:
                info=tarfile.TarInfo("canonical/x.txt")
                info.type=tarfile.SYMTYPE
                info.linkname="/etc/passwd"
                tf.addfile(info)
            else:
                tf.add(root/"canonical"/"x.txt",arcname="canonical/x.txt")
        return arc

    def _listing(self, *args, **kwargs):
        return subprocess.CompletedProcess(
            args=args[0],returncode=0,
            stdout="canonical/x.txt\nmanifest.json\n",stderr=""
        )

    def test_valid_archive_uses_only_one_external_tar_call(self):
        with tempfile.TemporaryDirectory() as td:
            root=pathlib.Path(td); self._fixture(root)
            with patch.object(m.subprocess,"run",side_effect=self._listing) as run:
                out=m.run({"manifest_path":"manifest.json","archive_path":"a.tar.gz"},root)
            self.assertTrue(out["verified"])
            self.assertEqual(run.call_count,1)
            self.assertEqual(run.call_args.args[0][0:2],["tar","-tzf"])

    def test_source_hash_mismatch_is_detected_without_extraction(self):
        with tempfile.TemporaryDirectory() as td:
            root=pathlib.Path(td); self._fixture(root)
            (root/"canonical"/"x.txt").write_text("changed\n",encoding="utf-8")
            with patch.object(m.subprocess,"run",side_effect=self._listing):
                with self.assertRaisesRegex(RuntimeError,"ARCHIVE_HASH_MISMATCH"):
                    m.run({"manifest_path":"manifest.json","archive_path":"a.tar.gz"},root)

    def test_symlink_member_is_rejected_without_following_it(self):
        with tempfile.TemporaryDirectory() as td:
            root=pathlib.Path(td); self._fixture(root,symlink=True)
            with patch.object(m.subprocess,"run",side_effect=self._listing):
                with self.assertRaisesRegex(RuntimeError,"ARCHIVE_HASH_MISMATCH"):
                    m.run({"manifest_path":"manifest.json","archive_path":"a.tar.gz"},root)

if __name__=="__main__":
    unittest.main(verbosity=2)
