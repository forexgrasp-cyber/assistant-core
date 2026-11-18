"""
API v1 Router for Tutor Service
"""
from fastapi import APIRouter

from app.api.v1.endpoints import auth, users, lessons, practice, progress, vocabulary, chat, voice, generation, llm, gamification, trust

api_router = APIRouter()

# Auth routes
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])

# User routes
api_router.include_router(users.router, prefix="/users", tags=["users"])

# Lesson routes
api_router.include_router(lessons.router, prefix="/lessons", tags=["lessons"])

# Practice routes
api_router.include_router(practice.router, prefix="/practice", tags=["practice"])

# Progress routes
api_router.include_router(progress.router, prefix="/progress", tags=["progress"])

# Vocabulary routes
api_router.include_router(vocabulary.router, prefix="/vocabulary", tags=["vocabulary"])

# Chat routes
api_router.include_router(chat.router, prefix="/chat", tags=["chat"])

# Voice settings routes
api_router.include_router(voice.router, prefix="/voice", tags=["voice"])

# Lesson Generation routes
api_router.include_router(generation.router, prefix="/generation", tags=["generation"])

# LLM Configuration routes
api_router.include_router(llm.router, prefix="/llm", tags=["llm"])

# Gamification routes
api_router.include_router(gamification.router, prefix="/gamification", tags=["gamification"])

# Trust & Social Proof routes
api_router.include_router(trust.router, prefix="/trust", tags=["trust"])