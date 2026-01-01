"""
NullTale Backend API - Flask Server
Provides API endpoints for file upload, classification, and participant extraction.
"""

import os
import sys
import uuid
import hashlib
from pathlib import Path
from flask import Flask, request, jsonify
from flask_cors import CORS
from werkzeug.utils import secure_filename
from dotenv import load_dotenv

# Load .env from root Nulltale folder
ROOT_DIR = Path(__file__).parent.parent
load_dotenv(ROOT_DIR / ".env")

# Import processing modules
from processor import classify_file, extract_participants

app = Flask(__name__)

# CORS for Vite dev server
CORS(app, origins=["http://localhost:5173", "http://127.0.0.1:5173"])

# Configure upload directory
UPLOAD_DIR = Path(__file__).parent / "uploads"
UPLOAD_DIR.mkdir(exist_ok=True)
(UPLOAD_DIR / "text").mkdir(exist_ok=True)
(UPLOAD_DIR / "voice").mkdir(exist_ok=True)

# Allowed extensions for text files
ALLOWED_TEXT_EXTENSIONS = {'.txt', '.json'}


def compute_file_hash(file_path):
    """Compute SHA256 hash of a file's content."""
    sha256_hash = hashlib.sha256()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            sha256_hash.update(chunk)
    return sha256_hash.hexdigest()


def get_existing_hashes(folder):
    """Get hashes of all existing files in a folder."""
    hashes = {}
    if not folder.exists():
        return hashes
    
    for file_path in folder.iterdir():
        if file_path.is_file() and not file_path.name.endswith('.meta.json'):
            try:
                file_hash = compute_file_hash(file_path)
                hashes[file_hash] = file_path.name
            except Exception:
                pass
    return hashes


def get_file_metadata(file_path):
    """Get metadata for a file including type detection and participants."""
    path = Path(file_path)
    file_id = path.stem  # Use filename without extension as ID
    
    detected_type = classify_file(str(path))
    participants = []
    if detected_type in ["WhatsApp", "Instagram"]:
        participants = extract_participants(str(path), detected_type)
    
    return {
        "id": file_id,
        "original_name": path.name,
        "saved_as": path.name,
        "file_type": "text" if path.parent.name == "text" else "voice",
        "detected_type": detected_type,
        "participants": participants,
        "subject": None,
        "path": str(path),
        "size": path.stat().st_size
    }


def scan_uploads_folder(file_type):
    """Scan uploads folder and return all files with metadata."""
    folder = UPLOAD_DIR / file_type
    if not folder.exists():
        return []
    
    files = []
    for file_path in folder.iterdir():
        # Skip meta files and non-files
        if not file_path.is_file():
            continue
        if file_path.name.endswith('.meta.json'):
            continue
        
        try:
            metadata = get_file_metadata(file_path)
            
            # Load subject from meta file if exists
            meta_file = folder / f"{metadata['id']}.meta.json"
            if meta_file.exists():
                import json
                with open(meta_file, 'r') as f:
                    meta_data = json.load(f)
                    metadata['subject'] = meta_data.get('subject')
            
            files.append(metadata)
        except Exception as e:
            print(f"Error scanning file {file_path}: {e}")
    
    return files


# --- File Upload Endpoints ---

@app.route("/api/files/<file_type>", methods=["POST"])
def upload_files(file_type):
    """
    Upload one or more files. For text files, validates that they are 
    WhatsApp or Instagram exports before saving. Also checks for duplicates.
    Returns list of uploaded files with their metadata.
    """
    if file_type not in ["text", "voice"]:
        return jsonify({"error": "Invalid file type"}), 400
    
    if "file" not in request.files:
        return jsonify({"error": "No file provided"}), 400
    
    # Get all files (supports multiple)
    files = request.files.getlist("file")
    if not files or all(f.filename == "" for f in files):
        return jsonify({"error": "No files selected"}), 400
    
    # Get hashes of existing files to detect duplicates
    folder = UPLOAD_DIR / file_type
    existing_hashes = get_existing_hashes(folder)
    # Track hashes of newly uploaded files in this batch
    batch_hashes = {}
    
    uploaded = []
    rejected = []
    
    for file in files:
        if file.filename == "":
            continue
        
        original_name = secure_filename(file.filename)
        file_ext = Path(original_name).suffix.lower()
        
        # Validate extension for text files
        if file_type == "text" and file_ext not in ALLOWED_TEXT_EXTENSIONS:
            rejected.append({
                "name": file.filename,
                "reason": f"Only .txt and .json files are accepted"
            })
            continue
        
        # Generate unique filename
        file_id = uuid.uuid4().hex[:12]
        unique_name = f"{file_id}{file_ext}"
        file_path = UPLOAD_DIR / file_type / unique_name
        
        # Save file temporarily to check type and hash
        file.save(str(file_path))
        
        # Check for duplicate content
        file_hash = compute_file_hash(file_path)
        
        if file_hash in existing_hashes:
            # Duplicate of existing file
            file_path.unlink()
            rejected.append({
                "name": file.filename,
                "reason": "Duplicate file. This content has already been uploaded."
            })
            continue
        
        if file_hash in batch_hashes:
            # Duplicate within this upload batch
            file_path.unlink()
            rejected.append({
                "name": file.filename,
                "reason": f"Duplicate of {batch_hashes[file_hash]} in this upload."
            })
            continue
        
        # For text files, validate it's WhatsApp or Instagram
        if file_type == "text":
            detected_type = classify_file(str(file_path))
            
            if detected_type not in ["WhatsApp", "Instagram"]:
                # Delete the file and reject
                file_path.unlink()
                rejected.append({
                    "name": file.filename,
                    "reason": "Not a supported chat file. Please upload WhatsApp or Instagram chat exports."
                })
                continue
            
            # Get participants
            participants = extract_participants(str(file_path), detected_type)
            
            uploaded.append({
                "id": file_id,
                "original_name": file.filename,
                "saved_as": unique_name,
                "file_type": file_type,
                "detected_type": detected_type,
                "participants": participants,
                "subject": None,
                "path": str(file_path),
                "size": file_path.stat().st_size
            })
            # Track this file's hash for batch duplicate detection
            batch_hashes[file_hash] = file.filename
        else:
            # Voice files - just save
            uploaded.append({
                "id": file_id,
                "original_name": file.filename,
                "saved_as": unique_name,
                "file_type": file_type,
                "detected_type": "voice",
                "participants": [],
                "subject": None,
                "path": str(file_path),
                "size": file_path.stat().st_size
            })
            # Track this file's hash for batch duplicate detection
            batch_hashes[file_hash] = file.filename
    
    return jsonify({
        "success": True,
        "uploaded": uploaded,
        "rejected": rejected,
        "uploaded_count": len(uploaded),
        "rejected_count": len(rejected)
    })


@app.route("/api/files/<file_type>", methods=["GET"])
def list_files(file_type):
    """List all files in uploads folder by type - direct folder scan."""
    if file_type not in ["text", "voice"]:
        return jsonify({"error": "Invalid file type"}), 400
    
    # Scan folder directly for real-time sync
    files = scan_uploads_folder(file_type)
    
    return jsonify({
        "files": files,
        "count": len(files)
    })


@app.route("/api/files/<file_type>/<file_id>/participants", methods=["GET"])
def get_participants(file_type, file_id):
    """Get participants for an uploaded file."""
    folder = UPLOAD_DIR / file_type
    
    # Find file by ID prefix
    matching_files = list(folder.glob(f"{file_id}.*"))
    if not matching_files:
        return jsonify({"error": "File not found"}), 404
    
    file_path = matching_files[0]
    detected_type = classify_file(str(file_path))
    participants = []
    if detected_type in ["WhatsApp", "Instagram"]:
        participants = extract_participants(str(file_path), detected_type)
    
    return jsonify({
        "file_id": file_id,
        "participants": participants,
        "detected_type": detected_type
    })


@app.route("/api/files/<file_type>/<file_id>/subject", methods=["POST"])
def set_subject(file_type, file_id):
    """Set the subject for an uploaded file (stored in a metadata file)."""
    folder = UPLOAD_DIR / file_type
    
    # Find file by ID prefix
    matching_files = list(folder.glob(f"{file_id}.*"))
    if not matching_files:
        return jsonify({"error": "File not found"}), 404
    
    data = request.get_json()
    subject = data.get("subject")
    
    if not subject:
        return jsonify({"error": "Subject is required"}), 400
    
    # Store subject in a metadata JSON file
    meta_file = folder / f"{file_id}.meta.json"
    import json
    meta_data = {"subject": subject}
    with open(meta_file, 'w') as f:
        json.dump(meta_data, f)
    
    return jsonify({
        "success": True,
        "file_id": file_id,
        "subject": subject
    })


@app.route("/api/files/<file_type>/<file_id>", methods=["DELETE"])
def delete_file(file_type, file_id):
    """Delete an uploaded file."""
    folder = UPLOAD_DIR / file_type
    
    # Find and delete file by ID prefix
    matching_files = list(folder.glob(f"{file_id}.*"))
    if not matching_files:
        return jsonify({"error": "File not found"}), 404
    
    for file_path in matching_files:
        file_path.unlink()
    
    # Also delete metadata file if exists
    meta_file = folder / f"{file_id}.meta.json"
    if meta_file.exists():
        meta_file.unlink()
    
    return jsonify({
        "success": True,
        "deleted_id": file_id
    })


# --- Health Check ---

@app.route("/api/health", methods=["GET"])
def health_check():
    """Health check endpoint."""
    return jsonify({
        "status": "ok",
        "service": "nulltale-api"
    })


if __name__ == "__main__":
    print("Starting NullTale API on http://localhost:5000")
    print(f"Upload directory: {UPLOAD_DIR}")
    print(f"Root .env loaded from: {ROOT_DIR / '.env'}")
    app.run(host="0.0.0.0", port=5000, debug=True)
