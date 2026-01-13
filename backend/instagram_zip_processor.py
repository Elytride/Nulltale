"""
Instagram ZIP Processor Module
Handles extraction and parsing of Instagram data export ZIP files.
"""

import os
import json
import zipfile
import shutil
import tempfile
from pathlib import Path


# Temporary directory for ZIP extraction
TEMP_ZIP_DIR = Path(__file__).parent / "temp_zip"
TEMP_ZIP_DIR.mkdir(exist_ok=True)


def extract_zip(zip_path, zip_id):
    """
    Extract a ZIP file to a temporary directory.
    
    Args:
        zip_path: Path to the ZIP file
        zip_id: Unique identifier for this ZIP (used for temp folder name)
        
    Returns:
        Path to the extracted directory
    """
    extract_dir = TEMP_ZIP_DIR / zip_id
    
    # Clean up if exists
    if extract_dir.exists():
        shutil.rmtree(extract_dir)
    
    extract_dir.mkdir(parents=True)
    
    with zipfile.ZipFile(zip_path, 'r') as zip_ref:
        zip_ref.extractall(extract_dir)
    
    return extract_dir


def find_inbox_path(extracted_path):
    """
    Find the inbox folder within the extracted ZIP.
    The path structure is: your_instagram_activity/messages/inbox/
    
    Args:
        extracted_path: Path to extracted ZIP contents
        
    Returns:
        Path to inbox folder or None if not found
    """
    # Try common path patterns
    patterns = [
        extracted_path / "your_instagram_activity" / "messages" / "inbox",
        # Sometimes the root folder name varies
    ]
    
    # Also check one level deep in case ZIP has a root folder
    for item in extracted_path.iterdir():
        if item.is_dir():
            patterns.append(item / "your_instagram_activity" / "messages" / "inbox")
            patterns.append(item / "messages" / "inbox")
    
    for pattern in patterns:
        if pattern.exists() and pattern.is_dir():
            return pattern
    
    return None


def find_conversations(extracted_path):
    """
    Find all conversation folders in the extracted ZIP.
    
    Args:
        extracted_path: Path to extracted ZIP contents
        
    Returns:
        List of conversation info dicts with:
        - folder_name: Raw folder name
        - display_name: Cleaned display name
        - path: Full path to the folder
        - participants: List of participant names
        - message_count: Approximate message count
        - has_json: Whether folder has JSON message files
        - has_html: Whether folder has HTML message files
    """
    inbox_path = find_inbox_path(extracted_path)
    
    if not inbox_path:
        return []
    
    conversations = []
    
    for folder in inbox_path.iterdir():
        if not folder.is_dir():
            continue
        
        # Check if this folder contains message files (JSON or HTML)
        json_files = list(folder.glob("message_*.json"))
        html_files = list(folder.glob("*.html"))
        
        if not json_files and not html_files:
            continue
        
        # Get conversation preview
        preview = get_conversation_preview(folder)
        
        if preview:
            conversations.append({
                "folder_name": folder.name,
                "display_name": preview.get("display_name", folder.name),
                "path": str(folder),
                "participants": preview.get("participants", []),
                "message_count": preview.get("message_count", 0),
                "has_json": len(json_files) > 0,
                "has_html": len(html_files) > 0
            })
    
    # Sort by message count (most active first)
    conversations.sort(key=lambda x: x["message_count"], reverse=True)
    
    return conversations


def get_conversation_preview(folder_path):
    """
    Get preview info for a conversation folder.
    Supports both JSON and HTML message files.
    
    Args:
        folder_path: Path to the conversation folder
        
    Returns:
        Dict with display_name, participants, message_count
    """
    import re
    folder_path = Path(folder_path)
    
    participants = []
    message_count = 0
    
    # Try JSON first (message_1.json has participant info)
    message_1 = folder_path / "message_1.json"
    if message_1.exists():
        try:
            with open(message_1, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Extract participants from JSON
            if 'participants' in data:
                for p in data['participants']:
                    name = p.get('name', 'Unknown')
                    # Fix Instagram's mojibake encoding
                    try:
                        name = name.encode('latin-1').decode('utf-8')
                    except:
                        pass
                    participants.append(name)
            
            # Count messages across all message JSON files
            for msg_file in folder_path.glob("message_*.json"):
                try:
                    with open(msg_file, 'r', encoding='utf-8') as f:
                        msg_data = json.load(f)
                        message_count += len(msg_data.get('messages', []))
                except:
                    pass
        except Exception as e:
            print(f"Error reading JSON conversation preview: {e}")
    
    # Try HTML files if no JSON participants found
    html_files = list(folder_path.glob("*.html"))
    if not participants and html_files:
        try:
            # Parse first HTML file to get participants
            with open(html_files[0], 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Extract participants from sender name headers
            sender_pattern = r'<h2[^>]*class="[^"]*_a6-h[^"]*"[^>]*>([^<]+)</h2>'
            found_participants = set()
            for match in re.findall(sender_pattern, content):
                name = match.strip()
                if name:
                    found_participants.add(name)
            participants = sorted(list(found_participants))
            
            # Count messages from HTML (each message block has _a6-g class)
            for html_file in html_files:
                try:
                    with open(html_file, 'r', encoding='utf-8') as f:
                        html_content = f.read()
                    # Count message blocks
                    message_count += len(re.findall(r'<div class="pam _3-95 _2ph- _a6-g uiBoxWhite noborder">', html_content))
                except:
                    pass
        except Exception as e:
            print(f"Error reading HTML conversation preview: {e}")
    
    # Also count HTML messages if we have participants from JSON (mixed case)
    elif participants and html_files:
        for html_file in html_files:
            try:
                with open(html_file, 'r', encoding='utf-8') as f:
                    html_content = f.read()
                # Don't double count if we already counted JSON
                message_count += len(re.findall(r'<div class="pam _3-95 _2ph- _a6-g uiBoxWhite noborder">', html_content))
            except:
                pass
    
    if not participants:
        return None
    
    # Create display name from participants
    display_name = ", ".join(participants[:2])
    if len(participants) > 2:
        display_name += f" +{len(participants) - 2}"
    
    return {
        "display_name": display_name,
        "participants": participants,
        "message_count": message_count
    }


def merge_conversation_messages(folder_path):
    """
    Merge all message files (JSON and/or HTML) in a conversation folder into a single JSON object.
    
    Args:
        folder_path: Path to the conversation folder
        
    Returns:
        Combined JSON data with all messages in Instagram JSON format
    """
    import re
    from datetime import datetime
    
    folder_path = Path(folder_path)
    
    # Find all message files
    json_files = sorted(
        folder_path.glob("message_*.json"),
        key=lambda x: int(x.stem.split('_')[1]),
        reverse=True  # Start from highest number (oldest) to lowest (newest)
    )
    html_files = list(folder_path.glob("*.html"))
    
    if not json_files and not html_files:
        return None
    
    all_messages = []
    participants_set = set()
    
    # Process JSON files
    if json_files:
        # Start with the first file as base (has participants info)
        first_file = folder_path / "message_1.json"
        if not first_file.exists():
            first_file = json_files[-1]  # Use lowest number file
        
        with open(first_file, 'r', encoding='utf-8') as f:
            combined_data = json.load(f)
        
        # Extract participants from JSON
        if 'participants' in combined_data:
            for p in combined_data['participants']:
                name = p.get('name', 'Unknown')
                try:
                    name = name.encode('latin-1').decode('utf-8')
                except:
                    pass
                participants_set.add(name)
        
        # Collect messages from all JSON files
        for msg_file in json_files:
            try:
                with open(msg_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    messages = data.get('messages', [])
                    all_messages.extend(messages)
            except Exception as e:
                print(f"Error reading {msg_file}: {e}")
    else:
        # No JSON files, create base structure
        combined_data = {'participants': [], 'messages': []}
    
    # Process HTML files
    for html_file in html_files:
        try:
            with open(html_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Parse HTML message blocks
            block_pattern = r'<div class="pam _3-95 _2ph- _a6-g uiBoxWhite noborder">(.*?)</div>\s*<div class="_3-94 _a6-o">([^<]+)</div>'
            
            for block_match in re.finditer(block_pattern, content, re.DOTALL):
                block_content = block_match.group(1)
                timestamp_str = block_match.group(2).strip()
                
                # Extract sender name
                sender_match = re.search(r'<h2[^>]*class="[^"]*_a6-h[^"]*"[^>]*>([^<]+)</h2>', block_content)
                if not sender_match:
                    continue
                sender = sender_match.group(1).strip()
                participants_set.add(sender)
                
                # Extract message content
                content_match = re.search(r'<div class="_3-95 _a6-p"><div>(?:<div></div>)?<div>([^<]*)</div>', block_content)
                if content_match:
                    msg_content = content_match.group(1).strip()
                else:
                    content_match = re.search(r'<div class="_3-95 _a6-p">(.*?)</div>\s*</div>', block_content, re.DOTALL)
                    if content_match:
                        inner = content_match.group(1)
                        msg_content = re.sub(r'<[^>]+>', ' ', inner).strip()
                        msg_content = ' '.join(msg_content.split())
                    else:
                        msg_content = ""
                
                # Skip empty messages or attachment placeholders
                if not msg_content or msg_content.lower().endswith('sent an attachment.'):
                    continue
                
                # Parse timestamp to milliseconds
                try:
                    dt = datetime.strptime(timestamp_str, "%b %d, %Y %I:%M %p")
                except ValueError:
                    try:
                        dt = datetime.strptime(timestamp_str, "%b %d, %Y %I:%M%p")
                    except ValueError:
                        try:
                            dt = datetime.strptime(timestamp_str.lower(), "%b %d, %Y %I:%M %p")
                        except:
                            dt = datetime.now()
                
                timestamp_ms = int(dt.timestamp() * 1000)
                
                # Create Instagram-format message object
                all_messages.append({
                    'sender_name': sender,
                    'content': msg_content,
                    'timestamp_ms': timestamp_ms
                })
        except Exception as e:
            print(f"Error reading HTML file {html_file}: {e}")
    
    # Sort messages by timestamp (oldest first for consistency)
    all_messages.sort(key=lambda x: x.get('timestamp_ms', 0))
    
    # Build participants list if needed
    if not combined_data.get('participants'):
        combined_data['participants'] = [{'name': name} for name in sorted(participants_set)]
    
    # Update combined data with all messages
    combined_data['messages'] = all_messages
    
    return combined_data


def cleanup_zip(zip_id):
    """
    Clean up temporary files for a ZIP extraction.
    
    Args:
        zip_id: The ZIP identifier
    """
    extract_dir = TEMP_ZIP_DIR / zip_id
    if extract_dir.exists():
        shutil.rmtree(extract_dir)


def cleanup_all_temp():
    """Clean up all temporary ZIP files."""
    if TEMP_ZIP_DIR.exists():
        for item in TEMP_ZIP_DIR.iterdir():
            if item.is_dir():
                shutil.rmtree(item)
            else:
                item.unlink()


if __name__ == "__main__":
    # Test the module
    import sys
    
    if len(sys.argv) >= 2:
        zip_path = sys.argv[1]
        zip_id = "test_extraction"
        
        print(f"Extracting {zip_path}...")
        extracted = extract_zip(zip_path, zip_id)
        print(f"Extracted to: {extracted}")
        
        print("\nFinding conversations...")
        conversations = find_conversations(extracted)
        
        for conv in conversations:
            print(f"\n  {conv['display_name']}")
            print(f"    Folder: {conv['folder_name']}")
            print(f"    Participants: {conv['participants']}")
            print(f"    Messages: {conv['message_count']}")
        
        # Cleanup
        cleanup_zip(zip_id)
        print("\nCleaned up temp files.")
    else:
        print("Usage: python instagram_zip_processor.py <zip_file_path>")
