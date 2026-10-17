"""Is this claim about the machine actually true? Re-read it and find out.

Every other capability here is verified against something the machine
attests. A claim about a system was not. It could be asserted, and nothing
checked it, which is the one place where the system could agree with
itself. "Not Self-Decidable" (arXiv:2610.04699) puts it exactly:

    a check over a field the agent asserts establishes only that the
    agent agreed with itself.

So a claim must name where its evidence lives, and the machine re-reads
the bytes. The claim is not evaluated, weighed or interpreted -- it is
looked up. That is the whole mechanism, and it is the same one used
everywhere else: do not ask the program, ask the machine.

Three verdicts, and the third is why this exists:

    GROUNDED      the cited evidence contains what was claimed.
    CONTRADICTED  it was read, and it says something else.
    UNVERIFIABLE  it could not be read -- missing, unreadable, or the
                  claim cites no evidence at all.

UNVERIFIABLE is not a soft yes. A claim that cannot be checked is not a
supported claim, and collapsing it into GROUNDED would be the oldest
failure in this codebase: a check affirming when it should stay silent.
Reporting it as its own verdict is what keeps "I could not tell" from
becoming "yes".

Claims are ordinary data, so they can be written down, stored beside the
work, and re-checked later -- after the files have moved, or after someone
has edited them.
"""
from __future__ import annotations

import hashlib
import re
import subprocess
from pathlib import Path

SCHEMA = "PROJECT_BRAIN_GROUNDING_V1"

GROUNDED = "GROUNDED"
CONTRADICTED = "CONTRADICTED"
UNVERIFIABLE = "UNVERIFIABLE"


def _read(path: Path, limit: int = 20_000_000) -> str | None:
    """The bytes, or None when they cannot be had.

    None rather than "" -- an empty file and an unreadable file are
    different facts, and conflating them turns every missing file into a
    file that contradicts everything.
    """
    try:
        if not path.is_file():
            return None
        if path.stat().st_size > limit:
            return None
        return path.read_text(errors="ignore")
    except OSError:
        return None


def _resolve(root: str, name: str) -> Path | None:
    """A path inside the project, or None if it escapes or climbs out.

    Reading is as much an action as writing, and a claim that cites
    ../../etc/passwd is not asking about the project.
    """
    if not name:
        return None
    path = Path(name)
    if path.is_absolute() or ".." in Path(name).parts:
        return None
    resolved = (Path(root) / path).resolve()
    base = Path(root).resolve()
    if resolved != base and base not in resolved.parents:
        return None
    return resolved


def check(claim: dict, root: str = ".", timeout: int = 60) -> dict:
    """Verify one claim against the machine.

    A claim is a mapping naming both what is asserted and where the
    evidence for it lives. Recognised forms:

        {"file": "src/a.py", "contains": "def f"}      literal text
        {"file": "src/a.py", "matches": "def f\\("}    a pattern
        {"file": "src/a.py", "absent":  "TODO"}        must NOT be there
        {"path": "src/a.py", "exists": true}           presence
        {"command": "python3 -V", "matches": "3\\."}    observed output

    Anything else is UNVERIFIABLE, because a claim in a form that cannot
    be checked has no business being believed.
    """
    def verdict(state: str, evidence: str = "", **extra) -> dict:
        result = {"schema": SCHEMA, "verdict": state, "claim": claim,
                  "evidence": evidence}
        result.update(extra)
        return result

    if not isinstance(claim, dict) or not claim:
        return verdict(UNVERIFIABLE, "no claim")

    # --- presence -----------------------------------------------------
    if "path" in claim and "exists" in claim:
        target = _resolve(root, str(claim.get("path") or ""))
        if target is None:
            return verdict(UNVERIFIABLE, f"path {claim.get('path')!r} is outside the project")
        exists = target.exists()
        wanted = bool(claim.get("exists"))
        if exists is wanted:
            return verdict(GROUNDED, f"{target.name} {'exists' if exists else 'is absent'}")
        return verdict(CONTRADICTED,
                       f"{target.name} {'exists' if exists else 'is absent'}")

    # --- command output ------------------------------------------------
    if "command" in claim and ("contains" in claim or "matches" in claim):
        try:
            r = subprocess.run(str(claim["command"]), shell=True, cwd=root,
                               timeout=timeout, capture_output=True, text=True)
            out = (r.stdout or "") + (r.stderr or "")
        except subprocess.TimeoutExpired:
            return verdict(UNVERIFIABLE, "command timed out")
        except Exception as exc:
            return verdict(UNVERIFIABLE, f"command did not run: {exc}")
        needle = str(claim.get("contains") or "")
        pattern = claim.get("matches")
        if needle:
            hit = needle in out
            why = f"output {'contains' if hit else 'does not contain'} {needle[:60]!r}"
        else:
            try:
                hit = re.search(str(pattern), out) is not None
            except re.error as exc:
                return verdict(UNVERIFIABLE, f"bad pattern: {exc}")
            why = f"output {'matches' if hit else 'does not match'} {str(pattern)[:60]!r}"
        result = verdict(GROUNDED if hit else CONTRADICTED, why)
        result["exit_status"] = r.returncode
        return result

    # --- file contents -------------------------------------------------
    name = claim.get("file")
    if not name:
        return verdict(UNVERIFIABLE, "claim names no file, command or path")
    target = _resolve(root, str(name))
    if target is None:
        return verdict(UNVERIFIABLE, f"path {name!r} is outside the project")
    text = _read(target)
    if text is None:
        return verdict(UNVERIFIABLE, f"{name} could not be read")

    digest = hashlib.sha256(text.encode("utf-8", "replace")).hexdigest()[:16]

    if "contains" in claim:
        needle = str(claim["contains"])
        hit = needle in text
        base = verdict(GROUNDED if hit else CONTRADICTED,
                       f"{name} {'contains' if hit else 'does not contain'} {needle[:60]!r}",
                       sha256=digest, lines=text.count("\n") + 1)
        if hit:
            base["at_line"] = text[:text.index(needle)].count("\n") + 1
        return base

    if "matches" in claim:
        try:
            m = re.search(str(claim["matches"]), text)
        except re.error as exc:
            return verdict(UNVERIFIABLE, f"bad pattern: {exc}")
        base = verdict(GROUNDED if m else CONTRADICTED,
                       f"{name} {'matches' if m else 'does not match'} "
                       f"{str(claim['matches'])[:60]!r}",
                       sha256=digest, lines=text.count("\n") + 1)
        if m:
            base["at_line"] = text[:m.start()].count("\n") + 1
            base["matched"] = m.group(0)[:200]
        return base

    if "absent" in claim:
        needle = str(claim["absent"])
        hit = needle in text
        return verdict(CONTRADICTED if hit else GROUNDED,
                       f"{name} {'contains' if hit else 'does not contain'} {needle[:60]!r}",
                       sha256=digest, lines=text.count("\n") + 1)

    return verdict(UNVERIFIABLE,
                   "claim has no contains, matches or absent to check against")


def check_all(claims, root: str = ".", timeout: int = 60) -> dict:
    """Verify a set of claims. Every one must hold.

    UNVERIFIABLE counts against the set. A report that is nine tenths
    grounded and one tenth uncheckable is not a grounded report, and
    averaging them would let the unverifiable tenth ride on the rest.
    """
    claims = list(claims or [])
    results = [check(c, root, timeout=timeout) for c in claims]
    grounded = sum(1 for r in results if r["verdict"] == GROUNDED)
    contradicted = sum(1 for r in results if r["verdict"] == CONTRADICTED)
    unverifiable = sum(1 for r in results if r["verdict"] == UNVERIFIABLE)
    if contradicted:
        overall = CONTRADICTED
    elif unverifiable:
        overall = UNVERIFIABLE
    elif claims:
        overall = GROUNDED
    else:
        overall = UNVERIFIABLE
    return {
        "schema": SCHEMA,
        "verdict": overall,
        "total": len(results),
        "grounded": grounded,
        "contradicted": contradicted,
        "unverifiable": unverifiable,
        # Only true when every claim was actually checked and held.
        "all_grounded": bool(claims) and grounded == len(results),
        "results": results,
    }


if __name__ == "__main__":
    import tempfile

    with tempfile.TemporaryDirectory() as tmp:
        Path(tmp, "a.py").write_text("def f(x):\n    return x + 1\n")
        for claim in [
            {"file": "a.py", "contains": "def f(x)"},
            {"file": "a.py", "matches": r"return x \+ 1"},
            {"file": "a.py", "contains": "def g(x)"},
            {"file": "missing.py", "contains": "anything"},
            {"file": "a.py", "absent": "TODO"},
            {"file": "../outside.py", "contains": "x"},
            {"command": "echo hello", "contains": "hello"},
            {"file": "a.py"},
        ]:
            r = check(claim, tmp)
            extra = ""
            if r.get("at_line"):
                extra = f" (line {r['at_line']})"
            print(f"{r['verdict']:<14} {claim}  {r['evidence'][:44]}{extra}")
