import os
from datetime import datetime, timezone, timedelta
from typing import List, Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from database import db, create_document, get_documents

app = FastAPI(title="Coding Community API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --------------------------
# Utility
# --------------------------
LANGUAGES = [
    "python",
    "javascript",
    "java",
    "go",
    "rust",
    "cpp",
]


def today_str():
    return datetime.now(timezone.utc).astimezone().strftime("%Y-%m-%d")


# --------------------------
# Models
# --------------------------
class CreatePost(BaseModel):
    language: str
    kind: str
    title: str
    content: str
    author: str


class CreateComment(BaseModel):
    post_id: str
    author: str
    content: str


class CreateSubmission(BaseModel):
    username: str
    language: str
    code: Optional[str] = None


# --------------------------
# Routes
# --------------------------
@app.get("/")
def root():
    return {"message": "Coding Community Backend Running"}


@app.get("/languages")
def get_languages():
    return {"languages": LANGUAGES}


@app.get("/challenges/{language}")
def get_daily_challenge(language: str):
    if language not in LANGUAGES:
        raise HTTPException(status_code=404, detail="Language not supported")

    # Deterministic daily challenge based on date + language
    date = today_str()
    seed = sum(ord(c) for c in (language + date))
    titles = [
        "Two Sum Variant",
        "String Compression",
        "Balanced Brackets",
        "LRU Cache Mini",
        "Matrix Spiral",
        "Binary Tree Paths",
        "Anagram Groups",
        "Word Ladder Mini",
    ]
    descriptions = [
        "Solve the task and share your approach.",
        "Write clean, idiomatic code and discuss trade-offs.",
        "Consider time/space complexity and edge cases.",
    ]
    title = titles[seed % len(titles)]
    description = descriptions[seed % len(descriptions)]

    # Upsert-like behavior: ensure a challenge document exists (optional for display)
    # We'll just return the computed challenge; persistence is not required for viewing
    return {
        "date": date,
        "language": language,
        "title": f"{language.title()} Daily: {title}",
        "description": description,
        "id": f"{language}-{date}",
    }


@app.post("/posts")
def create_post(payload: CreatePost):
    if payload.language not in LANGUAGES:
        raise HTTPException(status_code=400, detail="Unsupported language")
    if payload.kind not in ("project", "question"):
        raise HTTPException(status_code=400, detail="Invalid kind")

    doc_id = create_document("communitypost", payload.model_dump())
    return {"id": doc_id}


@app.get("/posts")
def list_posts(language: Optional[str] = None, kind: Optional[str] = None, limit: int = 25):
    filt = {}
    if language:
        filt["language"] = language
    if kind:
        filt["kind"] = kind
    items = get_documents("communitypost", filt, limit)
    # Convert ObjectId to string if present
    for it in items:
        it["_id"] = str(it.get("_id"))
    return {"items": items}


@app.post("/comments")
def add_comment(payload: CreateComment):
    # naive existence check skipped for brevity
    doc_id = create_document("comment", payload.model_dump())
    return {"id": doc_id}


@app.get("/comments/{post_id}")
def list_comments(post_id: str, limit: int = 100):
    items = get_documents("comment", {"post_id": post_id}, limit)
    for it in items:
        it["_id"] = str(it.get("_id"))
    return {"items": items}


@app.post("/submit")
def submit_solution(payload: CreateSubmission):
    if payload.language not in LANGUAGES:
        raise HTTPException(status_code=400, detail="Unsupported language")

    # Record today's submission for the language
    date = today_str()
    sub_doc = {
        "username": payload.username,
        "language": payload.language,
        "date": date,
    }
    create_document("submission", sub_doc)

    # Update streaks: compute consecutive days up to today
    # Fetch last 60 days submissions for this user/language
    start_date = (datetime.now(timezone.utc).astimezone() - timedelta(days=60)).strftime("%Y-%m-%d")
    items = get_documents(
        "submission",
        {"username": payload.username, "language": payload.language, "date": {"$gte": start_date}},
        1000,
    )
    days = sorted({it["date"] for it in items})
    # compute streak ending today
    streak = 0
    current = datetime.strptime(date, "%Y-%m-%d").date()
    sset = set(days)
    while current.strftime("%Y-%m-%d") in sset:
        streak += 1
        current = current - timedelta(days=1)

    return {"ok": True, "date": date, "streak": streak}


@app.get("/streak/{username}/{language}")
def get_streak(username: str, language: str):
    if language not in LANGUAGES:
        raise HTTPException(status_code=400, detail="Unsupported language")
    date = today_str()
    start_date = (datetime.now(timezone.utc).astimezone() - timedelta(days=60)).strftime("%Y-%m-%d")
    items = get_documents(
        "submission",
        {"username": username, "language": language, "date": {"$gte": start_date}},
        1000,
    )
    days = sorted({it["date"] for it in items})
    streak = 0
    current = datetime.strptime(date, "%Y-%m-%d").date()
    sset = set(days)
    while current.strftime("%Y-%m-%d") in sset:
        streak += 1
        current = current - timedelta(days=1)
    return {"streak": streak, "days": days}


# Keep the diagnostic endpoint
@app.get("/test")
def test_database():
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

    import os as _os
    response["database_url"] = "✅ Set" if _os.getenv("DATABASE_URL") else "❌ Not Set"
    response["database_name"] = "✅ Set" if _os.getenv("DATABASE_NAME") else "❌ Not Set"

    return response


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
