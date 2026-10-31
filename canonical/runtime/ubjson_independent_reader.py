#!/usr/bin/env python3
"""In-repo, implementation-independent UBJSON (Universal Binary JSON) reader.

Purpose: producer-independent semantic round-trip verification for UBJSON
artifacts. This reader is a distinct implementation from any npm/pypi codec
(pure Python, struct byte-order walking of the UBJSON v12 type-tag stream).
It supports: null Z, true T, false F, int8 i, uint8 U, int16 I, int32 l,
int64 L, float32 F? (per spec: float32 = d, float64 = D), char C, string S,
high-precision number H, array [, ], object {, }, NOOP N, and typed-array /
optimized container ($, #) envelopes.
"""
from __future__ import annotations

import struct
from typing import Any


class UbjsonReaderError(RuntimeError):
    pass


class _Cursor:
    def __init__(self, data: bytes):
        self.data = data
        self.pos = 0

    def byte(self) -> int:
        if self.pos >= len(self.data):
            raise UbjsonReaderError("TRUNCATED_STREAM")
        b = self.data[self.pos]
        self.pos += 1
        return b

    def take(self, n: int) -> bytes:
        if self.pos + n > len(self.data):
            raise UbjsonReaderError("TRUNCATED_STREAM")
        b = self.data[self.pos : self.pos + n]
        self.pos += n
        return b

    def _int(self, tag: str) -> int:
        sizes = {"i": "b", "U": "B", "I": ">h", "l": ">i", "L": ">q"}
        fmt = sizes[tag]
        n = struct.calcsize(fmt)
        return struct.unpack(fmt, self.take(n))[0]

    def _float(self, tag: str) -> float:
        fmt = {"d": ">f", "D": ">d"}[tag]
        n = struct.calcsize(fmt)
        return struct.unpack(fmt, self.take(n))[0]

    def _string(self) -> str:
        tag = chr(self.byte())
        if tag == "i":
            n = struct.unpack("b", self.take(1))[0]
        elif tag == "U":
            n = self.byte()
        elif tag == "I":
            n = struct.unpack(">h", self.take(2))[0]
        elif tag == "l":
            n = struct.unpack(">i", self.take(4))[0]
        elif tag == "L":
            n = struct.unpack(">q", self.take(8))[0]
        else:
            raise UbjsonReaderError("STRING_LENGTH_TAG_INVALID:" + tag)
        if n < 0:
            raise UbjsonReaderError("STRING_LENGTH_NEGATIVE")
        return self.take(n).decode("utf-8")

    def value(self) -> Any:
        tag = chr(self.byte())
        if tag == "Z":
            return None
        if tag == "T":
            return True
        if tag == "F":
            return False
        if tag == "N":
            return self.value()
        if tag in ("i", "U", "I", "l", "L"):
            return self._int(tag)
        if tag in ("d", "D"):
            return self._float(tag)
        if tag == "C":
            return chr(self.byte())
        if tag == "H":
            return float(self._string())
        if tag == "S":
            return self._string()
        if tag == "[":
            # Possible optimized container: [$type | #count
            if self.data[self.pos : self.pos + 1] == b"$":
                self.pos += 1
                type_tag = chr(self.byte())
                if self.data[self.pos : self.pos + 1] == b"#":
                    self.pos += 1
                    count_tag = chr(self.byte())
                    count = self._int(count_tag)
                    return [self._typed_value(type_tag) for _ in range(count)]
                raise UbjsonReaderError("TYPED_ARRAY_MISSING_COUNT")
            if self.data[self.pos : self.pos + 1] == b"#":
                self.pos += 1
                count_tag = chr(self.byte())
                count = self._int(count_tag)
                return [self.value() for _ in range(count)]
            out = []
            while self.data[self.pos : self.pos + 1] != b"]":
                out.append(self.value_from_tag(chr(self.byte())))
            self.pos += 1
            return out
        if tag == "][":
            return []
        if tag == "{":
            return self._object_body()
        raise UbjsonReaderError("TAG_UNSUPPORTED:" + tag)

    def _bare_string(self) -> str:
        # Object keys are bare: <int-tag length><utf-8 bytes>, no S marker.
        tag = chr(self.byte())
        if tag == "i":
            n = struct.unpack("b", self.take(1))[0]
        elif tag == "U":
            n = self.byte()
        elif tag == "I":
            n = struct.unpack(">h", self.take(2))[0]
        elif tag == "l":
            n = struct.unpack(">i", self.take(4))[0]
        elif tag == "L":
            n = struct.unpack(">q", self.take(8))[0]
        else:
            raise UbjsonReaderError("KEY_LENGTH_TAG_INVALID:" + tag)
        if n < 0:
            raise UbjsonReaderError("KEY_LENGTH_NEGATIVE")
        return self.take(n).decode("utf-8")

    def _typed_value(self, type_tag: str) -> Any:
        if type_tag == "Z":
            return None
        if type_tag == "T":
            return True
        if type_tag == "F":
            return False
        if type_tag in ("i", "U", "I", "l", "L"):
            return self._int(type_tag)
        if type_tag in ("d", "D"):
            return self._float(type_tag)
        if type_tag == "C":
            return chr(self.byte())
        if type_tag in ("S", "H"):
            return self._string()
        raise UbjsonReaderError("TYPED_TAG_UNSUPPORTED:" + type_tag)

    def value_from_tag(self, tag: str) -> Any:
        if tag == "Z":
            return None
        if tag == "T":
            return True
        if tag == "F":
            return False
        if tag in ("i", "U", "I", "l", "L"):
            return self._int(tag)
        if tag in ("d", "D"):
            return self._float(tag)
        if tag == "C":
            return chr(self.byte())
        if tag in ("S", "H"):
            return self._string()
        if tag == "[":
            out = []
            if self.data[self.pos : self.pos + 1] == b"$":
                self.pos += 1
                type_tag = chr(self.byte())
                if self.data[self.pos : self.pos + 1] == b"#":
                    self.pos += 1
                    count = self._int(chr(self.byte()))
                    return [self._typed_value(type_tag) for _ in range(count)]
                raise UbjsonReaderError("TYPED_ARRAY_MISSING_COUNT")
            if self.data[self.pos : self.pos + 1] == b"#":
                self.pos += 1
                count = self._int(chr(self.byte()))
                return [self.value() for _ in range(count)]
            while self.data[self.pos : self.pos + 1] != b"]":
                out.append(self.value_from_tag(chr(self.byte())))
            self.pos += 1
            return out
        if tag == "{":
            return self._object_body()
        raise UbjsonReaderError("TAG_UNSUPPORTED_IN_ARRAY:" + tag)

    def _object_body(self) -> dict:
        out: dict[str, Any] = {}
        if self.data[self.pos : self.pos + 1] == b"#":
            self.pos += 1
            count = self._int(chr(self.byte()))
            for _ in range(count):
                key = self._bare_string()
                out[key] = self.value()
            return out
        while self.data[self.pos : self.pos + 1] != b"}":
            key = self._bare_string()
            out[key] = self.value()
        self.pos += 1
        return out

    # value() handles object bodies; value_from_tag used only inside untyped


def decode(data: bytes) -> Any:
    cur = _Cursor(data)
    value = cur.value()
    if cur.pos != len(data):
        raise UbjsonReaderError("TRAILING_BYTES:" + str(len(data) - cur.pos))
    return value
