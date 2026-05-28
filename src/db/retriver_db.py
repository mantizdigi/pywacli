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