import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

import websockets
import asyncio
import json
from pywacli.db.database import save_conversation
from pywacli.db.init_db import init_database
from pywacli.db.database import (
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
                    from pywacli.utils.bucket_utils import upload_file_to_s3
                    from pywacli.utils.local_utils import store_media_local
                    from pywacli.db.database import (
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
                    is_status = bool(media_data.get("isStatus"))
                    is_view_once = bool(media_data.get("isViewOnce"))
                    push_name = media_data.get("pushName", "Unknown")
                    phone_number = media_data.get("phoneNumber", "")
                    contact_phone = media_data.get("contactPhone", phone_number)

                    # Build contact-based sub-folder: "pushName_contactPhone"
                    contact_dir = f"{push_name}_{contact_phone}".strip("_ ")

                    from pywacli.cli.config_manager import load_config
                    config = load_config()
                    entries = config.get("media_storage", {}).get("entries", [])

                    any_success = False

                    for entry in entries:
                        provider = entry.get("provider")

                        # Decide whether this entry wants this item and which
                        # sub-folder / key-prefix it belongs under. Status and
                        # view-once media get their own top-level folders, then
                        # the contact-based sub-folder and media type.
                        if is_status:
                            if not entry.get("store_status", False):
                                continue
                            rel_parts = ["status", contact_dir]
                        elif is_view_once:
                            if not entry.get("store_view_once", False):
                                continue
                            rel_parts = ["viewonce", contact_dir]
                        else:
                            if not entry.get(f"store_{media_type}", False):
                                continue
                            rel_parts = [f"{media_type}s", contact_dir]

                        if provider in ("s3", "r2"):
                            bucket_name = entry.get("bucket_name", "whatsapp-media")
                            object_name = "/".join(rel_parts + [data['data']['fileName']])
                            status = upload_file_to_s3(
                                file_path=data['data']['filePath'],
                                object_name=object_name,
                                bucket_name=bucket_name,
                                entry=entry
                            )
                        elif provider == "local":
                            dest_dir = os.path.join(
                                entry.get("local_path", "./media"), *rel_parts
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