#!/usr/bin/env python3
"""Read-only MCP tool introspection.

Requires the official MCP Python SDK. This script never calls a remote tool; it
only negotiates the protocol and lists advertised tool definitions.
"""
import argparse
import asyncio
import json
import importlib.metadata


def _dump_model(value):
    if value is None:
        return None
    if hasattr(value, "model_dump"):
        return value.model_dump(mode="json", by_alias=True)
    if hasattr(value, "dict"):
        return value.dict()
    return str(value)


def _format_exception(exc):
    children=getattr(exc,"exceptions",None)
    head=type(exc).__name__+":"+str(exc)
    if children:
        return head+" => ["+" | ".join(_format_exception(child) for child in children)+"]"
    return head

async def inspect_one(url):
    try:
        from mcp import Client
    except Exception as exc:
        return {"url": url, "ok": False, "error": "MCP_SDK_IMPORT:" + _format_exception(exc)}

    try:
        async with Client(url) as client:
            result = await client.list_tools()
            tools = []
            for tool in result.tools:
                tools.append({
                    "name": getattr(tool, "name", None),
                    "title": getattr(tool, "title", None),
                    "description": getattr(tool, "description", None),
                    "input_schema": getattr(tool, "input_schema", None) or getattr(tool, "inputSchema", None),
                    "annotations": _dump_model(getattr(tool, "annotations", None)),
                })
            return {
                "url": url,
                "ok": True,
                "protocol_version": str(getattr(client, "protocol_version", None)),
                "server_info": _dump_model(getattr(client, "server_info", None)),
                "server_capabilities": _dump_model(getattr(client, "server_capabilities", None)),
                "tool_count": len(tools),
                "tools": tools,
            }
    except Exception as exc:
        return {"url": url, "ok": False, "error": _format_exception(exc)}


async def main_async(urls):
    return await asyncio.gather(*(inspect_one(url) for url in urls))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("urls", nargs="+")
    args = ap.parse_args()
    results = asyncio.run(main_async(args.urls))
    try:
        sdk_version = importlib.metadata.version("mcp")
    except Exception:
        sdk_version = None
    print(json.dumps({
        "schema": "PROJECT_BRAIN_MCP_TOOL_INTROSPECTION_V1",
        "mcp_sdk_version": sdk_version,
        "read_only": True,
        "tool_calls_performed": 0,
        "results": results,
    }, indent=2, sort_keys=True))
    return 0 if any(r.get("ok") for r in results) else 2


if __name__ == "__main__":
    raise SystemExit(main())
