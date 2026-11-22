"""Pins the actuator: plans are instantiated from the program's own text, not recalled.

The two shapes that matter are covered by fixtures -- a program with semantic slot
names in its usage line, and one whose usage line is only `[OPTION]...[FILE]` but
whose option table describes each flag. The second is where a naive matcher mints
confidently wrong slots, so the minter's precision is pinned here.
"""
from __future__ import annotations

import ast
import pathlib
import sys

TOOLS = pathlib.Path(__file__).resolve().parents[1] / "tools"
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))

import an_effect_not_a_description_v1 as effect  # noqa: E402

SEMANTIC_HELP = """usage: former [-l LEXER | -g] [-f FORMATTER] [-o OUTPUTFILE] [INPUTFILE]

Options:
  -l LEXER      specify the lexer
  -f FORMATTER  specify the formatter
  -o OUTPUTFILE write the result to this file
"""

GENERIC_HELP = """Usage: packer [OPTION]... [FILE]...
Pack or unpack FILEs in place.

  -c, --stdout      write on standard output, keep original files unchanged
  -d, --decompress  decompress
  -f, --force       force overwrite of output file and compress links
  -k, --keep        keep (don't delete) input files
  -l, --list        list compressed file contents
  -t, --test        test compressed file integrity
"""


def test_the_usage_line_is_a_signature() -> None:
    sig = effect.signature_from_text("former", SEMANTIC_HELP)
    assert any("LEXER" in entry for entry in sig["optionals"]), sig["optionals"]
    assert any("OUTPUTFILE" in entry for entry in sig["optionals"])
    assert "INPUTFILE" in sig["positionals"]


def test_roles_are_minted_from_the_programs_own_description() -> None:
    sig = effect.signature_from_text("packer", GENERIC_HELP)
    minted = effect.mint_slots(sig)
    assert set(minted["roles_found"]) == {"to_stdout", "decompress", "keep", "list", "test"}
    assert minted["slots"]["decompress"]["flag"] == "--decompress"
    assert minted["slots"]["to_stdout"]["flag"] == "--stdout"


def test_a_mention_is_not_a_role() -> None:
    """`--force  force overwrite of output file` must not mint an output-file slot."""
    sig = effect.signature_from_text("packer", GENERIC_HELP)
    minted = effect.mint_slots(sig)
    assert "to_file" not in minted["slots"], minted["slots"]
    assert minted["slots"]["decompress"]["flag"] != "--force"


def test_a_wrong_flag_would_not_survive_its_own_description() -> None:
    """`--files-from  get names to extract` mentions extract; it is not decompression."""
    text = """Usage: packer [OPTION]... [FILE]...
  -T, --files-from      get names to extract or create from FILE
  -d, --decompress      decompress
"""
    minted = effect.mint_slots(effect.signature_from_text("packer", text))
    assert minted["slots"]["decompress"]["flag"] == "--decompress", minted["slots"]


def test_instantiate_fills_slots_from_the_rendered_vocabulary() -> None:
    sig = effect.signature_from_text("former", SEMANTIC_HELP)
    vocab = {"formatters": {"names": ["html", "latex"], "count": 2},
             "lexers": {"names": ["python", "bash"], "count": 2}}
    goal = {"name": "py", "lexer": "python", "formatter": "html"}
    plan = effect.instantiate(sig, goal, vocab)
    assert not plan["blocked"], plan["blocked"]
    assert plan["argv"] == ["-l", "python", "-f", "html", "-o", "OUT", "IN"], plan["argv"]
    assert len(plan["provenance"]) >= 3


def test_an_absent_value_is_blocked_not_invented() -> None:
    sig = effect.signature_from_text("former", SEMANTIC_HELP)
    vocab = {"formatters": {"names": ["html"], "count": 1},
             "lexers": {"names": ["python"], "count": 1}}
    plan = effect.instantiate(sig, {"name": "x", "lexer": "cobol", "formatter": "html"}, vocab)
    assert plan["blocked"], "a lexer the program never rendered must block the plan"


def test_the_planner_never_invokes_the_program() -> None:
    """E1/E2 are structural: instantiate() and mint_slots() must not run anything."""
    tree = ast.parse(pathlib.Path(effect.__file__).read_text(encoding="utf-8"))
    pure = {"instantiate", "mint_slots", "signature_from_text", "_cue_matches"}
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name in pure:
            for call in ast.walk(node):
                if isinstance(call, ast.Call):
                    name = getattr(call.func, "id", None) or getattr(call.func, "attr", None)
                    assert name not in ("run", "Popen", "check_output"), node.name
            names = {getattr(inner, "id", None) for inner in ast.walk(node)}
            assert "subprocess" not in names, f"{node.name} must stay a pure function"
