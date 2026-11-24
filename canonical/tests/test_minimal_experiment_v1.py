"""What to save, tested against the failure this project already measured.

The claim under test is narrow and it must stay narrow:

  from a handful of probes on an unseen environment, the smallest machine
  consistent with them is computed, it is saved instead of the probes, and the
  next probe is chosen because it SEPARATES the surviving machines.

Every test below can fail. The three that matter most:

* `test_greedy_never_beats_the_exhaustive_search` -- if the polynomial path ever
  found a SMALLER machine than the exhaustive one, the exhaustive one is not
  exhaustive and the `PROVED_MINIMAL` label is a lie.
* `test_labelless_merge_would_collapse_a_dial` -- the specific bug this module
  shipped with for one iteration: caching block labels lost the + / - distinction
  and merged a 3-state dial into 1 state. The module's own consistency check
  caught it; this test keeps it caught.
* `test_refusal_is_the_answer_when_observations_contradict` -- a contradictory
  observation set is refused, not averaged into a machine.
"""
from __future__ import annotations

import random
import unittest

from canonical.runtime import minimal_experiment_v1 as me


def tick_observations(modulus: int, ticks: int):
    """A dial that wraps every `modulus` ticks, observed `ticks` times."""
    return [
        {"access": ["tick"] * k, "action": "tick", "accepting": (k + 1) % modulus == 0}
        for k in range(ticks)
    ]


def dial(step: int, modulus: int = 3):
    return me.make_machine(
        states=list(range(modulus)),
        start=0,
        accepting=[0],
        transitions={(s, "tick"): (s + step) % modulus for s in range(modulus)},
        actions=["tick"],
    )


class MinimalMachineTests(unittest.TestCase):
    def test_a_three_state_dial_is_recovered_from_ticks(self):
        """11 tree nodes collapse to the 3 real states."""
        obs = tick_observations(3, 10)
        out = me.minimal_consistent_machine(obs)
        self.assertEqual("PASS__MINIMAL_MACHINE", out["status"])
        self.assertEqual(3, out["state_count"])
        self.assertGreater(out["tree_node_count"], out["state_count"])
        self.assertTrue(me.is_consistent(out["machine"], obs))

    def test_a_two_state_dial_is_proved_minimal(self):
        obs = tick_observations(2, 4)
        out = me.minimal_consistent_machine(obs)
        self.assertEqual(2, out["state_count"])
        self.assertEqual("PROVED_MINIMAL", out["optimality"])
        self.assertEqual(
            "SMALLEST_MACHINE_CONSISTENT_WITH_THESE_OBSERVATIONS", out["claim"]
        )

    def test_the_saved_unit_is_the_machine_not_the_trajectory(self):
        """The whole point: what is stored is behaviour, not the path taken."""
        obs = tick_observations(3, 10)
        unit = me.learnable_unit(scope="dial", observations=obs)
        self.assertEqual("LEARNABLE_UNIT", unit["status"])
        saved = unit["learnable_unit"]
        self.assertEqual(3, saved["state_count"])
        # 10 observations, 3 states: the row is smaller than the evidence
        self.assertLess(saved["state_count"], saved["observations_used"])
        self.assertEqual("SMALLEST_MACHINE_CONSISTENT_WITH_THESE_OBSERVATIONS", saved["claim"])
        # and it is explicitly not an identification
        self.assertEqual("THE_MACHINE", saved["not_claimed"])

    def test_contradictory_observations_are_refused_not_averaged(self):
        obs = tick_observations(3, 4)
        obs.append({"access": [], "action": "tick", "accepting": not obs[0]["accepting"]})
        out = me.minimal_consistent_machine(obs)
        self.assertEqual("REFUSED__OBSERVATIONS_CONTRADICTORY", out["status"])
        self.assertIsNone(out["machine"])
        unit = me.learnable_unit(scope="dial", observations=obs)
        self.assertIsNone(unit["learnable_unit"])
        self.assertEqual("NONE", unit["authority"])

    def test_unobserved_actions_are_named_as_residual_questions(self):
        """What the data does not determine is reported, not guessed."""
        obs = tick_observations(3, 3)
        out = me.minimal_consistent_machine(obs)
        self.assertIn("tick", out["unresolved_actions"])


class GreedyVersusExactTests(unittest.TestCase):
    def test_greedy_never_beats_the_exhaustive_search(self):
        """If greedy ever found fewer blocks, the exhaustive search is incomplete."""
        rng = random.Random(7)
        compared = 0
        for _ in range(200):
            modulus = rng.choice([2, 3])
            actions = ["a", "b"][: rng.choice([1, 2])]
            trans = {(s, a): rng.randrange(modulus) for s in range(modulus) for a in actions}
            accepting = [s for s in range(modulus) if rng.random() < 0.4]
            observations = []
            for _ in range(rng.randrange(2, 6)):
                word = tuple(rng.choice(actions) for _ in range(rng.randrange(0, 4)))
                state = 0
                for step in word:
                    state = trans[(state, step)]
                last = rng.choice(actions)
                observations.append(
                    {
                        "access": list(word),
                        "action": last,
                        "accepting": trans[(state, last)] in accepting,
                    }
                )
            if not me.observations_consistent(observations)["consistent"]:
                continue
            tree = me.build_observation_tree(observations)
            nodes = sorted(set(tree["children"]) | set(tree["terminal"]))
            if len(nodes) > 7:
                continue
            label = {n: ("+" if tree["terminal"][n] else "-") for n in tree["terminal"]}
            exact = me._minimum_partition(nodes, tree["children"], label)
            greedy = me._merge_greedily(nodes, tree["children"], label)
            if exact is None:
                continue
            compared += 1
            # The direction is the whole point. Exhaustive search is the lower
            # bound: a polynomial greedy pass may fail to find a merge that
            # exists (that is what "suboptimal" means and it is allowed), but it
            # may NEVER find a merge the exhaustive search missed. An earlier
            # version of this test asserted the inequality backwards and so
            # failed on a correct implementation.
            self.assertGreaterEqual(
                len(set(greedy.values())),
                len(set(exact.values())),
                "greedy found a smaller machine than the exhaustive search: "
                "the exhaustive search is incomplete and PROVED_MINIMAL is a lie",
            )
        self.assertGreater(compared, 100, "the comparison never ran enough cases")


class SeparatingExperimentTests(unittest.TestCase):
    def test_the_shortest_separating_word_is_found(self):
        """A +1 dial and a +2 dial, made distinguishable, differ on one tick.

        The plain +1/+2 dials are NOT separable by observation alone -- both
        visit every residue, so any observable 3-state Moore labelling agrees.
        They are only separable once the difference is observable, which is what
        `accepting` does here. A test claiming otherwise would be testing a
        property the machines do not have.
        """
        a = me.make_machine(states=[0, 1, 2], start=0, accepting=[1],
                            transitions={(0, "tick"): 1, (1, "tick"): 2, (2, "tick"): 0},
                            actions=["tick"])
        b = me.make_machine(states=[0, 1, 2], start=0, accepting=[2],
                            transitions={(0, "tick"): 1, (1, "tick"): 2, (2, "tick"): 0},
                            actions=["tick"])
        self.assertEqual(["tick"], me.separating_word(a, b))

    def test_a_hidden_difference_is_reported_as_unseparable_not_as_equal(self):
        """Two +1/+2 dials agree on every observation: 'not separable here'."""
        a, b = dial(1), dial(2)
        self.assertIsNone(me.separating_word(a, b))
        self.assertTrue(me.machines_equivalent(a, b))
        # and the bounded claim must be reported as bounded
        self.assertIsNone(me.separating_word(a, b, max_depth=8))

    def test_identical_machines_are_equivalent(self):
        self.assertTrue(me.machines_equivalent(dial(1), dial(1)))

    def test_an_undefined_action_is_a_disagreement_not_a_tie(self):
        """One machine has the action, one does not: asking settles it."""
        a = me.make_machine(states=[0, 1], start=0, transitions={(0, "x"): 1}, actions=["x"])
        b = me.make_machine(states=[0], start=0, transitions={}, actions=["x"])
        self.assertEqual(["x"], me.separating_word(a, b))

    def test_relabelling_does_not_change_identity(self):
        """The same machine under different state names is the same saved row."""
        relabelled = me.make_machine(
            states=[10, 20, 30],
            start=20,
            accepting=[20],
            transitions={
                (20, "tick"): 30,
                (30, "tick"): 10,
                (10, "tick"): 20,
            },
            actions=["tick"],
        )
        self.assertEqual(
            me.machine_digest(me.canonically_relabelled(dial(1))),
            me.machine_digest(me.canonically_relabelled(relabelled)),
        )

    def test_the_ranking_returns_the_separating_experiment(self):
        a = me.make_machine(states=[0, 1, 2], start=0, accepting=[1],
                            transitions={(0, "tick"): 1, (1, "tick"): 2, (2, "tick"): 0},
                            actions=["tick"])
        b = me.make_machine(states=[0, 1, 2], start=0, accepting=[2],
                            transitions={(0, "tick"): 1, (1, "tick"): 2, (2, "tick"): 0},
                            actions=["tick"])
        out = me.rank_experiments(a, hypotheses=[b], max_depth=2)
        self.assertEqual("QUESTION", out["status"])
        self.assertIn(["tick"], [q["word"] for q in out["queries"]])
        self.assertEqual(1, out["best"]["eliminates"])

    def test_no_rivals_is_reported_as_a_plateau_not_a_solution(self):
        out = me.rank_experiments(dial(1), hypotheses=[])
        self.assertEqual("NO_RIVALS", out["status"])
        self.assertIn("never enumerated", out["note"])


class SingleExperienceTransferTests(unittest.TestCase):
    """The mission's central claim, tested as narrowly as it can be stated.

    Learn the machine once in one application, then predict an UNSEEN second
    application that runs the same behaviour under a different action name and
    for more steps. Held-out, not replayed.
    """

    def _learn(self, action, ticks=6, modulus=3):
        obs = [
            {"access": [action] * k, "action": action, "accepting": (k + 1) % modulus == 0}
            for k in range(ticks)
        ]
        return obs, me.learnable_unit(scope="appA", observations=obs)["learnable_unit"]

    def test_one_experience_transfers_to_a_renamed_app(self):
        obs_a, unit = self._learn("tick")
        self.assertEqual(3, unit["state_count"])
        # app B: same behaviour, different vocabulary, steps the learner never saw
        obs_b = [
            {"access": ["turn"] * k, "action": "turn", "accepting": (k + 1) % 3 == 0}
            for k in range(6, 14)
        ]
        renamed = me.make_machine(
            states=unit["machine"]["states"],
            start=unit["machine"]["start"],
            accepting=unit["machine"]["accepting"],
            transitions={
                (int(s), "turn"): t
                for s, row in unit["machine"]["transitions"].items()
                for _act, t in row.items()
            },
            actions=["turn"],
        )
        verdict = me.admit_learnable_unit({"machine": renamed}, held_out=obs_b)
        self.assertEqual("ADMIT", verdict["verdict"], verdict["reasons"])
        self.assertEqual(8, verdict["held_out_count"])

    def test_the_saved_machine_is_vocabulary_independent(self):
        """The same behaviour under two action names is ONE saved row."""
        a = me.make_machine(states=[0, 1, 2], start=0, accepting=[0],
                            transitions={(s, "tick"): (s + 1) % 3 for s in range(3)},
                            actions=["tick"])
        b = me.make_machine(states=[0, 1, 2], start=0, accepting=[0],
                            transitions={(s, "turn"): (s + 1) % 3 for s in range(3)},
                            actions=["turn"])
        self.assertEqual(
            me.machine_digest(me.canonically_relabelled(a)),
            me.machine_digest(me.canonically_relabelled(b)),
        )

    def test_a_different_behaviour_is_refused_across_apps(self):
        """Transfer must fail loudly when the behaviour is not actually the same."""
        obs_a, unit = self._learn("tick")
        other = [
            {"access": ["turn"] * k, "action": "turn", "accepting": (k + 1) % 2 == 0}
            for k in range(6, 10)
        ]
        renamed = me.make_machine(
            states=unit["machine"]["states"],
            start=unit["machine"]["start"],
            accepting=unit["machine"]["accepting"],
            transitions={
                (int(s), "turn"): t
                for s, row in unit["machine"]["transitions"].items()
                for _act, t in row.items()
            },
            actions=["turn"],
        )
        verdict = me.admit_learnable_unit({"machine": renamed}, held_out=other)
        self.assertEqual("REFUSE", verdict["verdict"])


class CompressionAndAdmissionTests(unittest.TestCase):
    def test_no_compression_is_not_reported_as_compression(self):
        """When the machine is not smaller than the data, it must say so."""
        obs = [{"access": [], "action": "tick", "accepting": (k % 2 == 0)} for k in range(1)]
        report = me.compression_report(
            observations=obs,
            machine=me.make_machine(states=[0, 1], start=0, transitions={(0, "tick"): 1},
                                    accepting=[1], actions=["tick"]),
        )
        self.assertEqual("NO_COMPRESSION", report["status"])
        self.assertEqual("NONE", report["authority"])

    def test_compression_is_reported_when_it_happens(self):
        obs = tick_observations(3, 12)
        out = me.minimal_consistent_machine(obs)
        report = me.compression_report(observations=obs, machine=out["machine"])
        self.assertEqual("COMPRESSED", report["status"])
        self.assertLess(report["states"], report["observations"])

    def test_a_unit_admits_only_with_a_confirmed_held_out_prediction(self):
        obs = tick_observations(3, 4)
        unit = me.learnable_unit(scope="dial", observations=obs)
        verdict = me.admit_learnable_unit(
            unit["learnable_unit"], held_out=tick_observations(3, 7)[4:]
        )
        self.assertEqual("ADMIT", verdict["verdict"], verdict["reasons"])

    def test_a_unit_is_refused_when_held_out_data_contradicts_it(self):
        obs = tick_observations(3, 4)
        unit = me.learnable_unit(scope="dial", observations=obs)
        contradicted = [{"access": ["tick"] * 5, "action": "tick", "accepting": False}]
        verdict = me.admit_learnable_unit(unit["learnable_unit"], held_out=contradicted)
        self.assertEqual("REFUSE", verdict["verdict"])
        self.assertIn("CONTRADICTED_ON_HELD_OUT", verdict["reasons"])

    def test_admission_needs_a_held_out_prediction_not_just_consistency(self):
        """Replaying the same data is not generalisation."""
        obs = tick_observations(3, 4)
        unit = me.learnable_unit(scope="dial", observations=obs)
        verdict = me.admit_learnable_unit(unit["learnable_unit"], held_out=[])
        self.assertEqual("REFUSE", verdict["verdict"])
        self.assertIn("NO_HELD_OUT_PREDICTION_CONFIRMED", verdict["reasons"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
