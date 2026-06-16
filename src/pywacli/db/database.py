import logging

from pywacli.cli.config_manager import setup_logging
from pywacli.db.engine import get_engine, get_db_driver, execute, insert_and_get_id


setup_logging()
logger = logging.getLogger(__name__)


def _integer_pk():
    driver = get_db_driver()
    if driver == "postgresql":
        return "SERIAL PRIMARY KEY"
    elif driver == "mysql":
        return "INTEGER AUTO_INCREMENT PRIMARY KEY"
    return "INTEGER PRIMARY KEY AUTOINCREMENT"


def _ensure_column(table: str, column: str, decl: str):
    engine = get_engine()
    conn = engine.raw_connection()
    cursor = conn.cursor()
    driver = get_db_driver()
    try:
        if driver == "postgresql":
            cursor.execute(
                "SELECT column_name FROM information_schema.columns "
                "WHERE table_name=%s AND column_name=%s", (table, column))
            if not cursor.fetchone():
                cursor.execute(f"ALTER TABLE {table} ADD COLUMN {column} {decl}")
                conn.commit()
        elif driver == "mysql":
            cursor.execute(f"SHOW COLUMNS FROM {table} LIKE '{column}'")
            if not cursor.fetchone():
                cursor.execute(f"ALTER TABLE {table} ADD COLUMN {column} {decl}")
                conn.commit()
        else:
            cursor.execute(f"PRAGMA table_info({table})")
            existing = {row[1] for row in cursor.fetchall()}
            if column not in existing:
                cursor.execute(f"ALTER TABLE {table} ADD COLUMN {column} {decl}")
                conn.commit()
    except Exception as e:
        logger.error("Error ensuring column %s.%s: %s", table, column, e)
    finally:
        cursor.close()
        conn.close()


def create_table():
    try:
        execute("""
            CREATE TABLE IF NOT EXISTS messages (
                id TEXT PRIMARY KEY,
                jid TEXT,
                text TEXT,
                from_me INTEGER,
                push_name TEXT,
                timestamp INTEGER
            )
        """)
        _ensure_column("messages", "phone_number", "TEXT")
        print("✅ messages table ready")
        return True
    except Exception as e:
        logger.error("Error creating table: %s", e)
        return False


def save_message(data):
    try:
        execute("""
            INSERT INTO messages (id, jid, text, from_me, push_name, phone_number, timestamp)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, [
            data.get("id"),
            data.get("jid"),
            data.get("text"),
            1 if data.get("fromMe") else 0,
            data.get("pushName", ""),
            data.get("phoneNumber", ""),
            data.get("timestamp", 0)
        ])
        print("✅ Message saved")
        return True
    except Exception as e:
        logger.error("Error saving message: %s", e)
        return False


def create_edit_table():
    try:
        execute(f"""
            CREATE TABLE IF NOT EXISTS message_edits (
                id {_integer_pk()},
                message_id TEXT,
                new_text TEXT,
                edited_at INTEGER
            )
        """)
        print("✅ edits table ready")
        return True
    except Exception as e:
        logger.error("Error creating edits table: %s", e)
        return False


def save_edited_message(data):
    try:
        execute("""
            INSERT INTO message_edits (message_id, new_text, edited_at)
            VALUES (?, ?, ?)
        """, [
            data.get("id"),
            data.get("text"),
            data.get("timestamp", 0)
        ])
        print("✅ Edited message saved")
        return True
    except Exception as e:
        logger.error("Error saving edited message: %s", e)
        return False


def create_status_table():
    try:
        execute("""
            CREATE TABLE IF NOT EXISTS statuses (
                id TEXT PRIMARY KEY,
                jid TEXT,
                text TEXT,
                push_name TEXT,
                from_me INTEGER,
                timestamp INTEGER
            )
        """)
        _ensure_column("statuses", "phone_number", "TEXT")
        print("✅ statuses table ready")
        return True
    except Exception as e:
        logger.error("Error creating statuses table: %s", e)
        return False


def save_status(data):
    try:
        execute("""
            INSERT INTO statuses (id, jid, text, push_name, phone_number, from_me, timestamp)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, [
            data.get("id"),
            data.get("jid"),
            data.get("text"),
            data.get("pushName"),
            data.get("phoneNumber", ""),
            1 if data.get("fromMe") else 0,
            data.get("timestamp")
        ])
        print("✅ Status saved")
        return True
    except Exception as e:
        logger.error("Error saving status: %s", e)
        return False


def create_reactions_table():
    try:
        execute(f"""
            CREATE TABLE IF NOT EXISTS reactions (
                id {_integer_pk()},
                message_id TEXT,
                reacted_message_id TEXT,
                jid TEXT,
                reaction TEXT,
                from_me INTEGER,
                timestamp INTEGER
            )
        """)
        print("✅ reactions table ready")
    except Exception as e:
        logger.error("Error creating reactions table: %s", e)


def save_reaction(data):
    try:
        execute("""
            INSERT INTO reactions (message_id, reacted_message_id, jid, reaction, from_me, timestamp)
            VALUES (?, ?, ?, ?, ?, ?)
        """, [
            data.get("messageId"),
            data.get("reactedTo", {}).get("id"),
            data.get("jid"),
            data.get("reaction"),
            int(data.get("fromMe", False)),
            data.get("timestamp", 0)
        ])
        print("✅ Reaction saved")
        return True
    except Exception as e:
        logger.error("Error saving reaction: %s", e)
        return False


def create_media_table():
    try:
        execute(f"""
            CREATE TABLE IF NOT EXISTS media (
                media_id {_integer_pk()},
                jid TEXT,
                media_type VARCHAR(20),
                media_mimetype VARCHAR(50),
                file_name VARCHAR(255),
                file_path TEXT,
                push_name TEXT,
                from_me INTEGER DEFAULT 0,
                is_status INTEGER DEFAULT 0,
                is_view_once INTEGER DEFAULT 0,
                timestamp INTEGER DEFAULT 0
            )
        """)
        _ensure_column("media", "is_status", "INTEGER DEFAULT 0")
        _ensure_column("media", "is_view_once", "INTEGER DEFAULT 0")
        _ensure_column("media", "phone_number", "TEXT")
        print("✅ media table ready")
        return True
    except Exception as e:
        print(f"❌ Error in media table: {e}")
        return False


def create_media_handshake_table():
    try:
        execute(f"""
            CREATE TABLE IF NOT EXISTS media_handshake (
                id {_integer_pk()},
                media_id INTEGER,
                sync BOOLEAN DEFAULT 0,
                failure_reason TEXT,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        print("✅ media_handshake table ready")
        return True
    except Exception as e:
        print(f"❌ Error in media_handshake table: {e}")
        return False


def save_media_table(data):
    try:
        rid = insert_and_get_id("""
            INSERT INTO media (jid, media_type, media_mimetype, file_name, file_path,
                               push_name, phone_number, from_me, is_status, is_view_once, timestamp)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, [
            data.get("jid"),
            data.get("mediaType"),
            data.get("mimeType"),
            data.get("fileName"),
            data.get("filePath"),
            data.get("pushName"),
            data.get("phoneNumber", ""),
            1 if data.get("fromMe") else 0,
            1 if data.get("isStatus") else 0,
            1 if data.get("isViewOnce") else 0,
            data.get("timestamp")
        ])
        print("✅ Media Saved")
        return rid
    except Exception as e:
        print(f"❌ Error in save_media_table: {e}")
        return False


def save_media_handshake(data):
    try:
        execute("""
            INSERT INTO media_handshake (media_id, sync, failure_reason)
            VALUES (?, ?, ?)
        """, [
            data.get("media_id"),
            data.get("sync"),
            data.get("failure_reason")
        ])
        print("✅ media_handshake saved")
        return True
    except Exception as e:
        print(f"❌ Error saving handshake: {e}")
        return False


def create_conversations_table():
    try:
        execute(f"""
            CREATE TABLE IF NOT EXISTS conversations (
                conversation_id {_integer_pk()},
                message_id TEXT,
                jid TEXT,
                message_type TEXT,
                text TEXT,
                media_type TEXT,
                media_mimetype TEXT,
                file_name TEXT,
                file_path TEXT,
                push_name TEXT,
                from_me INTEGER DEFAULT 0,
                participant TEXT,
                is_status INTEGER DEFAULT 0,
                is_view_once INTEGER DEFAULT 0,
                timestamp INTEGER
            )
        """)
        _ensure_column("conversations", "is_view_once", "INTEGER DEFAULT 0")
        _ensure_column("conversations", "phone_number", "TEXT")
        print("✅ conversations table ready")
        return True
    except Exception as e:
        print(f"❌ Error creating conversations table: {e}")
        return False


def save_conversation(data):
    try:
        rid = insert_and_get_id("""
            INSERT INTO conversations (message_id, jid, message_type, text, media_type,
                media_mimetype, file_name, file_path, push_name, phone_number, from_me,
                participant, is_status, is_view_once, timestamp)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, [
            data.get("id"),
            data.get("jid"),
            data.get("messageType"),
            data.get("text"),
            data.get("mediaType"),
            data.get("mimeType"),
            data.get("fileName"),
            data.get("filePath"),
            data.get("pushName"),
            data.get("phoneNumber", ""),
            1 if data.get("fromMe") else 0,
            data.get("participant"),
            1 if data.get("isStatus") else 0,
            1 if data.get("isViewOnce") else 0,
            data.get("timestamp")
        ])
        print("✅ Conversation saved")
        return rid
    except Exception as e:
        print(f"❌ Error saving conversation: {e}")
        return False
