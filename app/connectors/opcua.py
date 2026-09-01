from __future__ import annotations
import asyncio

def opcua_available() -> bool:
    try:
        import asyncua  # noqa
        return True
    except Exception:
        return False

async def read_nodes(endpoint: str, node_ids: list[str]) -> dict[str, object]:
    from asyncua import Client
    async with Client(url=endpoint) as client:
        out={}
        for node_id in node_ids:
            out[node_id]=await client.get_node(node_id).read_value()
        return out
