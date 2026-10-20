"""Did the world change the way the action intended? Read it. Do not ask.

Why this exists
---------------
A user sitting at a machine does something no benchmark measures: they
look. Not at a report of what happened -- at what happened. The file is
there or it is not. The value in the cell is the one they wanted or it
is not.

Everything else about "using a computer" is downstream of that. Choosing
an action is the easy part; any model can emit a keystroke. What makes
computer use hard -- and what makes it possible at all on an application
nobody has seen before -- is knowing whether the action landed.

First principles
----------------
A computer is a state machine over bytes. That is the whole of it: files,
memory, the screen and the network are all bytes, and the machine will
report those bytes on request at interfaces the running program cannot
forge. A road will not tell you its geometry. A computer will tell you
its state. Computer use is therefore *more* tractable than driving, not
less -- provided the question is asked at the right interface.

The wrong interface is the program's own account of itself. "OK" printed
to stdout is a sentence the program chose to say. The exit status is a
fact the kernel decided. The first can be written by anything at all;
the second cannot be written by the thing being judged.

So every fact below carries where it came from and whether the actor
under examination could have written it. A fact the actor can write is
evidence about the actor, not about the world.

What this cannot do
-------------------
A state diff alone cannot tell you whether a value is *right*, and the
module says so rather than implying otherwise. StateAct (arXiv:2607.22798)
is exact about the ceiling: reading state catches structural failures --
missing, unsaved, wrong path, wrong shape -- and still passes 68 of 76
imperfect tasks whose error is in the value, because re-deriving a value
from the same source under the same interpretation reproduces the same
mistake. ERPBench (arXiv:2609.17885) measured what that gap is worth: one
model committed in 85% of runs and was database-correct in 3%.

So this module has three verdicts, not two. A channel that cannot be
read is INDETERMINATE and is never quietly scored as a pass -- pretending
that an unreadable channel is the same as an unchanged one is precisely
how a system learns to lie to itself while its numbers go up.
"""
from __future__ import annotations

import hashlib
import json
import subprocess
import time
from pathlib import Path

SCHEMA = "PROJECT_BRAIN_ATTESTED_STATE_V1"

# Who produced a fact, and whether the thing being judged could write it.
# The entire discipline is this table: a fact is worth what its source is.
ATTESTED = "attested"   # decided by the kernel; unwritable by the actor
REPORTED = "reported"   # emitted by the program under examination
ABSENT = "absent"       # the channel could not be read at all

# Verdicts. Three, deliberately -- see the module docstring.
CHANGED = "CHANGED"
UNCHANGED = "UNCHANGED"
INDETERMINATE = "INDETERMINATE"
VERIFIED = "VERIFIED"
POSTCONDITION_FAILED = "POSTCONDITION_FAILED"

_MAX_BYTES = 50_000_000
_MAX_FILES = 20_000


def _digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _canon(obj) -> str:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), default=str)


def seal(spec) -> str:
    """Bind a question to the evidence collected for it.

    A receipt is only evidence about the question it was sealed with. This
    is what catches the failure mode where a candidate verifies because
    the question changed underneath it -- the general form of a command
    wired to exit zero. Without the seal, a receipt gathered against one
    request can be presented as an answer to another.
    """
    return _digest(_canon(spec).encode())


def _fact(channel: str, state: str, source: str, **rest) -> dict:
    return {"channel": channel, "state": state, "source": source, **rest}


def file_fact(path: str | Path, root: str = "") -> dict:
    """One file, as the filesystem reports it.

    Size, content hash and mtime are decided by the kernel, not by the
    program that wrote the file, which is why they are worth reading.
    """
    p = Path(path)
    if not p.is_absolute() and root:
        p = Path(root) / p
    try:
        st = p.stat()
    except FileNotFoundError:
        return _fact("file", "ABSENT", ATTESTED, path=str(p), reason="no such file")
    except PermissionError as exc:
        return _fact("file", INDETERMINATE, ABSENT, path=str(p),
                     reason=f"permission denied: {exc}")
    except OSError as exc:
        return _fact("file", INDETERMINATE, ABSENT, path=str(p), reason=str(exc))
    if not p.is_file():
        return _fact("file", "ABSENT", ATTESTED, path=str(p),
                     reason="not a regular file")
    if st.st_size > _MAX_BYTES:
        return _fact("file", INDETERMINATE, ABSENT, path=str(p),
                     reason=f"too large to hash ({st.st_size} bytes)")
    try:
        sha = _digest(p.read_bytes())
    except OSError as exc:
        return _fact("file", INDETERMINATE, ABSENT, path=str(p), reason=str(exc))
    return _fact("file", "PRESENT", ATTESTED, path=str(p),
                 size=st.st_size, sha256=sha, mtime_ns=st.st_mtime_ns)


def tree_fact(root: str, pattern: str = "**/*") -> dict:
    """A whole tree as one hash: every file's content, keyed by relative path.

    This is the fact that makes "did anything anywhere change" answerable
    without knowing in advance which file was supposed to move. It is what
    lets the question be asked in an application nobody has seen.
    """
    base = Path(root)
    if not base.is_dir():
        return _fact("tree", INDETERMINATE, ABSENT, root=str(base),
                     reason="not a directory")
    manifest: dict[str, str] = {}
    try:
        for p in sorted(base.glob(pattern)):
            if not p.is_file():
                continue
            if len(manifest) >= _MAX_FILES:
                # A partial manifest would hash to something that looks
                # authoritative and is not. Refuse rather than truncate.
                return _fact("tree", INDETERMINATE, ABSENT, root=str(base),
                             reason=f"more than {_MAX_FILES} files")
            try:
                manifest[str(p.relative_to(base))] = _digest(p.read_bytes())
            except OSError as exc:
                return _fact("tree", INDETERMINATE, ABSENT, root=str(base),
                             reason=f"unreadable {p.name}: {exc}")
    except OSError as exc:
        return _fact("tree", INDETERMINATE, ABSENT, root=str(base), reason=str(exc))
    return _fact("tree", "PRESENT", ATTESTED, root=str(base),
                 count=len(manifest), sha256=_digest(_canon(manifest).encode()))


_SCREEN_READER = None


def register_screen_reader(fn) -> None:
    """Supply a way to read pixels.

    Pixels are the one channel that shows what a human would see, and the
    only check on a stale accessibility tree -- models follow outdated
    structure up to 88% of the time (arXiv:2607.04334). But a screen that
    cannot be read is not an empty screen, so until one is registered the
    channel reports unreadable rather than unchanged.
    """
    global _SCREEN_READER
    _SCREEN_READER = fn


def screen_fact() -> dict:
    if _SCREEN_READER is None:
        return _fact("screen", INDETERMINATE, ABSENT,
                     reason="no screen reader registered; pixels unreadable here")
    try:
        data = _SCREEN_READER()
    except Exception as exc:
        return _fact("screen", INDETERMINATE, ABSENT,
                     reason=f"{type(exc).__name__}: {exc}")
    if not data:
        return _fact("screen", INDETERMINATE, ABSENT, reason="screen reader returned nothing")
    if isinstance(data, str):
        data = data.encode()
    return _fact("screen", "PRESENT", ATTESTED,
                 bytes=len(data), sha256=_digest(data))


def observe(root: str, files: list[str] | None = None,
            trees: list[str] | None = None, screen: bool = False) -> dict:
    """Read the world now, at interfaces the actor cannot write.

    Returns the facts plus the list of channels that could not be read.
    That list is the important half: a verdict computed while ignoring it
    would be a verdict computed on a world that was never observed.
    """
    facts: dict[str, dict] = {}
    for name in files or []:
        facts[f"file:{name}"] = file_fact(name, root)
    for name in trees or []:
        facts[f"tree:{name}"] = tree_fact(str(Path(root) / name) if name not in (".", "") else root)
    if screen:
        facts["screen"] = screen_fact()

    unreadable = sorted(k for k, v in facts.items() if v["source"] == ABSENT)
    return {"schema": SCHEMA, "time_ns": time.time_ns(), "root": root,
            "facts": facts, "unreadable": unreadable}


def _same(a: dict, b: dict) -> bool:
    """Two readings of the same channel describe the same world."""
    if a.get("state") != b.get("state"):
        return False
    if a.get("state") == INDETERMINATE:
        return False          # two unknowns are not an agreement
    for key in ("sha256", "size", "count", "mtime_ns"):
        if key in a or key in b:
            if a.get(key) != b.get(key):
                return False
    return True


def diff(before: dict, after: dict) -> dict:
    """What the action did to the world.

    `decidable` is the field that keeps this honest: if any channel was
    unreadable either side, the question "did it change" has no answer,
    and this says so instead of defaulting to no.
    """
    fb = before.get("facts", {})
    fa = after.get("facts", {})
    added = sorted(set(fa) - set(fb))
    removed = sorted(set(fb) - set(fa))
    modified, unchanged, unknown = [], [], []
    for key in sorted(set(fa) & set(fb)):
        if fa[key]["source"] == ABSENT or fb[key]["source"] == ABSENT:
            unknown.append(key)
        elif _same(fb[key], fa[key]):
            unchanged.append(key)
        else:
            modified.append(key)
    unknown += sorted(set(before.get("unreadable", [])) | set(after.get("unreadable", [])))
    unknown = sorted(set(unknown))
    return {
        "schema": SCHEMA,
        "added": added, "removed": removed, "modified": modified,
        "unchanged": unchanged, "unknown": unknown,
        "changed": bool(added or removed or modified),
        "decidable": not unknown,
    }


def tests_ran_in(relpath: str):
    """A postcondition: the attested bytes of `relpath` describe a real run.

    This is the rung above the state diff. The diff answers "did the world
    move"; this answers "did it move to the state that was asked for". The
    liar in env_toolchain writes a report saying all tests passed without
    running any -- the file genuinely appears, the diff genuinely fires,
    and the diff alone would call that success. Reading the bytes it wrote
    and asking whether they contain the evidence of a test run is what
    separates the two.

    It is still not proof the tests passed. It is proof the artifact is
    not a forgery, which is a different and cheaper thing, and it is the
    most that can be claimed without an independent re-derivation.
    """
    def check(facts: dict, root: str):
        key = f"file:{relpath}"
        fact = facts.get(key)
        if fact is None or fact.get("source") == ABSENT:
            return None, f"{relpath} could not be read"
        if fact.get("state") != "PRESENT":
            return False, f"{relpath} does not exist"
        try:
            text = Path(fact["path"]).read_text(errors="ignore")
        except OSError as exc:
            return None, f"{relpath} unreadable: {exc}"
        try:
            from repair_v1 import tests_ran
        except ImportError:                      # pragma: no cover
            from canonical.runtime.repair_v1 import tests_ran
        ran, n, _kind = tests_ran(text)
        if not ran:
            return False, f"{relpath} contains no evidence that tests ran"
        return True, f"{relpath} reports {n} tests having run"
    return check


def attest(action: str, root: str, files: list[str] | None = None,
           trees: list[str] | None = None, spec=None, timeout: int = 300,
           screen: bool = False, check=None) -> dict:
    """Run something, then say what it did to the world -- in three states.

    The exit status is recorded because the kernel decides it, and the
    output is attached as a REPORTED fact: hashed so it is comparable,
    never trusted, because the program under examination wrote it. A
    command that exits zero and changes nothing gets UNCHANGED, which is
    the point -- exit zero is not a claim about the world.
    """
    before = observe(root, files, trees, screen)
    try:
        r = subprocess.run(action, shell=True, cwd=root, timeout=timeout,
                           capture_output=True, text=True)
        code = r.returncode
        out = (r.stdout or "") + (r.stderr or "")
        timed_out = False
    except subprocess.TimeoutExpired:
        code, out, timed_out = None, "", True
    except Exception as exc:
        code, out, timed_out = None, f"{type(exc).__name__}: {exc}", False

    after = observe(root, files, trees, screen)
    d = diff(before, after)

    if timed_out or code is None or not d["decidable"]:
        verdict = INDETERMINATE
        check_state, check_reason = None, "state diff undecidable"
    elif not d["changed"]:
        verdict = UNCHANGED
        check_state, check_reason = None, "nothing changed"
    elif check is None:
        verdict = CHANGED
        check_state, check_reason = None, "no postcondition supplied"
    else:
        try:
            check_state, check_reason = check(after.get("facts", {}), root)
        except Exception as exc:
            check_state, check_reason = None, f"{type(exc).__name__}: {exc}"
        if check_state is None:
            verdict = INDETERMINATE
        elif check_state:
            verdict = VERIFIED
        else:
            verdict = POSTCONDITION_FAILED

    return {
        "schema": SCHEMA,
        "action": action,
        "root": root,
        # The two facts that decide, in order of how much they can be lied to.
        "exit_status": code,                      # attested: the kernel decided
        "output_sha256": _digest(out.encode()),   # reported: the program wrote it
        "output_bytes": len(out),
        "before": before,
        "after": after,
        "diff": d,
        "spec_seal": seal(spec) if spec is not None else None,
        "verdict": verdict,
        "postcondition": {"passed": check_state, "reason": check_reason,
                          "supplied": check is not None},
        "timed_out": timed_out,
        # Whether this receipt may be read as an answer to `spec` at all.
        "sealed": spec is not None,
    }


def matches(receipt: dict, spec) -> bool:
    """Was this receipt gathered against this question?

    A receipt with no seal cannot be matched to anything, which is the
    safe default: unsealed evidence is evidence about an unknown request.
    """
    if not receipt.get("sealed"):
        return False
    return receipt.get("spec_seal") == seal(spec)


if __name__ == "__main__":
    import tempfile

    with tempfile.TemporaryDirectory() as tmp:
        Path(tmp, "out").mkdir()
        spec = {"goal": "write a report", "path": "out/report.txt"}

        real = attest("printf 'hello\\n' > out/report.txt", tmp, trees=["out"], spec=spec)
        print("writes the file      ->", real["verdict"],
              "| exit", real["exit_status"], "| sealed:", matches(real, spec))

        liar = attest("echo 'no tests here' && exit 0", tmp, trees=["out"], spec=spec)
        print("claims success, idle ->", liar["verdict"],
              "| exit", liar["exit_status"],
              "| changed:", liar["diff"]["changed"])

        broken = attest("definitely-not-a-command", tmp, trees=["out"], spec=spec)
        print("fails                ->", broken["verdict"], "| exit", broken["exit_status"])

        # A program that writes the report without running anything: the
        # world really does change, so the diff fires. Only reading the
        # bytes it wrote reveals that no test ever ran.
        Path(tmp, "liar.py").write_text(
            "import pathlib\n"
            "pathlib.Path('out/report.txt').write_text('All tests passed\\n')\n")
        lie = attest("python3 liar.py", tmp,
                     files=["out/report.txt"], trees=["out"],
                     spec=spec, check=tests_ran_in("out/report.txt"))
        print("writes a fake report  ->", lie["verdict"],
              "|", lie["postcondition"]["reason"])
        Path(tmp, "honest.py").write_text(
            "import pathlib, unittest\n"
            "pathlib.Path('out/report.txt').write_text('Ran 3 tests\\nOK\\n')\n")
        honest = attest("python3 honest.py", tmp,
                        files=["out/report.txt"], trees=["out"],
                        spec=spec, check=tests_ran_in("out/report.txt"))
        print("writes a real report  ->", honest["verdict"],
              "|", honest["postcondition"]["reason"])

        print("receipt reused on a different question ->",
              matches(real, {"goal": "delete everything", "path": "out/report.txt"}))
