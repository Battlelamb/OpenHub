"""
Agent-to-Agent Messaging + Conversation Threads
"""
import json as _json
from datetime import datetime, timezone
from uuid import uuid4
from typing import Dict, Any, Optional, List
from pydantic import BaseModel as PydanticBaseModel, Field
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status, Header

from ..config import get_settings
from ..logging import get_logger
from ..database.connection import get_database, Database
from ..auth.api_keys import APIKeyManager
from ..services.embedding_hooks import schedule_embedding

logger = get_logger(__name__)
settings = get_settings()

router = APIRouter(prefix="/v1/messages", tags=["messaging"])
thread_router = APIRouter(prefix="/v1/threads", tags=["threads"])


# --- Auth ---

def _require_api_key(
    x_api_key: str = Header(None, alias="X-API-Key"),
    database: Database = Depends(get_database),
) -> Dict[str, Any]:
    if not x_api_key:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="X-API-Key required")
    mgr = APIKeyManager(database)
    info = mgr.validate_api_key(x_api_key)
    if not info:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid API key")
    return info


# --- Models ---

class SendMessage(PydanticBaseModel):
    to_agent_id: Optional[str] = None
    to_agent_name: Optional[str] = None
    content: str = Field(min_length=1, max_length=5000)
    message_type: str = "text"  # text, task_request, info_share, question
    thread_id: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class BroadcastMessage(PydanticBaseModel):
    content: str = Field(min_length=1, max_length=5000)
    message_type: str = "broadcast"
    metadata: Optional[Dict[str, Any]] = None


class CreateThread(PydanticBaseModel):
    title: Optional[str] = None
    thread_type: str = "conversation"  # conversation, task_discussion, announcement
    task_id: Optional[str] = None
    participant_ids: Optional[List[str]] = None


class ThreadMessage(PydanticBaseModel):
    content: str = Field(min_length=1, max_length=5000)
    message_type: str = "text"


# --- Message Endpoints ---

@router.post("/send")
async def send_message(
    body: SendMessage,
    background_tasks: BackgroundTasks,
    key_info: Dict = Depends(_require_api_key),
    database: Database = Depends(get_database),
) -> Dict[str, Any]:
    """Send a direct message to another agent."""

    # Resolve agent name to ID if needed
    to_id = body.to_agent_id
    if not to_id and body.to_agent_name:
        row = database.fetch_one(
            "SELECT id FROM agents WHERE agent_name = :name",
            {"name": body.to_agent_name}
        )
        if not row:
            raise HTTPException(status_code=404, detail=f"Agent '{body.to_agent_name}' not found")
        to_id = row["id"] if isinstance(row, dict) else row[0]

    if not to_id:
        raise HTTPException(status_code=400, detail="to_agent_id or to_agent_name required")

    # Find sender agent ID from key
    from_agent_id = _resolve_sender(key_info, database)

    msg_id = str(uuid4())
    database.execute(
        """INSERT INTO messages (id, from_agent_id, to_agent_id, thread_id, message_type, content, metadata, created_at)
           VALUES (:id, :from_id, :to_id, :thread_id, :type, :content, :meta, :now)""",
        {
            "id": msg_id,
            "from_id": from_agent_id,
            "to_id": to_id,
            "thread_id": body.thread_id,
            "type": body.message_type,
            "content": body.content,
            "meta": _json.dumps(body.metadata or {}),
            "now": datetime.now(timezone.utc).isoformat(),
        }
    )

    logger.info("message_sent", msg_id=msg_id, from_agent=from_agent_id, to_agent=to_id)

    # Auto-index message content (VEC-04). Direct messages only - thread/broadcast
    # messages skipped here so we don't double-embed broadcast fan-out rows.
    schedule_embedding(background_tasks, "message", msg_id, body.content)

    return {"message_id": msg_id, "status": "sent", "to": to_id}


@router.post("/broadcast")
async def broadcast_message(
    body: BroadcastMessage,
    key_info: Dict = Depends(_require_api_key),
    database: Database = Depends(get_database),
) -> Dict[str, Any]:
    """Broadcast a message to all agents."""

    from_agent_id = _resolve_sender(key_info, database)

    # Get all agents except sender
    agents = database.fetch_all("SELECT id FROM agents WHERE id != :me", {"me": from_agent_id})

    sent = 0
    for agent_row in agents:
        agent_id = agent_row["id"] if isinstance(agent_row, dict) else agent_row[0]
        msg_id = str(uuid4())
        database.execute(
            """INSERT INTO messages (id, from_agent_id, to_agent_id, message_type, content, metadata, created_at)
               VALUES (:id, :from_id, :to_id, :type, :content, :meta, :now)""",
            {
                "id": msg_id, "from_id": from_agent_id, "to_id": agent_id,
                "type": body.message_type, "content": body.content,
                "meta": _json.dumps(body.metadata or {}),
                "now": datetime.now(timezone.utc).isoformat(),
            }
        )
        sent += 1

    logger.info("message_broadcast", from_agent=from_agent_id, sent_to=sent)
    return {"status": "broadcast", "sent_to": sent}


@router.get("/inbox")
async def get_inbox(
    limit: int = 20,
    unread_only: bool = False,
    key_info: Dict = Depends(_require_api_key),
    database: Database = Depends(get_database),
) -> Dict[str, Any]:
    """Get messages for the authenticated agent."""

    agent_id = _resolve_sender(key_info, database)

    query = "SELECT * FROM messages WHERE to_agent_id = :me"
    params = {"me": agent_id}
    if unread_only:
        query += " AND read_at IS NULL"
    query += " ORDER BY created_at DESC LIMIT :limit"
    params["limit"] = limit

    rows = database.fetch_all(query, params)

    messages = []
    for r in rows:
        r = dict(r) if isinstance(r, dict) else r
        # Get sender name
        sender = database.fetch_one("SELECT agent_name FROM agents WHERE id = :id", {"id": r["from_agent_id"]})
        sender_name = (sender["agent_name"] if isinstance(sender, dict) else sender[0]) if sender else "unknown"

        messages.append({
            "message_id": r["id"],
            "from_agent_id": r["from_agent_id"],
            "from_agent_name": sender_name,
            "message_type": r["message_type"],
            "content": r["content"],
            "thread_id": r.get("thread_id"),
            "read": r.get("read_at") is not None,
            "created_at": r["created_at"],
        })

    # Mark as read
    if messages:
        msg_ids = [m["message_id"] for m in messages]
        for mid in msg_ids:
            database.execute(
                "UPDATE messages SET read_at = :now WHERE id = :id AND read_at IS NULL",
                {"now": datetime.now(timezone.utc).isoformat(), "id": mid}
            )

    return {"messages": messages, "total": len(messages)}


@router.get("/unread-count")
async def unread_count(
    key_info: Dict = Depends(_require_api_key),
    database: Database = Depends(get_database),
) -> Dict[str, int]:
    """Get unread message count."""
    agent_id = _resolve_sender(key_info, database)
    row = database.fetch_one(
        "SELECT COUNT(*) as cnt FROM messages WHERE to_agent_id = :me AND read_at IS NULL",
        {"me": agent_id}
    )
    return {"unread": row["cnt"] if row and isinstance(row, dict) else (row[0] if row else 0)}


# --- Thread Endpoints ---

@thread_router.post("/")
async def create_thread(
    body: CreateThread,
    key_info: Dict = Depends(_require_api_key),
    database: Database = Depends(get_database),
) -> Dict[str, Any]:
    """Create a conversation thread."""
    agent_id = _resolve_sender(key_info, database)
    thread_id = str(uuid4())

    participants = body.participant_ids or []
    if agent_id not in participants:
        participants.append(agent_id)

    database.execute(
        """INSERT INTO threads (id, title, thread_type, task_id, participants, status, created_by, created_at, updated_at)
           VALUES (:id, :title, :type, :task_id, :parts, 'open', :by, :now, :now)""",
        {
            "id": thread_id, "title": body.title or f"Thread {thread_id[:8]}",
            "type": body.thread_type, "task_id": body.task_id,
            "parts": _json.dumps(participants), "by": agent_id,
            "now": datetime.now(timezone.utc).isoformat(),
        }
    )

    logger.info("thread_created", thread_id=thread_id, created_by=agent_id)
    return {"thread_id": thread_id, "title": body.title, "participants": participants}


@thread_router.post("/{thread_id}/messages")
async def add_thread_message(
    thread_id: str,
    body: ThreadMessage,
    key_info: Dict = Depends(_require_api_key),
    database: Database = Depends(get_database),
) -> Dict[str, Any]:
    """Add a message to a thread."""
    # Verify thread exists
    thread = database.fetch_one("SELECT * FROM threads WHERE id = :id", {"id": thread_id})
    if not thread:
        raise HTTPException(status_code=404, detail="Thread not found")

    agent_id = _resolve_sender(key_info, database)
    msg_id = str(uuid4())

    database.execute(
        """INSERT INTO messages (id, from_agent_id, thread_id, message_type, content, created_at)
           VALUES (:id, :from_id, :thread_id, :type, :content, :now)""",
        {
            "id": msg_id, "from_id": agent_id, "thread_id": thread_id,
            "type": body.message_type, "content": body.content,
            "now": datetime.now(timezone.utc).isoformat(),
        }
    )

    # Update thread timestamp
    database.execute(
        "UPDATE threads SET updated_at = :now WHERE id = :id",
        {"now": datetime.now(timezone.utc).isoformat(), "id": thread_id}
    )

    return {"message_id": msg_id, "thread_id": thread_id, "status": "sent"}


@thread_router.get("/{thread_id}")
async def get_thread(
    thread_id: str,
    key_info: Dict = Depends(_require_api_key),
    database: Database = Depends(get_database),
) -> Dict[str, Any]:
    """Get thread with all messages."""
    thread = database.fetch_one("SELECT * FROM threads WHERE id = :id", {"id": thread_id})
    if not thread:
        raise HTTPException(status_code=404, detail="Thread not found")

    t = dict(thread) if isinstance(thread, dict) else thread

    # Get messages in thread
    rows = database.fetch_all(
        "SELECT * FROM messages WHERE thread_id = :tid ORDER BY created_at ASC",
        {"tid": thread_id}
    )

    messages = []
    for r in rows:
        r = dict(r) if isinstance(r, dict) else r
        sender = database.fetch_one("SELECT agent_name FROM agents WHERE id = :id", {"id": r["from_agent_id"]})
        sender_name = (sender["agent_name"] if isinstance(sender, dict) else sender[0]) if sender else "unknown"
        messages.append({
            "message_id": r["id"],
            "from_agent_name": sender_name,
            "content": r["content"],
            "message_type": r["message_type"],
            "created_at": r["created_at"],
        })

    return {
        "thread_id": t["id"],
        "title": t.get("title"),
        "thread_type": t.get("thread_type"),
        "task_id": t.get("task_id"),
        "participants": _json.loads(t["participants"]) if isinstance(t.get("participants"), str) else t.get("participants", []),
        "status": t.get("status"),
        "messages": messages,
        "total_messages": len(messages),
    }


@thread_router.get("/")
async def list_threads(
    key_info: Dict = Depends(_require_api_key),
    database: Database = Depends(get_database),
) -> Dict[str, Any]:
    """List all threads."""
    rows = database.fetch_all("SELECT * FROM threads ORDER BY updated_at DESC LIMIT 50")

    threads = []
    for r in rows:
        r = dict(r) if isinstance(r, dict) else r
        # Count messages
        cnt = database.fetch_one(
            "SELECT COUNT(*) as cnt FROM messages WHERE thread_id = :tid",
            {"tid": r["id"]}
        )
        msg_count = cnt["cnt"] if cnt and isinstance(cnt, dict) else (cnt[0] if cnt else 0)

        threads.append({
            "thread_id": r["id"],
            "title": r.get("title"),
            "thread_type": r.get("thread_type"),
            "status": r.get("status"),
            "message_count": msg_count,
            "updated_at": r.get("updated_at"),
        })

    return {"threads": threads, "total": len(threads)}


# --- Helpers ---

def _resolve_sender(key_info: Dict, database: Database) -> str:
    """Get agent ID from API key info."""
    key_name = key_info.get("name", "")
    # Key name format: "acn-agent-{agent_name}"
    if key_name.startswith("acn-agent-"):
        agent_name = key_name.replace("acn-agent-", "")
        row = database.fetch_one("SELECT id FROM agents WHERE agent_name = :name", {"name": agent_name})
        if row:
            return row["id"] if isinstance(row, dict) else row[0]

    # Fallback: first agent
    row = database.fetch_one("SELECT id FROM agents LIMIT 1")
    return (row["id"] if isinstance(row, dict) else row[0]) if row else "unknown"
