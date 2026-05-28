# PyWacli — Python WhatsApp CLI

Real-time WhatsApp ingestion and monitoring system built with Python, [Baileys](https://github.com/WhiskeySockets/Baileys), WebSockets, SQLite, [Rich](https://github.com/Textualize/rich), and S3-compatible storage. Captures messages, edits, reactions, statuses, images, videos, and documents with a live terminal dashboard, media syncing, and conversation tracking.

## Features

- **Live Dashboard** — Real-time terminal UI with message feed and database statistics (Rich + `Live`)
- **WhatsApp Ingestion** — Full event capture via Baileys (messages, edits, reactions, statuses, media)
- **Media Storage** — Automatically sync media to S3, Cloudflare R2, or local filesystem with per-media-type filtering
- **Media Viewer** — Browse, inspect, and download stored media by type (image/video/document)
- **Interactive Setup** — Guided configuration wizard for WhatsApp connection, storage providers, DB path, dashboard theme, and logging
- **SQLite Database** — 7 tables: messages, edits, statuses, reactions, media, media_handshake, conversations
- **CLI Menu** — Simple numbered menu for all operations
- **Multiple Themes** — Default, Dark, and Light dashboard themes

## Architecture

```
WhatsApp (mobile)
    |
    | Baileys library
    v
Node.js (baileys_service.js)
    |-- Downloads media to media/ folder
    |-- Normalizes events
    |
    v
WebSocket Server (ws_server.js :3000)
    |
    +---> Python Client (websocket_services.py)
              |
              +---> SQLite (messages, media, etc.)
              +---> S3 / R2 / Local (media files)
              +---> Rich Dashboard (dashboard.py)
```

## Prerequisites

- Python 3.10+
- Node.js 18+
- npm
- (Optional) Localstack or S3-compatible storage for media sync

## Installation

```bash
# Clone the repository
git clone <repo-url> && cd pywacli

# Python dependencies
python -m venv .venv
.venv\Scripts\activate     # Windows
# source .venv/bin/activate  # Linux/Mac
pip install -r requirements.txt

# Node.js dependencies
npm install
```

## Configuration

Run the setup wizard to configure everything interactively:

```bash
python main.py setup
```

Or configure individual sections later via the menu.

### Configuration file location

```
~/.pywacli/config.json
```

### Sections

| Section | Description | Defaults |
|---|---|---|
| `whatsapp` | WebSocket URL, auto-reconnect | `ws://localhost:3000`, `true` |
| `media_storage` | One or more storage entries (S3/R2/Local) with media type toggles | Empty |
| `database` | SQLite file path | `./pywacli.db` |
| `dashboard` | Refresh interval, theme | `1s`, `default` |
| `logging` | Log level, output file | `INFO`, `./pywacli.log` |

### Example media storage entry

```json
{
  "store_image": true,
  "store_video": true,
  "store_document": true,
  "provider": "s3",
  "endpoint": "http://localhost:4566",
  "access_key_id": "test",
  "secret_access_key": "test",
  "region": "us-east-1",
  "bucket_name": "whatsapp-media",
  "local_path": null,
  "id": 1
}
```

## Usage

### Start the application

```bash
python main.py
```

This shows the main menu:

```
  1   Dashboard     Launch the WhatsApp dashboard
  2   Setup         Run the interactive configuration wizard
  3   Config        Open configuration menu
  4   Run           Start baileys + websocket services
  5   Media         Browse stored media
  0   Exit          Exit the application
```

### CLI commands

All commands are also available directly:

| Command | Description |
|---|---|
| `python main.py dashboard` | Launch the live dashboard |
| `python main.py setup` | Run configuration wizard |
| `python main.py config` | Open configuration menu |
| `python main.py run` | Start baileys + websocket in separate terminals |
| `python main.py media` | Browse and download stored media |

Or using the module directly:

```bash
python -m src.cli [command]
```

### Run services

Opens two new terminal windows:

```bash
python main.py run
```

- **Terminal 1:** `node src/services/baileys_service.js` (WhatsApp client)
- **Terminal 2:** `python src/services/websocket_service.py` (Event listener)

After starting, scan the QR code in the Node.js terminal with WhatsApp to connect.

### Media viewer

Browse and download stored media files:

```
Media Viewer
  1   Images
  2   Videos
  3   Documents
  4   All Media
  0   Back
```

Select a media ID to view full details (type, filename, sender, timestamp, sync status) and download the file from S3 or local storage.

## Events

| Event | Description |
|---|---|
| `message.new` | New text message |
| `message.update` | Message edited |
| `message.reaction` | Emoji reaction |
| `status.new` | Status/story update |
| `conversation.new` | Unified conversation event |
| `media.new` | Image/video/document received |

## Database tables

| Table | Contents |
|---|---|
| `messages` | Text messages with sender metadata |
| `message_edits` | Edit history |
| `statuses` | WhatsApp status updates |
| `reactions` | Emoji reactions |
| `media` | Media metadata (type, filename, path, sender) |
| `media_handshake` | Per-entry sync status (success/failure reason) |
| `conversations` | Unified conversation log |

## Project structure

```
pywacli/
├── main.py                          # Entry point
├── package.json                     # Node.js dependencies
├── requirements.txt                 # Python dependencies
├── src/
│   ├── cli/
│   │   ├── __init__.py
│   │   ├── __main__.py              # Typer CLI app & menu
│   │   ├── app.py                   # App orchestrator
│   │   ├── config_manager.py        # ~/.pywacli/config.json management
│   │   ├── configuration.py         # Interactive setup wizard
│   │   └── ui/
│   │       ├── dashboard.py         # Live Rich dashboard
│   │       ├── media_viewer.py      # Media browser & downloader
│   │       ├── tables.py            # (reserved)
│   │       └── live_feed.py         # (reserved)
│   ├── db/
│   │   ├── database.py              # SQLite schema & CRUD
│   │   ├── init_db.py               # Table initializer
│   │   ├── retriver_db.py           # Read queries
│   │   └── bucket_connection.py     # S3/R2 connection manager
│   ├── services/
│   │   ├── baileys_service.js       # WhatsApp Baileys client
│   │   ├── ws_server.js             # WebSocket server
│   │   ├── session_manager.js       # Baileys socket singleton
│   │   └── websocket_services.py    # Python WebSocket consumer
│   └── utils/
│       ├── bucket_utils.py          # S3 upload/download helpers
│       └── local_utils.py           # Local file storage
├── .env.example                     # Environment template
└── LICENSE                          # MIT
```

## License

MIT
