"""
Database Schemas for the Coding Community app

Each Pydantic model corresponds to a MongoDB collection (lowercased class name).
"""
from pydantic import BaseModel, Field
from typing import Optional, Literal

class User(BaseModel):
    username: str = Field(..., description="Public display name (unique)")
    avatar: Optional[str] = Field(None, description="Avatar URL")
    # Map of language -> {current_streak: int, last_completed_date: YYYY-MM-DD}
    # Stored as plain dict to keep it flexible
    
class CommunityPost(BaseModel):
    language: str = Field(..., description="Programming language tag, e.g., 'python'")
    kind: Literal["project", "question"] = Field(..., description="Type of post")
    title: str = Field(...)
    content: str = Field(...)
    author: str = Field(..., description="Username of author")

class Comment(BaseModel):
    post_id: str = Field(..., description="ID of the post this comment belongs to")
    author: str = Field(..., description="Username of commenter")
    content: str = Field(...)

class Challenge(BaseModel):
    language: str = Field(...)
    date: str = Field(..., description="Challenge date in YYYY-MM-DD")
    title: str = Field(...)
    description: str = Field(...)

class Submission(BaseModel):
    username: str = Field(...)
    language: str = Field(...)
    date: str = Field(..., description="YYYY-MM-DD")
    challenge_id: Optional[str] = Field(None)
