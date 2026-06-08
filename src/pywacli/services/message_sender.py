import asyncio
import json
import websockets


async def _send(jid: str, text: str, uri: str = "ws://localhost:3000"):
    """Send a text message to a WhatsApp contact via the Baileys WebSocket bridge.
    `jid` should be the full WhatsApp JID (e.g. 919876543210@s.whatsapp.net or 200437751877786@lid)."""
    payload = json.dumps({
        "event": "send.message",
        "data": {
            "jid": jid,
            "text": text,
        }
    })

    async with websockets.connect(uri) as ws:
        await ws.send(payload)
        response = await ws.recv()
        return json.loads(response)


def send_message(phone: str, text: str, uri: str = "ws://localhost:3000", jid: str = None):
    """Synchronous wrapper. If `jid` is provided, uses it directly.
    Otherwise constructs JID from phone number."""
    if jid:
        target = jid
    elif "@" in phone:
        target = phone
    else:
        target = f"{phone}@s.whatsapp.net"
    return asyncio.run(_send(target, text, uri))


def send_message_to_group(group_id: str, text: str, uri: str = "ws://localhost:3000"):
    """Send a text message to a WhatsApp group via the Baileys WebSocket bridge."""
    payload = json.dumps({
        "event": "send.message",
        "data": {
            "jid": group_id,
            "text": text,
        }
    })

    async def _send_group():
        async with websockets.connect(uri) as ws:
            await ws.send(payload)
            response = await ws.recv()
            return json.loads(response)

    return asyncio.run(_send_group())
