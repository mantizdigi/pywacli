import sqlite3
import logging

from pywacli.cli.config_manager import get_db_path


logger = logging.getLogger(__name__)


# Same configured path the writer (database.py) uses, so the dashboard reads
# the database the services actually write to.
DB_PATH = get_db_path()

conn = sqlite3.connect(DB_PATH, check_same_thread=False)
cursor = conn.cursor()



def get_total_messages():

    sql = "SELECT COUNT(*) FROM messages"

    cursor.execute(sql)

    return cursor.fetchone()[0]

def get_total_statuses():

    sql = "SELECT COUNT(*) FROM statuses"

    cursor.execute(sql)

    return cursor.fetchone()[0]

def get_total_reactions():

    sql = "SELECT COUNT(*) FROM reactions"

    cursor.execute(sql)

    return cursor.fetchone()[0]

def get_total_media():

    sql = "SELECT COUNT(*) FROM media"

    cursor.execute(sql)

    return cursor.fetchone()[0]

def get_recent_messages(limit=10):

    sql = """
        SELECT push_name, text
        FROM messages
        ORDER BY rowid DESC
        LIMIT ?
    """

    cursor.execute(sql, (limit,))

    return cursor.fetchall()


def get_media_types():
    sql = "SELECT DISTINCT media_type FROM media WHERE media_type IS NOT NULL"
    cursor.execute(sql)
    return [row[0] for row in cursor.fetchall()]


def get_media_by_type(media_type=None, limit=50):
    if media_type:
        sql = """
            SELECT m.media_id, m.media_type, m.file_name, m.push_name,
                   m.from_me, m.timestamp, m.file_path, h.sync
            FROM media m
            LEFT JOIN media_handshake h ON m.media_id = h.media_id
            WHERE m.media_type = ?
            ORDER BY m.timestamp DESC
            LIMIT ?
        """
        cursor.execute(sql, (media_type, limit))
    else:
        sql = """
            SELECT m.media_id, m.media_type, m.file_name, m.push_name,
                   m.from_me, m.timestamp, m.file_path, h.sync
            FROM media m
            LEFT JOIN media_handshake h ON m.media_id = h.media_id
            ORDER BY m.timestamp DESC
            LIMIT ?
        """
        cursor.execute(sql, (limit,))
    return cursor.fetchall()


def get_media_by_id(media_id):
    sql = """
        SELECT m.media_id, m.media_type, m.file_name, m.push_name,
               m.from_me, m.timestamp, m.file_path, m.media_mimetype,
               h.sync, h.failure_reason
        FROM media m
        LEFT JOIN media_handshake h ON m.media_id = h.media_id
        WHERE m.media_id = ?
    """
    cursor.execute(sql, (media_id,))
    return cursor.fetchone()


def get_messages_by_contact(phone_number, limit=50):
    """Get recent messages from a specific contact (incoming only).
    Matches by phone_number, jid prefix, or push_name."""
    sql = """
        SELECT id, text, from_me, push_name, phone_number, timestamp, jid
        FROM messages
        WHERE from_me = 0
          AND (
            phone_number = ?
            OR jid LIKE ?
            OR push_name = ?
          )
        ORDER BY timestamp ASC
        LIMIT ?
    """
    jid_pattern = f"{phone_number}%"
    cursor.execute(sql, (phone_number, jid_pattern, phone_number, limit))
    return cursor.fetchall()


def get_latest_message_id(phone_number):
    """Get the latest message ID from a contact."""
    sql = """
        SELECT id FROM messages
        WHERE from_me = 0
          AND (
            phone_number = ?
            OR jid LIKE ?
            OR push_name = ?
          )
        ORDER BY timestamp DESC
        LIMIT 1
    """
    jid_pattern = f"{phone_number}%"
    cursor.execute(sql, (phone_number, jid_pattern, phone_number))
    row = cursor.fetchone()
    return row[0] if row else None


def get_new_messages_after(phone_number, last_message_id):
    """Get new incoming messages after a specific message ID."""
    sql = """
        SELECT id, text, from_me, push_name, phone_number, timestamp, jid
        FROM messages
        WHERE from_me = 0
          AND (
            phone_number = ?
            OR jid LIKE ?
            OR push_name = ?
          )
        ORDER BY timestamp ASC
    """
    jid_pattern = f"{phone_number}%"
    cursor.execute(sql, (phone_number, jid_pattern, phone_number))
    all_messages = cursor.fetchall()

    if not last_message_id:
        return all_messages

    found = False
    new_messages = []
    for msg in all_messages:
        if msg[0] == last_message_id:
            found = True
            continue
        if found:
            new_messages.append(msg)
    return new_messages


def get_all_contacts():
    """Get all unique contacts from messages table (incoming only)."""
    sql = """
        SELECT DISTINCT phone_number, push_name, jid
        FROM messages
        WHERE from_me = 0
          AND (phone_number != '' OR push_name != '')
        ORDER BY timestamp DESC
    """
    cursor.execute(sql)
    return cursor.fetchall()