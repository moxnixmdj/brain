"""The computer-use loop, closed end to end without a display.

Every earlier note in this repo said the OSWorld stack was present but unexercised, and blamed
the missing desktop. The desktop is genuinely missing -- no browser, no chromedriver, no Xvfb.

But the loop itself needs only a four-member environment seam, and `execute_typed_action` /
`observe` are already written against `env: Any`. So the loop can be closed against a virtual
desktop, and what remains unproven is narrowed to exactly one thing: that pyautogui drives a
real operating system.

What is exercised here for real, not simulated:

  * `BrainOSWorldAgent` -- the shipped OSWorld adapter, its 1920x1080 protocol gate, its
    observation builder, its action compiler
  * `route_relational_visual` / `ground_visual_region` -- the shipped pixel-grounding policy
  * `compile_actions` -> `compile_osworld_pyautogui` -- the shipped command compiler
  * `execute_typed_action` / `observe` -- the shipped surface validator and observer

Only `VirtualDesktop` is a double.
"""
from __future__ import annotations

import pathlib
import sys

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

PIL = pytest.importorskip("PIL", reason="visual grounding and the virtual desktop need Pillow")

from canonical.tests.virtual_desktop_v1 import (  # noqa: E402
    HEIGHT,
    WIDTH,
    VirtualDesktop,
    VirtualDesktopError,
    Widget,
)
from canonical.runtime.osworld_computer_surface_v1 import (  # noqa: E402
    execute_typed_action,
    observe,
)
from canonical.runtime.osworld_v21_brain_agent_adapter_v1 import (  # noqa: E402
    BrainOSWorldAgent,
)
from canonical.runtime.osworld_v21_visual_relational_grounding_v1 import (  # noqa: E402
    route_relational_visual,
)

LEFT = Widget("left", (200, 400, 400, 600))
RIGHT = Widget("right", (1500, 400, 1700, 600))


def _desktop(instruction: str, widgets=None) -> VirtualDesktop:
    widgets = [LEFT, RIGHT] if widgets is None else widgets
    target = "left" if "leftmost" in instruction else "right"
    return VirtualDesktop(
        widgets,
        instruction=instruction,
        success=lambda d: d.selected == target,
    )


def _agent() -> BrainOSWorldAgent:
    return BrainOSWorldAgent(route_relational_visual, policy_id="visual-relational-v1")


def _run(desktop: VirtualDesktop) -> tuple[str, list[str]]:
    agent = _agent()
    observation = observe(desktop)
    return agent.predict(desktop.instruction, observation)


# --------------------------------------------------------------------------- the desktop is real
def test_the_virtual_screen_is_a_real_1920x1080_png():
    from PIL import Image
    import io

    screenshot = VirtualDesktop([LEFT, RIGHT], instruction="x").render("rgb_array")
    assert screenshot.startswith(b"\x89PNG\r\n\x1a\n")
    assert Image.open(io.BytesIO(screenshot)).size == (WIDTH, HEIGHT)


def test_the_observation_satisfies_the_surface_contract():
    observation = observe(_desktop("click the leftmost red box"))
    assert isinstance(observation["screenshot"], bytes)
    assert observation["instruction"] == "click the leftmost red box"
    assert observation["screen"] == {"width": WIDTH, "height": HEIGHT}


def test_the_desktop_refuses_a_command_it_cannot_honour():
    """A harness that swallowed an unknown command would invent a passing loop."""
    desktop = _desktop("click the leftmost red box")
    with pytest.raises(VirtualDesktopError):
        desktop.step("pyautogui.teleport(x=1, y=1)")


# --------------------------------------------------------------------------- the loop closes
def test_leftmost_instruction_clicks_the_left_widget_and_wins():
    desktop = _desktop("click the leftmost red box")
    response, actions = _run(desktop)

    assert len(actions) == 1
    observation, reward, done, _ = desktop.step(actions[0])

    assert desktop.selected == "left", actions
    assert desktop.widget("right").selected is False
    assert reward == 1.0 and done is True
    assert isinstance(response, str) and response


def test_rightmost_instruction_clicks_the_right_widget_and_wins():
    desktop = _desktop("click the rightmost red box")
    _, actions = _run(desktop)
    desktop.step(actions[0])

    assert desktop.selected == "right", actions
    assert desktop.widget("left").selected is False


def test_the_click_lands_inside_the_widget_the_pixels_show():
    """Not 'a number was returned' -- inside the correct box, decided from the screenshot."""
    desktop = _desktop("click the leftmost red box")
    _, actions = _run(desktop)
    desktop.step(actions[0])

    click = desktop.clicks[-1]
    x0, y0, x1, y1 = LEFT.rect
    assert x0 <= click["x"] < x1
    assert y0 <= click["y"] < y1


def test_the_typed_surface_path_reaches_the_same_widget():
    """The second route: execute_typed_action validates then actuates."""
    desktop = _desktop("click the leftmost red box")
    result = execute_typed_action(
        desktop, {"type": "click", "x": 300, "y": 500, "button": "left"}
    )
    assert desktop.selected == "left"
    assert result["reward"] == 1.0
    assert result["compiled_action"] == "pyautogui.click(x=300, y=500, button='left')"


def test_the_action_changes_what_the_next_screenshot_shows():
    """The loop is only closed if the world moved and the agent can see that it moved."""
    desktop = _desktop("click the leftmost red box")
    before = desktop.render("rgb_array")
    _, actions = _run(desktop)
    desktop.step(actions[0])
    after = desktop.render("rgb_array")

    assert before != after
    observation = observe(desktop)
    assert observation["screenshot"] == after


# --------------------------------------------------------------------------- refusals
def test_no_matching_widget_makes_the_agent_wait_and_click_nothing():
    desktop = _desktop("click the leftmost red box", widgets=[])
    _, actions = _run(desktop)
    desktop.step(actions[0])

    assert actions == ["WAIT"]
    assert desktop.clicks == []
    assert desktop.selected is None
    assert desktop.reward == 0.0


def test_a_tie_makes_the_agent_wait_and_click_nothing():
    tied = [Widget("a", (800, 300, 1000, 500)), Widget("b", (800, 600, 1000, 800))]
    desktop = VirtualDesktop(tied, instruction="click the leftmost red box")
    _, actions = _run(desktop)
    desktop.step(actions[0])

    assert actions == ["WAIT"]
    assert desktop.clicks == []


def test_an_instruction_without_a_relation_is_not_routed():
    desktop = _desktop("click the red box")
    with pytest.raises(Exception):
        _run(desktop)
    assert desktop.clicks == []


# --------------------------------------------------------------------------- repeatability
def test_the_same_screen_gives_the_same_answer_twice():
    first = _run(_desktop("click the leftmost red box"))[1]
    second = _run(_desktop("click the leftmost red box"))[1]
    assert first == second
