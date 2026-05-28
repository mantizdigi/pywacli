import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(__file__)))

import websockets
import asyncio
import json
from db.database import save_conversation
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
                    from src.db.database import (
                        save_media_table,
                        save_media_handshake
                    )
                    import os 
                    
                    media_id = save_media_table(media_data)

                    if not media_id:
                        print("Failed to save media metadata to database.")
                        continue

                    BUCKET_NAME = "whatsapp-other"
                    media_type = media_data.get("mediaType")

                    if media_type == "image":
                        BUCKET_NAME = "whatsapp-media-image"

                    elif media_type == "video":
                        BUCKET_NAME = "whatsapp-media-video"

                    elif media_type == "document":
                        BUCKET_NAME = "whatsapp-media-document"
                    media_type = media_data.get("mediaType")
                    BUCKET_NAME = "whatsapp-other"

                    BUCKET_NAME ="other"
                    if data['data']['mediaType'] in ["image"]:
                        BUCKET_NAME = "whatsapp-media-image"
                    
                    status = upload_file_to_s3(
                        file_path=data['data']['filePath'],
                        object_name=data['data']['fileName'],
                        bucket_name=BUCKET_NAME
                    )
                    print(f"Upload status: {status}")
                    if status:
                        save_media_handshake({
                            "media_id": media_id,
                            "sync": 1,
                            "failure_reason": None
                        })

                        print("✅ Uploaded to S3")

                        # DELETE LOCAL FILE
                        if os.path.exists(media_data['filePath']):
                            os.remove(media_data['filePath'])
                            print("🗑 Local file deleted")
                        else:
                            save_media_handshake({
                                "media_id": media_id,
                                "sync": 0,
                                "failure_reason": "S3 Upload Failed"
                            })
                            print("❌ Upload failed")
                    else:
                        save_media_handshake({
                            "media_id": media_id,
                            "sync": 0,
                            "failure_reason": "S3 Upload Failed"
                        })
                        print("❌ Upload failed")
                except Exception as e:
                    print(f"❌ Error handling media.new event: {e}")
                    save_media_handshake({
                    "media_id": media_id,
                    "sync": 0,
                    "failure_reason": "S3 Upload Failed"
                    })                       
                
                # Handle media saving logic here (e.g., save to S3 or local storage)
                # You can use the data['data'] to get details about the media and save it accordingly

if __name__ == "__main__":
    asyncio.run(main())