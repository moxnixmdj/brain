"""Round 22: the code that calls the changed function, asked for a real argument.

The fire proof is built so that only a CALL SITE can explain the pin: the failing test passes "a", which no
mutation or operation reaches, while another module in the same repository calls the same function with the literal
the fix is about. That call site is neither the change nor its test.

The honesty proof is the mirror: a caller that passes a name or an expression states no value, and the harness
reports no candidate rather than inventing an argument.
"""

from __future__ import annotations

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))

from canonical.swe_kernel import pins_from_the_reverted_part_v1 as SYN  # noqa: E402
from canonical.swe_kernel import the_callers_were_never_asked_v1 as K  # noqa: E402
from canonical.swe_kernel import what_the_verifier_actually_pins_v1 as PINS  # noqa: E402

DEFECTIVE = '''def parse(text):
    return len(text)
'''

FIXED = '''def parse(text):
    if text == "gamma-delta":
        raise ValueError("reserved")
    return len(text)
'''

TEST = '''from mod import parse


def test_one():
    assert parse("a") == 1
'''

#: another module of the same program, calling the same function for its own reasons
CALLER = '''from mod import parse

CONFIG = "gamma-delta"


def load():
    return parse("gamma-delta")


def load_indirect():
    return parse(CONFIG)
'''


def _tree(tmp_path: pathlib.Path, caller: str = CALLER) -> pathlib.Path:
    (tmp_path / "mod.py").write_text(DEFECTIVE, encoding="utf-8")
    (tmp_path / "test_mod.py").write_text(TEST, encoding="utf-8")
    (tmp_path / "consumer.py").write_text(caller, encoding="utf-8")
    return tmp_path


def _part():
    return next(part for part in PINS.hunks(DEFECTIVE, FIXED)
                if PINS.is_behavioural(FIXED, part) and not PINS.typing_only(FIXED, part))


def _seeds():
    return [{"module": call["module"], "function": call["function"]}
            for call in SYN.calls_from_the_test(TEST)]


def test_a_caller_argument_pins_what_the_tests_literal_cannot(tmp_path):
    tree = _tree(tmp_path)
    sites = K.harvest_call_sites(tree, "mod.py", "test_mod.py", ["parse"])
    literals = [site for site in sites if site["site"] == "consumer.py"]
    assert any(site["args"] == ["gamma-delta"] for site in literals)
    calls = K.candidates_for(sites, _seeds())
    mutant = PINS.revert(FIXED, DEFECTIVE, _part())
    verdict = K.judge_part(tree, "mod.py", FIXED, mutant, calls)
    assert verdict["state"] == "PINNED_BY_A_CALLER", verdict
    assert verdict["pin"]["args"] == ["=gamma-delta"]
    assert "pytest.raises(ValueError)" in verdict["pin"]["assertion"]


def test_a_caller_that_passes_a_name_states_no_value(tmp_path):
    tree = _tree(tmp_path, caller="from mod import parse\n\nCONFIG = 'x'\n\n\ndef load():\n    return parse(CONFIG)\n")
    sites = K.harvest_call_sites(tree, "mod.py", "test_mod.py", ["parse"])
    assert sites == []            # nothing literal was passed, so nothing is invented


def test_the_change_and_its_test_are_never_harvested(tmp_path):
    tree = _tree(tmp_path, caller="")
    (tmp_path / "test_mod.py").write_text(TEST + '\n\nparse("gamma-delta")\n', encoding="utf-8")
    sites = K.harvest_call_sites(tree, "mod.py", "test_mod.py", ["parse"])
    assert sites == []


def test_the_module_path_is_read_from_where_the_source_lives():
    assert K.module_of("src/packaging/utils.py") == "packaging.utils"
    assert K.module_of("tomli/_parser.py") == "tomli._parser"
    assert K.module_of("pkg/__init__.py") == "pkg"


def test_defined_names_reads_what_the_module_itself_defines():
    names = K.defined_names(FIXED + "\n\nclass Thing:\n    pass\n")
    assert names == ["parse", "Thing"]


def test_the_tree_is_restored_and_no_pin_file_survives(tmp_path):
    tree = _tree(tmp_path)
    calls = K.candidates_for(K.harvest_call_sites(tree, "mod.py", "test_mod.py", ["parse"]), _seeds())
    mutant = PINS.revert(FIXED, DEFECTIVE, _part())
    K.judge_part(tree, "mod.py", FIXED, mutant, calls)
    assert not (tree / K.PIN_TEST_NAME).exists()
    assert (tree / "mod.py").read_text(encoding="utf-8") == DEFECTIVE
