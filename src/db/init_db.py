from src.db.database import (
    create_table,
    create_edit_table,
    create_status_table,
    create_reactions_table,
    create_media_table,
    create_media_handshake_table,
    create_conversations_table,
)


def init_database():

    create_table()
    create_edit_table()
    create_status_table()
    create_reactions_table()
    create_media_table()
    create_media_handshake_table()
    create_conversations_table()