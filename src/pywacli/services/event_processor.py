import os
from pywacli.cli.config_manager import get_service_logger
from pywacli.db.database import (
    save_message,
    save_conversation,
    save_edited_message,
    save_media_handshake,
    save_media_table,
    save_reaction,
    save_status
)
from pywacli.db.init_db import init_database

# File-only logger: event handling runs in the background session, so its
# status lines go to the log file instead of the interactive console.
logger = get_service_logger("pywacli.events")

init_database()


def process_event(event_type, data):
    if event_type == "message.new":
        try:
            save_message(data)
        except Exception as e:
            logger.error(f"Error saving message: {e}")

    elif event_type == "message.update":
        try:
            save_edited_message(data)
        except Exception as e:
            logger.error(f"Error saving edited message: {e}")

    elif event_type == "message.reaction":
        try:
            reactions = data.get("reactions", [])
            for reaction in reactions:
                save_reaction(reaction)
        except Exception as e:
            logger.error(f"Error saving reaction: {e}")

    elif event_type == "status.new":
        try:
            save_status(data)
        except Exception as e:
            logger.error(f"Error saving status: {e}")

    elif event_type == "conversation.new":
        save_conversation(data)

    elif event_type == "media.new":
        _process_media(data)


def _process_media(media_data):
    try:
        logger.info("Media received: %s", media_data)
        from pywacli.utils.bucket_utils import upload_file_to_s3
        from pywacli.utils.local_utils import store_media_local
        from pywacli.cli.config_manager import load_config

        media_id = save_media_table(media_data)
        if not media_id:
            logger.error("Failed to save media metadata to database.")
            return

        media_type = media_data.get("mediaType", "").lower()
        is_status = bool(media_data.get("isStatus"))
        is_view_once = bool(media_data.get("isViewOnce"))
        push_name = media_data.get("pushName", "Unknown")
        phone_number = media_data.get("phoneNumber", "")
        contact_phone = media_data.get("contactPhone", phone_number)
        contact_dir = f"{push_name}_{contact_phone}".strip("_ ")

        config = load_config()
        entries = config.get("media_storage", {}).get("entries", [])

        any_success = False

        for entry in entries:
            provider = entry.get("provider")

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
                object_name = "/".join(rel_parts + [media_data['fileName']])
                status = upload_file_to_s3(
                    file_path=media_data['filePath'],
                    object_name=object_name,
                    bucket_name=bucket_name,
                    entry=entry
                )
            elif provider == "local":
                dest_dir = os.path.join(
                    entry.get("local_path", "./media"), *rel_parts
                )
                status = store_media_local(
                    file_path=media_data['filePath'],
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
                logger.info(f"Stored via {provider} (entry #{entry.get('id')})")
            else:
                save_media_handshake({
                    "media_id": media_id,
                    "sync": 0,
                    "failure_reason": f"{provider.upper()} Upload Failed"
                })
                logger.error(f"Failed via {provider} (entry #{entry.get('id')})")

        if any_success and os.path.exists(media_data['filePath']):
            os.remove(media_data['filePath'])
    except Exception as e:
        logger.error(f"Error handling media.new event: {e}")



        try:
            save_media_handshake({
                "media_id": media_id,
                "sync": 0,
                "failure_reason": str(e)
            })
        except Exception:
            pass
