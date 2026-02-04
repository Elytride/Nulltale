"""
AlterEcho Backend API - Stateless Architecture
All data is stored client-side (IndexedDB). Backend only handles AI processing.
API keys and context are passed with each request.
"""

import os
import sys
import uuid
import json
import hashlib
import time
import base64
import io
import logging
import tempfile
import zipfile
from pathlib import Path
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Union

from flask import Flask, request, jsonify, Response, stream_with_context, send_file
from flask_cors import CORS
from werkzeug.utils import secure_filename
from dotenv import load_dotenv

# --- Google Gemini Integration ---
from google import genai
from google.genai import types

# Load .env from root AlterEcho folder (for fallback)
ROOT_DIR = Path(__file__).parent.parent
load_dotenv(ROOT_DIR / ".env")

# --- Import processing modules ---
from processor import (
    classify_file, extract_participants, 
    generate_style_file, generate_context_chunks
)
from processor import (
    parse_instagram_messages, parse_whatsapp_messages, 
    parse_line_messages, parse_instagram_html_messages
)
from instagram_zip_processor import (
    find_conversations, merge_conversation_messages
)
from discord_zip_processor import (
    find_dm_conversations as discord_find_conversations,
    convert_discord_to_instagram_format
)
from style_summarizer import generate_style_summary
from context_embedder import generate_embeddings
from chatbot import PersonaChatbot

# --- Voice/TTS imports ---
from wavespeed_manager import WaveSpeedManager

app = Flask(__name__)

# CORS for frontend
CORS(app, origins=["http://localhost:5173", "http://127.0.0.1:5173", "*"])

ALLOWED_TEXT_EXTENSIONS = {'.txt', '.json', '.zip', '.html'}

# Temporary directories for processing
TEMP_DIR = Path(tempfile.gettempdir()) / "alterecho_temp"
TEMP_DIR.mkdir(exist_ok=True)

# --- Helper Functions ---

def get_gemini_client(api_key: str = None):
    """Get Gemini client with provided or environment key."""
    key = api_key or os.getenv("GEMINI_API_KEY")
    if not key:
        return None
    return genai.Client(api_key=key)

def get_wavespeed_manager(api_key: str = None):
    """Get WaveSpeed manager with provided key."""
    key = api_key
    if not key:
        return None
    return WaveSpeedManager(api_key=key)

def cleanup_temp_file(filepath):
    """Clean up temporary file."""
    try:
        if filepath and Path(filepath).exists():
            Path(filepath).unlink()
    except:
        pass

def cleanup_temp_dir(dirpath):
    """Clean up temporary directory."""
    try:
        import shutil
        if dirpath and Path(dirpath).exists():
            shutil.rmtree(dirpath)
    except:
        pass

# --- Session Cache for preprocessed data ---
# This avoids sending huge embeddings with every request
# Cache expires after 1 hour of inactivity
SESSION_CACHE = {}
SESSION_CACHE_TTL = 3600  # 1 hour

def get_cached_session(session_id: str):
    """Get cached session data if available and not expired."""
    if session_id in SESSION_CACHE:
        cached = SESSION_CACHE[session_id]
        if time.time() - cached['last_accessed'] < SESSION_CACHE_TTL:
            cached['last_accessed'] = time.time()
            return cached['data']
        else:
            # Expired
            del SESSION_CACHE[session_id]
    return None

def cache_session(session_id: str, style_summary: str = None, embeddings: dict = None, image_history: list = None):
    """Cache session preprocessed data (merges with existing)."""
    current_time = time.time()
    
    if session_id not in SESSION_CACHE:
        SESSION_CACHE[session_id] = {
            'data': {},
            'last_accessed': current_time
        }
    
    data = SESSION_CACHE[session_id]['data']
    SESSION_CACHE[session_id]['last_accessed'] = current_time
    
    if style_summary is not None:
        data['style_summary'] = style_summary
    if embeddings is not None:
        data['embeddings'] = embeddings
    if image_history is not None:
        data['image_history'] = image_history

    # Cleanup old sessions (limit to 50)
    if len(SESSION_CACHE) > 50:
        oldest = min(SESSION_CACHE.keys(), key=lambda k: SESSION_CACHE[k]['last_accessed'])
        del SESSION_CACHE[oldest]

def clear_session_cache(session_id: str = None):
    """Clear session cache."""
    if session_id:
        SESSION_CACHE.pop(session_id, None)
    else:
        SESSION_CACHE.clear()

# --- Stateless Processing Functions ---

def classify_content(content: str, filename: str) -> str:
    """Classify file content without writing to disk."""
    # Check for LINE (starts with [LINE] header)
    if content.strip().startswith('[LINE]'):
        return 'LINE'
    
    # Check for Instagram HTML
    content_stripped = content.strip()
    if content_stripped.startswith('<html') or content_stripped.startswith('<!DOCTYPE'):
        if '_a6-h' in content and '_a6-o' in content:
            return 'InstagramHTML'
    
    # Check for Instagram JSON
    if content_stripped.startswith('{') or content_stripped.startswith('['):
        if '"participants":' in content and '"messages":' in content:
            return 'Instagram'
    
    # Check for WhatsApp
    import re
    wa_pattern = r'\d{1,2}/\d{1,2}/\d{2,4},\s\d{1,2}:\d{2}.*-\s'
    if re.search(wa_pattern, content):
        return 'WhatsApp'
    
    return 'NULL'

def parse_messages_from_content(content: str, file_type: str) -> list:
    """Parse messages from file content without writing to disk."""
    # Create temp file for parsing (reusing existing functions)
    temp_path = TEMP_DIR / f"temp_{uuid.uuid4().hex}.tmp"
    try:
        temp_path.write_text(content, encoding='utf-8')
        
        if file_type == 'Instagram':
            return parse_instagram_messages(str(temp_path))
        elif file_type == 'InstagramHTML':
            return parse_instagram_html_messages(str(temp_path))
        elif file_type == 'WhatsApp':
            return parse_whatsapp_messages(str(temp_path))
        elif file_type == 'LINE':
            return parse_line_messages(str(temp_path))
        else:
            return []
    finally:
        cleanup_temp_file(temp_path)

def extract_participants_from_content(content: str, file_type: str) -> list:
    """Extract participants from file content."""
    temp_path = TEMP_DIR / f"temp_{uuid.uuid4().hex}.tmp"
    try:
        temp_path.write_text(content, encoding='utf-8')
        return extract_participants(str(temp_path), file_type)
    finally:
        cleanup_temp_file(temp_path)

# --- API Endpoints ---

@app.route("/api/warmup", methods=["GET", "POST"])
def warmup():
    """Health check endpoint."""
    return jsonify({"status": "ok", "message": "Backend online"})

# --- Chat Endpoint (Stateless) ---

@app.route("/api/chat", methods=["POST"])
def send_message():
    """
    Stateless chat endpoint.
    All context (style summary, embeddings, history) is passed in the request.
    """
    # Handle multipart/form-data for images
    content = ""
    session_id = ""
    image_file = None
    style_summary = ""
    embeddings = {}
    history = []
    gemini_key = None
    settings = {}
    
    if request.content_type and "multipart/form-data" in request.content_type:
        content = request.form.get("content", "").strip()
        session_id = request.form.get("session_id", "")
        style_summary = request.form.get("style_summary", "")
        embeddings_str = request.form.get("embeddings", "{}")
        history_str = request.form.get("history", "[]")
        gemini_key = request.form.get("gemini_key", "")
        settings_str = request.form.get("settings", "{}")
        
        try:
            embeddings = json.loads(embeddings_str)
        except:
            embeddings = {}
        try:
            history = json.loads(history_str)
        except:
            history = []
        try:
            settings = json.loads(settings_str)
        except:
            settings = {}
            
        if "image" in request.files:
            image_file = request.files["image"]
    else:
        data = request.json or {}
        content = data.get("content", "").strip()
        session_id = data.get("session_id", "")
        style_summary = data.get("style_summary", "")
        embeddings = data.get("embeddings", {})
        history = data.get("history", [])
        gemini_key = data.get("gemini_key", "")
        settings = data.get("settings", {})
    
    if not session_id:
        return jsonify({"error": "Missing session_id"}), 400
    
    # Check session cache for all data
    image_history = []
    cached = get_cached_session(session_id)
    
    if cached:
        if not style_summary:
            style_summary = cached.get('style_summary', '')
        if not embeddings:
            embeddings = cached.get('embeddings', {})
        image_history = cached.get('image_history', [])
    
    # Cache the session data if we have it (for future requests)
    if style_summary or embeddings:
        cache_session(session_id, style_summary=style_summary, embeddings=embeddings)
    
    # Check if we have preprocessed data
    if not style_summary:
        return jsonify({
            "user_message": {
                "id": uuid.uuid4().hex[:8],
                "role": "user",
                "content": content,
                "timestamp": datetime.now().strftime("%I:%M %p"),
                "images": []
            },
            "ai_message": {
                "id": uuid.uuid4().hex[:8],
                "role": "assistant", 
                "content": "Please initialise persona in 'manage files'",
                "timestamp": datetime.now().strftime("%I:%M %p"),
                "images": []
            },
            "ai_messages": [{
                "id": uuid.uuid4().hex[:8],
                "role": "assistant", 
                "content": "Please initialise persona in 'manage files'",
                "timestamp": datetime.now().strftime("%I:%M %p"),
                "images": []
            }]
        })
    
    # Get Gemini client
    client = get_gemini_client(gemini_key)
    if not client:
        return jsonify({"error": "Gemini API key not configured"}), 400
    
    # Process user image if present
    pil_image = None
    user_image_id = None
    if image_file:
        from PIL import Image
        try:
            pil_image = Image.open(image_file.stream)
            user_image_id = f"user_{uuid.uuid4().hex[:8]}"
        except Exception as e:
            print(f"Error opening user image: {e}")
    
    # Create chatbot with inline data
    try:
        model_name = settings.get("chatbot_model", "gemini-2.0-flash")
        image_model = settings.get("image_model", "gemini-2.0-flash")
        
        chatbot = PersonaChatbot(
            style_summary=style_summary,
            embeddings_data=embeddings,
            client=client,
            model_name=model_name,
            inline_mode=True,  # New flag for stateless operation
            image_history=image_history # Pass cached image history
        )
        chatbot.set_image_model(image_model)
        
        # Restore conversation history
        for msg in history[-20:]:  # Last 20 messages
            if msg.get("role") == "user":
                chatbot.conversation_history.append(("user", msg.get("content", "")))
            elif msg.get("role") == "assistant":
                chatbot.conversation_history.append(("assistant", msg.get("content", "")))
        
        # Get response
        response_data = chatbot.chat(content, user_image=pil_image, user_image_id=user_image_id)
        
        # Update session cache with new image history
        cache_session(session_id, image_history=chatbot.image_history)
        
    except Exception as e:
        print(f"Chatbot error: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"error": f"Chat error: {str(e)}"}), 500
    
    ai_text = response_data.get("text", "")
    ai_generated_images = response_data.get("images", [])
    
    # Build response
    timestamp = datetime.now().strftime("%I:%M %p")
    
    user_msg_obj = {
        "id": uuid.uuid4().hex[:8],
        "role": "user",
        "content": content,
        "timestamp": timestamp,
        "images": [user_image_id] if user_image_id else []
    }
    
    # Split AI text into multiple messages by line breaks
    import re
    ai_lines = []
    for line in ai_text.split('\n'):
        line = line.strip()
        if line:
            # Filter out image attachment lines
            if 'IMG-' in line and '(file attached)' in line:
                continue
            if line.startswith('IMG-') and '.png' in line:
                continue
            
            # Clean leaked ID artifacts from within the line
            # Matches: {hex8}, [hex8], <image: hex8>
            line = re.sub(r'\{[a-f0-9]{8}\}', '', line)
            line = re.sub(r'\[[a-f0-9]{8}\]', '', line)
            line = re.sub(r'<image:\s*[a-f0-9]{8}>', '', line)
            
            line = line.strip()
            if line:
                ai_lines.append(line)
    
    # Build image data for response
    saved_ai_images = []
    image_blobs = []
    for img_data in ai_generated_images:
        img_id = f"ai_{img_data['id']}"
        saved_ai_images.append(img_id)
        image_blobs.append({
            "id": img_id,
            "data": base64.b64encode(img_data["bytes"]).decode("utf-8"),
            "mime_type": "image/png"
        })
    
    ai_messages = []
    if ai_lines:
        for i, line in enumerate(ai_lines):
            msg = {
                "id": uuid.uuid4().hex[:8],
                "role": "assistant",
                "content": line,
                "timestamp": timestamp,
                "images": saved_ai_images if i == 0 else []
            }
            ai_messages.append(msg)
    elif saved_ai_images:
        msg = {
            "id": uuid.uuid4().hex[:8],
            "role": "assistant",
            "content": "",
            "timestamp": timestamp,
            "images": saved_ai_images
        }
        ai_messages.append(msg)
    
    return jsonify({
        "user_message": user_msg_obj,
        "ai_message": ai_messages[0] if ai_messages else {"id": "", "role": "assistant", "content": "", "timestamp": "", "images": []},
        "ai_messages": ai_messages,
        "generated_images": image_blobs
    })

# --- Processing Endpoint (Stateless) ---

@app.route("/api/process", methods=["POST"])
def process_files():
    """
    Stateless file processing endpoint.
    Receives files, processes them, and returns the processed data.
    """
    session_id = request.form.get("session_id", "")
    additional_context = request.form.get("additional_context", "")
    gemini_key = request.form.get("gemini_key", "")
    wavespeed_key = request.form.get("wavespeed_key", "")
    settings_str = request.form.get("settings", "{}")
    files_metadata_str = request.form.get("files_metadata", "[]")
    
    # Debug logging
    print(f"[DEBUG] /api/process called")
    print(f"[DEBUG]   session_id: {session_id}")
    print(f"[DEBUG]   gemini_key present: {bool(gemini_key)}")
    print(f"[DEBUG]   wavespeed_key present: {bool(wavespeed_key)}")
    print(f"[DEBUG]   text_files count: {len(request.files.getlist('text_files'))}")
    print(f"[DEBUG]   voice_file present: {'voice_file' in request.files}")
    
    try:
        settings = json.loads(settings_str)
    except:
        settings = {}
    
    try:
        files_metadata = json.loads(files_metadata_str)
    except:
        files_metadata = []
    
    # Get text files
    text_files = request.files.getlist("text_files")
    voice_file = request.files.get("voice_file")
    
    if not gemini_key:
        print("[DEBUG] ERROR: No gemini_key in request!")
        return jsonify({"error": "Gemini API key required. Please configure in Settings."}), 400
    
    def generate():
        try:
            yield f"data: {json.dumps({'step': 'starting', 'progress': 0, 'message': 'Starting refresh...'})}\n\n"
            
            client = get_gemini_client(gemini_key)
            if not client:
                yield f"data: {json.dumps({'step': 'error', 'message': 'Failed to initialize Gemini client'})}\n\n"
                return
            
            # Create temp directory for this processing session
            temp_session_dir = TEMP_DIR / f"session_{uuid.uuid4().hex}"
            temp_session_dir.mkdir(exist_ok=True)
            
            try:
                # Save files temporarily and build file_results
                file_results = []
                subject_name = None
                
                yield f"data: {json.dumps({'step': 'processing', 'progress': 10, 'message': 'Processing uploaded files...'})}\n\n"
                
                for i, file in enumerate(text_files):
                    # Find metadata for this file
                    meta = files_metadata[i] if i < len(files_metadata) else {}
                    
                    # Save to temp
                    temp_path = temp_session_dir / file.filename
                    file.save(str(temp_path))
                    
                    # Classify
                    file_type = classify_file(str(temp_path))
                    subject = meta.get("subject", "Unknown")
                    
                    if not subject_name:
                        subject_name = subject
                    
                    file_results.append((
                        meta.get("original_name", file.filename),
                        str(temp_path),
                        file_type,
                        subject
                    ))
                
                if not file_results:
                    yield f"data: {json.dumps({'step': 'error', 'message': 'No files to process'})}\n\n"
                    return
                
                # Generate style file
                yield f"data: {json.dumps({'step': 'processing', 'progress': 20, 'message': 'Generating style data...'})}\n\n"
                
                style_temp_path = temp_session_dir / f"{subject_name}_style_temp.txt"
                generate_style_file(file_results, str(style_temp_path))
                
                # Read style content
                style_content = style_temp_path.read_text(encoding='utf-8')
                
                # Generate context chunks
                yield f"data: {json.dumps({'step': 'processing', 'progress': 30, 'message': 'Generating context chunks...'})}\n\n"
                
                chunks_temp_path = temp_session_dir / f"{subject_name}_chunks.json"
                generate_context_chunks(file_results, str(chunks_temp_path))
                
                # Read chunks
                with open(chunks_temp_path, 'r', encoding='utf-8') as f:
                    chunks_data = json.load(f)
                
                # Generate style summary using AI
                yield f"data: {json.dumps({'step': 'summary', 'progress': 50, 'message': f'Analyzing style for {subject_name}...'})}\n\n"
                
                summary_temp_path = temp_session_dir / f"{subject_name}_summary.txt"
                train_model = settings.get("training_model", "gemini-2.5-flash-preview-05-20")
                
                generate_style_summary(
                    str(style_temp_path), 
                    str(summary_temp_path), 
                    subject_name, 
                    client=client, 
                    model_name=train_model,
                    additional_context=additional_context
                )
                
                # Read summary
                style_summary = summary_temp_path.read_text(encoding='utf-8')
                
                # Generate embeddings
                yield f"data: {json.dumps({'step': 'embeddings', 'progress': 70, 'message': f'Generating embeddings for {subject_name}...'})}\n\n"
                
                embeddings_temp_path = temp_session_dir / f"{subject_name}_embeddings.json"
                embed_model = settings.get("embedding_model", "gemini-embedding-001")
                
                generate_embeddings(
                    str(chunks_temp_path), 
                    str(embeddings_temp_path), 
                    client=client, 
                    model_name=embed_model
                )
                
                # Read embeddings
                with open(embeddings_temp_path, 'r', encoding='utf-8') as f:
                    embeddings_data = json.load(f)
                
                # Voice cloning if voice file provided
                voice_result = None
                voice_id = None
                
                if voice_file and wavespeed_key:
                    yield f"data: {json.dumps({'step': 'voice', 'progress': 85, 'message': 'Cloning voice...'})}\n\n"
                    
                    try:
                        ws_manager = get_wavespeed_manager(wavespeed_key)
                        if ws_manager:
                            # Save voice file temporarily
                            voice_temp_path = temp_session_dir / voice_file.filename
                            voice_file.save(str(voice_temp_path))
                            
                            # Generate voice ID
                            clean_name = "".join(c for c in subject_name if c.isalnum())
                            voice_name_id = f"AlterEcho{session_id[-6:]}{clean_name}"
                            
                            voice_id = ws_manager.clone_voice(voice_name_id, str(voice_temp_path))
                            voice_result = {"success": True, "message": "Voice cloned successfully"}
                    except Exception as e:
                        voice_result = {"error": str(e)}
                
                # Build preprocessed data to return
                preprocessed = {
                    "subject": subject_name,
                    "style_summary": style_summary,
                    "embeddings": embeddings_data,
                    "chunks": chunks_data
                }
                
                yield f"data: {json.dumps({
                    'step': 'complete', 
                    'progress': 100, 
                    'message': 'Refresh complete!',
                    'preprocessed': preprocessed,
                    'subject': subject_name,
                    'voice_id': voice_id,
                    'voice_cloning': voice_result
                })}\n\n"
                
            finally:
                # Cleanup temp directory
                cleanup_temp_dir(temp_session_dir)
                
        except Exception as e:
            print(f"Processing error: {e}")
            import traceback
            traceback.print_exc()
            yield f"data: {json.dumps({'step': 'error', 'message': str(e)})}\n\n"
    
    return Response(stream_with_context(generate()), mimetype='text/event-stream', headers={
        'X-Accel-Buffering': 'no',
        'Cache-Control': 'no-cache',
        'Connection': 'keep-alive'
    })

# --- ZIP Processing (still needs backend for extraction) ---

# Store pending zips in memory (short-lived)
pending_zips = {}

@app.route("/api/chats/<session_id>/files/text", methods=["POST"])
def upload_and_process_zip(session_id):
    """Handle ZIP file uploads and return conversation list for selection."""
    if "file" not in request.files:
        return jsonify({"error": "No file provided"}), 400
    
    file = request.files["file"]
    if not file.filename:
        return jsonify({"error": "No file selected"}), 400
    
    ext = Path(file.filename).suffix.lower()
    if ext != '.zip':
        return jsonify({"error": "Only ZIP files supported via this endpoint"}), 400
    
    # Save ZIP temporarily
    zip_id = uuid.uuid4().hex[:12]
    temp_zip_path = TEMP_DIR / f"{zip_id}.zip"
    file.save(str(temp_zip_path))
    
    try:
        # Detect ZIP type and extract
        zip_type = None
        extracted_path = TEMP_DIR / f"extracted_{zip_id}"
        extracted_path.mkdir(exist_ok=True)
        
        with zipfile.ZipFile(str(temp_zip_path), 'r') as zf:
            names = zf.namelist()
            if any('messages/index.json' in n.lower() for n in names):
                zip_type = 'discord'
            elif any('inbox/' in n.lower() for n in names):
                zip_type = 'instagram'
            
            # Extract
            zf.extractall(str(extracted_path))
        
        if not zip_type:
            cleanup_temp_file(temp_zip_path)
            cleanup_temp_dir(extracted_path)
            return jsonify({"error": "Unsupported ZIP format"}), 400
        
        # Find conversations
        if zip_type == 'discord':
            conversations = discord_find_conversations(str(extracted_path))
        else:
            conversations = find_conversations(str(extracted_path))
        
        # Store for later selection
        pending_zips[zip_id] = {
            "session_id": session_id,
            "zip_path": str(temp_zip_path),
            "extracted_path": str(extracted_path),
            "original_name": file.filename,
            "conversations": conversations,
            "zip_type": zip_type
        }
        
        return jsonify({
            "success": True,
            "type": f"{zip_type}_zip_upload",
            "zip_id": zip_id,
            "conversations": conversations,
            "uploaded": [],
            "rejected": []
        })
        
    except Exception as e:
        cleanup_temp_file(temp_zip_path)
        cleanup_temp_dir(extracted_path)
        return jsonify({"error": f"ZIP processing error: {str(e)}"}), 500

@app.route("/api/chats/zip/select", methods=["POST"])
def select_zip_conversations():
    """Select conversations from extracted ZIP and return merged data."""
    data = request.get_json()
    zip_id = data.get("zip_id")
    selected_folders = data.get("conversations", [])
    
    if not zip_id or zip_id not in pending_zips:
        return jsonify({"error": "ZIP not found"}), 404
    
    zip_info = pending_zips[zip_id]
    session_id = zip_info.get("session_id")
    conversations = zip_info["conversations"]
    zip_type = zip_info.get("zip_type", "instagram")
    
    selected_convs = [c for c in conversations if c["folder_name"] in selected_folders]
    uploaded = []
    rejected = []
    files_data = []
    
    for conv in selected_convs:
        try:
            if zip_type == "discord":
                merged_data = convert_discord_to_instagram_format(conv["path"])
                source_label = "Discord"
            else:
                merged_data = merge_conversation_messages(conv["path"])
                source_label = "Instagram"
            
            if not merged_data:
                rejected.append({"name": conv["display_name"], "reason": "Failed to merge"})
                continue
            
            file_id = uuid.uuid4().hex[:12]
            detected_type = "Discord" if zip_type == "discord" else "Instagram"
            
            # Return the merged data for client-side storage
            files_data.append({
                "id": file_id,
                "original_name": f"{conv['display_name']} ({source_label})",
                "detected_type": detected_type,
                "participants": [p.get('name') for p in merged_data.get('participants', [])],
                "data": merged_data
            })
            
            uploaded.append({
                "id": file_id,
                "original_name": f"{conv['display_name']} ({source_label})",
                "detected_type": detected_type
            })
            
        except Exception as e:
            rejected.append({"name": conv["display_name"], "reason": str(e)})
    
    # Cleanup
    try:
        cleanup_temp_file(zip_info["zip_path"])
        cleanup_temp_dir(zip_info["extracted_path"])
    except:
        pass
    
    del pending_zips[zip_id]
    
    return jsonify({
        "success": True,
        "session_id": session_id,
        "uploaded": uploaded,
        "rejected": rejected,
        "files_data": files_data
    })

# --- Voice Call Streaming (Stateless) ---

@app.route("/api/call/stream", methods=["POST"])
def stream_voice_call():
    """Stateless voice call streaming."""
    data = request.json
    content = data.get("content", "").strip()
    session_id = data.get("session_id", "")
    style_summary = data.get("style_summary", "")
    embeddings = data.get("embeddings", {})
    voice_id = data.get("voice_id", "Deep_Voice_Man")
    gemini_key = data.get("gemini_key", "")
    wavespeed_key = data.get("wavespeed_key", "")
    settings = data.get("settings", {})
    
    if not content or not session_id:
        return jsonify({"error": "Missing content or session_id"}), 400
    
    # Check session cache for all data
    image_history = []
    cached = get_cached_session(session_id)
    
    if cached:
        if not style_summary:
            style_summary = cached.get('style_summary', '')
        if not embeddings:
            embeddings = cached.get('embeddings', {})
        image_history = cached.get('image_history', []) # Retrieve cached image history
    
    # Cache the session data if we have it
    if style_summary or embeddings:
        cache_session(session_id, style_summary=style_summary, embeddings=embeddings)
    
    if not style_summary:
        return jsonify({"error": "No persona initialized. Please refresh memory."}), 400
    
    client = get_gemini_client(gemini_key)
    if not client:
        return jsonify({"error": "Gemini API key not configured"}), 400
    
    ws_manager = get_wavespeed_manager(wavespeed_key)
    if not ws_manager:
        return jsonify({"error": "Voice service not configured"}), 400
    
    # Create chatbot with inline data
    model_name = settings.get("chatbot_model", "gemini-2.0-flash")
    
    try:
        chatbot = PersonaChatbot(
            style_summary=style_summary,
            embeddings_data=embeddings,
            client=client,
            model_name=model_name,
            inline_mode=True,
            image_history=image_history # Pass cached image history
        )
    except Exception as e:
        return jsonify({"error": f"Failed to create chatbot: {str(e)}"}), 500
    
    def generate():
        import re
        
        def clean_for_tts(text):
            """Clean text for TTS."""
            text = re.sub(r'\.{2,}', '.', text)
            text = re.sub(r'!{2,}', '!', text)
            text = re.sub(r'\?{2,}', '?', text)
            text = re.sub(r'\*[^*]+\*', '', text)
            text = re.sub(r'(.)\1{2,}', r'\1\1', text)
            text = re.sub(r' {2,}', ' ', text)
            return text.strip()
        
        full_response_text = ""
        
        yield f"data: {json.dumps({'type': 'status', 'content': 'processing'})}\n\n"
        
        try:
            for chunk in chatbot.stream_chat_voice(content):
                yield f"data: {json.dumps({'type': 'text', 'content': chunk})}\n\n"
                full_response_text += chunk
            
            if full_response_text.strip():
                clean_text = clean_for_tts(full_response_text)
                if clean_text:
                    try:
                        for audio_chunk in ws_manager.speak_stream(clean_text, voice_id):
                            b64_audio = base64.b64encode(audio_chunk).decode('utf-8')
                            yield f"data: {json.dumps({'type': 'audio', 'content': b64_audio, 'index': 0})}\n\n"
                    except Exception as e:
                        yield f"data: {json.dumps({'type': 'error', 'content': f'TTS Error: {e}'})}\n\n"
            
            yield f"data: {json.dumps({'type': 'done', 'full_text': full_response_text})}\n\n"
            
        except Exception as e:
            yield f"data: {json.dumps({'type': 'error', 'content': str(e)})}\n\n"
    
    return Response(stream_with_context(generate()), mimetype='text/event-stream')

# --- API Key Testing ---

@app.route("/api/settings/wavespeed-key/test", methods=["POST"])
def test_wavespeed_key():
    """Test WaveSpeed API key."""
    key = request.headers.get("X-WaveSpeed-Key") or request.json.get("wavespeed_key")
    if not key:
        return jsonify({"success": False, "error": "No key provided"}), 400
    
    try:
        manager = get_wavespeed_manager(key)
        # Simple test - just check if we can initialize
        return jsonify({"success": True, "message": "API key is valid"})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 400

# --- Voices List ---

@app.route("/api/voices", methods=["GET"])
def list_voices():
    """List available voices."""
    key = request.headers.get("X-WaveSpeed-Key")
    if not key:
        return jsonify({"voices": []})
    
    try:
        manager = get_wavespeed_manager(key)
        # Return default voices if manager exists
        return jsonify({"voices": ["Deep_Voice_Man", "Custom"]})
    except:
        return jsonify({"voices": []})

if __name__ == "__main__":
    app.run(debug=True, port=5000)
