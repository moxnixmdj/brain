"""Taught programs must carry their dependencies into the isolated execution environment."""
import ast
import subprocess
import sys

from canonical.tools import teach_actions_v1 as teach


def test_edit_lesson_runs_without_the_repository_on_python_path(tmp_path):
    lesson = next(item for item in teach.LESSONS if item["action"] == "edit_by_example_v1")
    program, request = teach.program_and_request(lesson)
    imports = [node for node in ast.walk(ast.parse(program)) if isinstance(node, ast.ImportFrom)]
    assert not any(node.level or (node.module or "").startswith("canonical") for node in imports)
    for path, content in lesson["first_example"]["before"].items():
        destination = tmp_path / path
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(content, encoding="utf-8")
    script = tmp_path / "taught_program.py"
    script.write_text(program, encoding="utf-8")
    ran = subprocess.run([sys.executable, "-I", str(script)], cwd=tmp_path,
                         capture_output=True, text=True, timeout=20)
    assert ran.returncode == 0, ran.stdout + ran.stderr
    assert ran.stdout.strip() == lesson["answers"].format(**request)
    for path, expected in lesson["first_example"]["after"].items():
        assert (tmp_path / path).read_text(encoding="utf-8") == expected


def test_unverified_structural_word_overlap_is_not_executable_authority():
    import json
    from canonical.swe_kernel import causal_trace_to_skill_compiler_v1 as compiler

    bundle = json.loads(teach.BUNDLE.read_text(encoding="utf-8"))
    skill = next(item for item in bundle["skills"] if item["goal_skeleton"] ==
                 "remember in ?path0 the way ?path1 was changed into ?path2")
    taught = "remember in notes/kept.lesson the way old.py was changed into new.py"
    untaught = "remember notes/kept.lesson the way old.py was changed into new.py"
    assert compiler.bind_goal_parameters(skill, taught, allow_structural=False) is not None
    assert compiler.bind_goal_parameters(skill, untaught) is not None
    assert compiler.bind_goal_parameters(skill, untaught, allow_structural=False) is None
