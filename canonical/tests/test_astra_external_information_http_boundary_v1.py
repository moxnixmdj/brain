from __future__ import annotations

import urllib.request

import pytest

from canonical.runtime import astra_runtime as rt


def test_urlopen_post_is_rejected_before_information_context_or_transport():
    req = urllib.request.Request("https://example.invalid/", data=b"x=1")
    with pytest.raises(rt.Blocker, match="EXTERNAL_INFORMATION_HTTP_METHOD_FORBIDDEN:POST"):
        rt._bridge_aware_urlopen(req, timeout=1)


def test_urlopen_non_read_method_is_rejected_without_body():
    with pytest.raises(rt.Blocker, match="EXTERNAL_INFORMATION_HTTP_METHOD_FORBIDDEN:DELETE"):
        rt._authorize_external_information(
            "urlopen",
            {
                "url": "https://example.invalid/resource",
                "method": "DELETE",
                "data_b64": None,
            },
        )


def test_urlopen_body_is_rejected_even_if_method_claims_get():
    with pytest.raises(rt.Blocker, match="EXTERNAL_INFORMATION_HTTP_BODY_FORBIDDEN"):
        rt._authorize_external_information(
            "urlopen",
            {
                "url": "https://example.invalid/",
                "method": "GET",
                "data_b64": "eA==",
            },
        )


def test_read_only_get_still_requires_continuous_obs_authority():
    old_context = rt._ACTIVE_CONTINUOUS_OBS_CONTEXT
    old_module = rt._ACTIVE_CONTINUOUS_OBS_MODULE
    try:
        rt._ACTIVE_CONTINUOUS_OBS_CONTEXT = None
        rt._ACTIVE_CONTINUOUS_OBS_MODULE = None
        with pytest.raises(rt.Blocker, match="CONTINUOUS_OBS_INFORMATION_CONTEXT_NOT_BOUND"):
            rt._authorize_external_information(
                "urlopen",
                {
                    "url": "https://example.invalid/",
                    "method": "GET",
                    "data_b64": None,
                },
            )
    finally:
        rt._ACTIVE_CONTINUOUS_OBS_CONTEXT = old_context
        rt._ACTIVE_CONTINUOUS_OBS_MODULE = old_module


def test_unregistered_external_tool_kind_fails_closed_before_obs_or_transport():
    with pytest.raises(rt.Blocker, match="EXTERNAL_TOOL_KIND_UNREGISTERED:arbitrary_tool"):
        rt._authorize_external_information(
            "arbitrary_tool",
            {"resource": "anything"},
        )
