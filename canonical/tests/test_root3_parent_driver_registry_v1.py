from __future__ import annotations

import pytest

from canonical.runtime import root3_parent_driver_registry_v1 as m


def drivers():
    return {
        "PING":lambda p:{"pong":True},
        "EXTERNAL_TOOL":lambda p:{"ok":"external"},
        "DURABLE_ADMIN_WRITE":lambda p:{"ok":"admin"},
    }


def test_exact_driver_universe_passes():
    out=m.validate_registry(drivers())
    assert out["driver_count"]==3
    assert out["kinds"]==["PING","EXTERNAL_TOOL","DURABLE_ADMIN_WRITE"]


def test_missing_driver_fails_closed():
    d=drivers(); d.pop("EXTERNAL_TOOL")
    with pytest.raises(m.ParentDriverRegistryError,match="DRIVER_KIND_SET_MISMATCH"):
        m.validate_registry(d)


def test_extra_driver_fails_closed():
    d=drivers(); d["ARBITRARY_HOST_EFFECT"]=lambda p:{}
    with pytest.raises(m.ParentDriverRegistryError,match="DRIVER_KIND_SET_MISMATCH"):
        m.validate_registry(d)


def test_unknown_dispatch_denied():
    with pytest.raises(m.ParentDriverRegistryError,match="BROKER_KIND_DENIED"):
        m.dispatch(drivers(),"ARBITRARY_HOST_EFFECT",{})


def test_dispatch_requires_mapping_result():
    d=drivers(); d["PING"]=lambda p:"bad"
    with pytest.raises(m.ParentDriverRegistryError,match="DRIVER_RESULT_NOT_MAPPING"):
        m.dispatch(d,"PING",{})
