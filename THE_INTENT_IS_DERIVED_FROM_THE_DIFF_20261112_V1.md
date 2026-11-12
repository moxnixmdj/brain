# The intent is derived from the diff

**2026-11-12.** Base `808e72ac`. Branch `arena/de5cf49c-brain`. Round 12.

Last round's change was nine lines in one registry file. It took **four failed CI runs and about an
hour** to merge. Every failure was mechanical:

```
DRIFT_GUARD_FAIL
 - ACTION_INTENT_MISSING
 - V22_COUNTEREXAMPLE_RECEIPT_BLOB_STALE_OR_MISMATCH:0
 - V22_COUNTEREXAMPLE_RECEIPT_BLOB_STALE_OR_MISMATCH:1
 - BLOCKER_LEASE_KEY_MISSING_OR_MISMATCH
 - RECURSIVE_OBS_STALE_BASE_COMMIT
 - RECURSIVE_OBS_PARENT_CHANGE_MISMATCH
 - RECURSIVE_OBS_STOP_CONDITION_MISMATCH
```

Not one was a judgement call. A base commit one merge behind. Two receipt blob shas left pointing at
another session's files. A lease key that had to be ``generation::capability_target::causal_blocker``
and was not. Two observation fields that the guard compares *by equality* against the intent fields
they were copied from, at different times.

Meanwhile `main` moved six times during that PR. Six autonomous sessions write to this tree.

**That is the limiting factor on this project, and it is not learning theory.** The learning was
already solved — rounds 8 and 9 measured it. What costs the hours is a hand-typed form whose contents
git already knows.

## What this round adds

`derive_action_intent_20261112.py`. Meaning stays human. Binding becomes machine.

You write a spec with only the fields nothing can derive:

```json
{"action_id": "...", "action_kind": "RECONCILE_FRONTIER",
 "action_summary": "...", "causal_blocker": "...", "selected_route": "...",
 "expected_parent_change": "...", "expected_parent_frontier_change": "...",
 "stop_condition": "...", "falsification_condition": "...", "measured_effect": "..."}
```

The tool then sets, from git and from the record itself:

| field | derived from |
|---|---|
| `canonical_base_commit` | `git rev-parse <base>` — the sha, never the ref string |
| `blocker_lease_key` | the guard's own concatenation, computed |
| `recursive_obs.canonical_base_commit` | the same sha |
| `recursive_obs.stop_condition` | forced equal to `stop_condition` |
| `recursive_obs.expected_parent_level_state_change` | forced equal to `expected_parent_frontier_change` |
| `v22_prewrite_admission.active_pointer_git_blob_sha` | `git rev-parse <base>:<pointer>` |
| `tournament.counterexample_receipts` | the probe and test files this change adds, bound to `git rev-parse HEAD:<path>` |
| `agent_orientation.progress_evidence_paths` | the same evidence files |

Three of those exist only because two fields must agree and were being typed twice. Deriving them
makes disagreement *unrepresentable*, which is stronger than remembering to check.

## What it does not do

**It does not weaken a single check.** The guard still decides. The tool fills the same fields from
the same sources and then prints the exact command that validates the result:

```
NEXT python3 canonical/runtime/enforce_goal_hierarchy.py --base <sha> --head HEAD
```

`--check` re-binds an existing record and writes nothing, reporting which fields are stale and what
they should be. That is the answer to "why did the guard fail this time", available locally in a
second instead of after a CI round-trip:

```
INTENT_BINDINGS_STALE:2
  canonical_base_commit
    have 191f4f5b9a0b91873f583000e266c23a69097027
    want 808e72ac4a5a306ee122e69cadebff94db123b96
  recursive_obs.canonical_base_commit
    have 191f4f5b…
    want 808e72ac…
```

That is last round's real failure, reproduced and named in one command.

## Why this is the right thing to have built

The owner's goal is an agent that does arbitrary work on a computer, fast. Three rounds of
measurement say the capability work is gated by two things: **operators** (written in code, one part
at a time) and **verification** (a check that can fail). A fourth gate sits in front of both:
**a coordination ritual that costs more than the change**.

Building the operator set while paying an hour per merge is not the fastest path. This removes the
hour. It does not touch the content of any check — a reviewer can diff it against
`enforce_goal_hierarchy.py` and see the same field names, the same sources, the same equality rules.

What it deliberately does not do is serialize writes to `BOUND_CAPABILITY_REGISTRY_V1.json`. That
would be a governance change, it needs the owner's authorisation, and it could break the other
sessions mid-flight. It is the next thing to decide, not the next thing to build.

## Receipts

```
python3 derive_action_intent_20261112.py --base $(git rev-parse origin/main) --spec spec.json
python3 derive_action_intent_20261112.py --base $(git rev-parse origin/main) \
        --check canonical/action_intents/MEASURED_ACCEPTANCE_CHECKS_THE_OUTCOME_NOT_THE_WRITE_20261112_V1.json
python3 -m pytest -q canonical/tests/test_derive_action_intent_v1.py      10 passed
```

## Non-claims

The tool derives eight fields; the guard has more checks than that, and a record can still fail on a
semantic field a human wrote badly. It was validated against the failure modes measured in round 11,
not against every branch shape. It changes no guard, no registry, and no capability, runs in-process,
spends $0, and has zero model dependency. No benchmark movement, no capability credit,
`truth.achieved` false.
