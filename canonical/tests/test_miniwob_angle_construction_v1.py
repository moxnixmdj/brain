import importlib.util
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
MODULE_PATH = ROOT / "canonical" / "runtime" / "miniwob_actuator_v1.py"
spec = importlib.util.spec_from_file_location("miniwob_actuator_angle_test", MODULE_PATH)
actuator = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = actuator
spec.loader.exec_module(actuator)


def _point(color, x, y):
    return {"color": color, "cx": x, "cy": y}


def test_right_angle_target_is_perpendicular_and_inside_svg():
    points = [_point("black", 70, 100), _point("blue", 70, 60)]
    target = actuator._angle_target("right", points, 150, 130)

    assert target is not None
    assert 5 <= target[0] <= 145
    assert 5 <= target[1] <= 125
    angle = actuator._angle_degrees((70, 100), (70, 60), target)
    assert angle is not None
    assert abs(angle - 90.0) < 1e-8


def test_bisector_target_splits_the_visible_angle():
    vertex = (60, 60)
    first = (60, 20)
    second = (100, 60)
    target = actuator._angle_target(
        "bisect",
        [_point("blue", *vertex), _point("black", *first), _point("black", *second)],
        150,
        130,
    )

    assert target is not None
    assert 5 <= target[0] <= 145
    assert 5 <= target[1] <= 125
    angle_a = actuator._angle_degrees(first, vertex, target)
    angle_b = actuator._angle_degrees(second, vertex, target)
    assert angle_a is not None and angle_b is not None
    assert abs(angle_a - angle_b) < 1e-8


def test_angle_target_fails_closed_for_missing_or_degenerate_points():
    assert actuator._angle_target("right", [_point("blue", 20, 20)], 150, 130) is None
    assert actuator._angle_target(
        "right", [_point("blue", 20, 20), _point("black", 20, 20)], 150, 130
    ) is None
    assert actuator._angle_target(
        "bisect",
        [_point("blue", 75, 60), _point("black", 30, 60), _point("black", 120, 60)],
        150,
        130,
    ) is None


def test_visible_svg_fill_names_are_normalized():
    assert actuator._svg_point_colour("rgb(0, 0, 255)") == "blue"
    assert actuator._svg_point_colour("black") == "black"
    assert actuator._svg_point_colour("red") is None
