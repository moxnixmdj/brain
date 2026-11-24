"""An optional parameter the demonstration never supplied must not block every later call.

THE FOUR DEFECTS BETWEEN A CORRECT LEARNING AND A CORRECT ANSWER.

Measured 2026-11-23. A room contained one honest tool:

    def count_rows(path, delimiter=","):
        \"\"\"Count the data rows in a csv file, excluding the header.\"\"\"

The census found it, the forge admitted it (3/3 cases, 12/12 mutations killed), and asking
"count the rows in the csv people.csv" then failed four times in a row, each for a different reason:

    1. `delimiter` was reported MISSING. The contract knew it was optional -- the function declares a
       default -- but `register` never put that on the row, so the binder saw a placeholder with no
       way to fill it.
    2. An `optional` list was then added to the row, which the binder has never read. This tree's one
       way of saying "may be absent, use this" is `${input.name | default}`
       (`declared_argument_default_v1`); a second vocabulary is decoration.
    3. With the placeholder written, the default was the SOURCE TEXT of the literal -- `','` with the
       quotes -- so the function received a three-character string and raised
       `TypeError: delimiter must be a 1-character string`.
    4. Even then, `act` chose a PYTHON SOURCE ANALYSER, because procedure memory still held the route
       from a run that had certified the wrong answer before the verdict was fixed. Memory outranked
       fresh measurement by 42.86 to 17.62.

After all four, the same sentence returns VERIFIED_ACTION from `forged.rows.count_rows` with
`{"rows": 3}` -- and the same capability answers a file it was never shown.

THE GENERAL LESSON, which is why these are one file and not four: each defect looked like "the
capability does not work", and none of them was about the capability.
"""
from __future__ import annotations

import json
import pathlib
import shutil
import sys
import uuid

ROOT = pathlib.Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from canonical.runtime import room_census_v1 as RC  # noqa: E402


def test_a_literal_default_is_its_value_not_its_source_text(tmp_path):
    """`ast.unparse` gives `','`; `ast.literal_eval` gives `,`. The placeholder needs the second."""
    (tmp_path / "d.py").write_text(
        'def f(path, delimiter=",", n=3, flag=True, name="x"):\n'
        '    """Do a thing."""\n'
        '    return {}\n', encoding="utf-8")
    row = RC.survey(str(tmp_path))["functions"][0]
    # the source text is still shown, because that is what a person reading a census wants
    assert row["defaults"]["delimiter"] == "','", row["defaults"]
    # but the VALUE is what a caller needs
    assert row["default_values"]["delimiter"] == ",", row["default_values"]
    assert row["default_values"]["n"] == 3, row["default_values"]
    assert row["default_values"]["flag"] is True, row["default_values"]


def test_a_non_literal_default_is_simply_unknown(tmp_path):
    """A default that is a call or a name has no value without running it, and nothing is run."""
    (tmp_path / "d.py").write_text(
        'import os\n'
        'def f(path, base=os.getcwd(), name=str):\n'
        '    """Do a thing."""\n'
        '    return {}\n', encoding="utf-8")
    row = RC.survey(str(tmp_path))["functions"][0]
    assert "base" not in row["default_values"], row["default_values"]
    assert "name" not in row["default_values"], row["default_values"]
    # the source text is still recorded, so the census is not silent about it
    assert row["defaults"]["base"].startswith("os.getcwd"), row["defaults"]


def test_the_whole_chain_on_a_two_argument_tool(monkeypatch):
    """Discover, learn, then act -- on a function with an optional second parameter.

    The end-to-end case that failed four times. It is written as one test because the four defects
    were only visible as one symptom.
    """
    from canonical.runtime import capability_forge_v1 as F, grounded_action_v1 as GA

    room = ROOT / "canonical" / "astra_runtime" / "tmp" / "test_forged_default_room"
    shutil.rmtree(room, ignore_errors=True)
    room.mkdir(parents=True, exist_ok=True)
    (room / "__init__.py").write_text("", encoding="utf-8")
    fname = "tally_" + uuid.uuid4().hex[:8]
    (room / "tally.py").write_text(
        '"""Counting."""\n'
        "import csv\n\n\n"
        "def %s(path, delimiter=','):\n"
        '    """Count the data rows in a delimited file, excluding the header."""\n'
        '    with open(path, newline="") as fh:\n'
        '        return {"rows": sum(1 for _ in csv.reader(fh, delimiter=delimiter)) - 1}\n' % fname,
        encoding="utf-8")
    taught = room / "taught.csv"
    taught.write_text("a,b\n1,2\n3,4\n5,6\n", encoding="utf-8")

    monkeypatch.chdir(ROOT)
    census = RC.survey(str(room))
    row = [f for f in census["functions"] if f["function"] == fname][0]
    admitted = F.forge_and_record(RC.forge_entry(row), root=ROOT,
                                  seed_cases=[{"path": str(taught)}])
    assert admitted["admitted"] is True, admitted
    try:
        # the default is declared where the binder reads it
        args = GA.load_registry()[admitted["capability_id"]]["action_template"]["args"]
        assert args.get("delimiter") == "${input.delimiter | ,}", args

        # a file never demonstrated, and no delimiter mentioned in the sentence
        fresh = room / "fresh.csv"
        fresh.write_text("x,y\n1,2\n", encoding="utf-8")
        acted = GA.act("count the rows in the delimited file %s" % fresh, root=str(ROOT))
        assert acted.get("status") == "VERIFIED_ACTION", acted
        assert acted.get("capability_id") == admitted["capability_id"], acted
        assert (acted.get("result") or {})["rows"] == 1, acted
    finally:
        state = ROOT / "canonical" / "runtime" / "state" / "forged_capabilities_v1.json"
        if state.is_file():
            data = json.loads(state.read_text(encoding="utf-8"))
            if data.get("forged", {}).pop(admitted.get("capability_id"), None) is not None:
                state.write_text(json.dumps(data, indent=1, sort_keys=True) + "\n",
                                 encoding="utf-8")
        shutil.rmtree(room, ignore_errors=True)
