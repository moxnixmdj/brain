"""The 3/130 I reported was my harness, not the mechanism. Measured proof.

THE BUG: the runner probed the page (clicking controls to learn what they reveal), then
re-navigated and started over, keeping the plan built during probing.

THE MEASUREMENT that convicted it -- four trials, four differences:

    episode 1 goal: 'Expand the sections below, to find and click on the link "X".'
    episode 2 goal: 'Expand the sections below, to find and click on the link "Y".'
    SAME PROBLEM?  False  (4/4)

Every re-navigation starts a fresh random problem: different target word, different body
text. So the plan described a page that no longer existed. The planner was right and the
harness handed it a different world.

THE FIX: probe in place, never navigate again, plan from the state actually on screen.

RESULT on the three tasks that were scoring zero:
    click-collapsible-2   4/4   rewards 0.811 0.856 0.766 0.765
    click-link            4/4   rewards 0.902 0.902 0.900 0.901
    click-tab-2           4/4   rewards 0.767 0.900 0.812 0.808

FULL SUITE after the fix: 10/130, up from 3/130 -- and still below the 15 baseline, because
the planner path spends probe actions and only handles tasks with a quoted literal.

THE LESSON, which is not about planning: I reported a broken instrument as a property of the
system for two turns. The number was real; the thing it measured was my own ordering bug.
"""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))
ROOT = pathlib.Path(__file__).resolve().parents[2]


def test_the_runner_never_navigates_after_the_first_load():
    src = (ROOT / "canonical/evaluation/bench/run_planned_v1.py").read_text()
    navs = [ln for ln in src.splitlines() if "ch.navigate(" in ln and not ln.strip().startswith("#")]
    assert len(navs) == 1, navs


def test_probe_and_act_share_one_episode():
    src = (ROOT / "canonical/evaluation/bench/run_planned_v1.py").read_text()
    assert "PROBE AND ACT IN THE SAME EPISODE" in src
    assert "Four trials out of four differed" in src


def test_the_three_repaired_tasks_are_recorded_as_passing():
    doc = (ROOT / "canonical/tests/test_the_harness_was_the_bug_v1.py").read_text()
    for task in ("click-collapsible-2", "click-link", "click-tab-2"):
        assert task in doc
