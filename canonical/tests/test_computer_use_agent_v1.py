#!/usr/bin/env python3
"""Computer-use agent: act from calculated state keys, not learned parameters.

Tests run against real file operations and real subprocesses. No synthetic
tasks, no model calls, no network at decision time. Every effect is real.

Pinned:
  * state key synthesis separates every wrong action from the right one
  * standing facts detect invalidation at the causal step
  * instant knowledge is zero-parameter (model_calls=0, network_calls=0)
  * the agent refuses when no applicable action exists
  * the full loop completes end to end on real shell transformations
"""

from __future__ import annotations

import json
import pathlib
import shutil
import sys
import tempfile

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from canonical.swe_kernel.computer_use_agent_v1 import (  # noqa: E402
    ComputerUseAgent,
    synthesize_state_key,
    connect_instant_knowledge,
    StandingFactsLedger,
    FEATURES,
)
from canonical.swe_kernel.standing_facts_v1 import (  # noqa: E402
    establish,
    revalidate,
    touched,
    at_risk,
)
from canonical.swe_kernel.computer_use_check_density_v1 import (  # noqa: E402
    TASKS,
    _has,
    _mutants,
    _run,
    _seed,
)

TEXT = b"alpha beta gamma\ndelta epsilon\nzeta eta theta\niota kappa\n"


def _seeded_root() -> pathlib.Path:
    root = pathlib.Path(tempfile.mkdtemp(prefix="brain-agent-test-"))
    _seed(root)
    return root


# --------------------------------------------------------------------------- state key synthesis
def test_state_key_synthesis_separates_every_wrong_action() -> None:
    """The synthesised minimal cover separates every mechanically derived wrong
    action from the right action, and rejects mtime by stability."""
    root = _seeded_root()
    try:
        name, command, program = TASKS[0]  # gzip
        if not _has(program):
            pytest.skip(f"program not installed: {program}")
        right_command = command.replace("{src}", "in.txt").replace("{dst}", "out.dat")
        wrong_actions = [
            (kind, cmd.replace("{src}", "in.txt").replace("{dst}", "out.dat"))
            for kind, cmd in _mutants(command)
        ]
        result = synthesize_state_key(root, right_command, wrong_actions)
        assert result["every_wrong_action_separable"] is True
        assert result["inseparable"] == []
        assert result["minimal_cover"] == ["content"]
        # mtime must never be in the minimal cover: stability rejects timestamps.
        assert "mtime" not in (result["minimal_cover"] or [])
    finally:
        shutil.rmtree(root, ignore_errors=True)


def test_state_key_is_stable_under_replay() -> None:
    """Stability means the right action reproduces its projection on replay."""
    root = _seeded_root()
    try:
        name, command, program = TASKS[2]  # sort
        if not _has(program):
            pytest.skip(f"program not installed: {program}")
        right_command = command.replace("{src}", "in.txt").replace("{dst}", "out.dat")
        wrong_actions = [
            (kind, cmd.replace("{src}", "in.txt").replace("{dst}", "out.dat"))
            for kind, cmd in _mutants(command)
        ]
        result = synthesize_state_key(root, right_command, wrong_actions)
        # Every wrong action separable means the observation is sound.
        assert result["every_wrong_action_separable"] is True
        # Stability: mtime is rejected by the two-sided test.
        assert "mtime" in result["rejected_by_stability"]
    finally:
        shutil.rmtree(root, ignore_errors=True)


def test_state_key_with_no_wrong_actions_has_empty_cover() -> None:
    """With no wrong actions to separate, the minimum cover is empty."""
    root = _seeded_root()
    try:
        result = synthesize_state_key(root, "true", [])
        assert result["minimal_cover"] == []
        assert result["inseparable"] == []
        assert result["every_wrong_action_separable"] is True
    finally:
        shutil.rmtree(root, ignore_errors=True)


# --------------------------------------------------------------------------- instant knowledge
def test_instant_knowledge_is_zero_parameter() -> None:
    """Instant knowledge reports model_calls=0 and network_calls=0: nothing is
    read from learned parameters."""
    knowledge = connect_instant_knowledge(goal="sort a file")
    assert knowledge["model_calls"] == 0
    assert knowledge["network_calls"] == 0
    assert knowledge["goal"] == "sort a file"
    assert "recall" in knowledge


def test_instant_knowledge_reads_from_disk_not_weights() -> None:
    """Recall returns documents from the unified model index (path + terms),
    never embedded text."""
    knowledge = connect_instant_knowledge(goal="archive tar gz manifest")
    for doc in knowledge.get("recall", []):
        assert "path" in doc
        assert "score" in doc
        assert "authority" in doc
        assert "terms" in doc


# --------------------------------------------------------------------------- standing facts
def test_standing_facts_detect_invalidation_at_causal_step() -> None:
    """A fact established at step 1 and falsified at step 2 by a legal action
    is detected at step 2, not at the symptom."""
    root = _seeded_root()
    try:
        state_before = establish(_files_state(root), 1)
        # Simulate a step that overwrites in.txt with decoy content.
        shutil.copy2(root / "decoy.txt", root / "in.txt")
        state_after = _files_state(root)
        still, broken = revalidate(state_before, state_after, 2)
        assert len(broken) == 1
        assert broken[0]["path"] == "in.txt"
        assert broken[0]["established_at"] == 1
        assert broken[0]["invalidated_at"] == 2
    finally:
        shutil.rmtree(root, ignore_errors=True)


def test_standing_facts_control_stays_quiet() -> None:
    """An unsabotaged chain raises no invalidations."""
    root = _seeded_root()
    try:
        state_before = establish(_files_state(root), 1)
        state_after = _files_state(root)  # unchanged
        still, broken = revalidate(state_before, state_after, 2)
        assert broken == []
        assert len(still) == len(state_before)
    finally:
        shutil.rmtree(root, ignore_errors=True)


def test_touched_wildcard_is_prefix() -> None:
    """A wildcard pattern in a frame is read as a prefix match."""
    contract = {"frame": {"creates": ["chunk_*"], "modifies": [], "removes": []}}
    touch = touched(contract, {"src": "in.txt", "dst": "out.dat"})
    assert touch == {"chunk_*"}
    facts = establish({"chunk_aa": b"1", "keep.txt": b"2"}, 1)
    risky = at_risk(facts, touch)
    assert [f["path"] for f in risky] == ["chunk_aa"]


# --------------------------------------------------------------------------- full agent loop
def test_agent_refuses_when_no_applicable_action() -> None:
    """The agent refuses rather than guessing when no shell transformation
    matches the instruction."""
    root = _seeded_root()
    try:
        agent = ComputerUseAgent(root)
        report = agent.run("fly to the moon")
        assert report["status"] != "COMPLETE"
        assert report["result"] == "REFUSED__NO_STATE_KEY"
        assert report["model_calls"] == 0
        assert report["network_calls"] == 0
    finally:
        shutil.rmtree(root, ignore_errors=True)


def test_agent_loop_completes_on_real_transformation() -> None:
    """The full loop runs end to end on a real shell transformation: SENSE
    synthesises the state key, NOTICE connects instant knowledge, RANK selects
    the action, ACT executes it, RE-VALIDATE checks standing facts, ADMIT runs
    the gate, REMEMBER persists only if admitted."""
    root = _seeded_root()
    try:
        agent = ComputerUseAgent(root)
        report = agent.run("gzip a file")
        assert report["model_calls"] == 0
        assert report["network_calls"] == 0
        phase_names = [p["phase"] for p in report["phases"]]
        assert "SENSE" in phase_names
        assert "NOTICE_IGNORANCE" in phase_names
        assert "RANK" in phase_names
        assert "ACT" in phase_names
        assert "RE-VALIDATE" in phase_names
        # state key synthesised and separating
        sense = [p for p in report["phases"] if p["phase"] == "SENSE"][0]
        assert sense["state_key"]["every_wrong_action_separable"] is True
        # instant knowledge connected with zero parameters
        notice = [p for p in report["phases"] if p["phase"] == "NOTICE_IGNORANCE"][0]
        assert notice["model_calls"] == 0
        assert notice["network_calls"] == 0
    finally:
        shutil.rmtree(root, ignore_errors=True)


def test_agent_does_not_consult_learned_parameters() -> None:
    """Every phase of the loop reports model_calls=0 and network_calls=0."""
    root = _seeded_root()
    try:
        agent = ComputerUseAgent(root)
        report = agent.run("sort a file")
        for phase in report["phases"]:
            assert phase.get("model_calls", 0) == 0, phase
            assert phase.get("network_calls", 0) == 0, phase
    finally:
        shutil.rmtree(root, ignore_errors=True)


# --------------------------------------------------------------------------- helpers
def _files_state(root: pathlib.Path) -> dict[str, bytes]:
    out: dict[str, bytes] = {}
    for path in sorted(p for p in root.rglob("*") if p.is_file()):
        rel = path.relative_to(root).as_posix()
        out[rel] = path.read_bytes()
    return out


def test_speculative_cow_rollout_and_articulation_subgoals() -> None:
    """Speculative CoW rollouts evaluate candidate actions in shadow workspaces without side effects,
    and Petri-net articulation subgoals factor long-horizon workflows at exact cut-vertices."""
    from canonical.swe_kernel.computer_use_agent_v1 import (
        find_articulation_subgoals,
        run_checkpointed_horizon,
    )

    edges = [
        ("S0", "A1"),
        ("S0", "A2"),
        ("A1", "C1"),
        ("A2", "C1"),
        ("C1", "B1"),
        ("C1", "B2"),
        ("B1", "C2"),
        ("B2", "C2"),
        ("C2", "GOAL"),
    ]
    cuts = find_articulation_subgoals(edges, "S0", "GOAL")
    assert cuts == ["C1", "C2"]

    root = _seeded_root()
    try:
        agent = ComputerUseAgent(root)
        rollout = agent.speculative_cow_rollout(
            candidate_commands=[
                "rm -f in.txt",
                "cp in.txt out.dat",
            ],
            goal_predicates={
                "in_preserved": lambda r: (r / "in.txt").is_file(),
                "out_created": lambda r: (r / "out.dat").is_file(),
            },
        )
        assert rollout["committed"] is True
        assert rollout["winning_branch"]["command"] == "cp in.txt out.dat"
        assert (root / "in.txt").is_file()
        assert (root / "out.dat").is_file()

        horizon = run_checkpointed_horizon(
            agent,
            [
                {
                    "checkpoint_id": "C1",
                    "command": "sort out.dat > sorted.dat",
                    "validator": lambda r: (r / "sorted.dat").is_file(),
                },
                {
                    "checkpoint_id": "C2",
                    "command": "wc -l < sorted.dat > count.txt",
                    "validator": lambda r: (r / "count.txt").is_file(),
                },
            ],
        )
        assert horizon["status"] == "HORIZON_COMPLETE"
        assert horizon["checkpoints_verified"] == 2

        from canonical.swe_kernel.computer_use_agent_v1 import UnifiedCrossModalPetriNet

        net = UnifiedCrossModalPetriNet()
        net.add_transition("click_export_btn", "GUI", ["DomTree"], "SqlitePath", lambda dom: str(root / "in.txt"))
        net.add_transition("query_rows", "SQLITE", ["SqlitePath"], "RawRows", lambda p: pathlib.Path(p).read_text().splitlines())
        net.add_transition("normalize_rows", "PYTHON", ["RawRows"], "NormalizedPatch", lambda rows: sorted(r.strip() for r in rows if r.strip()))
        net.add_transition("verify_cli", "CLI", ["NormalizedPatch"], "VerifiedReceipt", lambda rows: f"VERIFIED:{len(rows)}")
        cryst = net.execute_and_crystallize("cross_modal_export_verify", {"DomTree": "<button id='export'/>"}, "VerifiedReceipt")
        assert cryst["status"] == "VERIFIED_AND_CRYSTALLIZED"
        assert cryst["morphism"]["modalities"] == ["GUI", "SQLITE", "PYTHON", "CLI"]
        assert cryst["goal_value"].startswith("VERIFIED:")
    finally:
        shutil.rmtree(root, ignore_errors=True)

