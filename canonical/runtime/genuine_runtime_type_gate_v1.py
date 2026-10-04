from __future__ import annotations


def actual_mro(value):
    cls=type(value)
    return type.__getattribute__(cls,"__mro__")


def genuine_instance(value, base):
    if not isinstance(base,type):
        raise TypeError("base must be a type")
    return base in actual_mro(value)


def genuine_str(value):
    return genuine_instance(value,str)


def genuine_bytes(value):
    return genuine_instance(value,bytes)
