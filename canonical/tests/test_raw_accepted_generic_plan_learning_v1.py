"""An accepted goal whose plan is not the archive sentence must still be learnable.

`r3_raw_success_adapter_v1` and `r3_raw_success_checkpoint_verifier_v1` were both
hard-wired to ONE sentence. The adapter returned None unless `selected_plan` was
exactly `[archive.verify.tar_gz.gnu]`; the verifier raised
`RAW_CAPABILITY_NOT_ADMITTED` for anything else, matched the goal against the
archive regex, and asked the archive-specific acceptance verifier.

Measured consequence, on a tree wiped of every untracked artifact: 11 of 23 goals
reached semantic acceptance and 7 became verified experience. The four that did
not shared a single queued work item, `EXPAND_SUCCESS_VERIFICATION_FRONTIER` with
`observations: 4`, asking for an `INDEPENDENT_READONLY_SUCCESS_VERIFIER_OR_ADAPTER`.
Two of them -- "Rank source evidence by relevance to the objective." and "Read a
PDF and extract its text." -- had already been accepted with
`PASS__RAW_GOAL_EXECUTED_AND_EXACT_SEMANTIC_ACCEPTANCE_VERIFIED`. Their proof was
retained, the checkpoint was on disk, and the only thing refusing them was a
constant in two files.

The general path added here re-establishes the same argument without the
constant: recompile the raw contract from the goal text with the routing target
effects re-derived from the compile, require every capability in the plan to
still be a verified owned registry entry, re-open the controller checkpoint and
recompute its plan digest over the DECLARED plans, and re-derive the semantic
acceptance receipt from the checkpoint's own recorded results with the GENERIC
trace acceptance verifier -- which re-opens the produced artifacts from disk.
The re-derived receipt must byte-match the one retained at acceptance time.

Nothing is replayed. Nothing is believed from a producer.

After this change the same wiped-tree census measures 9 verified episodes from the
same 11 accepted goals, with acceptance itself unchanged.
"""
from __future__ import annotations

import hashlib
import json
import pathlib
from collections.abc import Mapping
import sys
import unittest
import uuid

REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]

if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from canonical.runtime import autonomous_verified_self_improvement_v1 as learning  # noqa: E402
from canonical.runtime import live_integrated_brain_v1 as live  # noqa: E402
from canonical.runtime import r3_improvement_queue_driver_v1 as driver  # noqa: E402
from canonical.runtime import r3_raw_success_adapter_v1 as raw_adapter  # noqa: E402
from canonical.runtime import r3_raw_success_checkpoint_verifier_v1 as raw_verifier  # noqa: E402
from canonical.runtime.raw_goal_archive_acceptance_v1 import (  # noqa: E402
    CAPABILITY as ARCHIVE_CAPABILITY,
)

# Both of these goals reach exact semantic acceptance on a clean tree and, before
# this change, produced no episode at all.
TWO_STEP_GOAL = "Rank source evidence by relevance to the objective."
TWO_STEP_PLAN = [
    "source.candidates.enumerate.stdlib",
    "source.objective_relevance.rank.bm25",
]
ONE_STEP_GOAL = "Read a PDF and extract its text."
ONE_STEP_PLAN = ["pdf.extract.text.pypdf"]
# Still accepted, still learning -- through the bound adapter, not this one.
ARCHIVE_GOAL = "Verify a tar.gz archive against its manifest."

_NONCE = uuid.uuid4().hex[:10]
_STATE_DIR = REPO_ROOT / "canonical/astra_runtime/state"
_STATE_PATH = learning.DEFAULT_STATE_PATH


_CHECKPOINTS: list[pathlib.Path] = []


def tearDownModule():
    for path in _CHECKPOINTS:
        try:
            path.unlink()
        except FileNotFoundError:
            pass


def _run(tag, goal):
    """Run one goal under a unique task_id, keeping its checkpoint on disk.

    A repeated task_id is short-circuited by the controller, so a fixed id would
    make this suite pass once and silently skip on every later run in the tree.

    The checkpoint must OUTLIVE the run: the independent verifier re-opens it
    from disk and recomputes its digest, which is the whole basis of the proof.
    Deleting it early -- as a suite that only inspects the returned result can --
    makes every adaptation here fail with CHECKPOINT_FILE_INVALID.
    """
    task_id = f"{tag}_{_NONCE}"
    checkpoint = _STATE_DIR / (
        f"{task_id}__live-raw-goal-controller__CONTROLLER_CHECKPOINT.json"
    )
    _CHECKPOINTS.append(checkpoint)
    return live.run_raw_goal({"task_id": task_id, "goal": goal}), checkpoint


def _adapted(tag, goal):
    """The adapter's candidate for one real accepted run, or None."""
    result, _ = _run(tag, goal)
    if result.get("semantic_acceptance_complete") is not True:
        return None, result
    state = learning.load_state(_STATE_PATH)
    observations = state.get("observations") or {}
    match = None
    for row in observations.values():
        if not isinstance(row, Mapping):
            continue
        material = ((row.get("proof_capsule") or {}).get("material") or {})
        if material.get("task_id") != f"{tag}_{_NONCE}":
            continue
        match = row
        break
    if match is None:
        return None, result
    replay = learning.get_success_replay_context(
        str(match.get("observation_id")), state_path=_STATE_PATH
    )
    adapted = raw_adapter.adapt(
        {
            "kind": "SUCCESS_TO_CANONICAL_EPISODE_CANDIDATE",
            "observation": json.loads(json.dumps(dict(match))),
            "replay_context": json.loads(json.dumps(dict(replay["context"]))),
            "authority_requested": "CANDIDATE_ONLY",
        },
        repo_root=REPO_ROOT,
    )
    return adapted, result


class GenericPlanBecomesExperienceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.two_step, cls.two_step_result = _adapted("GENERIC2", TWO_STEP_GOAL)
        cls.one_step, cls.one_step_result = _adapted("GENERIC1", ONE_STEP_GOAL)

    def _verify(self, adapted):
        solver = adapted["solver_output"]
        return raw_verifier.verify_material(
            problem=adapted["problem"],
            episode=solver["current_episode"],
            trace=solver["trace"],
            fact_capsule_head_hash=solver["state_capsule_head_hash"],
            value_capsule_head_hash=solver["value_capsule_head_hash"],
            repo_root=REPO_ROOT,
        )

    def test_the_two_step_goal_was_accepted_in_the_first_place(self):
        """Precondition, not a tautology: without acceptance there is no proof."""
        self.assertTrue(
            self.two_step_result.get("semantic_acceptance_complete"),
            self.two_step_result.get("raw_goal_acceptance"),
        )

    def test_the_adapter_now_admits_a_two_step_owned_plan(self):
        self.assertIsNotNone(self.two_step, "the adapter refused a two-step plan")
        self.assertEqual(
            self.two_step["problem"]["selected_plan"], TWO_STEP_PLAN
        )
        self.assertEqual(
            self.two_step["problem"]["selected_capability_id"], TWO_STEP_PLAN[-1]
        )

    def test_the_episode_has_one_step_per_capability_in_plan_order(self):
        steps = self.two_step["solver_output"]["current_episode"]["steps"]
        self.assertEqual([s["op"] for s in steps], TWO_STEP_PLAN)
        self.assertEqual([s["index"] for s in steps], [0, 1])
        # Only the terminal step carries the accepted effect; intermediate steps
        # must not claim an effect they did not produce.
        self.assertEqual([s["outputs"] for s in steps], [[], steps[1]["outputs"]])
        self.assertTrue(steps[1]["outputs"][0].startswith("raw_goal.accepted.sha256:"))

    def test_the_independent_verifier_passes_on_the_real_two_step_run(self):
        verdict = self._verify(self.two_step)
        self.assertTrue(verdict.get("pass"), verdict.get("reason"))
        self.assertIs(verdict.get("generic_owned_plan_verified"), True)
        self.assertIs(verdict.get("execution_replayed"), False)
        self.assertIs(verdict.get("semantic_acceptance_reverified"), True)
        self.assertIs(verdict.get("artifact_bytes_reverified"), True)

    def test_the_independent_verifier_passes_on_the_real_one_step_run(self):
        self.assertIsNotNone(self.one_step, "the adapter refused a one-step plan")
        self.assertEqual(self.one_step["problem"]["selected_plan"], ONE_STEP_PLAN)
        verdict = self._verify(self.one_step)
        self.assertTrue(verdict.get("pass"), verdict.get("reason"))

    def test_the_archive_sentence_still_takes_its_own_pinned_path(self):
        """Scope control: the generalisation must not swallow the archive branch.

        That branch matches a sentence-specific grammar, recompiles one
        capability and asks the archive acceptance verifier, and it is pinned by
        `test_r3_raw_accepted_readonly_learning_v1`. A real archive run never
        reaches the raw adapter at all -- its replay context is `compiled_bound`,
        so the BOUND adapter takes it -- which is why this asserts on the
        dispatch rather than on a live run.

        The assertion discriminates: the archive branch can only fail a
        non-archive sentence with RAW_GOAL_NO_LONGER_MATCHES_ACCEPTED_GRAMMAR,
        while the generic branch would have failed earlier and differently.
        """
        goal = "this is not the archive sentence at all"
        goal_sha = hashlib.sha256(goal.encode("utf-8")).hexdigest()
        problem = {
            "verification_kind": raw_adapter.VERIFICATION_KIND,
            "raw_goal": goal,
            "goal_sha256": goal_sha,
            "raw_task_contract_sha256": "0" * 64,
            "selected_plan": [ARCHIVE_CAPABILITY],
            "selected_capability_id": ARCHIVE_CAPABILITY,
            "checkpoint_path": "",
            "checkpoint_sha256": "0" * 64,
            "controller_plan_sha256": "0" * 64,
            "accepted_obligation_ids": [],
            "retained_acceptance": {},
            "target_effects": ["raw_goal.accepted.sha256:" + goal_sha],
        }
        verdict = raw_verifier.verify_material(
            problem=problem,
            episode={"steps": [], "preconditions": [], "postconditions": [],
                     "invalidators": []},
            trace=[],
            fact_capsule_head_hash="0" * 64,
            value_capsule_head_hash="0" * 64,
            repo_root=REPO_ROOT,
        )
        self.assertFalse(verdict["pass"])
        self.assertIn(
            "RAW_GOAL_NO_LONGER_MATCHES_ACCEPTED_GRAMMAR", verdict["reason"]
        )

    def test_a_generic_plan_never_falls_into_the_archive_grammar_check(self):
        """The mirror image: the two-step plan must be refused for generic
        reasons, never by the archive sentence grammar."""
        goal = TWO_STEP_GOAL
        goal_sha = hashlib.sha256(goal.encode("utf-8")).hexdigest()
        problem = {
            "verification_kind": raw_adapter.VERIFICATION_KIND,
            "raw_goal": goal,
            "goal_sha256": goal_sha,
            "raw_task_contract_sha256": "0" * 64,
            "selected_plan": list(TWO_STEP_PLAN),
            "selected_capability_id": TWO_STEP_PLAN[-1],
            "checkpoint_path": "",
            "checkpoint_sha256": "0" * 64,
            "controller_plan_sha256": "0" * 64,
            "accepted_obligation_ids": [],
            "retained_acceptance": {},
            "target_effects": ["raw_goal.accepted.sha256:" + goal_sha],
        }
        verdict = raw_verifier.verify_material(
            problem=problem,
            episode={"steps": [], "preconditions": [], "postconditions": [],
                     "invalidators": []},
            trace=[],
            fact_capsule_head_hash="0" * 64,
            value_capsule_head_hash="0" * 64,
            repo_root=REPO_ROOT,
        )
        self.assertFalse(verdict["pass"])
        self.assertNotIn("ACCEPTED_GRAMMAR", verdict["reason"])
        self.assertIn("RAW_TASK_CONTRACT_DIGEST_MISMATCH", verdict["reason"])


class TamperingIsRefusedTests(unittest.TestCase):
    """Every load-bearing claim in the general path must be falsifiable."""

    @classmethod
    def setUpClass(cls):
        cls.adapted, cls.result = _adapted("TAMPER", TWO_STEP_GOAL)
        assert cls.adapted is not None, "precondition: the two-step goal is accepted"
        cls.solver = cls.adapted["solver_output"]
        cls.problem = cls.adapted["problem"]
        cls.episode = cls.solver["current_episode"]
        cls.trace = cls.solver["trace"]

    def _verify(self, **over):
        problem = json.loads(json.dumps(self.problem))
        problem.update(over.get("problem") or {})
        episode = json.loads(json.dumps(over.get("episode") or self.episode))
        trace = over.get("trace") or self.trace
        return raw_verifier.verify_material(
            problem=problem,
            episode=episode,
            trace=trace,
            fact_capsule_head_hash=over.get(
                "fact", self.solver["state_capsule_head_hash"]
            ),
            value_capsule_head_hash=over.get(
                "value", self.solver["value_capsule_head_hash"]
            ),
            repo_root=REPO_ROOT,
        )

    def test_the_baseline_is_green(self):
        verdict = self._verify()
        self.assertTrue(verdict.get("pass"), verdict.get("reason"))

    def test_a_capability_that_is_not_verified_owned_is_refused(self):
        verdict = self._verify(
            problem={
                "selected_plan": [TWO_STEP_PLAN[0], "not.a.real.capability"],
                "selected_capability_id": "not.a.real.capability",
            }
        )
        self.assertFalse(verdict["pass"])
        self.assertIn("RAW_CAPABILITY_NO_LONGER_VERIFIED_OWNED", verdict["reason"])

    def test_a_reordered_plan_is_refused(self):
        """The checkpoint records the order the controller actually ran."""
        verdict = self._verify(
            problem={
                "selected_plan": list(reversed(TWO_STEP_PLAN)),
                "selected_capability_id": TWO_STEP_PLAN[0],
            }
        )
        self.assertFalse(verdict["pass"])
        self.assertIn("CHECKPOINT_ACTION_CAPABILITY_MISMATCH", verdict["reason"])

    def test_a_plan_that_does_not_match_the_retained_capability_is_refused(self):
        verdict = self._verify(
            problem={"selected_plan": [TWO_STEP_PLAN[0], ONE_STEP_PLAN[0]]}
        )
        self.assertFalse(verdict["pass"])
        self.assertIn("RAW_CAPABILITY_NOT_ADMITTED", verdict["reason"])

    def test_a_forged_acceptance_receipt_is_refused(self):
        """The whole point: the receipt is re-derived from the checkpoint's own
        recorded results, so a doctored retained copy cannot match."""
        forged = json.loads(json.dumps(self.problem["retained_acceptance"]))
        forged["accepted_obligation_ids"] = list(
            forged.get("accepted_obligation_ids") or []
        ) + ["RAWREQ:deadbeef"]
        forged["semantic_acceptance_complete"] = True
        verdict = self._verify(problem={"retained_acceptance": forged})
        self.assertFalse(verdict["pass"])
        self.assertIn("RAW_ACCEPTANCE_RECEIPT_MISMATCH", verdict["reason"])

    def test_a_checkpoint_that_no_longer_matches_its_digest_is_refused(self):
        verdict = self._verify(problem={"checkpoint_sha256": "0" * 64})
        self.assertFalse(verdict["pass"])
        self.assertIn("CHECKPOINT_SHA256_MISMATCH", verdict["reason"])

    def test_an_episode_whose_steps_are_not_the_plan_is_refused(self):
        episode = json.loads(json.dumps(self.episode))
        episode["steps"][0]["op"] = ONE_STEP_PLAN[0]
        verdict = self._verify(episode=episode)
        self.assertFalse(verdict["pass"])
        self.assertIn("EPISODE_STEPS_MISMATCH", verdict["reason"])

    def test_an_episode_that_claims_an_effect_on_an_early_step_is_refused(self):
        """Intermediate steps must not claim the accepted effect."""
        effect = self.episode["steps"][-1]["outputs"][0]
        episode = json.loads(json.dumps(self.episode))
        episode["steps"][0]["outputs"] = [effect]
        verdict = self._verify(episode=episode)
        self.assertFalse(verdict["pass"])
        self.assertIn("EPISODE_STEPS_MISMATCH", verdict["reason"])

    def test_a_forged_program_digest_is_refused(self):
        episode = json.loads(json.dumps(self.episode))
        episode["program_sha256"] = "sha256:" + "0" * 64
        verdict = self._verify(episode=episode)
        self.assertFalse(verdict["pass"])
        self.assertIn("EPISODE_PROGRAM_DIGEST_MISMATCH", verdict["reason"])

    def test_a_forged_fact_lineage_head_is_refused(self):
        verdict = self._verify(fact="0" * 64)
        self.assertFalse(verdict["pass"])
        self.assertIn("FACT_LINEAGE_MISMATCH", verdict["reason"])

    def test_a_forged_value_lineage_head_is_refused(self):
        verdict = self._verify(value="0" * 64)
        self.assertFalse(verdict["pass"])
        self.assertIn("VALUE_LINEAGE_MISMATCH", verdict["reason"])

    def test_a_trace_naming_a_different_capability_is_refused(self):
        trace = json.loads(json.dumps(self.trace))
        trace[0]["capability_id"] = ONE_STEP_PLAN[0]
        verdict = self._verify(trace=trace)
        self.assertFalse(verdict["pass"])
        self.assertIn("EPISODE_TRACE_MISMATCH", verdict["reason"])

    def test_a_goal_whose_text_no_longer_hashes_the_same_is_refused(self):
        verdict = self._verify(problem={"raw_goal": TWO_STEP_GOAL + " "})
        self.assertFalse(verdict["pass"])
        self.assertIn("RAW_GOAL_HASH_MISMATCH", verdict["reason"])

    def test_a_missing_selected_plan_is_refused_not_assumed(self):
        """No plan means nothing to re-derive; it must be refused, not assumed."""
        problem = json.loads(json.dumps(self.problem))
        problem.pop("selected_plan")
        verdict = raw_verifier.verify_material(
            problem=problem,
            episode=self.episode,
            trace=self.trace,
            fact_capsule_head_hash=self.solver["state_capsule_head_hash"],
            value_capsule_head_hash=self.solver["value_capsule_head_hash"],
            repo_root=REPO_ROOT,
        )
        self.assertFalse(verdict["pass"])
        self.assertIn("RAW_SELECTED_PLAN_MISSING", verdict["reason"])


class EndToEndLearningTests(unittest.TestCase):
    def test_the_two_step_goal_reaches_a_verified_episode_through_the_real_loop(self):
        """No hand-held verifier call: run the goal, let the front door drain its
        own improvement queue, and require a verified episode whose program is
        exactly this goal's plan."""
        result, _ = _run("E2E", TWO_STEP_GOAL)
        self.assertTrue(result.get("semantic_acceptance_complete"))
        for _ in range(4):
            driver.drain(state_path=_STATE_PATH, repo_root=REPO_ROOT, max_actions=32)
        state = learning.load_state(_STATE_PATH)
        episodes = state.get("episodes") or {}
        rows = list(episodes.values()) if isinstance(episodes, Mapping) else list(episodes)
        found = [
            row for row in rows
            if isinstance(row, Mapping)
            and str(row.get("episode_id") or "").startswith("raw-accepted:")
        ]
        self.assertTrue(found, "no raw-accepted episode was learned from an accepted goal")
        self.assertGreaterEqual(int(state["stats"]["verified_episode_count"]), 1)


if __name__ == "__main__":
    unittest.main()
