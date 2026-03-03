# iMessage MCP Server

An MCP server that exposes macOS iMessage data — read, search, send messages, and retrieve file attachments delivered via iMessage.

## Requirements

- macOS (iMessage uses `~/Library/Messages/chat.db`)
- Full Disk Access granted to your terminal or host application
- Python 3.10+

## Setup

```bash
# Install
pip install -e .

# Or run directly
pip install fastmcp phonenumbers
python server.py
```

### Claude Code / Claude Desktop

Add to your MCP configuration:

```json
{
  "mcpServers": {
    "imessage": {
      "command": "python",
      "args": ["/path/to/mcp/imessage/server.py"],
      "env": {
        "IMESSAGE_ATTACHMENT_DIR": "~/Downloads/imessage-attachments"
      }
    }
  }
}
```

### Full Disk Access

The server reads `~/Library/Messages/chat.db` directly. macOS requires Full Disk Access for any process accessing this file.

**System Settings > Privacy & Security > Full Disk Access** — add your terminal app (Terminal, iTerm, Cursor, Claude Desktop, etc.).

## Tools

### `search_messages`

Retrieve messages by contact with optional date range and text filter.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `contact` | str | required | Phone number, email, or contact name |
| `hours` | int | 72 | Look-back window (ignored if `start_date` set) |
| `start_date` | str | None | ISO date YYYY-MM-DD |
| `end_date` | str | None | ISO date YYYY-MM-DD |
| `query` | str | None | Text substring filter |
| `limit` | int | 100 | Max messages |

### `list_conversations`

Recent conversations with last message preview, participant resolution, and message counts.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `hours` | int | 168 | Look-back window (default 7 days) |
| `limit` | int | 30 | Max conversations |

### `get_thread`

Full conversation transcript for a specific chat, with backward pagination.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `chat_id` | str | required | Chat identifier from `list_conversations` |
| `limit` | int | 50 | Messages per page |
| `before_date` | str | None | ISO datetime for pagination |

### `get_attachments`

Copy file attachments from a conversation to a local directory. Converts HEIC images to JPEG using macOS `sips` (no external dependencies).

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `contact` | str | required | Phone number, email, or contact name |
| `hours` | int | 168 | Look-back window |
| `dest_dir` | str | env default | Override destination directory |
| `mime_filter` | str | None | Filter by MIME prefix (e.g. `"image/"`, `"application/pdf"`) |

### `send_message`

Send a message via iMessage with automatic SMS fallback for phone numbers.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `recipient` | str | required | Phone, email, or chat_id |
| `message` | str | required | Message text |
| `group_chat` | bool | False | True for group chat IDs |

### `search_contacts`

Fuzzy search the macOS AddressBook by name.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `name` | str | required | Name or partial name |
| `limit` | int | 10 | Max results |

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `IMESSAGE_DB_PATH` | `~/Library/Messages/chat.db` | Override database location |
| `IMESSAGE_ATTACHMENT_DIR` | `~/Downloads/imessage-attachments` | Default attachment destination |

## Architecture

Single-file Python server (`server.py`) using [FastMCP](https://github.com/jlowin/fastmcp). No external database dependencies — reads SQLite directly.

**Read path**: Direct SQLite queries against `chat.db` (read-only connection). Handles Apple's nanosecond-since-2001 timestamps, `attributedBody` binary parsing for older messages, and `message_summary_info` plist parsing for edited messages.

**Write path**: AppleScript via `osascript` to drive Messages.app. Tries iMessage first, falls back to SMS for phone numbers.

**Contact resolution**: Queries macOS AddressBook SQLite databases directly. Caches results for 5 minutes. Supports phone and email lookups.

**Attachment handling**: Queries the `attachment` + `message_attachment_join` tables. Copies files to a configurable destination. Converts HEIC to JPEG using macOS `sips` (built-in, no ImageMagick needed).

## Acknowledgments

Built on patterns from:
- [hannesrudolph/imessage-query-fastmcp-mcp-server](https://github.com/hannesrudolph/imessage-query-fastmcp-mcp-server) — attachment handling, text extraction
- [carterlasalle/mac_messages_mcp](https://github.com/carterlasalle/mac_messages_mcp) — contact resolution, send mechanism, query patterns

## License

MIT
