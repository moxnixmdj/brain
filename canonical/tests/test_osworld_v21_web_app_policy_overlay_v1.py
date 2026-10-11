from canonical.runtime.osworld_v21_web_app_policy_overlay_v1 import decide


def _state(instruction, history=None):
    return {
        "instruction": instruction,
        "a11y_tree": "",
        "history": history or [],
        "screenshot_sha256": "0" * 64,
    }


def test_teamchat_precedes_downstream_cloudcrm():
    out = decide(_state("Review TeamChat #general rules, then update CloudCRM leads."))
    action = out["actions"][0]
    assert action == {
        "type": "WEB_APP_OP",
        "app": "teamchat",
        "operation": "observe_workspace",
        "args": {},
    }


def test_vaultbank_explicit_routes_to_product_projection():
    out = decide(_state("Check VaultBank to see which clients paid in full."))
    assert out["actions"][0]["type"] == "WEB_APP_OP"
    assert out["actions"][0]["app"] == "vaultbank"
    assert out["actions"][0]["operation"] == "observe_dashboard"


def test_generic_email_discovers_surface_instead_of_guessing_mailhub():
    out = decide(_state("Check my inbox and reply to the warning email."))
    assert out["actions"] == [{"type": "BROWSER_OP", "op": {"type": "OBSERVE"}}]


def test_thunderbird_email_does_not_route_to_mailhub():
    out = decide(_state("Check the email in Thunderbird and reply."))
    first = out["actions"][0]
    assert not (first.get("type") == "WEB_APP_OP" and first.get("app") == "mailhub")


def test_discovered_mailhub_routes_to_product_projection():
    history = [{
        "browser_result": {
            "type": "OBSERVE",
            "active_url": "http://mailhub.local/inbox",
            "visible_text": "",
            "controls": [],
        }
    }]
    out = decide(_state("Check my inbox and reply to the warning email.", history))
    assert out["actions"][0] == {
        "type": "WEB_APP_OP",
        "app": "mailhub",
        "operation": "observe_mail",
        "args": {},
    }


def test_existing_product_receipt_is_not_reobserved_forever():
    history = [{
        "web_app_result": {
            "type": "WEB_APP_OP",
            "ok": True,
            "app": "teamchat",
            "operation": "observe_workspace",
            "result": {"teamchat": {}},
        }
    }]
    out = decide(_state("Review TeamChat for the instructions.", history))
    first = out["actions"][0]
    assert not (
        first.get("type") == "WEB_APP_OP"
        and first.get("app") == "teamchat"
        and first.get("operation") == "observe_workspace"
    )
