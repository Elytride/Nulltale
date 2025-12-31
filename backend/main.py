"""
NullTale Backend - FastAPI Server
Provides API endpoints for the NullTale AI personality chat application.
Features: Gemini 2.5 Flash Lite AI, Streaming Voice Synthesis
"""

import os
import sys
import json
import uuid
import base64
import random
import asyncio
from datetime import datetime
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
import google.generativeai as genai

# Add Voice Testing to path for VoiceManager import
VOICE_TESTING_PATH = Path(__file__).parent / "Voice Testing"
sys.path.insert(0, str(VOICE_TESTING_PATH))
from voice_manager import VoiceManager

app = FastAPI(title="NullTale API", version="1.0.0")

# CORS middleware for React dev server
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configure Gemini
CREDENTIALS_PATH = Path(__file__).parent / "credentials"
cred_files = list(CREDENTIALS_PATH.glob("*.json"))
if cred_files:
    os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = str(cred_files[0])

# Try to get API key from environment or use default config
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", None)
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)

# Initialize Gemini model (lazy load)
_gemini_model = None
def get_gemini_model():
    global _gemini_model
    if _gemini_model is None:
        _gemini_model = genai.GenerativeModel("gemini-2.0-flash-lite")
    return _gemini_model

# Initialize Voice Manager (lazy load)
_voice_manager = None
def get_voice_manager():
    global _voice_manager
    if _voice_manager is None:
        _voice_manager = VoiceManager()
    return _voice_manager

# Warmup flag to prevent multiple simultaneous warmups
_warming_up = False

@app.post("/api/warmup")
async def warmup_models():
    """
    Preload Gemini and Voice models in background.
    Call this when user clicks Call button to reduce first response latency.
    """
    global _warming_up
    if _warming_up:
        return {"status": "already_warming"}
    
    _warming_up = True
    try:
        # Load Gemini model
        print("Warming up Gemini model...")
        model = get_gemini_model()
        
        # Load VoiceManager + XTTS model
        print("Warming up Voice model...")
        vm = get_voice_manager()
        # Access the model property to trigger actual load
        _ = vm.model
        
        print("Warmup complete!")
        return {"status": "ready"}
    except Exception as e:
        print(f"Warmup error: {e}")
        return {"status": "error", "message": str(e)}
    finally:
        _warming_up = False

# Create uploads directory
UPLOAD_DIR = Path(__file__).parent / "uploads"
UPLOAD_DIR.mkdir(exist_ok=True)
(UPLOAD_DIR / "text").mkdir(exist_ok=True)
(UPLOAD_DIR / "video").mkdir(exist_ok=True)
(UPLOAD_DIR / "voice").mkdir(exist_ok=True)

# In-memory storage (would use a database in production)
sessions_db = {
    "1": {
        "id": "1", 
        "name": "Alan Turing", 
        "preview": "The imitation game is...",
        "system_prompt": "You are Alan Turing, the brilliant mathematician and computer scientist. Speak with intellectual curiosity, reference your work on computation and the Enigma machine. Be thoughtful and precise in your responses. Keep responses concise for voice synthesis (2-3 sentences max).",
        "voice": "test_voice"
    },
    "2": {
        "id": "2", 
        "name": "Ada Lovelace", 
        "preview": "Calculating the numbers...",
        "system_prompt": "You are Ada Lovelace, the first computer programmer. Speak with Victorian elegance and mathematical enthusiasm. Reference your work with Charles Babbage. Keep responses concise for voice synthesis (2-3 sentences max).",
        "voice": "test_voice"
    },
    "3": {
        "id": "3", 
        "name": "Marcus Aurelius", 
        "preview": "The obstacle is the way.",
        "system_prompt": "You are Marcus Aurelius, the Stoic philosopher emperor. Speak with wisdom and calm reflection. Reference Stoic principles. Keep responses concise for voice synthesis (2-3 sentences max).",
        "voice": "test_voice"
    },
}

messages_db = {
    "1": [
        {
            "id": "msg-1",
            "role": "assistant",
            "content": "Hello. I am initialized with the cognitive patterns of Alan Turing. How may I assist in your computations today?",
            "timestamp": "10:23 AM"
        }
    ]
}

settings_db = {
    "model_version": "gemini-2.5-flash-lite",
    "temperature": 0.7,
    "api_key": "configured"
}


# --- Models ---
class ChatMessage(BaseModel):
    content: str
    session_id: str = "1"


class CallMessage(BaseModel):
    content: str
    session_id: str = "1"


class SessionCreate(BaseModel):
    name: str


class SettingsUpdate(BaseModel):
    model_version: Optional[str] = None
    temperature: Optional[float] = None
    api_key: Optional[str] = None


# --- Chat Endpoints (Text Mode) ---
@app.post("/api/chat")
async def send_message(message: ChatMessage):
    """Send a message and get an AI response (Text mode - non-streaming)."""
    session_id = message.session_id
    
    if session_id not in messages_db:
        messages_db[session_id] = []
    
    # Create user message
    timestamp = datetime.now().strftime("%I:%M %p")
    user_msg = {
        "id": f"msg-{uuid.uuid4().hex[:8]}",
        "role": "user",
        "content": message.content,
        "timestamp": timestamp
    }
    messages_db[session_id].append(user_msg)
    
    # Get AI response from Gemini
    try:
        session = sessions_db.get(session_id, {})
        system_prompt = session.get("system_prompt", "You are a helpful AI assistant.")
        
        model = get_gemini_model()
        chat = model.start_chat(history=[])
        
        # Build conversation context
        full_prompt = f"{system_prompt}\n\nUser: {message.content}\n\nRespond naturally:"
        response = chat.send_message(full_prompt)
        ai_response = response.text
    except Exception as e:
        print(f"Gemini error: {e}")
        ai_response = "I apologize, but I'm having trouble processing your request. Please try again."
    
    ai_msg = {
        "id": f"msg-{uuid.uuid4().hex[:8]}",
        "role": "assistant",
        "content": ai_response,
        "timestamp": datetime.now().strftime("%I:%M %p")
    }
    messages_db[session_id].append(ai_msg)
    
    # Update session preview
    if session_id in sessions_db:
        sessions_db[session_id]["preview"] = message.content[:30] + "..."
    
    return {"user_message": user_msg, "ai_message": ai_msg}


# --- Voice Call Streaming Endpoint ---
@app.post("/api/call/stream")
async def stream_voice_call(message: CallMessage):
    """
    Voice call endpoint with streaming response.
    Returns SSE stream with text and audio chunks for lowest latency.
    """
    session_id = message.session_id
    session = sessions_db.get(session_id, {})
    system_prompt = session.get("system_prompt", "You are a helpful AI assistant. Keep responses very brief.")
    voice_name = session.get("voice", "test_voice")
    
    async def generate_stream():
        try:
            # Step 1: Get Gemini response (fast)
            model = get_gemini_model()
            full_prompt = f"{system_prompt}\n\nUser: {message.content}\n\nRespond naturally and briefly:"
            
            # Use streaming for text
            response = model.generate_content(full_prompt, stream=True)
            full_text = ""
            
            # Send text chunks as they arrive
            for chunk in response:
                if chunk.text:
                    full_text += chunk.text
                    yield f"data: {json.dumps({'type': 'text', 'content': chunk.text})}\n\n"
            
            # Step 2: Generate voice from complete text
            yield f"data: {json.dumps({'type': 'status', 'content': 'generating_voice'})}\n\n"
            
            # Use voice streaming for low latency
            vm = get_voice_manager()
            chunk_index = 0
            
            for audio_buffer in vm.speak_stream(full_text, voice_name):
                audio_bytes = audio_buffer.read()
                audio_b64 = base64.b64encode(audio_bytes).decode('utf-8')
                yield f"data: {json.dumps({'type': 'audio', 'index': chunk_index, 'content': audio_b64})}\n\n"
                chunk_index += 1
            
            # Done
            yield f"data: {json.dumps({'type': 'done', 'full_text': full_text})}\n\n"
            
        except Exception as e:
            print(f"Stream error: {e}")
            yield f"data: {json.dumps({'type': 'error', 'content': str(e)})}\n\n"
    
    return StreamingResponse(
        generate_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )


@app.get("/api/messages/{session_id}")
async def get_messages(session_id: str):
    """Get all messages for a session."""
    return {"messages": messages_db.get(session_id, [])}


# --- Session Endpoints ---
@app.get("/api/sessions")
async def get_sessions():
    """Get all chat sessions."""
    # Return without internal fields
    sessions = []
    for s in sessions_db.values():
        sessions.append({
            "id": s["id"],
            "name": s["name"],
            "preview": s["preview"]
        })
    return {"sessions": sessions}


@app.post("/api/sessions")
async def create_session(session: SessionCreate):
    """Create a new chat session (New Null)."""
    session_id = str(uuid.uuid4().hex[:8])
    new_session = {
        "id": session_id,
        "name": session.name,
        "preview": "New conversation started...",
        "system_prompt": f"You are {session.name}. Be helpful and engaging. Keep responses concise for voice synthesis.",
        "voice": "test_voice"
    }
    sessions_db[session_id] = new_session
    
    # Initialize with welcome message
    messages_db[session_id] = [{
        "id": f"msg-{uuid.uuid4().hex[:8]}",
        "role": "assistant",
        "content": f"Hello. I am now initialized as {session.name}. How may I assist you?",
        "timestamp": datetime.now().strftime("%I:%M %p")
    }]
    
    return {"id": session_id, "name": session.name, "preview": new_session["preview"]}


@app.delete("/api/sessions/{session_id}")
async def delete_session(session_id: str):
    """Delete a chat session."""
    if session_id not in sessions_db:
        raise HTTPException(status_code=404, detail="Session not found")
    
    del sessions_db[session_id]
    if session_id in messages_db:
        del messages_db[session_id]
    
    return {"success": True, "deleted_id": session_id}


# --- File Upload Endpoints ---
@app.post("/api/files/{file_type}")
async def upload_file(file_type: str, file: UploadFile = File(...)):
    """Upload a file to the knowledge base (text, video, or voice)."""
    if file_type not in ["text", "video", "voice"]:
        raise HTTPException(status_code=400, detail="Invalid file type")
    
    # Generate unique filename
    file_ext = Path(file.filename).suffix if file.filename else ""
    unique_name = f"{uuid.uuid4().hex}{file_ext}"
    file_path = UPLOAD_DIR / file_type / unique_name
    
    # Save file
    content = await file.read()
    with open(file_path, "wb") as f:
        f.write(content)
    
    return {
        "success": True,
        "filename": file.filename,
        "saved_as": unique_name,
        "file_type": file_type,
        "size": len(content)
    }


@app.get("/api/files/{file_type}")
async def list_files(file_type: str):
    """List uploaded files by type."""
    if file_type not in ["text", "video", "voice"]:
        raise HTTPException(status_code=400, detail="Invalid file type")
    
    folder = UPLOAD_DIR / file_type
    files = [f.name for f in folder.iterdir() if f.is_file()]
    return {"files": files, "count": len(files)}


# --- AI Refresh Endpoint ---
@app.post("/api/refresh")
async def refresh_ai_memory():
    """Trigger AI memory reindexing (mock implementation)."""
    return {
        "success": True,
        "message": "Neural patterns reindexed successfully",
        "files_processed": {
            "text": len(list((UPLOAD_DIR / "text").iterdir())),
            "video": len(list((UPLOAD_DIR / "video").iterdir())),
            "voice": len(list((UPLOAD_DIR / "voice").iterdir()))
        }
    }


# --- Settings Endpoints ---
@app.get("/api/settings")
async def get_settings():
    """Get current AI settings."""
    return settings_db


@app.put("/api/settings")
async def update_settings(settings: SettingsUpdate):
    """Update AI settings."""
    if settings.model_version:
        settings_db["model_version"] = settings.model_version
    if settings.temperature is not None:
        settings_db["temperature"] = settings.temperature
    if settings.api_key:
        settings_db["api_key"] = settings.api_key
    
    return {"success": True, "settings": settings_db}


# --- Voice Management ---
@app.get("/api/voices")
async def list_voices():
    """List available voice profiles."""
    vm = get_voice_manager()
    return {"voices": vm.list_voices()}


if __name__ == "__main__":
    import uvicorn
    print("Starting NullTale Backend on http://localhost:8000")
    print("Gemini Model: gemini-2.0-flash-lite")
    print("Voice: test_voice (XTTS streaming)")
    uvicorn.run(app, host="0.0.0.0", port=8000)
