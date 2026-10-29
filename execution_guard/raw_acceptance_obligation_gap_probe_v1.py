"""Reproduce whether raw trace acceptance credits an unperformed instruction.

This is a diagnostic, not a success receipt. It creates real cat and text-write
results in a throwaway directory, supplies single- and two-action traces, and
asks both the raw trace verifier and the existing residual localizer about the
same contract. A nonzero exit means an unperformed action was credited as complete.
"""
from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from canonical.runtime.bound_capabilities import cli_command, file_write_text  # noqa: E402
from canonical.runtime.lossless_raw_task_contract_v1 import compile_contract  # noqa: E402
from canonical.runtime.raw_goal_trace_acceptance_v1 import verify  # noqa: E402
from canonical.runtime.raw_task_acceptance_residual_localizer_v1 import localize  # noqa: E402


CASES = (
    ("delete", "delete other.txt"),
    ("modify", "change other.txt"),
    ("copy", "copy other.txt to copy.txt"),
    ("archive", "compress other.txt to other.gz"),
)


def measure() -> dict:
    rows = []
    with tempfile.TemporaryDirectory(prefix="brain-obligation-gap-") as td:
        root = Path(td)
        (root / "source.txt").write_text("source\n", encoding="utf-8")
        (root / "other.txt").write_text("unchanged\n", encoding="utf-8")
        command_args = {"capability_id": "shell.command.run", "argv": ["cat", "source.txt"]}
        text_args = {"capability_id": "text.file.write", "content": "hello", "output_path": "out.txt"}
        command_first = cli_command.run(command_args, str(root))
        command_second = cli_command.run(command_args, str(root))
        subjects = (
            ("single_command", "shell.command.run", "Run the shell command cat source.txt and ",
             [(command_args, command_first)], "shell.command.result"),
            ("single_text_write", "text.file.write", "Write the text 'hello' to the file out.txt and ",
             [(text_args, file_write_text.run(text_args, root))], "text.file.available"),
            ("two_commands", "shell.command.run", "Run the shell command cat source.txt and ",
             [(command_args, command_first), (command_args, command_second)], "shell.command.result"),
        )
        for shape, cid, prefix, steps, effect in subjects:
            trace = [{"plan": {"args": args}, "result": produced} for args, produced in steps]
            trace.append({"result": {"type": "finish"}})
            plan = ({"selected_capability": cid} if len(steps) == 1 else
                    {"compiled_parts": [{"selected_capability": cid} for _ in steps]})
            for label, extra in CASES:
                goal = prefix + extra
                contract = compile_contract(goal, source_id="user", routing_target_effects=[effect])
                result = verify(goal=goal, compiled_plan=plan,
                                execution=trace, raw_contract=contract, root=root)
                residuals = localize(contract)
                other = root / "other.txt"
                unperformed = (other.read_text(encoding="utf-8") == "unchanged\n"
                               and not (root / "copy.txt").exists()
                               and not (root / "other.gz").exists())
                rows.append({
                    "trace_shape": shape,
                    "capability_id": cid,
                    "extra_instruction": label,
                    "extra_action_not_performed": unperformed,
                    "semantic_acceptance_complete": result.get("semantic_acceptance_complete"),
                    "verifier_reason": result.get("reason"),
                    "accepted_obligation_count": len(result.get("accepted_obligation_ids") or []),
                    "localizer_semantic_residual_count": residuals.get("semantic_residual_obligation_count"),
                })
    unsafe = sum(row["extra_action_not_performed"] and row["semantic_acceptance_complete"] is True
                 for row in rows)
    return {"schema": "BRAIN_RAW_ACCEPTANCE_OBLIGATION_GAP_PROBE_V1",
            "status": "FAIL__UNPERFORMED_INSTRUCTION_ACCEPTED" if unsafe else "NO_UNSAFE_ACCEPTANCE_OBSERVED",
            "case_count": len(rows), "unsafe_acceptance_count": unsafe, "rows": rows,
            "terminal_authority": False}


def main() -> int:
    report = measure()
    print(json.dumps(report, indent=2, sort_keys=True))
    return 1 if report["unsafe_acceptance_count"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
