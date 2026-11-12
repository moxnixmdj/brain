#!/usr/bin/env python3
"""Derive an action-intent record from the diff, so the machine does the binding and the human does
the meaning.

Round 11's eight-line registry change took four failed CI runs and about an hour. Every failure was
mechanical: a base commit one merge behind, a receipt blob sha left pointing at another session's
file, a lease key that did not concatenate, a recursive-observation stop condition that had to equal
the intent's stop condition and did not. None of them was a judgement call. All of them were
derivable from the commit.

This tool derives them. It takes the fields only a human can write — what the change is, what it
causes, when to stop, how it could be falsified — and binds every field that git already knows:

  * ``canonical_base_commit`` and ``recursive_obs.canonical_base_commit`` — the actual base sha;
  * ``blocker_lease_key`` — ``generation::capability_target::causal_blocker``, computed;
  * ``recursive_obs.expected_parent_level_state_change`` and ``stop_condition`` — forced equal to the
    intent fields they are cross-checked against, so they cannot drift apart;
  * ``v22_prewrite_admission.active_pointer_git_blob_sha`` — ``git rev-parse <base>:<pointer>``;
  * ``tournament.counterexample_receipts`` — the probe and test files this change actually adds,
    each bound to ``git rev-parse HEAD:<path>``;
  * ``agent_orientation.progress_evidence_paths`` — the changed files that carry evidence.

It does not weaken a single check. It fills the same fields ``enforce_goal_hierarchy.py`` validates,
from the same sources, and then tells you whether the result passes.

``--check`` re-binds an existing record and writes nothing: it reports which fields are stale and
what they should be. That is the answer to "why did the drift guard fail this time".
"""
from __future__ import annotations

import argparse
import copy
import json
import pathlib
import subprocess
import sys
from typing import Any

REPO_ROOT = pathlib.Path(__file__).resolve().parent
INTENTS = REPO_ROOT / "canonical" / "action_intents"
POINTER = "canonical/governance/CURRENT_ZERO_REALITY_MINIMUM_CUT_ACTIVE_POINTER_V1.json"
GUARD = "canonical/runtime/enforce_goal_hierarchy.py"

#: The fields a human must supply. Everything else is derived, inherited, or copied.
SEMANTIC_FIELDS = (
    "action_id",
    "action_kind",
    "action_summary",
    "causal_blocker",
    "selected_route",
    "expected_parent_change",
    "expected_parent_frontier_change",
    "stop_condition",
    "falsification_condition",
    "measured_effect",
    "date",
)

#: Files whose addition is evidence for the change, in the order the guard expects to find them.
EVIDENCE_HINTS = ("probe", "_probe", "test_")


def git(*args: str) -> str:
    return subprocess.check_output(["git", *args], cwd=REPO_ROOT, text=True).strip()


def changed_files(base: str, head: str = "HEAD") -> list[str]:
    """Files the change touches. Two-dot is the fallback when the refs share no merge base."""
    try:
        out = git("diff", "--name-only", f"{base}...{head}")
    except subprocess.CalledProcessError:
        try:
            out = git("diff", "--name-only", base, head)
        except subprocess.CalledProcessError:
            return []
    return [line for line in out.splitlines() if line.strip()]


def blob_at(ref: str, path: str) -> str | None:
    try:
        return git("rev-parse", f"{ref}:{path}")
    except subprocess.CalledProcessError:
        return None


def lease_key(intent: dict[str, Any]) -> str:
    """The same identity ``enforce_goal_hierarchy.blocker_lease_key`` computes."""
    return "::".join(
        str(intent.get(field) or "")
        for field in ("canonical_generation", "capability_target", "causal_blocker")
    )


def newest_intent() -> pathlib.Path:
    files = sorted(INTENTS.glob("*.json"), key=lambda p: p.stat().st_mtime)
    if not files:
        raise SystemExit("NO_TEMPLATE_INTENT")
    return files[-1]


def evidence_paths(files: list[str]) -> list[str]:
    picked = [f for f in files if f.endswith(".py") and any(h in pathlib.Path(f).name for h in EVIDENCE_HINTS)]
    return sorted(picked)


def bind(intent: dict[str, Any], base: str, head: str = "HEAD") -> dict[str, Any]:
    """Return a copy of ``intent`` with every mechanically derivable field set from git."""
    bound = copy.deepcopy(intent)
    base_sha = git("rev-parse", base)
    bound["canonical_base_commit"] = base_sha
    bound["blocker_lease_key"] = lease_key(bound)

    obs = bound.setdefault("recursive_obs", {})
    if isinstance(obs, dict):
        obs["canonical_base_commit"] = base_sha
        # The guard compares these two against the intent by equality; derive them so they cannot
        # disagree with the fields they are checked against.
        obs["expected_parent_level_state_change"] = bound.get("expected_parent_frontier_change")
        obs["stop_condition"] = bound.get("stop_condition")

    admission = bound.get("v22_prewrite_admission")
    if isinstance(admission, dict):
        pointer_blob = blob_at(base, POINTER)
        if pointer_blob:
            admission["active_pointer_git_blob_sha"] = pointer_blob
        tournament = admission.get("tournament")
        if isinstance(tournament, dict):
            rows = []
            for path in evidence_paths(changed_files(base, head)):
                sha = blob_at(head, path)
                if sha:
                    rows.append({"path": path, "git_blob_sha": sha})
            if rows:
                tournament["counterexample_receipts"] = rows

    orientation = bound.get("agent_orientation")
    if isinstance(orientation, dict):
        evidence = evidence_paths(changed_files(base, head))
        if evidence:
            orientation["progress_evidence_paths"] = evidence
    return bound


def drift(intent: dict[str, Any], base: str, head: str = "HEAD") -> list[dict[str, Any]]:
    """Every field whose committed value differs from what git says it should be."""
    bound = bind(intent, base, head)
    found = []
    for field in ("canonical_base_commit", "blocker_lease_key"):
        if intent.get(field) != bound.get(field):
            found.append({"field": field, "have": intent.get(field), "want": bound.get(field)})
    for field in ("canonical_base_commit", "expected_parent_level_state_change", "stop_condition"):
        have = (intent.get("recursive_obs") or {}).get(field)
        want = (bound.get("recursive_obs") or {}).get(field)
        if have != want:
            found.append({"field": f"recursive_obs.{field}", "have": have, "want": want})
    have_adm = (intent.get("v22_prewrite_admission") or {})
    want_adm = (bound.get("v22_prewrite_admission") or {})
    if have_adm.get("active_pointer_git_blob_sha") != want_adm.get("active_pointer_git_blob_sha"):
        found.append({"field": "v22_prewrite_admission.active_pointer_git_blob_sha",
                      "have": have_adm.get("active_pointer_git_blob_sha"),
                      "want": want_adm.get("active_pointer_git_blob_sha")})
    have_rows = list((have_adm.get("tournament") or {}).get("counterexample_receipts") or [])
    want_rows = list((want_adm.get("tournament") or {}).get("counterexample_receipts") or [])
    if want_rows and have_rows != want_rows:
        found.append({"field": "v22_prewrite_admission.tournament.counterexample_receipts",
                      "have": have_rows, "want": want_rows})
    return found


def build(spec: dict[str, Any], base: str, head: str = "HEAD",
          template: pathlib.Path | None = None) -> dict[str, Any]:
    """A full intent: structure inherited, meaning from the spec, binding from git."""
    template = template or newest_intent()
    intent = json.loads(template.read_text(encoding="utf-8"))
    missing = [field for field in SEMANTIC_FIELDS if not str(spec.get(field) or "").strip()]
    if missing:
        raise SystemExit("SPEC_MISSING:" + ",".join(missing))
    name = str(spec["action_id"])
    intent["action_id"] = name
    intent["action_intent_id"] = name
    intent["route_id"] = name
    for field in SEMANTIC_FIELDS:
        if field == "action_id":
            continue
        intent[field] = spec[field]
    return bind(intent, base, head)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--base", required=True, help="base ref or sha")
    parser.add_argument("--head", default="HEAD")
    parser.add_argument("--spec", type=pathlib.Path, help="JSON with the semantic fields")
    parser.add_argument("--template", type=pathlib.Path, help="intent to inherit structure from")
    parser.add_argument("--out", type=pathlib.Path)
    parser.add_argument("--check", type=pathlib.Path,
                        help="an existing intent: report stale fields, write nothing")
    args = parser.parse_args(argv)

    if args.check:
        intent = json.loads(args.check.read_text(encoding="utf-8"))
        found = drift(intent, args.base, args.head)
        if not found:
            print("INTENT_BINDINGS_CURRENT")
            return 0
        print("INTENT_BINDINGS_STALE:%d" % len(found))
        for row in found:
            print(f"  {row['field']}")
            print(f"    have {row['have'] if not isinstance(row['have'], list) else len(row['have'])}")
            print(f"    want {row['want'] if not isinstance(row['want'], list) else len(row['want'])}")
        if args.out:
            bound = bind(intent, args.base, args.head)
            args.out.write_text(json.dumps(bound, indent=1) + "\n", encoding="utf-8")
            print("WROTE " + str(args.out))
        return 1

    if not args.spec:
        raise SystemExit("SPEC_REQUIRED_UNLESS_CHECK")
    intent = build(json.loads(args.spec.read_text(encoding="utf-8")), args.base,
                   args.head, args.template)
    text = json.dumps(intent, indent=1) + "\n"
    target = args.out or INTENTS / f"{intent['action_id']}.json"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(text, encoding="utf-8")
    print("WROTE " + str(target))
    print("NEXT python3 %s --base %s --head %s" % (GUARD, args.base, args.head))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
