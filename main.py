import os
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from bson import ObjectId

from database import db, create_document, get_documents
from schemas import ChatSession, Message

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def serialize_doc(doc: Dict[str, Any]) -> Dict[str, Any]:
    out = {}
    for k, v in doc.items():
        if k == "_id":
            out["id"] = str(v)
        elif isinstance(v, ObjectId):
            out[k] = str(v)
        else:
            out[k] = v
    return out


def basic_ai_reply(user_text: str, history: List[Dict[str, str]]) -> str:
    """
    A simple, dependency-free assistant.
    - Greets on hello
    - Answers simple FAQs
    - Mirrors questions with a helpful tone
    """
    text = user_text.strip().lower()
    if any(greet in text for greet in ["hello", "hi", "hey"]):
        return "Hi! I'm your AI helper. Ask me anything, and I'll do my best to assist."
    if "help" in text:
        return "You can ask me general questions. I'll store our conversation so you can come back later."
    if text.endswith("?"):
        return "That's a great question! Here's a simple take: " + user_text.rstrip(" ?!")
    if "thank" in text:
        return "You're welcome!"
    # Light transformation
    if len(user_text.split()) <= 3:
        return f"You said: '{user_text}'. Could you share a bit more detail?"
    return (
        "Here's what I understood: "
        + user_text
        + "\nIf you want, I can also summarize or clarify specific parts."
    )


@app.get("/")
def read_root():
    return {"message": "AI Chatbot Backend is running"}


@app.get("/test")
def test_database():
    """Test endpoint to check if database is available and accessible"""
    response = {
        "backend": "✅ Running",
        "database": "❌ Not Available",
        "database_url": None,
        "database_name": None,
        "connection_status": "Not Connected",
        "collections": [],
    }

    try:
        if db is not None:
            response["database"] = "✅ Available"
            response["database_url"] = "✅ Configured"
            response["database_name"] = db.name if hasattr(db, "name") else "✅ Connected"
            response["connection_status"] = "Connected"
            try:
                collections = db.list_collection_names()
                response["collections"] = collections[:10]
                response["database"] = "✅ Connected & Working"
            except Exception as e:
                response["database"] = f"⚠️  Connected but Error: {str(e)[:50]}"
        else:
            response["database"] = "⚠️  Available but not initialized"
    except Exception as e:
        response["database"] = f"❌ Error: {str(e)[:50]}"

    response["database_url"] = "✅ Set" if os.getenv("DATABASE_URL") else "❌ Not Set"
    response["database_name"] = "✅ Set" if os.getenv("DATABASE_NAME") else "❌ Not Set"
    return response


# --------- Chatbot API ---------
class CreateSessionBody(BaseModel):
    title: Optional[str] = "New Chat"
    system_prompt: Optional[str] = None
    user_id: Optional[str] = None


@app.post("/chat/session")
def create_session(body: CreateSessionBody):
    session = ChatSession(
        title=body.title or "New Chat",
        user_id=body.user_id,
        system_prompt=body.system_prompt,
    )
    session_id = create_document("chatsession", session)
    # Optionally create a system message
    if body.system_prompt:
        create_document(
            "message",
            Message(session_id=session_id, role="system", content=body.system_prompt),
        )
    return {"id": session_id, "title": session.title}


@app.get("/chat/sessions")
def list_sessions(limit: int = 50):
    docs = db["chatsession"].find({}).sort("created_at", -1).limit(limit)
    return [serialize_doc(d) for d in docs]


@app.get("/chat/{session_id}/messages")
def list_messages(session_id: str, limit: int = 200):
    try:
        # Validate session exists
        _ = db["chatsession"].find_one({"_id": ObjectId(session_id)})
        if _ is None:
            raise HTTPException(status_code=404, detail="Session not found")
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid session id")

    docs = (
        db["message"].find({"session_id": session_id}).sort("created_at", 1).limit(limit)
    )
    return [serialize_doc(d) for d in docs]


class UserMessageBody(BaseModel):
    content: str


@app.post("/chat/{session_id}/message")
def add_message(session_id: str, body: UserMessageBody):
    # Validate session id
    try:
        _ = db["chatsession"].find_one({"_id": ObjectId(session_id)})
        if _ is None:
            raise HTTPException(status_code=404, detail="Session not found")
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid session id")

    # Persist user message
    create_document(
        "message",
        Message(session_id=session_id, role="user", content=body.content),
    )

    # Gather short history for simple reply heuristic
    hist_docs = db["message"].find({"session_id": session_id}).sort("created_at", 1).limit(20)
    history = [
        {"role": d.get("role", "user"), "content": d.get("content", "")} for d in hist_docs
    ]

    assistant_text = basic_ai_reply(body.content, history)

    # Persist assistant message
    msg_id = create_document(
        "message",
        Message(session_id=session_id, role="assistant", content=assistant_text),
    )

    return {"id": msg_id, "role": "assistant", "content": assistant_text}


if __name__ == "__main__":
    import uvicorn

    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
