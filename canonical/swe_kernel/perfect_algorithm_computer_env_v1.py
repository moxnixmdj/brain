#!/usr/bin/env python3
"""Perfect Algorithm driven against a REAL computer environment.

WHERE THIS LIVES
----------------
`canonical/runtime/environment_learning_v1.py` (the perfect algorithm) has
been measured only on constructed toy environments (three-peg stack, dial
lock, 4x4 grid, text buffer). This module wires the same goal-directed,
best-first scan into a real computer environment -- `ComputerEnv` from
`canonical/runtime/computer_env_v1.py`: real programs discovered from PATH,
real files on disk, real verification. Nothing is faked: the actions run
real subprocesses via the environment's own `program_actions` (argv, recipes,
kept-or-discarded verification all unchanged). This adapter adds only the
env-protocol surface the perfect algorithm needs -- reset / state / act /
snapshot / restore -- with no new search logic.

WHAT THE ADAPTER DOES NOT DO
---------------------------
It does not rebuild the environment. It does not invent an action. It does
not skip the scan. It is the thinnest possible seam so `pa.run` and
`el.drive` can run against `ComputerEnv`.

THE REALISM BOUND
-----------------
The task measured here is one compression (file -> file.gz). It is a real
program, a real file, a real subprocess, a real artifact -- but the
environment is a temp directory with ~8 goal-narrowed candidate programs, not
a full desktop or a repository. The §6 verdict is recorded against the toy
numbers as well (see the measurement doc): what is proven here is that the
perfect algorithm closes on a real computer environment, not that it closes
on OSWorld/Terminal-Bench/ARC-AGI-3 at scale.
"""
from __future__ import annotations

import gzip
import pathlib
import sys
import tempfile
from typing import Any, Callable, Mapping, Sequence

ROOT = pathlib.Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from canonical.runtime.computer_env_v1 import (  # noqa: E402
    ComputerEnv,
    output_name,
    program_actions,
    programs_for_goal,
)

SCHEMA = "PROJECT_BRAIN_REAL_COMPUTER_PERFECT_ALGORITHM_V1"
KIND = "computer_file_ops"


def narrow_programs_for_goal(goal: str, limit: int = 8) -> list[str]:
    """The programs whose own manuals say they can do this goal (bounded).

    Reuses the environment's existing narrowing -- the one place the "right
    question" is asked about the world.
    """
    programs = programs_for_goal(goal, limit=limit)
    return [p for p in programs]


class RealComputerEnv:
    """The env-protocol wrapper over ComputerEnv for pa.run / el.drive.

    reset/state/act/snapshot/restore/action_names, all delegating to a real
    ComputerEnv. The state is the full file tree (name, content) so that
    verification and closeness are computed from the observed truth, never
    from a synthesized proxy.
    """

    kind = KIND

    def __init__(self, seed_contents: Mapping[str, bytes],
                 programs: Sequence[str], target_name: str,
                 goal: str | None = None,
                 root: str | pathlib.Path | None = None) -> None:
        self.root = pathlib.Path(root) if root else pathlib.Path(
            tempfile.mkdtemp(prefix="brain-real-computer-"))
        self.root.mkdir(parents=True, exist_ok=True)
        self._seed = dict(seed_contents)
        self._target_name = target_name
        self._goal = goal
        self._env = ComputerEnv(seed=self._seed, root=self.root,
                                programs=list(programs))
        target = target_name
        # one action per goal-narrowed program; same construction the
        # environment's own search uses (argv + kept-or-discarded verification)
        is_goal = goal_predicate_for(self._seed, target)

        # the action must satisfy the goal's own claim -- an archive with the
        # right name is not an archive unless its bytes verify. the same
        # predicate the scan applies as the success condition is the one the
        # action holds itself to.
        def _verify(tree):
            try:
                return bool(is_goal(tree))
            except Exception:  # noqa: BLE001
                return False

        self._env.register(program_actions(self._env, list(programs),
                                           target=target, goal=goal,
                                           verify=_verify))
        self._env.reset()

    # -- the computer it wraps --------------------------------------------- #
    @property
    def wrapped(self):
        return self._env

    @property
    def root_path(self):
        return self._env.root

    @property
    def target_name(self):
        return self._target_name

    # -- env protocol ------------------------------------------------------ #
    def reset(self) -> None:
        self._env.reset()

    def state(self) -> tuple:
        """The observation to index: the full file tree. A digest is less
        information than the scan deserves; the perfect algorithm indexes
        on structure, and the structure is the files."""
        return tuple(sorted(self.tree().items()))

    def snapshot(self):
        return self.state()

    def restore(self, token) -> None:
        for child in list(self._env.root.iterdir()):
            if child.is_dir():
                import shutil
                shutil.rmtree(child, ignore_errors=True)
            else:
                child.unlink()
        files = dict(token or ())
        for name, content in files.items():
            target = self._env.root / name
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(content)

    def tree(self) -> dict[str, bytes]:
        """The observed file tree: name -> bytes."""
        out: dict[str, bytes] = {}
        for path in sorted(self._env.root.rglob("*")):
            if path.is_file():
                rel = path.relative_to(self._env.root).as_posix()
                try:
                    out[rel] = path.read_bytes()
                except OSError:
                    out[rel] = b""
        return out

    def act(self, action: str):
        return self._env.act(action)

    def action_names(self):
        return sorted(self._env.action_names)

    def close(self) -> None:
        self._env.close()

    def is_goal(self) -> bool:
        return goal_predicate_for(self._seed, self._target_name)(self.tree())


def _files_from_state(state) -> dict[str, bytes]:
    try:
        return dict(state or ())
    except Exception:
        return {}


def tree_of(env) -> dict[str, bytes]:
    return env.tree() if hasattr(env, "tree") else dict(env.state() or ())


def goal_predicate_for(seed: Mapping[str, bytes], target_name: str) -> Callable[[tuple], bool]:
    """A predicate over the OBSERVED file-tree state.

    Each format is checked exactly as the goal claims it:
      - tar-family archives (.tar, .tar.gz/.tgz, .tar.bz2/.tbz2, .tar.xz/.txz):
        the target is a real tar archive that contains the source file,
        and the contained file's bytes are the source's bytes.
      - .zip: the target is a real zip archive that contains the source file
        by basename, and its bytes are the source's bytes.
      - .gz / .bz2 / .xz: the target decompresses to the source the goal named.
      - plain target, compressed/archive source ("decompress X into out.txt"):
        the target must equal the decompressed content of that source --
        the member's bytes for a single-member archive, the decompressed bytes
        for a single-file format.
      - anything else (plain file): the target exists and is non-empty.
    """
    import io as _io
    import tarfile as _tarfile
    import bz2 as _bz2
    import lzma as _lzma
    import zipfile as _zipfile
    import hashlib as _hashlib

    _HASH_SUFFIXES = {
        ".sha256": "sha256",
        ".sha512": "sha512",
        ".sha1": "sha1",
        ".md5": "md5",
    }

    def _hash_line_matches(tgt: bytes, src: bytes, algo: str) -> bool:
        # GNU "hash  filename", BSD "SHA256 (name) = hash", or a bare digest:
        # the file is the checksum of the source iff the digest of the source
        # appears in it -- the digest cannot be produced for the wrong source.
        expected = _hashlib.new(algo, src).hexdigest()
        text = tgt.decode("utf-8", "ignore")
        return bool(text.strip()) and expected in text

    src_names = sorted(seed)
    src_name = src_names[0] if src_names else None

    def _tar_members(tgt: bytes, mode: str) -> dict[str, bytes]:
        out: dict[str, bytes] = {}
        try:
            with _tarfile.open(fileobj=_io.BytesIO(tgt), mode=mode) as tf:
                for member in tf.getmembers():
                    if member.isfile():
                        fobj = tf.extractfile(member)
                        if fobj is not None:
                            out[member.name] = fobj.read()
        except Exception:
            return {}
        return out

    def _zip_members(tgt: bytes) -> dict[str, bytes]:
        out: dict[str, bytes] = {}
        try:
            with _zipfile.ZipFile(_io.BytesIO(tgt)) as zf:
                for info in zf.infolist():
                    if not info.is_dir():
                        try:
                            out[info.filename] = zf.read(info)
                        except Exception:  # noqa: BLE001
                            continue
        except Exception:
            return {}
        return out

    def _in_archive(members: dict[str, bytes], src: bytes) -> bool:
        # the archive is the claim: the source file is IN it, unchanged
        for m_name, m_bytes in members.items():
            path_part = m_name.rstrip("/").rsplit("/", 1)[-1]
            if path_part == src_name and m_bytes == src:
                return True
        return False

    _TAR_MODES = {
        ".tar": "r:",
        ".tar.gz": "r:gz",
        ".tgz": "r:gz",
        ".tar.bz2": "r:bz2",
        ".tbz2": "r:bz2",
        ".tar.xz": "r:xz",
        ".txz": "r:xz",
    }

    def is_goal(state) -> bool:
        files = dict(state or ())
        src = files.get(src_name)
        tgt = files.get(target_name, b"")
        if src is None or not tgt:
            return False

        for suffix in sorted(_TAR_MODES, key=lambda s: -len(s)):
            if target_name.endswith(suffix):
                members = _tar_members(tgt, _TAR_MODES[suffix])
                return _in_archive(members, src)

        if target_name.endswith(".zip"):
            members = _zip_members(tgt)
            return _in_archive(members, src)

        if target_name.endswith(".gz"):
            try:
                return gzip.decompress(tgt) == src
            except Exception:
                return False
        if target_name.endswith(".bz2"):
            try:
                return _bz2.decompress(tgt) == src
            except Exception:
                return False
        if target_name.endswith(".xz"):
            try:
                return _lzma.decompress(tgt) == src
            except Exception:
                return False
        # Hash-format targets: the target must carry the hash OF THE SOURCE.
        # The honest claim -- "hash input.txt into out.sha256": the file is a
        # checksum of that exact file, not of a different source, not of a
        # plausible-looking checksum the machine wrote from thin air.
        for suffix, algo in sorted(_HASH_SUFFIXES.items(), key=lambda kv: -len(kv[0])):
            if target_name.endswith(suffix):
                return _hash_line_matches(tgt, src, algo)

        # Plain target over a compressed/archive source: the claim is that the
        # target is the decompressed content of the source, not merely a
        # non-empty file. A source shape we cannot verify is refused, never
        # passed.
        src_suffix = next((s for s in sorted(_TAR_MODES, key=lambda s: -len(s))
                          if src_name.endswith(s)), None)
        if src_suffix is not None:
            members = _tar_members(src, _TAR_MODES[src_suffix])
            if len(members) == 1:
                return tgt == next(iter(members.values()))
            return False  # multiple/garbage members: cannot claim content
        if src_name.endswith(".zip"):
            members = _zip_members(src)
            if len(members) == 1:
                return tgt == next(iter(members.values()))
            return False  # cannot claim content
        if src_name.endswith(".gz"):
            try:
                return gzip.decompress(src) == tgt
            except Exception:
                return False
        if src_name.endswith(".bz2"):
            try:
                return _bz2.decompress(src) == tgt
            except Exception:
                return False
        if src_name.endswith(".xz"):
            try:
                return _lzma.decompress(src) == tgt
            except Exception:
                return False

        return True

    return is_goal


def heuristic_for(environment: Any, seed: Mapping[str, bytes],
                  target_name: str) -> Callable[[tuple], float]:
    """Closeness over the observed file tree: 0 when the goal holds.

    Admissibility is honest: the A* with this heuristic prefers paths that
    reach the 0-cost goal; ties are broken by depth (higher g) in the scan.
    """
    is_goal = goal_predicate_for(seed, target_name)

    def h(snapshot) -> float:
        try:
            files = snapshot
            if not isinstance(files, dict):
                files = dict(files or ())
            return 0.0 if is_goal(files) else 1.0
        except Exception:
            return 1.0

    return h


def build_env(goal: str, seed_contents: Mapping[str, bytes] | None = None,
              seed_file: str | pathlib.Path | None = None,
              limit: int = 8, root: str | pathlib.Path | None = None,
              ) -> tuple[RealComputerEnv, dict[str, Any]]:

    """Build the adapter over a narrowed real-env action space.

    Returns the env and the metadata the probes need (target name, goal
    predicate, heuristic, goal str).
    """
    if seed_file is not None:
        src_path = pathlib.Path(seed_file)
        seed = {src_path.name: src_path.read_bytes()}
    else:
        seed = dict(seed_contents if seed_contents is not None else {
            "seed.txt": b"brain real-computer env sample\nsecond line\n"})
    named = output_name(goal)
    if not named:
        raise ValueError("NO_OUTPUT_NAME_IN_GOAL")
    target = named
    programs = narrow_programs_for_goal(goal, limit=limit)
    env = RealComputerEnv(seed, programs, target, goal=goal, root=root)
    is_goal = goal_predicate_for(seed, target)
    heuristic = heuristic_for(env, seed, target)
    return env, {"goal": goal, "target": target, "programs": programs,
                 "is_goal": is_goal, "heuristic": heuristic,
                 "source_name": next(iter(seed))}


def drive_perfect_algorithm(goal: str,
                            seed_contents: Mapping[str, bytes] | None = None,
                            seed_file: str | pathlib.Path | None = None,
                            *,
                            limit: int = 8,
                            budget: int = 60,
                            max_depth: int = 4,
                            memory: dict[str, Any] | None = None,
                            memory_path_: str | pathlib.Path | None = None,
                            prior: Mapping[str, Any] | None = None,
                            ):
    """Run the perfect algorithm on a real computer environment.

    Cold path: an empty in-memory memory (nothing loaded from disk). The
    default path writes priors into `memory_path_` -- point that at a
    disposable file, never at the real TRANSFER_LEARNING_EPISODES store, or
    the kind/goal records will leak into real probes.

    Returns (receipts, meta, env). The env may be closed by the caller.
    """
    from canonical.swe_kernel import perfect_algorithm_v1 as pa

    env, meta = build_env(goal, seed_contents=seed_contents, seed_file=seed_file,
                         limit=limit)
    receipts = pa.run(
        env, goal, env.action_names(),
        goal_predicate=meta["is_goal"],
        env_kind=KIND,
        memory=memory if memory is not None else {"rules": [], "priors": {}},
        memory_path_=memory_path_,
        budget=budget,
        max_depth=max_depth,
        heuristic=meta["heuristic"],
        prior=prior,
    )
    return receipts, meta, env
