"""
Database Schemas

Define your MongoDB collection schemas here using Pydantic models.
These schemas are used for data validation in your application.

Each Pydantic model represents a collection in your database.
Model name is converted to lowercase for the collection name:
- User -> "user" collection
- Product -> "product" collection
- BlogPost -> "blogpost" collection
"""

from pydantic import BaseModel, Field
from typing import Optional, Literal

# Example schemas (you can keep or remove as needed)
class User(BaseModel):
    """
    Users collection schema
    Collection name: "user" (lowercase of class name)
    """
    name: str = Field(..., description="Full name")
    email: str = Field(..., description="Email address")
    address: str = Field(..., description="Address")
    age: Optional[int] = Field(None, ge=0, le=120, description="Age in years")
    is_active: bool = Field(True, description="Whether user is active")

class Product(BaseModel):
    """
    Products collection schema
    Collection name: "product" (lowercase of class name)
    """
    title: str = Field(..., description="Product title")
    description: Optional[str] = Field(None, description="Product description")
    price: float = Field(..., ge=0, description="Price in dollars")
    category: str = Field(..., description="Product category")
    in_stock: bool = Field(True, description="Whether product is in stock")

# Chatbot-related schemas
class ChatSession(BaseModel):
    """
    Chat sessions created when a user starts a new conversation
    Collection name: "chatsession"
    """
    title: str = Field(..., description="Session title shown in the sidebar")
    user_id: Optional[str] = Field(None, description="Optional user id if you support auth")
    system_prompt: Optional[str] = Field(
        None,
        description="Optional system prompt to steer the assistant behavior"
    )

class Message(BaseModel):
    """
    Chat messages that belong to a session
    Collection name: "message"
    """
    session_id: str = Field(..., description="ID of the chat session this message belongs to")
    role: Literal["system", "user", "assistant"] = Field(..., description="Who sent the message")
    content: str = Field(..., description="Message text content")
