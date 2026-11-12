#!/usr/bin/env python3
"""A refused measurement receipt is still marked verified.

Seven rounds ago nine repair-family capabilities were found accepting on `output_verified` while the
honest answer sat in `pass`. Eight were repointed with executed evidence. The ninth,
`python.task.acceptance.measured.objective.v1`, was left alone because it consumes a
content-addressed measurement receipt and a fabricated one would be worse than a transport field.

This probe stops fabricating and starts producing. It runs the repository's own measurement producer
(`python.repository.acceptance.measure.v1`) against a real fixture, feeds the receipt to the
consumer, and asks both predicates what they think — twice:

  * with a genuine, passing, content-addressed receipt;
  * with a receipt whose payload has been altered by one character, which the consumer refuses.

In both cases the consumer writes its answer to disk and marks the write `output_verified: True`.
`pass` is False both times. So the registered predicate accepts a run whose measured subject passed
and a run whose receipt was refused, and cannot tell them apart.

Authority NONE. Both capabilities run in-process against a temporary fixture. Nothing in the
repository is touched: the receipt is produced and consumed inside a temporary directory, $0, zero
model dependency.
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import pathlib
import shutil
import sys
import tempfile
from typing import Any

REPO_ROOT = pathlib.Path(__file__).resolve().parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

CAPABILITY_ID = "python.task.acceptance.measured.objective.v1"
PRODUCER = REPO_ROOT / "canonical" / "runtime" / "bound_capabilities" / "python_repository_acceptance_measurement_v1.py"
CONSUMER = REPO_ROOT / "canonical" / "runtime" / "python_measured_objective_acceptance_v1.py"
REGISTRY = REPO_ROOT / "canonical" / "runtime" / "BOUND_CAPABILITY_REGISTRY_V1.json"

FIXTURE = {
    "calc.py": "def square(x):\n    return x * x\n",
    "test_calc.py": (
        "from calc import square\n\n\n"
        "def test_square():\n"
        "    assert square(3) == 9\n"
    ),
}
TASK_TEXT = "make the tests in test_calc.py pass"

#: The predicate the capability carried until this round. Kept as data so the reason survives.
LEGACY_EXPECT: dict[str, Any] = {"type": "field_equals", "field": "output_verified", "value": True}
OUTCOME_EXPECT: dict[str, Any] = {"type": "field_equals", "field": "pass", "value": True}


def _load(path: pathlib.Path, name: str):
    spec = importlib.util.spec_from_file_location(name, str(path))
    if spec is None or spec.loader is None:  # pragma: no cover
        raise ImportError(str(path))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def apply_predicate(expect: dict[str, Any], result: dict[str, Any]) -> bool:
    if expect.get("type") != "field_equals":
        raise ValueError("UNSUPPORTED_EXPECT_TYPE:%s" % (expect.get("type"),))
    return result.get(expect.get("field")) == expect.get("value")


def _fixture() -> pathlib.Path:
    root = pathlib.Path(tempfile.mkdtemp(prefix="measured_objective_"))
    for name, body in FIXTURE.items():
        (root / name).write_text(body, encoding="utf-8")
    return root


def _run_case(tamper: bool) -> dict[str, Any]:
    root = _fixture()
    try:
        producer = _load(PRODUCER, "_measured_producer")
        consumer = _load(CONSUMER, "_measured_consumer")
        receipt = producer.run(
            {"source_root": ".", "output_path": "receipt.json",
             "test_paths": ["test_calc.py"], "timeout_s": 30},
            str(root),
        )
        receipt_path = root / "receipt.json"
        tampered = False
        if tamper:
            document = json.loads(receipt_path.read_text(encoding="utf-8"))
            document["measurements"]["test_count"] = int(
                document["measurements"].get("test_count", 0)
            ) + 1
            receipt_path.write_text(json.dumps(document, indent=2, sort_keys=True) + "\n",
                                    encoding="utf-8")
            tampered = True

        result = consumer.run(
            {"task_text": TASK_TEXT, "measurement_receipt_path": "receipt.json",
             "output_path": "answer.json"},
            str(root),
        )
        return {
            "result": result,
            "tampered": tampered,
            "receipt_producer_pass": receipt.get("pass"),
            "receipt_producer_status": receipt.get("status"),
            "receipt_measurements": receipt.get("measurements"),
            "consumer_pass": result.get("pass"),
            "consumer_status": result.get("status"),
            "consumer_output_verified": result.get("output_verified"),
            "consumer_output_sha256": result.get("output_sha256"),
            "legacy_accepts": apply_predicate(LEGACY_EXPECT, result),
            "outcome_accepts": apply_predicate(OUTCOME_EXPECT, result),
        }
    finally:
        shutil.rmtree(root, ignore_errors=True)


def _registry_expect() -> dict[str, Any]:
    registry = json.loads(REGISTRY.read_text(encoding="utf-8"))["capabilities"]
    return dict(registry[CAPABILITY_ID]["action_template"]["expect"])


def run() -> dict[str, Any]:
    genuine = _run_case(tamper=False)
    refused = _run_case(tamper=True)
    expect = _registry_expect()
    return {
        "probe": "a_refused_receipt_is_still_marked_verified",
        "authority": "NONE",
        "executed": True,
        "model_dependency_count": 0,
        "incremental_spend_usd": 0,
        "capability_id": CAPABILITY_ID,
        "task_text": TASK_TEXT,
        "genuine_receipt": genuine,
        "refused_receipt": refused,
        "registry_expect": expect,
        "registry_accepts_genuine": apply_predicate(expect, genuine["result"]),
        "registry_accepts_refused": apply_predicate(expect, refused["result"]),
        "legacy_expect": dict(LEGACY_EXPECT),
        "summary": {
            "cases": 2,
            "receipts_produced_by_the_tree": 2,
            "receipts_the_consumer_refused": sum(
                1 for case in (genuine, refused) if case["consumer_pass"] is not True
            ),
            "written_and_marked_output_verified": sum(
                1 for case in (genuine, refused) if case["consumer_output_verified"] is True
            ),
            "registry_accepts": sum(
                1 for case in (genuine, refused) if apply_predicate(expect, case["result"])
            ),
            "distinguishes_the_two": apply_predicate(expect, genuine["result"])
            != apply_predicate(expect, refused["result"]),
            "registry_reads_the_outcome": expect.get("field") == "pass",
        },
        "hard_nonclaims": [
            "NO_CAPABILITY_REGISTERED",
            "NO_RECEIPT_WRITTEN_INTO_THE_REPOSITORY",
            "ACCEPTANCE_NOT_GRANTED",
            "NO_TRUTH_ACHIEVED",
            "TWO_CASES_ONE_FIXTURE",
        ],
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", type=pathlib.Path, default=None)
    args = parser.parse_args(argv)

    report = run()
    if args.json:
        args.json.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    s = report["summary"]

    print("A refused measurement receipt, marked verified")
    print("=" * 72)
    for label, case in (("genuine receipt", report["genuine_receipt"]),
                        ("altered receipt", report["refused_receipt"])):
        print(f"\n  {label}")
        print(f"    producer said           {case['receipt_producer_pass']}  "
              f"{str(case['receipt_producer_status'])[:48]}")
        print(f"    consumer said           pass={case['consumer_pass']}  "
              f"{str(case['consumer_status'])[:44]}")
        print(f"    wrote the answer        output_verified={case['consumer_output_verified']}")
        live = apply_predicate(report["registry_expect"], case["result"])
        print(f"    legacy predicate        accepts={case['legacy_accepts']}"
              f"   live registry accepts={live}"
              f"   outcome predicate accepts={case['outcome_accepts']}")
    print(f"\n  registry field now reads: {report['registry_expect'].get('field')!r}")
    print(f"  accepts the genuine case: {report['registry_accepts_genuine']}")
    print(f"  accepts the refused case: {report['registry_accepts_refused']}")
    print(f"  tells them apart:         {s['distinguishes_the_two']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
