import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

import asyncio
import json
import websockets
from pywacli.services.event_processor import process_event


async def main():
    uri = "ws://localhost:3000/"

    async with websockets.connect(uri) as websocket:
        print("Connected to WebSocket server")

        while True:
            message = await websocket.recv()
            print(f"Received message: {message}")

            data = json.loads(message)
            if not data:
                continue

            process_event(data.get("event"), data.get("data"))


if __name__ == "__main__":
    asyncio.run(main())
