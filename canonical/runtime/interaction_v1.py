"""Learn how actions INTERACT, not just how each scores alone.

Everything before this judged actions one at a time: run it, see if it
changed anything, score it. But competence in an environment is mostly
about how actions relate to each other:

    A produces out/good.txt
    B deletes out/good.txt        <- B undoes A, and no single-action
                                     score will ever notice
    C must run before D           <- ordering

A machine that cannot see this will happily build something and then run
the step that deletes it. env_hard2 contained exactly this trap and the
system survived it only by refusing destructive commands outright -- a
blunt rule that works and understands nothing.

This learns the relations from EVIDENCE: run each action in isolation from
the SAME starting state, and compare what each one added and removed.

Isolation is the whole trick. Run B after A and you see "B changed
nothing"; run it from the original state and you see "B deleted
out/good.txt". Only the second is the truth about B.

Produces:
    produces / destroys / modifies   path sets per action
    conflicts   one action removes what another creates
    clashes     two actions write the same path
    order_hint  producers before consumers, destroyers last
"""
from __future__ import annotations

import shutil
import subprocess
import tempfile
from pathlib import Path

SCHEMA = "PROJECT_BRAIN_INTERACTION_V1"


def _snapshot(root: Path) -> set:
    out = set()
    for p in root.rglob("*"):
        if p.is_file():
            try:
                st = p.stat()
                # mtime matters: rewriting a file with identical content
                # changes nothing about size, and without time the action
                # looks like it did nothing at all.
                out.add((str(p.relative_to(root)), st.st_size,
                         st.st_mtime_ns))
            except OSError:
                pass
    return out


def _paths(delta) -> set:
    return {t[0] for t in delta}


def probe_isolated(root: str, commands: list[list[str]],
                   timeout_s: int = 60) -> list[dict]:
    """Run each command against a pristine copy, so effects don't mask each other."""
    rootp = Path(root).resolve()
    base = _snapshot(rootp)
    results = []
    for cmd in commands:
        tmp = Path(tempfile.mkdtemp(prefix="brain_iso_"))
        work = tmp / "work"
        try:
            shutil.copytree(rootp, work,
                            ignore=shutil.ignore_patterns(".git", "__pycache__"))
            try:
                subprocess.run(cmd, cwd=work, capture_output=True,
                               timeout=max(1, min(timeout_s, 300)))
                rc = 0
            except Exception:
                rc = -1
            after = _snapshot(work)
            base_paths = _paths(base)
            results.append({
                "argv": cmd,
                "added": sorted(_paths(after - base)),
                "removed": sorted(_paths(base - after)),
                "modified": sorted(
                    {t[0] for t in after if t[0] in base_paths
                     and t not in base}),
                "returncode": rc,
            })
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
    return results


def analyze(root: str, commands: list[list[str]],
            two_phase: bool = True) -> dict:
    """The interaction graph.

    ONE PHASE IS NOT ENOUGH, and env_hard3 proved it. Probing every action
    from a pristine copy shows what each one PRODUCES -- but a cleaner run
    against an empty output directory has nothing to delete, so it looks
    perfectly harmless. `python3 clean.py` deleted out/app.txt and single
    phase analysis reported no conflict at all.

    You can only observe destruction if the thing destroyed already exists.

    So: phase 1 discovers producers by isolation; phase 2 lets the producers
    actually run, then probes everything again on that BUILT state, where
    deletion is finally observable. Isolation finds creation. Composition
    finds destruction.
    """
    """The interaction graph, learned from isolated runs."""
    recs = probe_isolated(root, commands)
    if two_phase:
        recs = _augment_with_built_state(root, commands, recs)
    produces, destroys, modifies = {}, {}, {}
    for r in recs:
        key = " ".join(r["argv"])
        # Rewriting an existing file is producing it. If out/good.txt is
        # already there from an earlier run, re-running the publisher adds
        # nothing -- but it still produced that file, and saying otherwise
        # is how a destroyer goes unmatched to its producer.
        produces[key] = set(r["added"]) | set(r["modified"])
        destroys[key] = set(r["removed"])
        modifies[key] = set(r["modified"])

    conflicts, clashes = [], []
    keys = list(produces)
    for i, a in enumerate(keys):
        for b in keys[i + 1:]:
            shared = produces[a] & destroys[b]
            if shared:
                conflicts.append({"producer": a, "destroyer": b,
                                  "paths": sorted(shared)})
            if destroys[a] & destroys[b]:
                pass
            shared_w = (produces[a] | modifies[a]) & (produces[b] | modifies[b])
            if shared_w:
                clashes.append({"a": a, "b": b, "paths": sorted(shared_w)})

    # Order: anything producing something goes before anything removing it.
    destroyers = {c["destroyer"] for c in conflicts}
    order = [k for k in keys if k not in destroyers] + \
            [k for k in keys if k in destroyers]

    return {"schema": SCHEMA,
            "actions": len(recs),
            "produces": {k: sorted(v) for k, v in produces.items()},
            "destroys": {k: sorted(v) for k, v in destroys.items()},
            "conflicts": conflicts,
            "clashes": clashes,
            "suggested_order": order,
            "records": recs}


if __name__ == "__main__":
    import sys, json
    root = sys.argv[1] if len(sys.argv) > 1 else "."
    cmds = [["sh", "-c", "python3 ops/deep/deeper/publish.py"],
            ["sh", "-c", "rm -f out/good.txt"]]
    r = analyze(root, cmds)
    print(json.dumps({k: v for k, v in r.items() if k != "records"},
                     indent=2)[:1200])


def _augment_with_built_state(root: str, commands: list[list[str]],
                              recs: list[dict]) -> list[dict]:
    """Phase 2: let the producers run, then probe again on the built state.

    Deletion is only observable where there is something to delete, so build
    first and look again. Whatever the second pass reveals is merged into the
    isolation results.
    """
    rootp = Path(root).resolve()
    tmp = Path(tempfile.mkdtemp(prefix="brain_built_"))
    work = tmp / "work"
    by_key = {" ".join(r["argv"]): r for r in recs}
    try:
        shutil.copytree(rootp, work,
                        ignore=shutil.ignore_patterns(".git", "__pycache__"))
        # Phase 1 told us who creates something. Let them run.
        for r in recs:
            if r.get("added") or r.get("modified"):
                try:
                    subprocess.run(r["argv"], cwd=work, capture_output=True,
                                   timeout=300)
                except Exception:
                    pass
        built = _snapshot(work)
        built_paths = _paths(built)
        # Re-probe on the built state, where deletion finally shows.
        for i, cmd in enumerate(commands):
            w2 = tmp / ("probe_%d" % i)
            try:
                if w2.exists():
                    shutil.rmtree(w2)
                shutil.copytree(work, w2)
                try:
                    subprocess.run(cmd, cwd=w2, capture_output=True,
                                   timeout=300)
                except Exception:
                    pass
                after_paths = _paths(_snapshot(w2))
                rec = by_key.get(" ".join(cmd))
                if rec is None:
                    continue
                rec["removed"] = sorted(
                    set(rec.get("removed") or [])
                    | (built_paths - after_paths))
            finally:
                shutil.rmtree(w2, ignore_errors=True)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    return recs
