import logging

from pywacli.db.engine import fetchall, fetchone


logger = logging.getLogger(__name__)


def get_total_messages():
    return fetchone("SELECT COUNT(*) FROM messages")[0]


def get_total_statuses():
    return fetchone("SELECT COUNT(*) FROM statuses")[0]


def get_total_reactions():
    return fetchone("SELECT COUNT(*) FROM reactions")[0]


def get_total_media():
    return fetchone("SELECT COUNT(*) FROM media")[0]


def get_recent_messages(limit=10):
    return fetchall(
        "SELECT push_name, text FROM messages ORDER BY rowid DESC LIMIT ?",
        [limit]
    )


def get_media_types():
    rows = fetchall("SELECT DISTINCT media_type FROM media WHERE media_type IS NOT NULL")
    return [row[0] for row in rows]


def get_media_by_type(media_type=None, limit=50):
    if media_type:
        return fetchall("""
            SELECT m.media_id, m.media_type, m.file_name, m.push_name,
                   m.from_me, m.timestamp, m.file_path, h.sync
            FROM media m
            LEFT JOIN media_handshake h ON m.media_id = h.media_id
            WHERE m.media_type = ?
            ORDER BY m.timestamp DESC
            LIMIT ?
        """, [media_type, limit])
    else:
        return fetchall("""
            SELECT m.media_id, m.media_type, m.file_name, m.push_name,
                   m.from_me, m.timestamp, m.file_path, h.sync
            FROM media m
            LEFT JOIN media_handshake h ON m.media_id = h.media_id
            ORDER BY m.timestamp DESC
            LIMIT ?
        """, [limit])


def get_media_by_id(media_id):
    return fetchone("""
        SELECT m.media_id, m.media_type, m.file_name, m.push_name,
               m.from_me, m.timestamp, m.file_path, m.media_mimetype,
               h.sync, h.failure_reason
        FROM media m
        LEFT JOIN media_handshake h ON m.media_id = h.media_id
        WHERE m.media_id = ?
    """, [media_id])


def get_messages_by_contact(phone_number, limit=50, include_sent=False):
    where_extra = "" if include_sent else "AND from_me = 0"
    sql = f"""
        SELECT id, text, from_me, push_name, phone_number, timestamp, jid
        FROM messages
        WHERE 1=1
          {where_extra}
          AND (
            phone_number = ?
            OR jid LIKE ?
            OR push_name = ?
          )
        ORDER BY timestamp ASC
        LIMIT ?
    """
    jid_pattern = f"{phone_number}%"
    return fetchall(sql, [phone_number, jid_pattern, phone_number, limit])


def get_latest_message_id(phone_number):
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
    row = fetchone(sql, [phone_number, jid_pattern, phone_number])
    return row[0] if row else None


def get_new_messages_after(phone_number, last_message_id, include_sent=False):
    where_extra = "" if include_sent else "AND from_me = 0"
    sql = f"""
        SELECT id, text, from_me, push_name, phone_number, timestamp, jid
        FROM messages
        WHERE 1=1
          {where_extra}
          AND (
            phone_number = ?
            OR jid LIKE ?
            OR push_name = ?
          )
        ORDER BY timestamp ASC
    """
    jid_pattern = f"{phone_number}%"
    all_messages = fetchall(sql, [phone_number, jid_pattern, phone_number])

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
    return fetchall("""
        SELECT DISTINCT phone_number, push_name, jid
        FROM messages
        WHERE from_me = 0
          AND (phone_number != '' OR push_name != '')
        ORDER BY timestamp DESC
    """)
