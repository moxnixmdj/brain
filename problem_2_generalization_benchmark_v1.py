"""Problem 2 (generalization): what generalizes today, what does not, and what cannot.

THE CLAIM UNDER TEST. "If I see the exact same task again I solve it instantly (8.13x). If I see
a SIMILAR task I cannot adapt." The second half is the interesting one, and this module separates
its causes, because they need opposite fixes and only one of them is a matching problem.

THREE QUESTIONS, MEASURED SEPARATELY.

  1. DOES THE ROUTER ALREADY GENERALIZE? Take one taught sentence and a set of paraphrases.
     If the front door already answers the paraphrase, memory has nothing to add and any
     "improvement" claimed from memory would be the router's, not memory's.

  2. CAN A REMEMBERED PROCEDURE REACH A TASK THE ROUTER MISSES? This is the only measurement
     that tests generalization in memory. It requires the paraphrased capability to EXIST --
     if it does not, no amount of matching can help, and claiming a memory failure there
     would be false.

  3. HOW MUCH OF THE MISSING HALF IS COVERAGE RATHER THAN MATCHING? Measured against the
     registry: for a task the router refuses, is there a capability that could have served it?

WHY (3) IS THE ONE THAT MATTERS. It was found by asking (2) and repeatedly failing to construct
a rescue: "sum a column of numbers in a csv" is AMBIGUOUS among sqlite/xlsx creators that cannot
compute a sum, because the registry contains no capability that sums a CSV column. The paraphrase
did not fail to match; there was nothing to match. That is a ceiling on generalization that no
matching function can lift, and it is bounded by what the machine can DO, not by what it can find.
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SCHEMA = "PROBLEM_2_GENERALIZATION_BENCHMARK_V1"

# (teaching sentence, the capability that answered it, paraphrases of the SAME request)
TEACH_AND_PARAPHRASE = [
    (
        "convert the yaml file probe_a.yaml to json using yq",
        "yaml.to_json.yq",
        [
            "turn probe_b.yaml into json with yq",
            "export probe_b.yaml as json using yq",
            "transform probe_b.yaml to json with yq",
            "produce json from probe_b.yaml with yq",
            "make probe_b.yaml into json using yq",
            "translate probe_b.yaml into json",
            "serialize probe_b.yaml as json",
            "convert the yaml file probe_b.yaml to json with yq",
        ],
    ),
    (
        "extract the text from a pdf",
        "pdf.extract.text.pypdf",
        [
            "pull the text out of the pdf",
            "read the text from a pdf file",
            "get the text of the pdf",
        ],
    ),
]

# Tasks the front door does NOT answer, with the capability that would have to serve them.
# `exists` is measured against the live registry, never asserted here.
UNANSWERED_TASKS = [
    "sum a column of numbers in a csv",
    "diff two files",
    "sort the lines of a file",
    "make a zip archive of a directory",
    "read a spreadsheet and sum a column",
    "convert a docx to text",
]

# The capability id(s) that would serve each task, if the machine could do it at all.
WOULD_NEED = {
    "sum a column of numbers in a csv": ("csv", "sum"),
    "diff two files": ("diff",),
    "sort the lines of a file": ("sort",),
    "make a zip archive of a directory": ("zip",),
    "read a spreadsheet and sum a column": ("xlsx", "sum"),
    "convert a docx to text": ("docx", "text"),
}

# Paraphrases of EXISTING runnable capabilities that fail without memory (either by routing
# to a higher-scoring false-positive competitor that fails execution, or by dying as
# AMBIGUOUS__NO_DECISIVE_MARGIN) and are rescued after one verified teaching receipt.
FAILING_PARAPHRASES_OF_EXISTING_CAPABILITIES = (
    (
        "extract the text from a pdf",
        "pdf.extract.text.pypdf",
        [
            "read the text from a pdf document",
            "pull the text out of a pdf document",
            "get the text of a pdf document",
            "obtain text from a pdf document",
            "extract text from a pdf report",
        ],
    ),
    (
        "audit the python source canonical/runtime/solve_v1.py with ast",
        "python.source.audit.ast",
        [
            "inspect the python file canonical/runtime/solve_v1.py using ast",
            "analyze the python module canonical/runtime/solve_v1.py with ast",
            "check the python code canonical/runtime/solve_v1.py via ast",
            "inspect the python file canonical/runtime/macro_v1.py using ast",
        ],
    ),
    (
        "compute the cyclomatic complexity of canonical/runtime/solve_v1.py",
        "python.source.complexity.v1",
        [
            "measure the complexity of canonical/runtime/solve_v1.py",
            "evaluate code complexity in canonical/runtime/solve_v1.py",
            "measure the complexity of canonical/runtime/macro_v1.py",
        ],
    ),
)


def tool_substrate():
    """Can the yq demonstration run HERE? Reported, never assumed.

    `yq` and `pyyaml` are installed per-interpreter with `pip --user`, and they do not
    survive a new interpreter or a wiped sandbox -- measured twice in two rounds. A
    benchmark that assumed them would report a routing failure that is really an absent
    tool, which is the confusion this whole exercise exists to end.
    """
    import importlib.util
    import shutil
    return {"yq": bool(shutil.which("yq")),
            "pyyaml": importlib.util.find_spec("yaml") is not None}


def _act(sentence, memory):
    from canonical.runtime import grounded_action_v1 as GA
    return GA.act(sentence, memory=memory, bridge=False, computer_use=False)


def _registry():
    from canonical.runtime import grounded_action_v1 as GA
    return GA.load_registry()


def capability_exists(*terms):
    """Is there any registered capability whose id, keywords or provides mention every term?"""
    for cid, entry in _registry().items():
        blob = " ".join([str(cid)]
                        + [str(k) for k in (entry.get("keywords") or [])]
                        + [str(p) for p in (entry.get("provides") or [])]).lower()
        if all(term in blob for term in terms):
            return cid
    return None


def router_already_generalizes(state_path):
    """Question 1: does the paraphrase work with memory OFF?"""
    substrate = tool_substrate()
    rows = []
    for train, capability, paraphrases in TEACH_AND_PARAPHRASE:
        for phrase in paraphrases:
            receipt = _act(phrase, memory=False)
            rows.append({"train": train, "paraphrase": phrase,
                         "capability_id": receipt.get("capability_id"),
                         "status": receipt.get("status"),
                         "answered_without_memory":
                             receipt.get("status") == "VERIFIED_ACTION"})
    total = len(rows)
    answered = sum(1 for r in rows if r["answered_without_memory"])
    return {"schema": SCHEMA + "_ROUTER", "rows": rows, "total": total,
            "answered_without_memory": answered,
            "substrate": substrate,
            "routable": substrate["yq"] and substrate["pyyaml"],
            "share": round(answered / total, 3) if total else 0.0}


def memory_rescues(state_path):
    """Question 2: teach once, then look ONLY at paraphrases that failed with memory off."""
    import canonical.runtime.experience_v1 as EXP
    EXP.DEFAULT_STATE = Path(state_path)
    teaching = []
    for train, capability, _ in TEACH_AND_PARAPHRASE:
        receipt = _act(train, memory=True)
        teaching.append({"train": train, "status": receipt.get("status"),
                         "capability_id": receipt.get("capability_id"),
                         "learned": bool((receipt.get("procedure_learned") or {}).get("learned"))})
    rows = []
    for train, capability, paraphrases in TEACH_AND_PARAPHRASE:
        for phrase in paraphrases:
            without = _act(phrase, memory=False)
            if without.get("status") == "VERIFIED_ACTION":
                continue          # the router already answers it: memory adds nothing to measure
            with_memory = _act(phrase, memory=True)
            rows.append({"train": train, "paraphrase": phrase,
                         "without": without.get("status"),
                         "without_capability": without.get("capability_id"),
                         "with": with_memory.get("status"),
                         "with_capability": with_memory.get("capability_id"),
                         "rescued": (with_memory.get("status") == "VERIFIED_ACTION"
                                     and with_memory.get("capability_id") == capability)})
    return {"schema": SCHEMA + "_MEMORY", "teaching": teaching, "rows": rows,
            "substrate": tool_substrate(),
            "routable": tool_substrate()["yq"] and tool_substrate()["pyyaml"],
            "testable": len(rows), "rescued": sum(1 for r in rows if r["rescued"])}


def coverage_ceiling():
    """Question 3: of the tasks the door refuses, how many are missing CAPABILITY, not a match?"""
    rows = []
    for task in UNANSWERED_TASKS:
        receipt = _act(task, memory=False)
        terms = WOULD_NEED.get(task, ())
        served_by = capability_exists(*terms) if terms else None
        rows.append({"task": task, "status": receipt.get("status"),
                     "routed_to": receipt.get("capability_id"),
                     "would_need_terms": list(terms),
                     "capability_exists": served_by})
    missing = sum(1 for r in rows if r["capability_exists"] is None)
    return {"schema": SCHEMA + "_CEILING", "rows": rows, "total": len(rows),
            "no_capability_exists": missing,
            "registry_size": len(_registry()),
            "share_of_refusals_beyond_reach": round(missing / len(rows), 3) if rows else 0.0}


def memory_rescue_on_failing_paraphrases() -> dict:
    """Question 4: measure rescue on paraphrases of existing capabilities that fail with memory=False.

    Falsifies the zero-testable-target hypothesis: each paraphrase below fails with
    `memory=False` (`ACTION_FAILED` on a wrong capability or `AMBIGUOUS__NO_DECISIVE_MARGIN`)
    and succeeds (`VERIFIED_ACTION` on the taught capability via `REMEMBERED_PROCEDURE`)
    with `memory=True` after one verified teaching run.
    """
    import tempfile
    from canonical.runtime import experience_v1 as EXP

    orig_exp = EXP.DEFAULT_STATE
    with tempfile.TemporaryDirectory() as tmp:
        EXP.DEFAULT_STATE = Path(tmp) / "experience.json"
        try:
            taught = []
            rows = []
            for train_sentence, expected_cid, paraphrases in FAILING_PARAPHRASES_OF_EXISTING_CAPABILITIES:
                tr = _act(train_sentence, memory=True)
                taught_ok = tr.get("status") == "VERIFIED_ACTION" and tr.get("capability_id") == expected_cid
                taught.append({
                    "train": train_sentence,
                    "expected": expected_cid,
                    "routed_to": tr.get("capability_id"),
                    "status": tr.get("status"),
                    "taught_ok": taught_ok,
                })
                for p in paraphrases:
                    r_off = _act(p, memory=False)
                    off_ok = r_off.get("status") == "VERIFIED_ACTION" and r_off.get("capability_id") == expected_cid
                    r_on = _act(p, memory=True)
                    on_ok = r_on.get("status") == "VERIFIED_ACTION" and r_on.get("capability_id") == expected_cid
                    rows.append({
                        "paraphrase": p,
                        "expected": expected_cid,
                        "without_memory_status": r_off.get("status"),
                        "without_memory_routed_to": r_off.get("capability_id"),
                        "without_memory_ok": off_ok,
                        "with_memory_status": r_on.get("status"),
                        "with_memory_routed_to": r_on.get("capability_id"),
                        "with_memory_selected_because": r_on.get("selected_because"),
                        "rescued": (not off_ok) and on_ok,
                    })
        finally:
            EXP.DEFAULT_STATE = orig_exp

    testable = sum(1 for r in rows if not r["without_memory_ok"])
    rescued = sum(1 for r in rows if r["rescued"])
    return {
        "schema": SCHEMA + "_FAILING_PARAPHRASE_RESCUE",
        "taught": taught,
        "rows": rows,
        "total": len(rows),
        "testable": testable,
        "rescued": rescued,
        "rescue_rate": round(rescued / testable, 4) if testable else 0.0,
    }


def forged_ceiling_rescue() -> dict:
    """Question 5: forge the 6 unanswered-task capabilities, teach each once, and measure task + paraphrase rescue."""
    import tempfile
    from canonical.runtime import capability_forge_v1 as FG
    from canonical.runtime import experience_v1 as EXP
    from canonical.runtime import ordinary_computer_capabilities_v1 as OCC

    orig_fg = FG.STATE
    orig_exp = EXP.DEFAULT_STATE
    before_task = {spec["task"]: _act(spec["task"], memory=False) for spec in OCC.ORDINARY_CAPABILITY_SPECS}
    before_para = {spec["paraphrase"]: _act(spec["paraphrase"], memory=False) for spec in OCC.ORDINARY_CAPABILITY_SPECS}
    with tempfile.TemporaryDirectory() as tmp:
        FG.STATE = Path(tmp) / "forged.json"
        EXP.DEFAULT_STATE = Path(tmp) / "experience.json"
        try:
            forge_reports = OCC.forge_ordinary_capabilities(root=ROOT)
            admitted_count = sum(1 for r in forge_reports if r.get("admitted") is True)
            rows = []
            for spec in OCC.ORDINARY_CAPABILITY_SPECS:
                cid = f"forged.ordinary_computer_capabilities_v1.{spec['function']}"
                task = spec["task"]
                para = spec["paraphrase"]
                r_off_task = before_task[task]
                r_off_para = before_para[para]
                r_teach = _act(f"{task} using {cid}", memory=True)
                r_on_task = _act(task, memory=True)
                r_on_para = _act(para, memory=True)
                rows.append({
                    "task": task,
                    "paraphrase": para,
                    "capability_id": cid,
                    "before_task_status": r_off_task.get("status"),
                    "before_paraphrase_status": r_off_para.get("status"),
                    "teach_status": r_teach.get("status"),
                    "after_task_status": r_on_task.get("status"),
                    "after_task_selected_because": r_on_task.get("selected_because"),
                    "after_paraphrase_status": r_on_para.get("status"),
                    "after_paraphrase_selected_because": r_on_para.get("selected_because"),
                    "task_rescued": (
                        r_off_task.get("status") != "VERIFIED_ACTION"
                        and r_on_task.get("status") == "VERIFIED_ACTION"
                        and r_on_task.get("capability_id") == cid
                    ),
                    "paraphrase_rescued": (
                        r_off_para.get("status") != "VERIFIED_ACTION"
                        and r_on_para.get("status") == "VERIFIED_ACTION"
                        and r_on_para.get("capability_id") == cid
                    ),
                })
        finally:
            FG.STATE = orig_fg
            EXP.DEFAULT_STATE = orig_exp

    tasks_rescued = sum(1 for r in rows if r["task_rescued"])
    paras_rescued = sum(1 for r in rows if r["paraphrase_rescued"])
    return {
        "schema": SCHEMA + "_FORGED_CEILING_RESCUE",
        "forged_total": len(OCC.ORDINARY_CAPABILITY_SPECS),
        "forged_admitted": admitted_count,
        "rows": rows,
        "tasks_total": len(rows),
        "tasks_rescued": tasks_rescued,
        "paraphrases_total": len(rows),
        "paraphrases_rescued": paras_rescued,
    }


def main():
    import tempfile

    with tempfile.TemporaryDirectory() as tmp:
        state = Path(tmp) / "exp.json"
        router = router_already_generalizes(state)
        memory = memory_rescues(state)
    ceiling = coverage_ceiling()
    failing_rescue = memory_rescue_on_failing_paraphrases()
    forged_rescue = forged_ceiling_rescue()

    print("1. DOES THE ROUTER ALREADY GENERALIZE?")
    print(f"   paraphrases answered with memory OFF: {router['answered_without_memory']}"
          f"/{router['total']}  ({router['share']:.0%})")
    print("\n2. CAN MEMORY RESCUE WHAT THE ROUTER MISSES (ORIGINAL 11)?")
    print(f"   paraphrases that fail without memory: {memory['testable']}")
    print(f"   rescued by a remembered procedure    : {memory['rescued']}")
    for row in memory["rows"]:
        print(f"     {row['paraphrase'][:44]:44} {row['without']} -> {row['with']}")
    print("\n3. HOW MUCH OF THE MISSING HALF IS COVERAGE?")
    print(f"   refused tasks with NO capability behind them: "
          f"{ceiling['no_capability_exists']}/{ceiling['total']}")
    for row in ceiling["rows"]:
        print(f"     {row['task'][:44]:44} needs {str(row['would_need_terms']):22}"
              f" exists={row['capability_exists']}")
    print("\n4. CAN MEMORY RESCUE FAILING PARAPHRASES OF EXISTING CAPABILITIES?")
    print(f"   failing paraphrases rescued by memory: "
          f"{failing_rescue['rescued']}/{failing_rescue['testable']} "
          f"({failing_rescue['rescue_rate']:.0%})")
    for row in failing_rescue["rows"]:
        print(f"     {row['paraphrase'][:58]:58} "
              f"{row['without_memory_status']:13} -> {row['with_memory_status']} "
              f"({row['with_memory_selected_because']})")
    print("\n5. CAN FORGING + MEMORY RESCUE THE 6 UNANSWERED CEILING TASKS + 6 PARAPHRASES?")
    print(f"   forged admitted: {forged_rescue['forged_admitted']}/{forged_rescue['forged_total']}  "
          f"tasks rescued: {forged_rescue['tasks_rescued']}/{forged_rescue['tasks_total']}  "
          f"paraphrases rescued: {forged_rescue['paraphrases_rescued']}/{forged_rescue['paraphrases_total']}")
    for row in forged_rescue["rows"]:
        print(f"     [TASK] {row['task'][:42]:42} {row['before_task_status']:10} -> "
              f"{row['after_task_status']} ({row['after_task_selected_because']})")
        print(f"     [PARA] {row['paraphrase'][:42]:42} {row['before_paraphrase_status']:10} -> "
              f"{row['after_paraphrase_status']} ({row['after_paraphrase_selected_because']})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
