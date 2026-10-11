from canonical.runtime.osworld_v21_generic_policy_v3 import decide

S="https://accessibility.ubuntu.example.org/ns/state"
C="https://accessibility.ubuntu.example.org/ns/component"


def one_app(app, tag, name, active=True):
    a=' s:active="true"' if active else ""
    return (
        f'<root xmlns:s="{S}" xmlns:c="{C}">'
        f'<application name="{app}"><frame{a}>'
        f'<{tag} name="{name}" s:visible="true" s:showing="true" '
        f'c:screencoord="(100, 100)" c:size="(200, 40)" />'
        f'</frame></application></root>'
    )


def test_browser_search_routes_to_semantic_fill():
    out=decide({
        "instruction":"Search for cats",
        "a11y_tree":one_app("Google Chrome","searchbox","Search"),
        "history":[],"screenshot_sha256":"a",
    })
    assert out["actions"]==[{"type":"BROWSER_FILL","label":"Search","value":"cats"}]


def test_desktop_fill_routes_to_click_then_type():
    out=decide({
        "instruction":"Set Title to Hello",
        "a11y_tree":one_app("LibreOffice Writer","entry","Title"),
        "history":[],"screenshot_sha256":"b",
    })
    assert out["actions"]==[
        {"type":"CLICK","x":200,"y":120},
        {"type":"TYPE","text":"Hello"},
    ]


def test_background_chrome_does_not_hijack_active_desktop():
    xml=(
        f'<root xmlns:s="{S}" xmlns:c="{C}">'
        f'<application name="Google Chrome"><frame>'
        f'<searchbox name="Search" s:visible="true" s:showing="true" '
        f'c:screencoord="(10, 10)" c:size="(100, 20)" />'
        f'</frame></application>'
        f'<application name="LibreOffice Writer"><frame s:active="true">'
        f'<entry name="Title" s:visible="true" s:showing="true" '
        f'c:screencoord="(100, 100)" c:size="(200, 40)" />'
        f'</frame></application></root>'
    )
    out=decide({
        "instruction":"Set Title to Hello",
        "a11y_tree":xml,"history":[],"screenshot_sha256":"c",
    })
    assert out["actions"][0]["type"]=="CLICK"
    assert out["actions"][1]=={"type":"TYPE","text":"Hello"}


def test_duplicate_same_length_targets_fail_closed():
    xml=(
        f'<root xmlns:s="{S}" xmlns:c="{C}"><application name="App">'
        f'<frame s:active="true">'
        f'<button name="Save" s:visible="true" s:showing="true" c:screencoord="(10, 10)" c:size="(50, 20)" />'
        f'<button name="Save" s:visible="true" s:showing="true" c:screencoord="(100, 10)" c:size="(50, 20)" />'
        f'</frame></application></root>'
    )
    out=decide({
        "instruction":"Click Save",
        "a11y_tree":xml,"history":[],"screenshot_sha256":"d",
    })
    assert out["actions"]==[{"type":"WAIT"}]


def test_same_state_repeat_does_not_repeat_action():
    out=decide({
        "instruction":"Click Save",
        "a11y_tree":one_app("App","button","Save"),
        "history":[{"screenshot_sha256":"same"}],
        "screenshot_sha256":"same",
    })
    assert out["actions"]==[{"type":"WAIT"}]
