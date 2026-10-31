"""Show a remaining generic raw-acceptance obligation gap.

A real archive verifier runs on a correct disposable archive. The separate
follow-up instructions are not run; the generic trace-acceptance function is
then asked whether each entire request was completed. This is a direct API
counterexample, not proof of a particular live-front-door route.
"""
from __future__ import annotations

import json
from pathlib import Path
import sys
import tarfile
import tempfile

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from canonical.runtime.bound_capabilities import archive_verify_gnu_tar  # noqa: E402
from canonical.runtime.lossless_raw_task_contract_v1 import compile_contract  # noqa: E402
from canonical.runtime.raw_goal_trace_acceptance_v1 import verify  # noqa: E402

FOLLOWUPS = (
    ("delete", "delete canonical/victim.txt"),
    ("copy", "copy canonical/victim.txt to copy.txt"),
    ("modify", "change canonical/victim.txt"),
    ("compress", "compress canonical/victim.txt to victim.gz"),
)


def measure() -> dict:
    rows = []
    with tempfile.TemporaryDirectory(prefix="brain-inspector-gap-") as temporary:
        root = Path(temporary)
        (root / "canonical").mkdir()
        manifest = root / "canonical/manifest.json"
        manifest.write_text('{"records": []}', encoding="utf-8")
        victim = root / "canonical/victim.txt"
        victim.write_text("unchanged\n", encoding="utf-8")
        with tarfile.open(root / "bundle.tar.gz", "w:gz") as archive:
            archive.add(manifest, arcname="canonical/manifest.json")
        args = {"capability_id": "archive.verify.tar_gz.gnu",
                "manifest_path": "canonical/manifest.json", "archive_path": "bundle.tar.gz"}
        produced = archive_verify_gnu_tar.run(args, root)
        trace = [{"plan": {"args": args}, "result": produced}, {"result": {"type": "finish"}}]
        for label, instruction in FOLLOWUPS:
            goal = "Verify bundle.tar.gz against canonical/manifest.json and " + instruction
            contract = compile_contract(goal, source_id="user", routing_target_effects=["archive.verified"])
            result = verify(goal=goal, compiled_plan={"selected_capability": args["capability_id"]},
                            execution=trace, raw_contract=contract, root=root)
            unperformed = (victim.read_text(encoding="utf-8") == "unchanged\n"
                           and not (root / "copy.txt").exists()
                           and not (root / "victim.gz").exists())
            rows.append({"followup": label, "followup_unperformed": unperformed,
                         "semantic_acceptance_complete": result.get("semantic_acceptance_complete"),
                         "reason": result.get("reason")})
    unsafe = sum(row["followup_unperformed"] and row["semantic_acceptance_complete"] is True for row in rows)
    return {"schema": "BRAIN_UNCOVERED_INSPECTOR_OBLIGATION_PROBE_V1",
            "status": "FAIL__UNPERFORMED_INSTRUCTION_ACCEPTED" if unsafe else "NO_UNSAFE_ACCEPTANCE_OBSERVED",
            "case_count": len(rows), "unsafe_acceptances": unsafe, "rows": rows,
            "scope": "one real archive inspector with four direct generic-verifier requests; live routing not tested",
            "terminal_authority": False}


def main() -> int:
    result = measure()
    print(json.dumps(result, indent=2, sort_keys=True))
    return 1 if result["unsafe_acceptances"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
