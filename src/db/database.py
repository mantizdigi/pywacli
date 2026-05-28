import sqlite3
import logging
import os


logging.basicConfig(level=logging.INFO) 
logger = logging.getLogger(__name__)


BASE_DIR = os.path.dirname(
    os.path.dirname(__file__)
)

DB_PATH = os.path.join(
    BASE_DIR,
    "pywacli.db"
)

conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()


# CREATE TABLE
def create_table():

    sql = """
        CREATE TABLE IF NOT EXISTS messages (

            id TEXT PRIMARY KEY,

            jid TEXT,

            text TEXT,

            from_me INTEGER,

            push_name TEXT,

            timestamp INTEGER
        )
    """

    try:

        cursor.execute(sql)

        conn.commit()

        print("✅ messages table ready")

        return True

    except Exception as e:

        logger.error("Error creating table: %s", e)

        return False

# SAVE MESSAGE
def save_message(data):

    sql = """
        INSERT INTO messages (
            id,
            jid,
            text,
            from_me,
            push_name,
            timestamp
        )
        VALUES (?, ?, ?, ?, ?, ?)
    """

    try:

        message_id = data.get("id")

        jid = data.get("jid")

        text = data.get("text")

        from_me = 1 if data.get("fromMe") else 0

        push_name = data.get("pushName", "")

        timestamp = data.get("timestamp", 0)

        cursor.execute(sql, (
            message_id,
            jid,
            text,
            from_me,
            push_name,
            timestamp
        ))

        conn.commit()

        print("✅ Message saved")

        return True

    except Exception as e:

        logger.error("Error saving message: %s", e)

        return False

def create_edit_table():

    sql="""
        CREATE TABLE IF NOT EXISTS message_edits (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            message_id TEXT,
            new_text TEXT,
            edited_at INTEGER
        )
    """

    try:
        cursor.execute(sql)
        conn.commit()
        print("✅ edits table ready")
        return True

    except Exception as e:
        logger.error("Error creating edits table: %s", e)
        return False

def save_edited_message(data):
    sql = """
        INSERT INTO message_edits (
            message_id,
            new_text,
            edited_at
        )
        VALUES (?, ?, ?)
    """

    try:
        message_id = data.get("id")
        new_text = data.get("text")
        edited_at = data.get("timestamp", 0)
        cursor.execute(sql, (
            message_id,
            new_text,
            edited_at
        ))
        conn.commit()
        print("✅ Edited message saved")
        return True
    
    except Exception as e:
        logger.error("Error saving edited message: %s", e)
        return False
    
def create_status_table():

    sql = """
        CREATE TABLE IF NOT EXISTS statuses (

            id TEXT PRIMARY KEY,
            jid TEXT,
            text TEXT,
            push_name TEXT,
            from_me INTEGER,
            timestamp INTEGER
        )
    """

    try:

        cursor.execute(sql)
        conn.commit()
        print("✅ statuses table ready")
        return True

    except Exception as e:

        logger.error("Error creating statuses table: %s", e)
        return False
    
def save_status(data):

    sql = """
        INSERT INTO statuses (
            id,
            jid,
            text,
            push_name,
            from_me,
            timestamp
        )
        VALUES (?, ?, ?, ?, ?, ?)
    """

    try:

        cursor.execute(sql, (

            data.get("id"),
            data.get("jid"),
            data.get("text"),
            data.get("pushName"),
            1 if data.get("fromMe") else 0,
            data.get("timestamp")
        ))

        conn.commit()
        print("✅ Status saved")
        return True

    except Exception as e:

        logger.error("Error saving status: %s", e)
        return False
    
def create_reactions_table():

    sql = """
        CREATE TABLE IF NOT EXISTS reactions (

            id INTEGER PRIMARY KEY AUTOINCREMENT,
            message_id TEXT,
            reacted_message_id TEXT,
            jid TEXT,
            reaction TEXT,
            from_me INTEGER,
            timestamp INTEGER
        )
    """

    try:

        cursor.execute(sql)
        conn.commit()
        print("✅ reactions table ready")

    except Exception as e:

        logger.error(
            "Error creating reactions table: %s",
            e
        )

def save_reaction(data):

    sql = """
    INSERT INTO reactions (

        message_id,
        reacted_message_id,
        jid,
        reaction,
        from_me,
        timestamp

    ) VALUES (?, ?, ?, ?, ?, ?)
    """

    try:

        message_id = data.get("messageId")

        reacted_message_id = (
            data.get("reactedTo", {})
            .get("id")
        )

        jid = data.get("jid")

        reaction = data.get("reaction")

        from_me = int(
            data.get("fromMe", False)
        )

        timestamp = data.get("timestamp", 0)

        cursor.execute(sql, (

            message_id,
            reacted_message_id,
            jid,
            reaction,
            from_me,
            timestamp
        ))

        conn.commit()

        print("✅ Reaction saved")

        return True

    except Exception as e:

        logger.error(
            "Error saving reaction: %s",
            e
        )

        return False
    
def create_media_table():

    sql = """
        CREATE TABLE IF NOT EXISTS media (

            media_id INTEGER PRIMARY KEY AUTOINCREMENT,
            jid TEXT,
            media_type VARCHAR(20),
            media_mimetype VARCHAR(50),
            file_name VARCHAR(255),
            file_path TEXT,
            push_name TEXT,
            from_me INTEGER DEFAULT 0,
            timestamp INTEGER DEFAULT 0
        )
    """

    try:

        cursor.execute(sql)
        conn.commit()
        print("✅ media table ready")
        return True

    except Exception as e:
        print(f"❌ Error in media table: {e}")
        return False

def create_media_handshake_table():

    sql = """
        CREATE TABLE IF NOT EXISTS media_handshake (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            media_id INTEGER,
            sync BOOLEAN DEFAULT 0,
            failure_reason TEXT,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (media_id)
                REFERENCES media(media_id)
                ON DELETE CASCADE
        )
    """

    try:

        cursor.execute(sql)
        conn.commit()
        print("✅ media_handshake table ready")
        return True

    except Exception as e:
        print(f"❌ Error in media_handshake table: {e}")
        return False

def save_media_table(data):

    sql = """
        INSERT INTO media (
            jid,
            media_type,
            media_mimetype,
            file_name,
            file_path,
            push_name,
            from_me,
            timestamp
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """

    try:

        values = (

            data.get("jid"),
            data.get("mediaType"),
            data.get("mimeType"),
            data.get("fileName"),
            data.get("filePath"),
            data.get("pushName"),
            data.get("fromMe"),
            data.get("timestamp")
        )

        cursor.execute(sql, values)
        conn.commit()
        print("✅ Media Saved")
        return cursor.lastrowid

    except Exception as e:

        print(f"❌ Error in save_media_table: {e}")
        return False  
    
def save_media_handshake(data):

    sql = """
        INSERT INTO media_handshake (
            media_id,
            sync,
            failure_reason
        )
        VALUES (?, ?, ?)
    """

    try:

        values = (

            data.get("media_id"),

            data.get("sync"),

            data.get("failure_reason")
        )

        cursor.execute(sql, values)

        conn.commit()

        print("✅ media_handshake saved")

        return True

    except Exception as e:

        print(f"❌ Error saving handshake: {e}")

        return False


def create_conversations_table():

    sql = """
        CREATE TABLE IF NOT EXISTS conversations (

            conversation_id INTEGER PRIMARY KEY AUTOINCREMENT,

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

            timestamp INTEGER
        )
    """

    try:

        cursor.execute(sql)

        conn.commit()

        print("✅ conversations table ready")

        return True

    except Exception as e:

        print(f"❌ Error creating conversations table: {e}")

        return False

def save_conversation(data):

    sql = """
        INSERT INTO conversations (

            message_id,
            jid,
            message_type,
            text,
            media_type,
            media_mimetype,
            file_name,
            file_path,
            push_name,
            from_me,
            participant,
            is_status,
            timestamp

        )

        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """

    try:

        values = (

            data.get("id"),

            data.get("jid"),

            data.get("messageType"),

            data.get("text"),

            data.get("mediaType"),

            data.get("mimeType"),

            data.get("fileName"),

            data.get("filePath"),

            data.get("pushName"),

            1 if data.get("fromMe") else 0,

            data.get("participant"),

            1 if data.get("isStatus") else 0,

            data.get("timestamp")
        )

        cursor.execute(sql, values)

        conn.commit()

        print("✅ Conversation saved")

        return cursor.lastrowid

    except Exception as e:

        print(f"❌ Error saving conversation: {e}")

        return False