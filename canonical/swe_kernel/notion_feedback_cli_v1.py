"""Inspect and provide explicit feedback to a notion store.

The caller is responsible for the truth and independence of the evidence they
supply. This interface does not authenticate reviewers or certify a contract.
After a review or answer, run the workspace sensor again to obtain the next plan.
"""
from __future__ import annotations

import argparse
import json
from typing import Sequence

from canonical.swe_kernel.notions_v1 import NotionStore


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--store", required=True, help="notion_review.store returned by the board")
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("list", help="list stored questions, reviews, and current plans")
    review = commands.add_parser("review", help="confirm or reject a question")
    review.add_argument("finding_id")
    review.add_argument("--decision", choices=("confirm", "reject"), required=True)
    review.add_argument("--reviewer", required=True)
    review.add_argument("--basis", required=True)
    review.add_argument("--trusted-function")
    answer = commands.add_parser("answer", help="answer the current active query")
    answer.add_argument("finding_id")
    answer.add_argument("--args", required=True, help="JSON array from next_query.args")
    answer.add_argument("--expected", required=True, help="independently supplied JSON number")
    answer.add_argument("--reviewer", required=True)
    answer.add_argument("--basis", required=True)
    ns = parser.parse_args(argv)
    try:
        store = NotionStore(ns.store)
        if ns.command == "list":
            result = [{**finding, "priority_score": store.score(finding),
                       "review": store.reviews.get(fid), "plan": store.plans.get(fid)}
                      for fid, finding in store.findings.items()]
            result.sort(key=lambda row: (-row["priority_score"], row["id"]))
        elif ns.command == "review":
            result = store.review(ns.finding_id, decision=ns.decision, reviewer=ns.reviewer,
                                  basis=ns.basis, trusted_function=ns.trusted_function)
        else:
            args = json.loads(ns.args)
            expected = json.loads(ns.expected)
            result = store.answer(ns.finding_id, args=args, expected=expected,
                                  reviewer=ns.reviewer, basis=ns.basis)
    except (ValueError, OSError, TypeError) as exc:
        parser.error(str(exc))
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
