"""An action's meaning must be measured, and a claim of success must come from the reader.

Three ways this experiment could lie, each pinned below:

1. It could read the effect off the atom's NAME. The atom identifiers are opaque and the shuffled
   control changes them, so a solver that keys on labels would come apart -- the solved set must not
   move when labels and order move.
2. It could accept an atom's own report as evidence. A command that prints "ok" and changes nothing
   is INERT here, and can never satisfy a request.
3. It could pretend one experience per action is enough. The same atom measurably does different
   things depending on whether its target already exists, and both cells must be recorded.
"""
from __future__ import annotations

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "tools"))
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))

import instant_learning_in_a_new_environment_v1 as instant  # noqa: E402


class TestTheVocabularyIsStructural:
    def test_the_three_effects_and_inert_are_the_only_shapes_with_names(self) -> None:
        assert instant.classify(1, 1, 0) == instant.PERSIST
        assert instant.classify(-1, 0, 1) == instant.REMOVE
        assert instant.classify(0, 1, 1) == instant.REPLACE
        assert instant.classify(0, 0, 0) == instant.INERT

    def test_a_shape_outside_the_vocabulary_is_refused_rather_than_rounded(self) -> None:
        assert instant.classify(1, 2, 1) == instant.UNCLASSIFIED


class TestTheReaderDecides:
    def test_a_request_is_satisfied_only_by_the_state_change_it_asks_for(self) -> None:
        before = [("a", "x")]
        assert instant.satisfied(instant.Request(instant.PERSIST, content="y"), before, before + [("b", "y")])
        assert not instant.satisfied(instant.Request(instant.PERSIST, content="y"), before, before)
        assert instant.satisfied(instant.Request(instant.REMOVE, old="x"), before, [])
        assert not instant.satisfied(instant.Request(instant.REMOVE, old="x"), before, before)

    def test_an_atom_that_only_prints_ok_is_inert_and_never_counts(self) -> None:
        before = [("a", "x")]
        assert instant.effect_of(before, before, {"content": "y"})["effect"] == instant.INERT


class TestOneExperienceIsOneCellOfATable:
    def test_the_same_command_means_two_things_depending_on_the_state(self, tmp_path: pathlib.Path) -> None:
        machine = instant.build_filesystem(tmp_path)
        machine.reset()
        state = machine.read()
        args = {"content": "newone", "old": instant.PROBE_OLD,
                "name": "fresh_name", "target": "fresh_target"}
        absent = instant.effect_of(state, state + [("fresh_name", "newone")], args)
        exists = instant.effect_of(state, [("fresh_name", "newone"), ("seed2", "probe_second_content")], args)
        assert absent["effect"] == instant.PERSIST
        assert exists["effect"] == instant.REPLACE

    def test_probing_an_existing_target_binds_the_entity_that_actually_holds_it(self, tmp_path: pathlib.Path) -> None:
        machine = instant.build_filesystem(tmp_path)
        machine.reset()
        args = instant.probe_args(machine.read(), "TARGET_EXISTS")
        assert args["name"] == "seed"
        assert instant.probe_args(machine.read(), "TARGET_ABSENT")["name"] != "seed"


class TestLabelsAndPositionsCarryNoKnowledge:
    def test_shuffling_the_atom_names_and_order_does_not_change_what_is_solved(self, tmp_path: pathlib.Path) -> None:
        def solved(seed: int | None) -> list[str]:
            where = tmp_path / f"seed_{seed}"
            where.mkdir()
            machine = instant.build_filesystem(where)
            machine.reset()
            if seed is not None:
                machine = instant._shuffled(machine, seed)
            library = instant.adapt(machine, active=True)["library"]
            out = []
            for request in instant.requests_for():
                machine.reset()
                out.append(instant.solve(machine, request, library)["status"])
            return out

        assert solved(None) == solved(11) == solved(29)
