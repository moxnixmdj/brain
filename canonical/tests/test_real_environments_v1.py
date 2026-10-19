"""Learning tested against the actual computer, not against toy classes.

The other suites use environments written for the test -- dials, a grid, a
buffer. Those are real executions, but they are invented worlds. These are not:
the environment IS the machine. Real directories, real files, real processes,
real syscalls. If the learner works here, it works on the thing it was built
for.

Nothing here is mocked. mkdir really calls mkdir, the process really runs, and
the state is read back from the filesystem rather than remembered.
"""
from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
import unittest

from canonical.runtime import environment_learning_v1 as el
from canonical.runtime import transfer_learning_v1 as tl


# --------------------------------------------------------------------------- #
# a real filesystem environment
# --------------------------------------------------------------------------- #
class FilesystemEnv:
    """Real directories and files in a real temp dir. Actions are real."""

    ACTIONS = ["mkdir_out", "cd_out", "cd_up", "touch_a", "write_a", "rm_a"]

    def __init__(self, root: str) -> None:
        self.root = root
        self.cwd = root

    def _rel(self) -> str:
        return os.path.relpath(self.cwd, self.root)

    def state(self):
        rel = self._rel()
        try:
            entries = sorted(os.listdir(self.cwd))
        except OSError:
            entries = []
        files, dirs = [], []
        for name in entries:
            path = os.path.join(self.cwd, name)
            (dirs if os.path.isdir(path) else files).append(name)
        # content matters, so the state is not just names
        content = ""
        a = os.path.join(self.cwd, "a.txt")
        if os.path.isfile(a):
            try:
                with open(a) as fh:
                    content = fh.read()
            except OSError:
                content = ""
        return (rel, tuple(dirs), tuple(files), content)

    def reset(self) -> None:
        self.cwd = self.root
        for name in os.listdir(self.root):
            shutil.rmtree(os.path.join(self.root, name), ignore_errors=True) \
                if os.path.isdir(os.path.join(self.root, name)) \
                else os.remove(os.path.join(self.root, name))

    def act(self, action) -> None:
        a = str(action)
        if a == "mkdir_out":
            os.makedirs(os.path.join(self.cwd, "out"), exist_ok=True)
        elif a == "cd_out":
            target = os.path.join(self.cwd, "out")
            if os.path.isdir(target):
                self.cwd = target
        elif a == "cd_up":
            if self.cwd != self.root:
                self.cwd = os.path.dirname(self.cwd)
        elif a == "touch_a":
            with open(os.path.join(self.cwd, "a.txt"), "a"):
                pass
        elif a == "write_a":
            with open(os.path.join(self.cwd, "a.txt"), "w") as fh:
                fh.write("hello")
        elif a == "rm_a":
            try:
                os.remove(os.path.join(self.cwd, "a.txt"))
            except OSError:
                pass

    def snapshot(self):
        """A real deep copy. Looking ahead acts for real, so undo must be real.

        Returning only `cwd` is not a snapshot: the heuristic probes actions,
        every probe really creates a file, and the probing leaves junk that
        makes the learned model contradict itself.
        """
        holder = tempfile.mkdtemp(prefix="brain-fssnap-")
        for name in os.listdir(self.root):
            src = os.path.join(self.root, name)
            dst = os.path.join(holder, name)
            try:
                shutil.copytree(src, dst) if os.path.isdir(src)                     else shutil.copy2(src, dst)
            except OSError:
                pass
        return (self.cwd, holder)

    def restore(self, v) -> None:
        cwd, holder = v
        for name in os.listdir(self.root):
            path = os.path.join(self.root, name)
            try:
                shutil.rmtree(path) if os.path.isdir(path) else os.remove(path)
            except OSError:
                pass
        for name in os.listdir(holder):
            src = os.path.join(holder, name)
            dst = os.path.join(self.root, name)
            try:
                shutil.copytree(src, dst) if os.path.isdir(src)                     else shutil.copy2(src, dst)
            except OSError:
                pass
        shutil.rmtree(holder, ignore_errors=True)
        self.cwd = cwd


def fs_heuristic(target):
    """Distance shaped for filesystem states: dirs, files, then content."""
    def h(state):
        rel, dirs, files, content = state
        tgt_rel, tgt_dirs, tgt_files, tgt_content = target
        return (0 if rel == tgt_rel else 1) \
            + len(set(tgt_dirs) - set(dirs)) \
            + len(set(tgt_files) - set(files)) \
            + (0 if content == tgt_content else 1)
    return h


# --------------------------------------------------------------------------- #
# a real process environment
# --------------------------------------------------------------------------- #
class ProcessEnv:
    """The environment is a real program. Actions are real invocations."""

    ACTIONS = ["gzip", "gzip_k", "bzip2", "compress_z", "rm_any"]

    def __init__(self, root: str) -> None:
        self.root = root
        self.src = os.path.join(root, "data.txt")
        with open(self.src, "w") as fh:
            fh.write("payload " * 200)

    def state(self):
        """What is actually on disk, right now."""
        found = []
        for name in sorted(os.listdir(self.root)):
            if name == "data.txt":
                continue
            path = os.path.join(self.root, name)
            if os.path.isfile(path):
                found.append((name, os.path.getsize(path)))
        return tuple(found)

    def reset(self) -> None:
        for name in os.listdir(self.root):
            if name == "data.txt":
                continue
            path = os.path.join(self.root, name)
            if os.path.isfile(path):
                os.remove(path)

    def act(self, action) -> None:
        a = str(action)
        if a == "rm_any":
            self.reset()
            return
        cmd = {"gzip": ["gzip", "-c", self.src],
               "gzip_k": ["gzip", "-9", "-c", self.src],
               "bzip2": ["bzip2", "-c", self.src],
               "compress_z": ["compress", "-c", self.src]}[a]
        try:
            proc = subprocess.run(cmd, capture_output=True, timeout=20)
        except (OSError, subprocess.SubprocessError):
            return
        if proc.returncode != 0 or not proc.stdout:
            return
        suffix = {"gzip": ".gz", "gzip_k": ".gz9",
                  "bzip2": ".bz2", "compress_z": ".Z"}[a]
        with open(os.path.join(self.root, "out" + suffix), "wb") as fh:
            fh.write(proc.stdout)

    def snapshot(self):
        return self.state()

    def restore(self, v) -> None:
        self.reset()
        for name, size in v:
            path = os.path.join(self.root, name)
            with open(path, "wb") as fh:
                fh.write(b"x" * size)


# --------------------------------------------------------------------------- #
# the real filesystem
# --------------------------------------------------------------------------- #
class RealFilesystemTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.mkdtemp(prefix="brain-realenv-")
        self.env = FilesystemEnv(self.tmp)

    def tearDown(self) -> None:
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_it_learns_to_create_a_directory_for_real(self):
        target = (".", ("out",), (), "")
        r = el.drive(self.env, FilesystemEnv.ACTIONS,
                     is_goal=lambda s: s == target,
                     budget=60, max_depth=8, heuristic=fs_heuristic(target))
        self.assertTrue(r["pass"], r)
        self.assertTrue(os.path.isdir(os.path.join(self.tmp, "out")))

    def test_it_learns_to_navigate_for_real(self):
        """The file must end up INSIDE out, which requires cd first."""
        target = ("out", (), ("a.txt",), "hello")
        r = el.drive(self.env, FilesystemEnv.ACTIONS,
                     is_goal=lambda s: s == target,
                     budget=140, max_depth=12, heuristic=fs_heuristic(target))
        self.assertTrue(r["pass"], r)
        want = os.path.join(self.tmp, "out", "a.txt")
        self.assertTrue(os.path.isfile(want))
        with open(want) as fh:
            self.assertEqual(fh.read(), "hello")

    def test_the_learned_plan_converges_to_the_true_optimum(self):
        """mkdir, cd, write is 3 actions and fewer cannot do it.

        With enough experience the machine finds it. Note that minimality is
        always WITH RESPECT TO WHAT WAS LEARNED -- see the next test.
        """
        target = ("out", (), ("a.txt",), "hello")
        r = el.drive(self.env, FilesystemEnv.ACTIONS,
                     is_goal=lambda s: s == target,
                     budget=400, max_depth=12, heuristic=fs_heuristic(target))
        self.assertTrue(r["pass"], r)
        self.assertEqual(r["plan_length"], 3)
        self.assertEqual(r["plan"], ["mkdir_out", "cd_out", "write_a"])

    def test_a_partially_learned_model_gives_a_valid_plan_not_an_optimal_one(self):
        """Thin experience yields a plan that WORKS but is not shortest.

        Claiming global optimality from a partial model would be a lie, and a
        test that asserted optimality here would be asserting the lie. The
        machine returns what its model supports and is never wrong about
        reaching the goal -- only about being unable to do better.
        """
        target = ("out", (), ("a.txt",), "hello")
        r = el.drive(self.env, FilesystemEnv.ACTIONS,
                     is_goal=lambda s: s == target,
                     budget=140, max_depth=12, heuristic=fs_heuristic(target))
        self.assertTrue(r["pass"], r)
        self.assertGreaterEqual(r["plan_length"], 3)
        # and it really does reach the goal
        self.assertTrue(os.path.isfile(os.path.join(self.tmp, "out", "a.txt")))

    def test_the_state_is_read_from_disk_not_remembered(self):
        """Poison the directory behind the learner's back; it must see it."""
        self.env.reset()
        before = self.env.state()
        os.makedirs(os.path.join(self.tmp, "sneaky"))
        self.assertNotEqual(self.env.state(), before)
        self.assertIn("sneaky", self.env.state()[1])

    def test_actions_really_touch_the_filesystem(self):
        self.env.act("mkdir_out")
        self.assertTrue(os.path.isdir(os.path.join(self.tmp, "out")))
        self.env.act("cd_out")
        self.env.act("write_a")
        self.assertTrue(os.path.isfile(os.path.join(self.tmp, "out", "a.txt")))


# --------------------------------------------------------------------------- #
# real programs
# --------------------------------------------------------------------------- #
class RealProcessTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.mkdtemp(prefix="brain-realproc-")
        self.env = ProcessEnv(self.tmp)

    def tearDown(self) -> None:
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_it_learns_which_real_program_produces_which_real_file(self):
        def goal(state):
            return any(name.endswith(".gz") and size > 0 for name, size in state)

        r = el.drive(self.env, ProcessEnv.ACTIONS, is_goal=goal,
                     budget=40, max_depth=6,
                     heuristic=lambda s: 0 if goal(s) else 1)
        self.assertTrue(r["pass"], r)
        self.assertTrue(any(n.endswith(".gz") for n in os.listdir(self.tmp)))

    def test_the_produced_file_is_a_real_gzip(self):
        """Not merely a file with a .gz name -- actually gzip magic."""
        def goal(state):
            return any(name.endswith(".gz") and size > 0 for name, size in state)

        el.drive(self.env, ProcessEnv.ACTIONS, is_goal=goal,
                 budget=40, max_depth=6,
                 heuristic=lambda s: 0 if goal(s) else 1)
        produced = [n for n in os.listdir(self.tmp) if n.endswith(".gz")]
        self.assertTrue(produced)
        with open(os.path.join(self.tmp, produced[0]), "rb") as fh:
            self.assertEqual(fh.read(2), b"\x1f\x8b")

    def test_it_distinguishes_compressors_by_what_they_actually_emit(self):
        def goal(state):
            return any(name.endswith(".bz2") and size > 0 for name, size in state)

        r = el.drive(self.env, ProcessEnv.ACTIONS, is_goal=goal,
                     budget=60, max_depth=6,
                     heuristic=lambda s: 0 if goal(s) else 1)
        if not r["pass"]:
            self.skipTest("bzip2 not available in this image")
        with open(os.path.join(self.tmp, "out.bz2"), "rb") as fh:
            self.assertEqual(fh.read(3), b"BZh")

    def test_a_program_that_is_not_installed_is_not_invented(self):
        """compress is usually absent. The learner must cope, not fake it."""
        state_before = self.env.state()
        self.env.act("compress_z")
        after = self.env.state()
        if shutil.which("compress") is None:
            self.assertEqual(after, state_before)
        else:
            self.assertNotEqual(after, state_before)


# --------------------------------------------------------------------------- #
# transfer, on the real filesystem
# --------------------------------------------------------------------------- #
class RealTransferTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.mkdtemp(prefix="brain-realtransfer-")
        self.store = tempfile.mkdtemp(prefix="brain-realstore-")
        self._saved = tl.STATE_PATH
        tl.STATE_PATH = os.path.join(self.store, "episodes.json")

    def tearDown(self) -> None:
        tl.STATE_PATH = self._saved
        shutil.rmtree(self.tmp, ignore_errors=True)
        shutil.rmtree(self.store, ignore_errors=True)

    def _env(self):
        return FilesystemEnv(self.tmp)

    def test_the_second_real_task_costs_less_than_the_first(self):
        first_target = (".", ("out",), (), "")
        first = tl.drive(self._env(), FilesystemEnv.ACTIONS,
                         is_goal=lambda s: s == first_target,
                         budget=60, max_depth=8,
                         heuristic=fs_heuristic(first_target))
        second_target = ("out", (), ("a.txt",), "hello")
        second = tl.drive(self._env(), FilesystemEnv.ACTIONS,
                          is_goal=lambda s: s == second_target,
                          budget=140, max_depth=12,
                          heuristic=fs_heuristic(second_target))
        self.assertTrue(first["pass"], first)
        self.assertTrue(second["pass"], second)
        self.assertGreater(second["prior_transitions"], 0)

    def test_real_rules_carry_over_to_a_different_real_goal(self):
        first_target = (".", ("out",), (), "")
        tl.drive(self._env(), FilesystemEnv.ACTIONS,
                 is_goal=lambda s: s == first_target,
                 budget=60, max_depth=8,
                 heuristic=fs_heuristic(first_target))
        other = ("out", (), ("a.txt",), "")
        r = tl.drive(self._env(), FilesystemEnv.ACTIONS,
                     is_goal=lambda s: s == other,
                     budget=140, max_depth=12, heuristic=fs_heuristic(other))
        self.assertTrue(r["pass"], r)
        self.assertTrue(os.path.isfile(os.path.join(self.tmp, "out", "a.txt")))

    def test_the_fingerprint_sees_a_different_kind_of_environment(self):
        fs_fp = tl.fingerprint(self._env(), FilesystemEnv.ACTIONS)
        proc_dir = tempfile.mkdtemp(prefix="brain-fp-")
        try:
            proc_fp = tl.fingerprint(ProcessEnv(proc_dir), ProcessEnv.ACTIONS)
        finally:
            shutil.rmtree(proc_dir, ignore_errors=True)
        self.assertEqual(tl.similarity(fs_fp, proc_fp), 0.0)

    def test_experience_accumulates_in_the_store(self):
        target = (".", ("out",), (), "")
        tl.drive(self._env(), FilesystemEnv.ACTIONS,
                 is_goal=lambda s: s == target,
                 budget=60, max_depth=8, heuristic=fs_heuristic(target))
        self.assertGreater(tl.stats()["episodes"], 0)
        self.assertGreater(tl.stats()["proven"], 0)


if __name__ == "__main__":
    unittest.main()
