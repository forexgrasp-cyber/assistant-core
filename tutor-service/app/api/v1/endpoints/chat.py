"""
Chat endpoints for Tutor Service
"""
from typing import List, Optional
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Query, WebSocket, WebSocketDisconnect
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc
from sqlalchemy.orm import selectinload
import json

from app.core.database import get_db
from app.models.user import ChatSession, User
from app.schemas.user import ChatMessageBase, ChatSessionBase, ChatSessionCreate, ChatSessionResponse
from app.api.v1.endpoints.auth import get_current_active_user

router = APIRouter()


# WebSocket connection manager
class ConnectionManager:
    def __init__(self):
        self.active_connections: dict[int, List[WebSocket]] = {}
    
    async def connect(self, user_id: int, websocket: WebSocket):
        await websocket.accept()
        if user_id not in self.active_connections:
            self.active_connections[user_id] = []
        self.active_connections[user_id].append(websocket)
    
    def disconnect(self, user_id: int, websocket: WebSocket):
        if user_id in self.active_connections:
            self.active_connections[user_id].remove(websocket)
            if not self.active_connections[user_id]:
                del self.active_connections[user_id]
    
    async def send_personal_message(self, user_id: int, message: dict):
        if user_id in self.active_connections:
            for connection in self.active_connections[user_id]:
                try:
                    await connection.send_json(message)
                except:
                    pass
    
    async def broadcast(self, message: dict):
        for user_id, connections in self.active_connections.items():
            for connection in connections:
                try:
                    await connection.send_json(message)
                except:
                    pass


manager = ConnectionManager()


@router.get("/sessions", response_model=List[ChatSessionResponse])
async def list_chat_sessions(
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """List user's chat sessions"""
    result = await db.execute(
        select(ChatSession)
        .where(ChatSession.user_id == current_user.id)
        .order_by(desc(ChatSession.started_at))
        .offset(offset)
        .limit(limit)
    )
    return result.scalars().all()


@router.post("/sessions", response_model=ChatSessionResponse, status_code=201)
async def create_chat_session(
    session_data: ChatSessionCreate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Create new chat session"""
    session = ChatSession(
        user_id=current_user.id,
        session_id=session_data.session_id,
        lesson_id=session_data.lesson_id,
        messages=[msg.model_dump() for msg in session_data.messages],
    )
    db.add(session)
    await db.commit()
    await db.refresh(session)
    return session


@router.get("/sessions/{session_id}", response_model=ChatSessionResponse)
async def get_chat_session(
    session_id: str,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Get chat session by ID"""
    result = await db.execute(
        select(ChatSession).where(
            ChatSession.user_id == current_user.id,
            ChatSession.session_id == session_id
        )
    )
    session = result.scalar_one_or_none()
    
    if not session:
        raise HTTPException(status_code=404, detail="Chat session not found")
    
    return session


@router.put("/sessions/{session_id}/messages")
async def add_message_to_session(
    session_id: str,
    message: ChatMessageBase,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Add message to chat session"""
    result = await db.execute(
        select(ChatSession).where(
            ChatSession.user_id == current_user.id,
            ChatSession.session_id == session_id
        )
    )
    session = result.scalar_one_or_none()
    
    if not session:
        raise HTTPException(status_code=404, detail="Chat session not found")
    
    session.messages.append(message.model_dump())
    session.message_count = len(session.messages)
    await db.commit()
    await db.refresh(session)
    return session


@router.delete("/sessions/{session_id}")
async def delete_chat_session(
    session_id: str,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Delete chat session"""
    result = await db.execute(
        select(ChatSession).where(
            ChatSession.user_id == current_user.id,
            ChatSession.session_id == session_id
        )
    )
    session = result.scalar_one_or_none()
    
    if not session:
        raise HTTPException(status_code=404, detail="Chat session not found")
    
    await db.delete(session)
    await db.commit()
    return {"message": "Chat session deleted"}


@router.websocket("/ws/{user_id}")
async def websocket_endpoint(
    websocket: WebSocket,
    user_id: int,
    token: str = Query(...),
    db: AsyncSession = Depends(get_db)
):
    """WebSocket endpoint for real-time chat"""
    # Verify token
    from app.api.v1.endpoints.auth import get_current_user
    try:
        user = await get_current_user(token, db)
        if user.id != user_id:
            await websocket.close(code=4003)
            return
    except:
        await websocket.close(code=4001)
        return
    
    await manager.connect(user_id, websocket)
    
    try:
        while True:
            data = await websocket.receive_json()
            
            # Handle different message types
            message_type = data.get("type", "message")
            
            if message_type == "message":
                # Process user message and get AI response
                user_message = data.get("content", "")
                
                # Save user message
                # In production, this would call the tutor agent
                ai_response = await _get_ai_response(user_message, user_id, db)
                
                # Send AI response
                await websocket.send_json({
                    "type": "response",
                    "content": ai_response["content"],
                    "metadata": ai_response.get("metadata", {}),
                    "timestamp": datetime.utcnow().isoformat(),
                })
            
            elif message_type == "audio":
                # Handle audio message
                audio_data = data.get("audio")
                # Process speech-to-text
                transcript = await _process_audio(audio_data)
                
                # Get AI response
                ai_response = await _get_ai_response(transcript, user_id, db)
                
                await websocket.send_json({
                    "type": "response",
                    "content": ai_response["content"],
                    "metadata": {"transcript": transcript, **ai_response.get("metadata", {})},
                    "timestamp": datetime.utcnow().isoformat(),
                })
            
            elif message_type == "ping":
                await websocket.send_json({"type": "pong"})
    
    except WebSocketDisconnect:
        manager.disconnect(user_id, websocket)
    except Exception as e:
        await websocket.send_json({"type": "error", "message": str(e)})
        manager.disconnect(user_id, websocket)


async def _get_ai_response(message: str, user_id: int, db: AsyncSession) -> dict:
    """Get AI tutor response"""
    # In production, this would call the tutor agent service
    # For now, return mock response
    responses = [
        "That's a great question! Let me help you with that.",
        "Excellent! You're making good progress.",
        "I understand. Let me explain that differently.",
        "Good try! The correct form would be...",
        "Let's practice that together.",
    ]
    
    import random
    return {
        "content": random.choice(responses),
        "metadata": {
            "suggestions": ["Tell me more", "Give me an example", "Practice pronunciation"],
            "corrections": [],
        }
    }


async def _process_audio(audio_data: str) -> str:
    """Process audio data to text"""
    # In production, this would use speech-to-text service
    return "I'd like to practice Spanish conversation"