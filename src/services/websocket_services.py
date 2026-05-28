import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

import websockets
import asyncio
import json
from src.db.database import save_conversation
from src.db.init_db import init_database
from src.db.database import (
    save_message,
    save_conversation,
    save_edited_message,
    save_media_handshake,
    save_media_table,
    save_reaction,
    save_status
)
init_database()

async def main():
    uri ="ws://localhost:3000/"

    async with websockets.connect(uri) as websocket:
        print("Connected to WebSocket server")
    
        while True:

            message = await websocket.recv()
            print(f"Received message: {message}")
            
            data = json.loads(message)
            # Save to DB
            if not data:
                continue

            if data['event'] == "message.new":
                try:
                    save_message(data['data'])
                except Exception as e:
                    print(f"❌ Error saving message: {e}")

            elif data['event'] == "message.update":
                try:
                    save_edited_message(data['data'])
                except Exception as e:
                    print(f"❌ Error saving edited message: {e}")

            elif data['event'] == "message.reaction":
                try:
                    data = data['data']
                    reactions = data.get("reactions", [])
                    for reaction in reactions:
                        save_reaction(reaction)
                except Exception as e:
                    print(f"❌ Error saving reaction: {e}")

            elif data['event'] == "status.new":
                try:
                    save_status(data['data'])
                except Exception as e:
                    print(f"❌ Error saving status: {e}")   

            elif data['event'] == "conversation.new":
                save_conversation(data['data'])

            # Media Events
            elif data['event'] == "media.new":

                try:
                    media_data = data['data']
                    print("📦 New media received:", media_data)
                    from src.utils.bucket_utils import upload_file_to_s3
                    from src.utils.local_utils import store_media_local
                    from src.db.database import (
                        save_media_table,
                        save_media_handshake
                    )
                    import shutil
                    import os

                    media_id = save_media_table(media_data)

                    if not media_id:
                        print("Failed to save media metadata to database.")
                        continue

                    media_type = media_data.get("mediaType", "").lower()

                    from src.cli.config_manager import load_config
                    config = load_config()
                    entries = config.get("media_storage", {}).get("entries", [])

                    any_success = False

                    for entry in entries:
                        provider = entry.get("provider")
                        type_field = f"store_{media_type}"
                        if not entry.get(type_field, False):
                            continue

                        if provider in ("s3", "r2"):
                            bucket_name = entry.get("bucket_name", "whatsapp-media")
                            object_name = f"{media_type}/{data['data']['fileName']}"
                            status = upload_file_to_s3(
                                file_path=data['data']['filePath'],
                                object_name=object_name,
                                bucket_name=bucket_name,
                                entry=entry
                            )
                        elif provider == "local":
                            dest_dir = os.path.join(
                                entry.get("local_path", "./media"), media_type
                            )
                            status = store_media_local(
                                file_path=data['data']['filePath'],
                                dest_dir=dest_dir,
                                entry=entry
                            )
                        else:
                            continue

                        if status:
                            any_success = True
                            save_media_handshake({
                                "media_id": media_id,
                                "sync": 1,
                                "failure_reason": None
                            })
                            print(f"✅ Stored via {provider} (entry #{entry.get('id')})")
                        else:
                            save_media_handshake({
                                "media_id": media_id,
                                "sync": 0,
                                "failure_reason": f"{provider.upper()} Upload Failed"
                            })
                            print(f"❌ Failed via {provider} (entry #{entry.get('id')})")

                    if any_success and os.path.exists(data['data']['filePath']):
                        os.remove(data['data']['filePath'])
                        print("🗑 Local file deleted")

                except Exception as e:
                    print(f"❌ Error handling media.new event: {e}")
                    try:
                        save_media_handshake({
                            "media_id": media_id,
                            "sync": 0,
                            "failure_reason": str(e)
                        })
                    except Exception:
                        pass

if __name__ == "__main__":
    asyncio.run(main())