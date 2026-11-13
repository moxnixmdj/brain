#!/usr/bin/env python3
"""Pinned tests for the PEP 585 family operator and its measured worth."""
from __future__ import annotations

import json
import pathlib
import sys
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from canonical.swe_kernel.taught_actions import generic_alias_v1 as G

FIXTURE = ROOT / "canonical/tests/fixtures/generic_alias_measure_v1.json"

UP_BEFORE = "from typing import Any\n\ndef f(x: list[Any]) -> None:\n    return None\n"
UP_AFTER = "from typing import Any, List\n\ndef f(x: List[Any]) -> None:\n    return None\n"
DOWN_BEFORE = "from typing import Any, Dict, List\n\ndef f(x: List[int], y: Dict[str, int]) -> None:\n    return None\n"
DOWN_AFTER = "from typing import Any\n\ndef f(x: list[int], y: dict[str, int]) -> None:\n    return None\n"


class Direction(unittest.TestCase):
    def test_one_changed_annotation_says_which_way_the_family_goes(self):
        self.assertEqual(G.direction(UP_BEFORE, UP_AFTER)["list"], "List")
        self.assertEqual(G.direction(DOWN_BEFORE, DOWN_AFTER)["List"], "list")

    def test_two_directions_at_once_is_not_one_migration(self):
        before = "from typing import Any, List\n\ndef f(x: List[int], y: dict[str, Any]) -> None: ...\n"
        after = "from typing import Any, Dict\n\ndef f(x: list[int], y: Dict[str, Any]) -> None: ...\n"
        self.assertIsNone(G.direction(before, after))

    def test_no_changed_annotation_is_no_operator(self):
        self.assertIsNone(G.direction("x = 1\n", "x = 2\n"))


class Applying(unittest.TestCase):
    def test_the_whole_family_follows_the_shown_direction(self):
        target = "from typing import Any, Dict, Optional\n\ndef g(y: dict[str, Any], z: set[int]) -> tuple[int]:\n    return (1,)\n"
        text, did = G.apply(target, UP_BEFORE, UP_AFTER)
        self.assertEqual(did["direction"], "up")
        self.assertIn("Dict[str, Any]", text)
        self.assertIn("Set[int]", text)
        self.assertIn("Tuple[int]", text)
        self.assertIn("from typing import Any, Dict, Optional, Set, Tuple", text)

    def test_the_down_direction_removes_the_typing_names_it_stopped_using(self):
        target = "from typing import Any, Dict, List, Optional\n\ndef g(x: List[int], y: Dict[str, int]) -> None:\n    return None\n"
        text, did = G.apply(target, DOWN_BEFORE, DOWN_AFTER)
        self.assertEqual(did["direction"], "down")
        self.assertIn("x: list[int]", text)
        self.assertIn("y: dict[str, int]", text)
        self.assertIn("from typing import Any, Optional", text)

    def test_an_abc_companion_moves_to_the_line_it_stood_on(self):
        before = "from typing import Callable, List\n\ndef f(x: List[int], g: Callable[[], None]) -> None: ...\n"
        after = "from collections.abc import Callable\n\ndef f(x: list[int], g: Callable[[], None]) -> None: ...\n"
        target = "from typing import Callable, Dict, List\n\ndef g(x: List[int], h: Callable[[], None]) -> None: ...\n"
        text, _ = G.apply(target, before, after)
        self.assertIn("from collections.abc import Callable", text)
        self.assertNotIn("from typing import Callable", text)
        self.assertIn("x: list[int]", text)

    def test_nothing_is_returned_when_the_target_has_no_subscript_of_the_family(self):
        target = "from typing import Any\n\ndef g(y: Any) -> None:\n    return None\n"
        self.assertEqual(G.apply(target, UP_BEFORE, UP_AFTER), (None, {}))

    def test_only_the_identifier_bytes_change(self):
        target = "from typing import Any\n\n# a comment that must survive\ndef g(y: dict[str, Any]) -> None:  # trailing\n    return None\n"
        text, _ = G.apply(target, UP_BEFORE, UP_AFTER)
        self.assertIn("# a comment that must survive", text)
        self.assertIn("def g(y: Dict[str, Any]) -> None:  # trailing", text)


class Measured(unittest.TestCase):
    def test_the_recorded_measurement_is_the_one_pinned(self):
        record = json.loads(FIXTURE.read_text(encoding="utf-8"))
        self.assertEqual(record["schema"], "GENERIC_ALIAS_MEASURE_V1")
        base = record["summary"]["base"]
        self.assertEqual((base["right"], base["developers_changes"]), (493, 1674))
        self.assertAlmostEqual(base["coverage"], 0.294504, places=6)
        self.assertAlmostEqual(base["precision"], 0.918063, places=6)
        alias = record["summary"]["alias"]
        self.assertEqual(alias["right"], 952)
        self.assertAlmostEqual(alias["coverage"], 0.568698, places=6)
        self.assertAlmostEqual(alias["precision"], 0.927875, places=6)
        self.assertEqual(alias["wrong_changes"], 48)
        self.assertEqual(alias["whole_files"], 155)
        rows = record["per_pull_request"]
        self.assertEqual(rows["Prekzursil/env-inspector#72"]["alias"]["right"], 280)
        self.assertEqual(rows["fulcrumgenomics/fgpyo#300"]["alias"]["right"], 215)
        self.assertEqual(rows["nipy/nibabel#1609"]["alias"]["right"], 0)


if __name__ == "__main__":
    unittest.main()
