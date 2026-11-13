"""Standalone taught programs must carry their relative-import dependencies."""
from canonical.tools import teach_actions_v1 as teach


def test_standalone_and_package_fallback_imports_are_both_carried():
    for source in (
        "from . import kept_under_an_old_name_v1 as aliases\n",
        "try:\n"
        "    from . import kept_under_an_old_name_v1 as aliases\n"
        "except ImportError:  # package fallback\n"
        "    from canonical.swe_kernel.taught_actions import kept_under_an_old_name_v1 as aliases\n",
    ):
        standalone = teach.carried_along(source)
        assert "from . import" not in standalone
        assert "from canonical.swe_kernel.taught_actions import" not in standalone
        namespace = {"__name__": "not_main"}
        exec(compile(standalone, "standalone.py", "exec"), namespace)
        assert namespace["aliases"].alias_of("assertEquals", "assertEqual")
        assert not namespace["aliases"].alias_of("load", "safe_load")


def test_edit_program_is_self_contained_after_carrying():
    lesson = next(item for item in teach.LESSONS if item["action"] == "edit_by_example_v1")
    source, _ = teach.program_and_request(lesson)
    namespace = {"__name__": "not_main"}
    exec(compile(source, "standalone.py", "exec"), namespace)
    assert namespace["kept_under_an_old_name"].alias_of("assertEquals", "assertEqual")
