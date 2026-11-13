"""Tests for the test-entry-point finder.

Every test here is a bug this tool actually shipped with during development, found by running it on
real repositories. They are regressions, not illustrations:

1. `conftest.py` -- a finder scanning only `test_*.py` declared `jodal/comics` untested while five
   files imported the module. This was the original bug.
2. Name-based test discovery -- `torproject/stem` names tests after the module they test
   (`test/unit/util/connection.py`, not `test_connection.py`), so filename patterns found nothing.
3. Relative imports -- `from .validation import x` parses as module "validation" and produced a
   false match on an unrelated top-level file.
4. Declared package roots -- `django-argcache`'s `src/function.py` is imported as `argcache.function`;
   the name exists only in `setup.py`'s `packages=[...]`, unrecoverable from the path.
5. Router dispatch -- `comics/accounts/views.py` is exercised by tests that never import it, through
   `urls.py` and `client.get("/me/secret-key/")`.
6. Test files themselves -- a test file is not "unchecked"; it is the check.

AND THE ONE THAT MATTERS MOST: `COVERS` means a test imports the module and names something in it.
It does NOT mean a bug in it would be caught. Measured by mutation:
`Subscription.__str__ -> "MUTANT"` survived (10 passed), a wrong `db_table` was caught.
So the tool reports reachability and never claims adequacy.
"""

from __future__ import annotations

import pathlib
import sys
import textwrap

import pytest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "tools"))

from test_entry_point_finder_v1 import find  # noqa: E402


def _project(tmp_path: pathlib.Path, files: dict[str, str]) -> pathlib.Path:
    for name, body in files.items():
        path = tmp_path / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(textwrap.dedent(body), encoding="utf-8")
    return tmp_path


def test_conftest_counts_as_an_entry_point(tmp_path):
    """Bug 1: the finder that reported comics untested scanned only test_*.py."""
    project = _project(tmp_path, {
        "pkg/__init__.py": "",
        "pkg/models.py": "class Subscription:\n    pass\n",
        "tests/__init__.py": "",
        "tests/conftest.py": "from pkg.models import Subscription\n",
    })
    result = find(project, pathlib.Path("pkg/models.py"))
    assert result["verdict"] == "COVERS"
    assert "tests/conftest.py" in result["covers"]


def test_test_named_after_the_module_is_found(tmp_path):
    """Bug 2: stem names tests after the module under test, not `test_<module>.py`."""
    project = _project(tmp_path, {
        "pkg/__init__.py": "",
        "pkg/connection.py": "def is_valid_port(port):\n    return 0 < port < 65536\n",
        "test/unit/__init__.py": "",
        "test/unit/connection.py": (
            "import unittest\n"
            "from pkg.connection import is_valid_port\n"
            "class TestPorts(unittest.TestCase):\n"
            "    def test_port(self):\n"
            "        self.assertTrue(is_valid_port(80))\n"),
    })
    result = find(project, pathlib.Path("pkg/connection.py"))
    assert result["verdict"] == "COVERS"


def test_relative_import_does_not_produce_a_false_match(tmp_path):
    """Bug 3: `from .validation import x` must not match top-level `validation.py`."""
    project = _project(tmp_path, {
        "pkg/__init__.py": "",
        "pkg/validation.py": "def check():\n    return True\n",
        "pkg/ui/__init__.py": "",
        "pkg/ui/other_validation.py": "def check():\n    return True\n",
        "pkg/ui/consumer.py": "from .other_validation import check\n",
        "tests/__init__.py": "",
        "tests/test_ui.py": ("from pkg.ui.consumer import check\n"
                             "def test_check():\n    assert check()\n"),
    })
    result = find(project, pathlib.Path("pkg/validation.py"))
    assert result["verdict"] == "NONE", result["candidates"]


def test_declared_package_root_from_setup_py(tmp_path):
    """Bug 4: `src/function.py` imported as `argcache.function` -- name lives only in setup.py."""
    project = _project(tmp_path, {
        "setup.py": "setup(packages=['argcache'], package_dir={'': 'src'})\n",
        "src/function.py": "def cache_function(fn):\n    return fn\n",
        "tests/__init__.py": "",
        "tests/test_function.py": ("from argcache.function import cache_function\n"
                                   "def test_identity():\n    assert cache_function(1) == 1\n"),
    })
    result = find(project, pathlib.Path("src/function.py"))
    assert "argcache.function" in result["module_names_tried"]
    assert result["verdict"] == "COVERS"


def test_router_dispatch_is_not_invisible(tmp_path):
    """Bug 5: a view reached only through urls.py + client.get must not read as NONE."""
    project = _project(tmp_path, {
        "pkg/__init__.py": "",
        "pkg/views.py": "def secret_key(request):\n    return 'key'\n",
        "pkg/urls.py": ("from django.urls import path\n"
                        "from pkg import views\n"
                        "urlpatterns = [path('secret-key/', views.secret_key, name='secret_key')]\n"),
        "tests/__init__.py": "",
        "tests/test_secret_key.py": ("def test_secret_key(client):\n"
                                     "    assert client.get('/secret-key/').status_code == 200\n"),
    })
    result = find(project, pathlib.Path("pkg/views.py"))
    assert result["verdict"] == "DISPATCH", result["candidates"]
    assert result["dispatch"][0]["path"] == "tests/test_secret_key.py"


def test_a_test_file_is_not_reported_as_unchecked(tmp_path):
    """Bug 6: counting test files as untested deflates every coverage number."""
    project = _project(tmp_path, {
        "tests/__init__.py": "",
        "tests/test_thing.py": "def test_a():\n    assert True\n",
    })
    assert find(project, pathlib.Path("tests/test_thing.py"))["verdict"] == "IS_TEST_FILE"


def test_imports_is_reported_separately_from_covers(tmp_path):
    """A bare module import that names nothing in the module is weaker than a naming test.

    This is the honest form of the distinction. `from pkg.cache_token import mint` DOES name `mint`
    -- importing a symbol is naming it -- so that case is genuinely COVERS. What is weaker is
    `import pkg.cache_token` for a side effect (signal registration, app loading), where no function
    or class in the file is ever referenced. That is reported as IMPORTS, separately, and never
    silently promoted to coverage.
    """
    project = _project(tmp_path, {
        "pkg/__init__.py": "",
        "pkg/cache_token.py": "def mint(user):\n    return 'tok'\n",
        "tests/__init__.py": "",
        "tests/test_setup.py": ("import pkg.cache_token  # side effect: registers signals\n"
                                "def test_unrelated():\n    assert 1 + 1 == 2\n"),
    })
    result = find(project, pathlib.Path("pkg/cache_token.py"))
    assert result["verdict"] == "IMPORTS"
    assert result["imports_only"] == ["tests/test_setup.py"]


def test_importing_a_symbol_from_the_module_counts_as_naming_it(tmp_path):
    """The counterpart: `from x import y` is evidence, not merely an import."""
    project = _project(tmp_path, {
        "pkg/__init__.py": "",
        "pkg/cache_token.py": "def mint(user):\n    return 'tok'\n",
        "tests/__init__.py": "",
        "tests/test_token.py": ("from pkg.cache_token import mint\n"
                                "def test_unrelated():\n    assert 1 + 1 == 2\n"),
    })
    result = find(project, pathlib.Path("pkg/cache_token.py"))
    assert result["verdict"] == "COVERS"
    assert result["covers"] == ["tests/test_token.py"]


def test_missing_target_is_an_error_not_a_silent_none(tmp_path):
    project = _project(tmp_path, {"pkg/__init__.py": ""})
    assert find(project, pathlib.Path("pkg/gone.py"))["error"] == "TARGET_NOT_A_FILE"


def test_verdicts_never_claim_adequacy(tmp_path):
    """The tool must not have a verdict that means "this module is well tested"."""
    project = _project(tmp_path, {
        "pkg/__init__.py": "",
        "pkg/core.py": "def limit(n):\n    return n\n",
        "tests/__init__.py": "",
        "tests/test_core.py": ("from pkg.core import limit\n"
                               "def test_limit():\n    assert limit(1) == 1\n"),
    })
    result = find(project, pathlib.Path("pkg/core.py"))
    allowed = {"COVERS", "IMPORTS", "DISPATCH", "NONE", "IS_TEST_FILE"}
    assert result["verdict"] in allowed
    assert "adequa" not in result["verdict"].lower()
    assert "imports_only" in result and "covers" in result


@pytest.mark.parametrize("verdict_src,expected", [
    ("", "NONE"),
])
def test_empty_file_has_no_candidates(tmp_path, verdict_src, expected):
    project = _project(tmp_path, {"pkg/__init__.py": "", "pkg/empty.py": verdict_src})
    assert find(project, pathlib.Path("pkg/empty.py"))["verdict"] == expected
