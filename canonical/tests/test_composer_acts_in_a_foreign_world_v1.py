"""The composer must be able to act in a world that is not its own repository.

WHY THIS IS THE LOAD-BEARING TEST. `astra_runtime._invoke_bound_capability` was fixed to take an
`execution_root`, and its docstring states what the absence cost:

    "The system could not act in any environment but its own. That is fatal for learning where a plan
     applies. Every 'new environment' was the same environment, so no real contrast could ever be
     produced, so every applicability boundary stayed UNDETERMINED however many runs happened."

That fix stopped at the runtime call. `execute_chain` still ran every step against the repository, so a
correctly compiled chain for a goal naming files in a caller's directory died with `PATH_OUTSIDE_REPOSITORY`
before doing any work. Measured 2026-11-23.

Every claim about "a new environment" rests on this. If the system can only act in its own checkout, no
experience is ever new, and the core hypothesis cannot be tested at all.
"""
from __future__ import annotations

import json
import pathlib
import tempfile

from canonical.runtime import composer_route_v1 as C

_GOAL = "Verify the tar.gz archive {archive} against the manifest {manifest}"


def _world() -> tuple[pathlib.Path, str]:
    world = pathlib.Path(tempfile.mkdtemp(prefix="foreign_world_"))
    manifest = world / "M.json"
    manifest.write_text(json.dumps({"files": {}}))
    return world, _GOAL.format(archive=world / "x.tar.gz", manifest=manifest)


def test_a_chain_of_a_goal_that_names_a_file_outside_the_repository_runs() -> None:
    """THE DEFECT, END TO END. Before `root=`, this goal compiled correctly and then refused with
    `PATH_OUTSIDE_REPOSITORY`; the archive was never created. The two capabilities run directly against the
    same world produce it, so the limitation was never the capability's -- only this function's.
    """
    world, goal = _world()

    chain = C.route(goal, cwd=str(world))["chain"]
    assert chain, "the goal must compile before its execution can be judged"

    result = C.execute_chain(chain, goal, root=world)

    assert result["status"] == "PASS__COMPOSER_CHAIN_EXECUTED", result
    assert (world / "x.tar.gz").is_file(), sorted(p.name for p in world.iterdir())
    # and the effect is in the CALLER'S world, not the repository
    assert sorted(p.name for p in world.iterdir()) == ["M.json", "x.tar.gz"]


def test_no_root_still_behaves_exactly_as_before() -> None:
    """ADDITIVE BY DESIGN, and the reason it can be trusted.

    `root=None` must leave every existing caller untouched -- including the repository-only path refusal
    that a goal naming an outside file produces. A change that quietly widened the repository boundary for
    all callers would be a safety regression disguised as a feature.
    """
    world, goal = _world()
    chain = C.route(goal, cwd=str(world))["chain"]

    result = C.execute_chain(chain, goal)          # no root

    assert result["status"] != "PASS__COMPOSER_CHAIN_EXECUTED", result
    assert (result.get("failed_step") or {}).get("reason", "").endswith("PATH_OUTSIDE_REPOSITORY"), result


def test_the_guard_and_the_adapter_watch_the_same_tree() -> None:
    """THE TRAP A NAIVE FIX FALLS INTO.

    `run_adapter_locally` hands its adapter `fn(call_args, ROOT)`, runs the write-authority check against
    ROOT, captures transition preimages under ROOT and restores them under ROOT. Threading a world into
    only the adapter's argument would let it write to one place while the guard watched another -- and a
    guard watching the wrong tree does not fail, it APPROVES.

    `_with_workspace_root` moves all of those references at once, and moves `composer_route._ACTIVE_REPO_ROOT`
    with them, so the world a step is planned in and the world it is judged in are the same by construction.
    This test asserts that binding is actually used rather than reimplemented.
    """
    from canonical.runtime import live_brain_route_admission_v1 as ra

    world = pathlib.Path(tempfile.mkdtemp(prefix="bind_"))
    before = pathlib.Path(str(ra.ROOT))
    with ra._with_workspace_root(world):
        inside = pathlib.Path(str(ra.ROOT))
        composer_root = getattr(C, "_ACTIVE_REPO_ROOT", None)
        composer_sees = pathlib.Path(str(composer_root.get())) if composer_root is not None else None
    after = pathlib.Path(str(ra.ROOT))

    assert inside == world.resolve(), (inside, world)
    assert after == before, (after, before)
    if composer_sees is not None:
        assert composer_sees == world.resolve(), composer_sees
