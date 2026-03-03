"""
iMessage MCP Server

Exposes macOS Messages data and send capability via Model Context Protocol.
Requires macOS with Full Disk Access granted to the host process.

Tools:
    search_messages  - Retrieve messages by contact with date filtering
    list_conversations - Recent conversations with preview and metadata
    get_thread       - Full conversation transcript with pagination
    get_attachments  - Copy received files to a destination directory
    send_message     - Send via iMessage with SMS fallback
    search_contacts  - Fuzzy match against macOS AddressBook

Environment:
    IMESSAGE_DB_PATH       - Override chat.db location (default: ~/Library/Messages/chat.db)
    IMESSAGE_ATTACHMENT_DIR - Where to copy attachments (default: ~/Downloads/imessage-attachments)
"""

import glob
import os
import plistlib
import re
import shutil
import sqlite3
import subprocess
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Optional

from fastmcp import FastMCP

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

DB_PATH = Path(os.environ.get(
    "IMESSAGE_DB_PATH",
    Path.home() / "Library" / "Messages" / "chat.db",
))

ATTACHMENT_DIR = Path(os.environ.get(
    "IMESSAGE_ATTACHMENT_DIR",
    Path.home() / "Downloads" / "imessage-attachments",
))

# Apple epoch: 2001-01-01 00:00:00 UTC, stored as nanoseconds
_APPLE_EPOCH_OFFSET = 978307200
_NS = 1_000_000_000

# ---------------------------------------------------------------------------
# Server
# ---------------------------------------------------------------------------

mcp = FastMCP("iMessage")

# ---------------------------------------------------------------------------
# Database helpers
# ---------------------------------------------------------------------------


def _connect() -> sqlite3.Connection:
    """Return a read-only connection to chat.db."""
    if not DB_PATH.exists():
        raise FileNotFoundError(
            f"Messages database not found at {DB_PATH}. "
            "Ensure this is macOS and Full Disk Access is granted."
        )
    conn = sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    return conn


def _query(sql: str, params: tuple = ()) -> list[dict[str, Any]]:
    """Execute a query and return rows as dicts."""
    conn = _connect()
    try:
        rows = conn.execute(sql, params).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def _apple_ts_to_iso(ns_timestamp: int) -> str:
    """Convert Apple nanosecond timestamp to ISO 8601 string."""
    if ns_timestamp is None or ns_timestamp == 0:
        return None
    seconds = ns_timestamp / _NS + _APPLE_EPOCH_OFFSET
    dt = datetime.fromtimestamp(seconds, tz=timezone.utc)
    return dt.isoformat()


def _iso_to_apple_ns(iso_date: str) -> int:
    """Convert ISO date string (YYYY-MM-DD) to Apple nanosecond timestamp."""
    dt = datetime.fromisoformat(iso_date).replace(tzinfo=timezone.utc)
    seconds = (dt - datetime(2001, 1, 1, tzinfo=timezone.utc)).total_seconds()
    return int(seconds * _NS)


def _hours_ago_apple_ns(hours: int) -> int:
    """Apple nanosecond timestamp for N hours ago."""
    dt = datetime.now(timezone.utc) - timedelta(hours=hours)
    seconds = (dt - datetime(2001, 1, 1, tzinfo=timezone.utc)).total_seconds()
    return int(seconds * _NS)


# ---------------------------------------------------------------------------
# Text extraction
# ---------------------------------------------------------------------------


def _extract_text(
    text: Optional[str],
    attributed_body: Optional[bytes],
    summary_info: Optional[bytes],
) -> Optional[str]:
    """Extract message text from the three possible storage columns."""
    if text:
        return text

    if attributed_body:
        try:
            idx = attributed_body.find(b"NSString")
            if idx == -1:
                return None
            marker = b"\x01+"
            start = attributed_body.find(marker, idx)
            if start == -1:
                return None
            start += len(marker)
            while start < len(attributed_body) and attributed_body[start] < 0x20:
                start += 1
            end = attributed_body.find(b"\x86", start)
            if end == -1:
                end = len(attributed_body)
            decoded = attributed_body[start:end].decode("utf-8", errors="replace")
            cleaned = "".join(c for c in decoded if c == "\n" or c >= " ")
            cleaned = cleaned.replace("\ufffd", "").replace("\ufffc", "").strip()
            return cleaned or None
        except Exception:
            pass

    if summary_info:
        try:
            plist = plistlib.loads(summary_info)
            if "ec" in plist and "0" in plist["ec"]:
                latest = plist["ec"]["0"][-1]
                if "t" in latest:
                    return _extract_text(None, latest["t"], None)
        except Exception:
            pass

    return None


# ---------------------------------------------------------------------------
# Phone normalization
# ---------------------------------------------------------------------------


def _normalize_phone(phone: str) -> str:
    """Strip to digits only."""
    return "".join(c for c in phone if c.isdigit())


def _phone_formats(normalized: str) -> list[str]:
    """Generate format variants for handle lookup."""
    formats = [normalized]
    if len(normalized) == 10:
        formats.append(f"+1{normalized}")
        formats.append(f"1{normalized}")
    elif len(normalized) == 11 and normalized.startswith("1"):
        formats.append(f"+{normalized}")
        formats.append(normalized[1:])
    return formats


def _resolve_identifier(identifier: str) -> list[str]:
    """Resolve a contact identifier to handle ID strings for DB lookup."""
    identifier = identifier.strip()
    if "@" in identifier:
        return [identifier]
    digits = _normalize_phone(identifier)
    if digits:
        return _phone_formats(digits)
    return [identifier]


def _find_handle_ids(identifier: str) -> list[int]:
    """Find all handle ROWIDs matching an identifier."""
    variants = _resolve_identifier(identifier)
    placeholders = ",".join("?" for _ in variants)
    rows = _query(
        f"SELECT ROWID FROM handle WHERE id IN ({placeholders})",
        tuple(variants),
    )
    return [r["ROWID"] for r in rows]


# ---------------------------------------------------------------------------
# Contact resolution (AddressBook)
# ---------------------------------------------------------------------------

_CONTACTS_CACHE: Optional[dict] = None
_CACHE_TIME: float = 0
_CACHE_TTL = 300  # seconds


def _load_contacts() -> dict[str, str]:
    """Load contacts from macOS AddressBook SQLite databases.

    Returns a dict mapping normalized phone/email -> display name.
    """
    global _CONTACTS_CACHE, _CACHE_TIME
    import time

    now = time.time()
    if _CONTACTS_CACHE is not None and (now - _CACHE_TIME) < _CACHE_TTL:
        return _CONTACTS_CACHE

    contacts: dict[str, str] = {}
    home = os.path.expanduser("~")
    pattern = os.path.join(
        home,
        "Library/Application Support/AddressBook/Sources/*/AddressBook-v22.abcddb",
    )
    for db_path in glob.glob(pattern):
        try:
            conn = sqlite3.connect(db_path)
            conn.row_factory = sqlite3.Row
            rows = conn.execute("""
                SELECT
                    ZABCDRECORD.ZFIRSTNAME AS first_name,
                    ZABCDRECORD.ZLASTNAME AS last_name,
                    ZABCDPHONENUMBER.ZFULLNUMBER AS phone
                FROM ZABCDRECORD
                LEFT JOIN ZABCDPHONENUMBER
                    ON ZABCDRECORD.Z_PK = ZABCDPHONENUMBER.ZOWNER
                WHERE ZABCDPHONENUMBER.ZFULLNUMBER IS NOT NULL
            """).fetchall()
            conn.close()
            for row in rows:
                first = row["first_name"] or ""
                last = row["last_name"] or ""
                name = f"{first} {last}".strip()
                phone = _normalize_phone(row["phone"] or "")
                if phone and name:
                    contacts[phone] = name
        except Exception:
            continue

    # Also load email-based contacts
    for db_path in glob.glob(pattern):
        try:
            conn = sqlite3.connect(db_path)
            conn.row_factory = sqlite3.Row
            rows = conn.execute("""
                SELECT
                    ZABCDRECORD.ZFIRSTNAME AS first_name,
                    ZABCDRECORD.ZLASTNAME AS last_name,
                    ZABCDEMAILADDRESS.ZADDRESS AS email
                FROM ZABCDRECORD
                LEFT JOIN ZABCDEMAILADDRESS
                    ON ZABCDRECORD.Z_PK = ZABCDEMAILADDRESS.ZOWNER
                WHERE ZABCDEMAILADDRESS.ZADDRESS IS NOT NULL
            """).fetchall()
            conn.close()
            for row in rows:
                first = row["first_name"] or ""
                last = row["last_name"] or ""
                name = f"{first} {last}".strip()
                email = (row["email"] or "").lower()
                if email and name:
                    contacts[email] = name
        except Exception:
            continue

    _CONTACTS_CACHE = contacts
    _CACHE_TIME = now
    return contacts


def _resolve_contact_name(handle_id: str) -> str:
    """Best-effort contact name resolution for a handle ID string."""
    contacts = _load_contacts()
    # Try direct match
    if handle_id in contacts:
        return contacts[handle_id]
    # Try phone normalization
    normalized = _normalize_phone(handle_id)
    if normalized in contacts:
        return contacts[normalized]
    # Try last N digits
    for key, name in contacts.items():
        if len(normalized) >= 10 and key.endswith(normalized[-10:]):
            return name
    return handle_id


# ---------------------------------------------------------------------------
# Attachment helpers
# ---------------------------------------------------------------------------


def _convert_heic(src: Path, dest_dir: Path) -> Optional[Path]:
    """Convert HEIC to JPEG using macOS sips (no external deps)."""
    dest = dest_dir / (src.stem + ".jpeg")
    try:
        subprocess.run(
            ["sips", "-s", "format", "jpeg", str(src), "--out", str(dest)],
            check=True,
            capture_output=True,
        )
        return dest
    except Exception:
        return None


def _copy_attachment(src: Path, dest_dir: Path) -> Optional[dict]:
    """Copy a single attachment to dest_dir. Returns metadata dict or None."""
    if not src.exists():
        return None
    dest_dir.mkdir(parents=True, exist_ok=True)

    if src.suffix.lower() == ".heic":
        dest = _convert_heic(src, dest_dir)
        if dest:
            return {"path": str(dest), "mime_type": "image/jpeg", "original": str(src)}
        return None

    dest = dest_dir / src.name
    # Avoid overwriting by appending counter
    counter = 1
    while dest.exists():
        dest = dest_dir / f"{src.stem}_{counter}{src.suffix}"
        counter += 1
    shutil.copy2(src, dest)

    # Infer mime type from extension
    ext_map = {
        ".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".png": "image/png",
        ".gif": "image/gif", ".pdf": "application/pdf", ".mp4": "video/mp4",
        ".mov": "video/quicktime", ".m4a": "audio/mp4", ".mp3": "audio/mpeg",
        ".txt": "text/plain", ".doc": "application/msword",
        ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        ".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        ".zip": "application/zip",
    }
    mime = ext_map.get(src.suffix.lower(), "application/octet-stream")
    return {"path": str(dest), "mime_type": mime, "original": str(src), "size_bytes": dest.stat().st_size}


def _get_message_attachments(message_rowid: int) -> list[dict]:
    """Query attachment metadata for a message. Does not copy files."""
    rows = _query("""
        SELECT a.ROWID, a.filename, a.mime_type, a.transfer_name, a.total_bytes,
               a.is_outgoing, a.uti
        FROM attachment a
        JOIN message_attachment_join maj ON a.ROWID = maj.attachment_id
        WHERE maj.message_id = ?
    """, (message_rowid,))

    attachments = []
    for r in rows:
        filename = r["filename"]
        if filename and filename.startswith("~"):
            filename = os.path.expanduser(filename)
        attachments.append({
            "rowid": r["ROWID"],
            "filename": filename,
            "transfer_name": r["transfer_name"],
            "mime_type": r["mime_type"],
            "size_bytes": r["total_bytes"],
            "is_outgoing": bool(r["is_outgoing"]),
        })
    return attachments


# ---------------------------------------------------------------------------
# Message formatting
# ---------------------------------------------------------------------------


def _format_message(row: dict, include_attachments: bool = True) -> dict:
    """Format a raw message row into a clean dict."""
    text = _extract_text(
        row.get("text"),
        row.get("attributedBody"),
        row.get("message_summary_info"),
    )
    handle_id_str = row.get("handle_id_str", "")
    sender = "me" if row.get("is_from_me") else _resolve_contact_name(handle_id_str)

    msg = {
        "rowid": row["ROWID"],
        "date": _apple_ts_to_iso(row.get("date")),
        "sender": sender,
        "is_from_me": bool(row.get("is_from_me")),
        "text": text,
    }

    if include_attachments:
        atts = _get_message_attachments(row["ROWID"])
        if atts:
            msg["attachments"] = atts

    # Group chat context
    room = row.get("cache_roomnames")
    if room:
        msg["group"] = room

    return msg


# ---------------------------------------------------------------------------
# Tools
# ---------------------------------------------------------------------------


@mcp.tool()
def search_messages(
    contact: str,
    hours: int = 72,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    query: Optional[str] = None,
    limit: int = 100,
) -> dict[str, Any]:
    """Search messages by contact with optional date range and text filter.

    Args:
        contact: Phone number, email address, or contact name.
        hours: Look-back window in hours (default 72). Ignored if start_date is set.
        start_date: ISO date (YYYY-MM-DD) for range start. Overrides hours.
        end_date: ISO date (YYYY-MM-DD) for range end. Defaults to now.
        query: Text substring to filter messages (case-insensitive).
        limit: Maximum messages to return (default 100).

    Returns:
        Dict with messages list, total_count, and any warnings.
    """
    warnings = []

    # Resolve contact to handle IDs
    handle_ids = _find_handle_ids(contact)

    # If no handle found by identifier, try name-based contact search
    if not handle_ids:
        contacts = _load_contacts()
        contact_lower = contact.lower()
        matched_ids = []
        for key, name in contacts.items():
            if contact_lower in name.lower():
                matched_ids.extend(_find_handle_ids(key))
        handle_ids = list(set(matched_ids))
        if not handle_ids:
            return {"messages": [], "total_count": 0, "warnings": [f"No handles found for '{contact}'"]}

    # Build time filter
    if start_date:
        ts_min = _iso_to_apple_ns(start_date)
    else:
        ts_min = _hours_ago_apple_ns(hours)

    ts_max = _iso_to_apple_ns(end_date) if end_date else None

    # Query messages
    placeholders = ",".join("?" for _ in handle_ids)
    sql = f"""
        SELECT m.ROWID, m.date, m.text, m.attributedBody, m.message_summary_info,
               m.is_from_me, m.handle_id, m.cache_roomnames, h.id AS handle_id_str
        FROM message m
        LEFT JOIN handle h ON m.handle_id = h.ROWID
        WHERE m.handle_id IN ({placeholders})
          AND m.date > ?
    """
    params: list = list(handle_ids) + [ts_min]

    if ts_max:
        sql += " AND m.date < ?"
        params.append(ts_max)

    sql += " ORDER BY m.date DESC LIMIT ?"
    params.append(limit)

    rows = _query(sql, tuple(params))

    # Format and optionally filter
    messages = []
    for row in rows:
        msg = _format_message(row)
        if query and msg.get("text"):
            if query.lower() not in msg["text"].lower():
                continue
        messages.append(msg)

    # Reverse to chronological
    messages.reverse()

    return {"messages": messages, "total_count": len(messages), "warnings": warnings}


@mcp.tool()
def list_conversations(hours: int = 168, limit: int = 30) -> dict[str, Any]:
    """List recent conversations with last message preview.

    Args:
        hours: Look-back window (default 168 = 7 days).
        limit: Maximum conversations to return (default 30).

    Returns:
        Dict with conversations list containing chat_id, display_name,
        participants, last_message preview, and last_date.
    """
    ts_min = _hours_ago_apple_ns(hours)

    rows = _query("""
        SELECT
            c.ROWID AS chat_rowid,
            c.chat_identifier,
            c.display_name,
            c.room_name,
            MAX(m.date) AS last_date,
            COUNT(m.ROWID) AS message_count
        FROM chat c
        JOIN chat_message_join cmj ON c.ROWID = cmj.chat_id
        JOIN message m ON cmj.message_id = m.ROWID
        WHERE m.date > ?
        GROUP BY c.ROWID
        ORDER BY last_date DESC
        LIMIT ?
    """, (ts_min, limit))

    conversations = []
    for row in rows:
        chat_id = row["chat_identifier"]
        display = row["display_name"] or ""

        # Resolve participant names for 1:1 chats
        if not display:
            display = _resolve_contact_name(chat_id.replace("iMessage;-;", "").replace("SMS;-;", ""))

        # Get last message preview
        preview_rows = _query("""
            SELECT m.text, m.attributedBody, m.message_summary_info, m.is_from_me
            FROM message m
            JOIN chat_message_join cmj ON m.ROWID = cmj.message_id
            WHERE cmj.chat_id = ?
            ORDER BY m.date DESC LIMIT 1
        """, (row["chat_rowid"],))

        preview = ""
        if preview_rows:
            preview = _extract_text(
                preview_rows[0].get("text"),
                preview_rows[0].get("attributedBody"),
                preview_rows[0].get("message_summary_info"),
            ) or ""
            if len(preview) > 120:
                preview = preview[:120] + "..."

        conversations.append({
            "chat_id": chat_id,
            "display_name": display,
            "last_date": _apple_ts_to_iso(row["last_date"]),
            "message_count": row["message_count"],
            "preview": preview,
            "is_group": bool(row["room_name"]),
        })

    return {"conversations": conversations, "total": len(conversations)}


@mcp.tool()
def get_thread(
    chat_id: str,
    limit: int = 50,
    before_date: Optional[str] = None,
) -> dict[str, Any]:
    """Get full conversation transcript for a chat.

    Args:
        chat_id: The chat_identifier from list_conversations (e.g. "iMessage;-;+15551234567").
        limit: Maximum messages (default 50). Use for pagination.
        before_date: ISO datetime for backward pagination. Returns messages before this date.

    Returns:
        Dict with messages list and pagination metadata.
    """
    # Find chat ROWID
    chat_rows = _query(
        "SELECT ROWID FROM chat WHERE chat_identifier = ?", (chat_id,)
    )
    if not chat_rows:
        return {"messages": [], "error": f"Chat not found: {chat_id}"}

    chat_rowid = chat_rows[0]["ROWID"]

    sql = """
        SELECT m.ROWID, m.date, m.text, m.attributedBody, m.message_summary_info,
               m.is_from_me, m.handle_id, m.cache_roomnames, h.id AS handle_id_str
        FROM message m
        JOIN chat_message_join cmj ON m.ROWID = cmj.message_id
        LEFT JOIN handle h ON m.handle_id = h.ROWID
        WHERE cmj.chat_id = ?
    """
    params: list = [chat_rowid]

    if before_date:
        sql += " AND m.date < ?"
        params.append(_iso_to_apple_ns(before_date))

    sql += " ORDER BY m.date DESC LIMIT ?"
    params.append(limit)

    rows = _query(sql, tuple(params))
    messages = [_format_message(row) for row in rows]
    messages.reverse()

    oldest = messages[0]["date"] if messages else None

    return {
        "messages": messages,
        "total_count": len(messages),
        "oldest_date": oldest,
        "has_more": len(messages) == limit,
        "chat_id": chat_id,
    }


@mcp.tool()
def get_attachments(
    contact: str,
    hours: int = 168,
    dest_dir: Optional[str] = None,
    mime_filter: Optional[str] = None,
) -> dict[str, Any]:
    """Retrieve file attachments from a conversation and copy them locally.

    Copies received files to a destination directory, converting HEIC images
    to JPEG automatically. Use this to access documents, photos, and other
    files shared via iMessage.

    Args:
        contact: Phone number, email, or contact name.
        hours: Look-back window (default 168 = 7 days).
        dest_dir: Destination directory. Defaults to IMESSAGE_ATTACHMENT_DIR env var
                  or ~/Downloads/imessage-attachments.
        mime_filter: Optional MIME type prefix to filter (e.g. "image/", "application/pdf").

    Returns:
        Dict with list of copied files (path, mime_type, size, original_message).
    """
    destination = Path(dest_dir) if dest_dir else ATTACHMENT_DIR

    # Get messages with attachments
    handle_ids = _find_handle_ids(contact)
    if not handle_ids:
        contacts = _load_contacts()
        for key, name in contacts.items():
            if contact.lower() in name.lower():
                handle_ids.extend(_find_handle_ids(key))
        handle_ids = list(set(handle_ids))

    if not handle_ids:
        return {"files": [], "error": f"No handles found for '{contact}'"}

    ts_min = _hours_ago_apple_ns(hours)
    placeholders = ",".join("?" for _ in handle_ids)

    rows = _query(f"""
        SELECT a.filename, a.mime_type, a.transfer_name, a.total_bytes,
               a.is_outgoing, m.date, m.text, m.is_from_me, h.id AS handle_id_str
        FROM attachment a
        JOIN message_attachment_join maj ON a.ROWID = maj.attachment_id
        JOIN message m ON maj.message_id = m.ROWID
        LEFT JOIN handle h ON m.handle_id = h.ROWID
        WHERE m.handle_id IN ({placeholders})
          AND m.date > ?
        ORDER BY m.date DESC
    """, tuple(handle_ids) + (ts_min,))

    files = []
    for row in rows:
        mime = row.get("mime_type") or ""
        if mime_filter and not mime.startswith(mime_filter):
            continue

        filename = row.get("filename")
        if not filename:
            continue
        if filename.startswith("~"):
            filename = os.path.expanduser(filename)
        src = Path(filename)

        result = _copy_attachment(src, destination)
        if result:
            result["date"] = _apple_ts_to_iso(row.get("date"))
            result["from"] = "me" if row.get("is_from_me") else _resolve_contact_name(row.get("handle_id_str", ""))
            result["transfer_name"] = row.get("transfer_name")
            files.append(result)

    return {"files": files, "total": len(files), "destination": str(destination)}


@mcp.tool()
def send_message(
    recipient: str,
    message: str,
    group_chat: bool = False,
) -> dict[str, Any]:
    """Send an iMessage (with automatic SMS fallback for phone numbers).

    Args:
        recipient: Phone number, email, or chat_id for group chats.
        message: Message text to send.
        group_chat: Set True when sending to a group chat ID.

    Returns:
        Dict with status and delivery details.
    """
    safe_message = message.replace("\\", "\\\\").replace('"', '\\"')
    safe_recipient = recipient.replace("\\", "\\\\").replace('"', '\\"')

    if group_chat:
        script = f"""
        tell application "Messages"
            try
                set targetChat to chat "{safe_recipient}"
                send "{safe_message}" to targetChat
                return "success:group"
            on error errMsg
                return "error:" & errMsg
            end try
        end tell
        """
    else:
        # Try iMessage first, fall back to SMS for phone numbers
        script = f"""
        tell application "Messages"
            try
                set targetService to 1st service whose service type = iMessage
                set targetBuddy to participant "{safe_recipient}" of targetService
                send "{safe_message}" to targetBuddy
                return "success:iMessage"
            on error iMsgErr
                try
                    set smsService to first account whose service type = SMS and enabled is true
                    send "{safe_message}" to participant "{safe_recipient}" of smsService
                    return "success:SMS"
                on error smsErr
                    return "error:iMessage: " & iMsgErr & " | SMS: " & smsErr
                end try
            end try
        end tell
        """

    proc = subprocess.Popen(
        ["osascript", "-e", script],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    out, err = proc.communicate(timeout=30)
    result = out.decode("utf-8").strip()

    if result.startswith("success:"):
        service = result.split(":")[1]
        display = _resolve_contact_name(recipient)
        return {"status": "sent", "service": service, "recipient": display}

    error_detail = result.replace("error:", "") if result.startswith("error:") else (err.decode("utf-8") or result)
    return {"status": "failed", "error": error_detail, "recipient": recipient}


@mcp.tool()
def search_contacts(
    name: str,
    limit: int = 10,
) -> dict[str, Any]:
    """Fuzzy search contacts by name.

    Args:
        name: Name or partial name to search for.
        limit: Maximum results (default 10).

    Returns:
        Dict with matching contacts (name, phone/email, score).
    """
    contacts = _load_contacts()
    query_lower = name.lower()
    query_tokens = query_lower.split()

    scored: list[tuple[str, str, float]] = []

    for key, contact_name in contacts.items():
        name_lower = contact_name.lower()
        name_tokens = name_lower.split()

        # Scoring: exact substring > token match > prefix match
        score = 0.0

        if query_lower == name_lower:
            score = 1.0
        elif query_lower in name_lower:
            score = 0.9
        else:
            # Token-level matching
            token_scores = []
            for qt in query_tokens:
                best = 0.0
                for nt in name_tokens:
                    if qt == nt:
                        best = max(best, 0.95)
                    elif nt.startswith(qt):
                        best = max(best, 0.85)
                    elif qt.startswith(nt):
                        best = max(best, 0.75)
                    else:
                        # Simple character overlap ratio
                        common = len(set(qt) & set(nt))
                        total = max(len(set(qt) | set(nt)), 1)
                        ratio = common / total
                        if ratio > 0.5:
                            best = max(best, ratio * 0.6)
                token_scores.append(best)
            if token_scores:
                score = sum(token_scores) / len(token_scores)

        if score >= 0.5:
            scored.append((key, contact_name, score))

    scored.sort(key=lambda x: x[2], reverse=True)

    results = []
    seen_names = set()
    for key, contact_name, score in scored[:limit * 2]:
        if contact_name in seen_names:
            continue
        seen_names.add(contact_name)
        results.append({
            "name": contact_name,
            "identifier": key,
            "score": round(score, 2),
        })
        if len(results) >= limit:
            break

    return {"contacts": results, "total": len(results)}


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    mcp.run()
