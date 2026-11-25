"""Is the oracle weak, or is the harness using a weak oracle?

``oracle_discriminating_power_v1`` measured that a large share of wrong mutants of the real fix
still pass the *target* test. Two readings are possible, and they imply opposite next moves:

* the oracle is inherently blunt -> search is futile, because a wrong edit is indistinguishable
  from the right one under any test in the repo;
* the oracle is fine but we query it too narrowly -> a wrong edit IS distinguishable, just not by
  the single failing node, and the fix is to judge with more of the suite.

This measures which. For each surviving mutant it runs the whole test FILE the target node lives in
and compares failure sets against the real fix:

    rejected  == the mutant introduces a failure the real fix does not have
    accepted  == failure set identical to the real fix's

A high rejection rate means the discriminating power was already in the repository and the loss was
ours for not asking. Nothing here is a solve attempt.
"""
from __future__ import annotations

import argparse
import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from real_fix_oracle_baseline_v1 import Oracle  # noqa: E402
from oracle_discriminating_power_v1 import (  # noqa: E402
    CORPUS, changed_lines, mutants_of,
)


def _test_files(nodes: list[str]) -> list[str]:
    return sorted({n.split("::")[0] for n in nodes if "::" in n})


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--power", default="/tmp/oracle_power.json")
    ap.add_argument("--workdir", default="/tmp/real")
    ap.add_argument("--out", default="/tmp/oracle_strengthening.json")
    a = ap.parse_args(argv)

    power = json.loads(pathlib.Path(a.power).read_text())
    by_sha = {r["sha"]: r for r in power["rows"] if r.get("well_formed")}
    tasks = json.loads(CORPUS.read_text())["tasks"]
    workdir = pathlib.Path(a.workdir)
    oracles: dict[str, Oracle] = {}
    rows: list[dict] = []

    for t in tasks:
        sha = t["sha"][:10]
        p = by_sha.get(sha)
        if not p or not p.get("survivors"):
            continue
        slug = t["repo"]
        if slug not in oracles:
            oracles[slug] = Oracle(slug, workdir)
            oracles[slug].ensure()
        o = oracles[slug]
        files = _test_files(t["failed_nodes"])
        row = {"repo": slug, "sha": sha, "test_files": files, "survivors": len(p["survivors"])}
        try:
            o.checkout(t["sha"])
            o.write_source(t["source"], t["after"])
            base = o.fail_set(files)
            row["baseline_failures"] = len(base)

            lines = changed_lines(t["before"], t["after"])
            muts = {n: b for n, b in mutants_of(t["after"], lines, 10_000)}
            rejected, accepted = [], []
            for name in p["survivors"]:
                body = muts.get(name)
                if body is None:
                    continue
                o.write_source(t["source"], body)
                fs = o.fail_set(files)
                (rejected if fs != base else accepted).append(name)
            o.write_source(t["source"], t["after"])
            row.update(rejected=len(rejected), accepted=len(accepted),
                       rejected_names=rejected, accepted_names=accepted)
        except Exception as exc:  # noqa: BLE001
            row["reason"] = f"HARNESS_{type(exc).__name__}"
        rows.append(row)
        print(f"  {slug:20s} {sha} survivors={row['survivors']} "
              f"rejected_by_file={row.get('rejected')} accepted={row.get('accepted')} "
              f"{row.get('reason', '')}", flush=True)

    rj = sum(r.get("rejected", 0) for r in rows)
    ac = sum(r.get("accepted", 0) for r in rows)
    out = {"schema": "PROJECT_BRAIN_ORACLE_STRENGTHENING_V1",
           "authority": "NONE__PRODUCER_RUN_SANDBOX",
           "note": ("a rejected mutant is one the whole test FILE catches but the single target "
                    "node does not. Not a solve attempt; no mutant counts as a repair."),
           "tasks": len(rows), "rejected": rj, "accepted": ac,
           "rejection_rate": round(rj / (rj + ac), 4) if (rj + ac) else None,
           "rows": rows}
    pathlib.Path(a.out).write_text(json.dumps(out, indent=1))
    print(f"\n== {len(rows)} tasks | {rj} of {rj + ac} surviving mutants REJECTED by the whole "
          f"test file | rejection rate {out['rejection_rate']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
