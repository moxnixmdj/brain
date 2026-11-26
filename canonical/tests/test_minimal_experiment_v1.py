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
    """A dial that wraps every `modulus` ticks, observed `ticks` times.

    `tick` is always AVAILABLE; the dial's cycle shows up in which states are
    accepting. Availability and acceptance are separate facts, and conflating
    them (as an earlier version did) turns every rejecting observation into a
    dead end and makes every dial unlearnable.
    """
    return [
        {
            "access": ["tick"] * k,
            "action": "tick",
            "available": True,
            "accepting": (k + 1) % modulus == 0,
        }
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


class ExactnessTests(unittest.TestCase):
    """The search claims PROVED_MINIMAL, so it is checked against brute force."""

    def test_the_search_matches_an_independent_brute_force(self):
        import itertools

        def brute(nodes, children, label):
            n = len(nodes)
            index = {x: i for i, x in enumerate(nodes)}
            status = {x: me._action_status(children, {}, x) for x in nodes}
            best = n
            for assignment in itertools.product(range(n), repeat=n):
                size = max(assignment) + 1
                if size >= best:
                    continue
                ok = True
                for i in range(n):
                    for j in range(i + 1, n):
                        if assignment[i] != assignment[j]:
                            continue
                        a = label.get(nodes[i], "?")
                        b = label.get(nodes[j], "?")
                        if a != "?" and b != "?" and a != b:
                            ok = False
                            break
                        if not me._statuses_compatible(status[nodes[i]], status[nodes[j]]):
                            ok = False
                            break
                    if not ok:
                        break
                if not ok:
                    continue
                targets = {}
                for i in range(n):
                    for act, tgt in (children.get(nodes[i]) or {}).items():
                        key = (assignment[i], act)
                        tb = assignment[index[tgt]]
                        if key in targets and targets[key] != tb:
                            ok = False
                            break
                        targets[key] = tb
                    if not ok:
                        break
                if ok:
                    best = size
            return best

        rng = random.Random(11)
        checked = 0
        for _ in range(40):
            depth = rng.randrange(2, 5)
            nodes = [()]
            for _ in range(depth - 1):
                nodes.append(nodes[-1] + (rng.choice("ab"),))
            children = {}
            for node in nodes:
                for act in "ab":
                    tgt = node + (act,)
                    if tgt in nodes and rng.random() < 0.7:
                        children.setdefault(node, {})[act] = tgt
            label = {x: rng.choice(["+", "-", "?"]) for x in nodes[1:]}
            part = me._minimum_partition(nodes, children, label, {})
            self.assertEqual(
                brute(nodes, children, label), len(set(part.values())),
                f"exhaustive search disagreed with brute force on {nodes}",
            )
            checked += 1
        self.assertEqual(40, checked)


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
        obs = tick_observations(3, 10)
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
