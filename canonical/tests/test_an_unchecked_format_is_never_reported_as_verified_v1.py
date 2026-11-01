"""The machine's own learning channel reported formats it never checked.

Measured 2026-11-01 on main (073540d), transfer store empty, ``discover()`` called
directly on eight goal families it had never been told about:

    "convert tiny.png into tiny.jpg"      -> PASS__SINGLE_ACTION_FOUND_AND_VERIFIED
                                             plan ['run_unexpand']      (a whitespace tool)
    "pack pkg into pkg.tar.gz"            -> PASS..., plan ['run_gzip']
    "dump data.db into data.csv"          -> PASS..., plan ['run_tar']   (a tarball)
    "hash blob.bin into blob.sha256"      -> PASS..., plan ['run_sha256sum']
    "write the commit log of repo into
     log.txt"                             -> PASS..., plan ['run_md5sum.textutils']

Six of thirteen formats had no verifier at all and the machine returned
``True, "NO_VERIFIER_FOR_FORMAT"`` for every one of them; and for the formats that
did have one, ``pathlib`` handed the verifier ``.gz`` for ``pkg.tar.gz``, so a gzip
of a single file was accepted as a tarball, and ``csv.reader`` accepted a tar as a
table.  Each closed goal was remembered as proven, so the falseness became durable.

What is asserted here is the property, not the fixes: a goal closes only when the
file it made really is the thing that was asked for, and a format with no way to
check that is refused instead of passed.
"""
import gzip
import io
import pathlib
import sys
import tarfile
import tempfile
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from canonical.runtime import computer_env_v1 as cenv  # noqa: E402
from canonical.runtime import program_synthesis_v1 as ps  # noqa: E402
from canonical.runtime import cli_capability_acquisition_v1 as acq  # noqa: E402


def _jpeg() -> bytes:
    return b"\xff\xd8\xff\xe0" + b"\x00" * 8 + b"\xff\xc0" + b"\x00" * 8 + b"\xff\xd9"


class AnUncheckedFormatIsNeverAVerifiedOne(unittest.TestCase):

    def setUp(self) -> None:
        self.dir = pathlib.Path(tempfile.mkdtemp(prefix="brain-verifier-"))

    def _file(self, name: str, data: bytes) -> pathlib.Path:
        path = self.dir / name
        path.write_bytes(data)
        return path

    def _tarball(self, name: str) -> pathlib.Path:
        path = self.dir / name
        with tarfile.open(path, "w:gz") as tar:
            payload = self.dir / "_member.txt"
            payload.write_text("one\ntwo\n", encoding="utf-8")
            tar.add(payload, arcname="member.txt")
        return path

    # -- the format that is claimed is the format that must be checked ----- #

    def test_a_format_with_no_verifier_is_not_reported_as_verified(self) -> None:
        text = self._file("mystery.bin", b"anything at all\n")
        good, why = ps.verify_round_trip(text, ".bin")
        self.assertFalse(good, "an unverifiable format was reported as verified")
        self.assertEqual(why, "NO_VERIFIER_FOR_FORMAT")

    def test_a_gzip_of_one_file_is_not_a_tarball(self) -> None:
        fake = self._file("pkg.tar.gz", gzip.compress(b"just text\n"))
        good, why = ps.verify_round_trip(fake, ".tar.gz")
        self.assertFalse(good, "a gzip stream was accepted as a tarball: %s" % why)

    def test_a_real_tarball_is_a_tarball(self) -> None:
        real = self._tarball("real.tar.gz")
        self.assertEqual(ps.verify_round_trip(real, ".tar.gz"),
                         (True, "ROUND_TRIP_OK"))

    def test_the_goal_names_the_longest_suffix_it_asks_for(self) -> None:
        # pathlib answers '.gz' here, and '.gz' is the wrong question
        self.assertEqual(ps.suffix_for_name("pkg.tar.gz"), ".tar.gz")
        self.assertEqual(acq._requested_suffix("pack pkg into pkg.tar.gz"), ".tar.gz")
        self.assertEqual(acq._requested_suffix("compress notes.txt into notes.txt.gz"),
                         ".gz")

    # -- bytes that are another format entirely --------------------------- #

    def test_a_tarball_named_csv_is_not_a_csv(self) -> None:
        plain = self.dir / "plain.tar"
        with tarfile.open(plain, "w") as tar:
            payload = self.dir / "_m.txt"
            payload.write_text("x\n", encoding="utf-8")
            tar.add(payload, arcname="m.txt")
        fake = self._file("data.csv", plain.read_bytes())
        good, why = ps.verify_round_trip(fake, ".csv")
        self.assertFalse(good, "a tarball was accepted as a table: %s" % why)
        self.assertIn("CONTAINER_MISMATCH", why)

    def test_a_digest_is_not_a_table(self) -> None:
        line = self._file("out.csv", b"9f86d081884c7d659a2feaa0c55ad015  blob.bin\n")
        self.assertFalse(ps.verify_round_trip(line, ".csv")[0])

    def test_a_png_named_jpeg_is_not_a_jpeg(self) -> None:
        png = bytes.fromhex("89504e470d0a1a0a0000000d49484452000000010000000108060000001f15c4"
                            "890000000a49444154789c6300010000050001")
        fake = self._file("tiny.jpg", png)
        good, why = ps.verify_round_trip(fake, ".jpg")
        self.assertFalse(good)
        self.assertIn("png", why)

    def test_a_real_jpeg_is_a_jpeg(self) -> None:
        self.assertEqual(ps.verify_round_trip(self._file("real.jpg", _jpeg()), ".jpg"),
                         (True, "ROUND_TRIP_OK"))

    # -- a digest is a digest shape, and nothing else is ------------------ #

    def test_md5_output_is_not_a_sha256_file(self) -> None:
        md5 = self._file("blob.sha256", b"d41d8cd98f00b204e9800998ecf8427e  blob.bin\n")
        good, why = ps.verify_round_trip(md5, ".sha256")
        self.assertFalse(good, "a 32-digit digest satisfied a 64-digit claim: %s" % why)

    def test_sha256_output_is_a_sha256_file(self) -> None:
        dig = self._file("blob.sha256", b"a" * 64 + b"  blob.bin\n")
        self.assertEqual(ps.verify_round_trip(dig, ".sha256"), (True, "ROUND_TRIP_OK"))

    # -- and the channel asks before it pays ------------------------------ #

    def test_text_carries_no_evidence_so_the_format_says_so(self) -> None:
        self.assertFalse(ps.carries_content_evidence(".txt"))
        self.assertFalse(ps.carries_content_evidence(".md"))
        self.assertTrue(ps.carries_content_evidence(".sha256"))

    def test_a_text_goal_is_refused_without_running_anything(self) -> None:
        out = cenv.discover("write the commit log of repo into log.txt")
        self.assertFalse(out.get("closed"))
        self.assertEqual(out.get("status"), "OPEN__FORMAT_CARRIES_NO_EVIDENCE")

    def test_a_two_layer_format_is_refused_without_a_search(self) -> None:
        out = cenv.discover("pack pkg into pkg.tar.gz")
        self.assertFalse(out.get("closed"))
        self.assertEqual(out.get("status"),
                         "OPEN__FORMAT_NEEDS_A_CHAIN_THIS_CHANNEL_CANNOT_KEEP")

    def test_no_status_that_starts_with_pass_is_returned_for_an_unverified_goal(
            self) -> None:
        # the same lie in a different field: closed False, status PASS__...
        for goal in ("pack pkg into pkg.tar.gz",
                     "write the commit log of repo into log.txt"):
            out = cenv.discover(goal)
            self.assertFalse(str(out.get("status") or "").startswith("PASS"),
                             "%r reported %r" % (goal, out.get("status")))


if __name__ == "__main__":
    unittest.main()
