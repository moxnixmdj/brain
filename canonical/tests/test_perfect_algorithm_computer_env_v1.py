"""Real-computer proof for the perfect algorithm.

The perfect algorithm has always been measured on constructed toys
(dials, grids, buffers, towers). This test drives it -- cold, with no
instant knowledge, no model calls -- against the REAL computer environment
adapter: real programs (gzip) found on the PATH, real files, real
subprocess execution, real verified artifact.

Not a capability claim: the measured task is one compression of one file in
a temp sandbox. It does not claim OSWorld/Terminal-Bench/ARC-AGI-3 closure.
"""
from __future__ import annotations

import gzip
import json
import shutil
import tempfile
import time
import unittest
from pathlib import Path

from canonical.swe_kernel.perfect_algorithm_computer_env_v1 import (
    build_env,
    drive_perfect_algorithm,
)

GOAL = "compress seed.txt into seed.txt.gz"
SEED_BYTES = b"alpha beta gamma\ndelta epsilon\nzeta eta\n"


def _fresh():
    return Path(tempfile.mkdtemp(prefix="pa_computer_env_test_"))


class RealComputerAdapterTests(unittest.TestCase):
    def test_narrowing_recommends_the_program_that_compresses_not_decompresses(self):
        env, meta = build_env(GOAL, seed_contents={"seed.txt": SEED_BYTES}, limit=8)
        self.assertIn("gzip", meta["programs"],
                      "the narrowing must keep the compress-specific program "
                      "even though gunzip is the same binary and wins the "
                      "tie-break by name")
        env.close()

    def test_cold_run_closes_with_a_verified_artifact(self):
        tmp = _fresh()
        receipts, meta, env = drive_perfect_algorithm(
            GOAL, seed_contents={"seed.txt": SEED_BYTES},
            limit=8, budget=60, max_depth=4,
            memory_path_=tmp / "memory.json",
        )
        self.assertTrue(receipts.get("pass"), receipts)
        self.assertEqual(receipts.get("outcome"), "VERIFIED_NOT_PERSISTED")
        plan = (receipts.get("steps") or {}).get("act", {}).get("executed")
        self.assertIn("run_gzip", plan or [])
        tree = env.tree()
        self.assertIn("seed.txt.gz", tree)
        self.assertEqual(gzip.decompress(tree["seed.txt.gz"]), SEED_BYTES)
        env.close()

    def test_unseen_content_warm_replay_is_instant(self):
        """Teach on content A, replay on content B: rule does not name bytes."""
        from canonical.swe_kernel import perfect_algorithm_v1 as pa

        tmp = _fresh()
        teach_seed = b"teach seed bytes\nsecond line\n"
        target_seed = b"different bytes entirely\nsame goal\n"
        env_t, meta_t = build_env(GOAL, seed_contents={"seed.txt": teach_seed}, limit=8)
        fresh = []
        for variant in (b"variant alpha\n", b"variant beta\n"):
            fe, _ = build_env(GOAL, seed_contents={"seed.txt": variant}, limit=8)
            fresh.append(fe)
        mem_path = tmp / "memory.json"
        out_teach = pa.run(
            env_t, GOAL, env_t.action_names(),
            goal_predicate=meta_t["is_goal"], env_kind="computer_file_ops",
            memory_path_=mem_path, budget=200, max_depth=4,
            heuristic=meta_t["heuristic"],
            unseen_instances=fresh,
            fresh_reset=lambda e: e.reset(),
            fresh_act=lambda e, a: e.act(a),
            fresh_state=lambda e: e.state(),
        )
        self.assertEqual(out_teach.get("status"), "PASS__PERFECT_ALGORITHM_RUN")
        admit = (out_teach.get("steps") or {}).get("admit") or {}
        self.assertEqual(admit.get("verdict"), "ADMIT")

        env_b, meta_b = build_env(GOAL, seed_contents={"seed.txt": target_seed}, limit=8)
        out_warm = pa.run(
            env_b, GOAL, env_b.action_names(),
            goal_predicate=meta_b["is_goal"], env_kind="computer_file_ops",
            memory_path_=mem_path, budget=200, max_depth=4,
            heuristic=meta_b["heuristic"],
        )
        self.assertEqual(out_warm.get("outcome"), "INSTANT_RECALL")
        warm_steps = out_warm.get("steps") or {}
        self.assertEqual((warm_steps.get("memory_replay") or {}).get("status"),
                         "PASS__REPLAY_REACHED_GOAL")
        env_t.close()
        env_b.close()

        for e in fresh:
            try:
                e.close()
            except Exception:
                pass


class ArchiveGoalTests(unittest.TestCase):
    """The archive goal's predicate: the claim is 'the named archive really
    contains the source, byte for byte'. A file is not its format."""

    def test_predicate_requires_the_source_inside_as_bytes(self):
        import io
        import tarfile

        from canonical.swe_kernel.perfect_algorithm_computer_env_v1 import (
            goal_predicate_for,
        )

        seed = {"data.txt": b"alpha\nbeta\ngamma\n"}
        src = seed["data.txt"]

        def _archive(mode, entries, uncompressed=None):
            # build a real archive on the CPU; the predicate's job is to
            # judge exactly this
            import tempfile, pathlib
            root = pathlib.Path(tempfile.mkdtemp(prefix="pa-archive-test-"))
            tgt = root / "data.tar.gz"
            with tarfile.open(tgt, mode) as tf:
                for name, data in entries:
                    info = tarfile.TarInfo(name)
                    info.size = len(data)
                    tf.addfile(info, io.BytesIO(data))
            return root, tgt

        # good: gz archive containing data.txt with the seed bytes
        root, good = _archive("w:gz", [("data.txt", src)])
        is_goal = goal_predicate_for(seed, "data.tar.gz")
        self.assertTrue(is_goal({"data.txt": src, "data.tar.gz": good.read_bytes()}),
                        "the archive holding the source byte for byte is the goal")
        self.assertFalse(is_goal({"data.txt": src}), "no archive yet is not the goal")

        # wrong: plain (uncompressed) tar named .tar.gz -- not a gzip archive
        root, plain = _archive("w", [("data.txt", src)])
        self.assertFalse(is_goal({"data.txt": src, "data.tar.gz": plain.read_bytes()}),
                         "a plain tar named data.tar.gz is not a tar.gz")

        # wrong: gz archive holding different bytes
        root, bad_bytes = _archive("w:gz", [("data.txt", b"WRONG\n")])
        self.assertFalse(is_goal({"data.txt": src, "data.tar.gz": bad_bytes.read_bytes()}),
                         "an archive holding different text is not the goal")

        # wrong: gz archive holding the source under a different name
        root, wrong_name = _archive("w:gz", [("other.txt", src)])
        self.assertFalse(is_goal({"data.txt": src, "data.tar.gz": wrong_name.read_bytes()}),
                         "an archive holding the source under another name is not the goal")

    def test_archive_predicate_verifies_each_format_as_the_goal_claims_it(self):
        """The claim is 'the target file is that format and holds the source'.
        A file CALLED out.zip is not a zip; an archive holding wrong bytes
        is not the goal."""
        import bz2 as _bz2
        import io
        import lzma as _lzma
        import tarfile
        import zipfile

        from canonical.swe_kernel.perfect_algorithm_computer_env_v1 import (
            goal_predicate_for,
        )

        seed = {"data.txt": b"alpha\nbeta\ngamma\n"}
        src = seed["data.txt"]

        def _tar(mode):
            b = io.BytesIO()
            with tarfile.open(fileobj=b, mode=mode) as tf:
                info = tarfile.TarInfo("data.txt")
                info.size = len(src)
                tf.addfile(info, io.BytesIO(src))
            return b.getvalue()

        def _zip():
            b = io.BytesIO()
            with zipfile.ZipFile(b, mode="w") as zf:
                zf.writestr("data.txt", src)
            return b.getvalue()

        good = [
            (".tar", _tar("w")),
            (".tar.gz", _tar("w:gz")),
            (".tar.bz2", _tar("w:bz2")),
            (".tar.xz", _tar("w:xz")),
            (".zip", _zip()),
            (".gz", gzip.compress(src)),
            (".bz2", _bz2.compress(src)),
            (".xz", _lzma.compress(src)),
        ]
        for suffix, payload in good:
            with self.subTest(suffix=suffix):
                pred = goal_predicate_for(seed, f"out{suffix}")
                self.assertTrue(pred({"data.txt": src, f"out{suffix}": payload}),
                                f"{suffix} archive holding the source bytes is the goal")

        # wrong-format decoys: a gzipped file named .bz2, a plain tar named .zip,
        # an archive holding different bytes named .zip
        import gzip as _gzip
        decoys = [
            (".bz2", _gzip.compress(src)),   # gzip bytes named .bz2
            (".zip", _tar("w:gz")),          # tar bytes named .zip
            (".tar.xz", _tar("w")),          # plain tar named .tar.xz
        ]
        for suffix, payload in decoys:
            with self.subTest(decoy=suffix):
                pred = goal_predicate_for(seed, f"out{suffix}")
                self.assertFalse(pred({"data.txt": src, f"out{suffix}": payload}),
                                 f"{suffix} holding the wrong format is not the goal")

        def _zip_wrong_bytes():
            b = io.BytesIO()
            with zipfile.ZipFile(b, mode="w") as zf:
                zf.writestr("data.txt", b"wrong bytes\n")
            return b.getvalue()

        pred = goal_predicate_for(seed, "out.zip")
        self.assertFalse(pred({"data.txt": src, "out.zip": _zip_wrong_bytes()}),
                         "a zip holding wrong bytes is not the goal")

    def test_drive_reaches_the_goal_and_recipe_asserts_the_real_shape(self):
        if shutil.which("tar") is None:
            self.skipTest("tar not available")
        seed = {"data.txt": b"alpha\nbeta\ngamma\ndelta\n"}
        env, meta = build_env("archive data.txt into data.tar.gz",
                              seed_contents=seed, limit=8)
        self.assertIn("tar", meta["programs"])
        tree_before = env.tree()
        self.assertIn("run_tar", env.action_names())
        ok = env.act("run_tar")
        self.assertTrue(ok, "run_tar did not create the target")
        target_bytes = env.tree().get("data.tar.gz") or b""
        self.assertTrue(target_bytes, "the archive was not written")
        self.assertTrue(meta["is_goal"](env.state()),
                        "the archive predicate did not hold after run_tar")
        # the recipe is the honest record of the exact argv that worked
        recipe = env.wrapped.recipes.get("run_tar")
        self.assertIsNotNone(recipe, "the recipe was not recorded")
        self.assertIn("--file", recipe.get("argv") or [],
                      "the recipe argv must name the archive file")
        env.close()


if __name__ == "__main__":
    unittest.main()


class FormatNameNarrowingTests(unittest.TestCase):
    """The target's extension names the format the goal hands it.

    'zip the files into out.zip' must surface the program literally called
    `zip`; 'make a bzip2 archive out.bz2' must surface `bzip2`; 'archive
    data.txt into data.tar.gz' must surface `tar`. A format-name program is
    the goal's own first candidate, not a program inferred from flag
    descriptions.
    """

    def test_format_goal_surfaces_the_format_name_program(self):
        from canonical.runtime.computer_env_v1 import programs_for_goal

        cases = [
            ("zip the files into out.zip", "zip"),
            ("make a zip archive out.zip", "zip"),
            ("make a bzip2 archive out.bz2", "bzip2"),
            ("make an archive out.tar.gz", "tar"),
            ("archive data.txt into data.tar.gz", "tar"),
            ("make an archive out.tar", "tar"),
        ]
        for goal, expected in cases:
            with self.subTest(goal=goal):
                progs = programs_for_goal(goal, limit=8)
                self.assertIn(expected, progs,
                              f"{goal!r} must surface {expected!r}")
                self.assertEqual(progs[0], expected,
                                 f"{goal!r}: {expected!r} must lead the candidates")

    def test_basenames_are_noise_and_not_candidates(self):
        from canonical.runtime.computer_env_v1 import programs_for_goal

        # A goal whose basename happens to be the name of a program: the
        # basename is the file the goal is FOR, never a signal.
        progs = programs_for_goal("zip data.zip into out.zip", limit=8)
        self.assertNotIn("data", progs)
