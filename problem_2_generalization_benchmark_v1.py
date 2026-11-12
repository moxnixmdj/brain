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


def main():
    import tempfile

    with tempfile.TemporaryDirectory() as tmp:
        state = Path(tmp) / "exp.json"
        router = router_already_generalizes(state)
        memory = memory_rescues(state)
    ceiling = coverage_ceiling()

    print("1. DOES THE ROUTER ALREADY GENERALIZE?")
    print(f"   paraphrases answered with memory OFF: {router['answered_without_memory']}"
          f"/{router['total']}  ({router['share']:.0%})")
    print("\n2. CAN MEMORY RESCUE WHAT THE ROUTER MISSES?")
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
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
