"""Is the value right, when nobody knows the right value?

Structural checks answer "did the world change". They cannot answer "is
the number correct", because to check a value you must know what it
should be -- and asking the thing that produced it what it should have
produced is a circle, not a check.

The way out is not to know the answer. It is to know the PROPERTIES that
every correct answer must have:

    a sort is ordered, and is a permutation of its input
    encode then decode is the identity
    a report's row count equals the records it came from
    the parts sum to the whole

None of these requires knowing the right answer in advance, and all of
them are checkable by deterministic code. That is what makes them
independent of the implementation being judged.

Which leaves the real question: who writes the properties? If the thing
under examination writes them, it writes weak ones. The literature is
blunt about this -- VeriAct notes that `ensures true` satisfies any
verifier, and SEAL found agents whose self-tests saturated and certified
policies that scored below random.

So each property is validated by MUTATION. Deliberately wrong outputs are
generated -- generic ones, needing no knowledge of the domain -- and the
property must reject them. A property that no wrong answer violates has
no discriminative power, whatever it claims. Mutation score is the
independence test, and it is the same rule applied throughout this
system: a check that cannot fail is not a check.

Two mutants are non-negotiable. If a property accepts the EMPTY output or
a TRUNCATED one, it is disqualified outright rather than merely scored
down, because there is no reading of any task on which those are right.
"""
from __future__ import annotations

import os
import re
import subprocess
import tempfile
from pathlib import Path

SCHEMA = "PROJECT_BRAIN_PROPERTY_V1"

# A property accepts by exiting zero and rejects by exiting non-zero.
# Exit status is used because the kernel decides it: the property cannot
# flatter itself by printing something reassuring.
ACCEPT = 0


def _run(command: str, cwd: str, timeout: int) -> tuple[int | None, str]:
    try:
        r = subprocess.run(command, shell=True, cwd=cwd, timeout=timeout,
                           capture_output=True, text=True)
        return r.returncode, ((r.stdout or "") + (r.stderr or ""))[-4000:]
    except subprocess.TimeoutExpired:
        return None, "timed out"
    except Exception as exc:
        return None, f"{type(exc).__name__}: {exc}"


def mutate(text: str) -> list[tuple[str, str]]:
    """Deliberately wrong variants, needing no knowledge of the domain.

    These are generic on purpose. A mutation tailored to one artifact
    would only measure whether the property knows that artifact, and
    would flatter it. Truncation, deletion and perturbation are wrong for
    every artifact there is, which is what makes the score mean
    something.
    """
    lines = text.splitlines()
    out: list[tuple[str, str]] = []

    if not lines:
        return [("empty", "")]

    out.append(("empty", ""))

    if len(lines) > 1:
        half = max(1, len(lines) // 2)
        out.append(("truncated", "\n".join(lines[:half]) + "\n"))
        out.append(("reversed", "\n".join(reversed(lines)) + "\n"))
        # Drop the line most likely to matter: the last non-blank one.
        keep = [i for i, ln in enumerate(lines) if ln.strip()]
        if keep:
            victim = keep[-1]
            out.append(("last_line_removed",
                        "\n".join(ln for i, ln in enumerate(lines) if i != victim) + "\n"))
        if len(keep) > 1:
            victim = keep[0]
            out.append(("first_line_removed",
                        "\n".join(ln for i, ln in enumerate(lines) if i != victim) + "\n"))

    # Perturb every number: a value that is off by one is still a value.
    def bump(m: re.Match) -> str:
        return str(int(m.group(0)) + 1)

    perturbed, n = re.subn(r"\b\d+\b", bump, text)
    if n:
        out.append(("numbers_perturbed", perturbed))

    out.append(("corrupted", text + "\nCORRUPTION\n"))
    return out


def score(property_command: str, good: str, workdir: str | None = None,
          timeout: int = 60, minimum: float = 0.5,
          filename: str = "artifact.txt") -> dict:
    """How well does this property tell right from wrong?

    The property is run against a known-good artifact, which it MUST
    accept, and against every mutant, which it should reject. Returns the
    kill rate, the survivors, and whether the property is admissible.
    """
    tmp = workdir or tempfile.mkdtemp(prefix="brain_property_")
    base = Path(tmp)
    base.mkdir(parents=True, exist_ok=True)
    target = base / filename
    owned = workdir is None

    def against(text: str) -> tuple[int | None, str]:
        target.write_text(text)
        return _run(property_command, tmp, timeout)

    try:
        code, why = against(good)
        if code != ACCEPT:
            return {
                "schema": SCHEMA, "admissible": False,
                "reason": "PROPERTY_REJECTS_THE_TRUTH",
                "detail": f"it rejected the known-good artifact: {why[:200]}",
                "score": 0.0, "kills": 0, "total": 0,
                "survivors": [], "disqualified": True,
            }

        mutants = mutate(good)
        kills, survivors, disqualified = 0, [], False
        for name, text in mutants:
            mcode, _mwhy = against(text)
            if mcode is None:
                survivors.append(name)
                continue
            if mcode == ACCEPT:
                survivors.append(name)
                # No reading of any task on which these are right.
                if name in ("empty", "truncated"):
                    disqualified = True
            else:
                kills += 1

        total = len(mutants)
        rate = (kills / total) if total else 0.0
        admissible = (not disqualified) and rate >= minimum
        return {
            "schema": SCHEMA,
            "admissible": admissible,
            "score": round(rate, 4),
            "kills": kills,
            "total": total,
            "survivors": survivors,
            "disqualified": disqualified,
            "minimum": minimum,
            "reason": ("DISQUALIFIED_ACCEPTS_EMPTY_OR_TRUNCATED" if disqualified
                       else ("ADMISSIBLE" if admissible
                             else f"score {rate:.2f} below {minimum}")),
        }
    finally:
        if owned:
            try:
                target.unlink(missing_ok=True)
            except OSError:
                pass


def check(property_command: str, candidate: str, workdir: str | None = None,
          timeout: int = 60, filename: str = "artifact.txt") -> dict:
    """Does this property hold for this candidate?"""
    tmp = workdir or tempfile.mkdtemp(prefix="brain_property_")
    base = Path(tmp)
    base.mkdir(parents=True, exist_ok=True)
    (base / filename).write_text(candidate)
    code, why = _run(property_command, tmp, timeout)
    if code is None:
        return {"schema": SCHEMA, "verdict": "UNVERIFIABLE", "detail": why}
    return {
        "schema": SCHEMA,
        "verdict": "HOLDS" if code == ACCEPT else "VIOLATED",
        "exit_status": code,
        "detail": why[-500:],
    }


if __name__ == "__main__":
    with tempfile.TemporaryDirectory() as tmp:
        good = "rows: 3\ntotal: 42\nstatus: ok\n"

        # A real property: rows must be 3 and total must be 42.
        strong = (r"""python3 -c "
import sys,re
t=open('artifact.txt').read()
assert re.search(r'rows:\s*3\b',t),'rows'
assert re.search(r'total:\s*42\b',t),'total'
" """)
        # A vacuous property: always satisfied, certifies nothing.
        weak = "true"

        for label, prop in (("meaningful", strong), ("vacuous (exit 0 always)", weak)):
            r = score(prop, good, workdir=tmp)
            print(f"{label:<24} admissible={str(r['admissible']):<5} "
                  f"score={r['score']:<6} {r['reason']}")
            if r["survivors"]:
                print(f"{'':<24} survived: {', '.join(r['survivors'][:6])}")
