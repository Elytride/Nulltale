"""
WaveSpeed Voice Manager
-----------------------
Simple interface for WaveSpeed MiniMax Speech 2.6 Turbo API.
Users only need to provide:
1. API key
2. Audio file for voice cloning

All other settings are handled automatically with sensible defaults.
"""
import os
import io
import requests
import logging
from pathlib import Path
from typing import Optional

# Setup logging
logging.basicConfig(level=logging.WARNING)
logger = logging.getLogger("WaveSpeedManager")


class WaveSpeedManager:
    """
    Simplified WaveSpeed TTS with voice cloning.
    
    Usage:
        manager = WaveSpeedManager(api_key="your-key")
        
        # Clone your voice (one-time setup)
        manager.clone_voice("my_voice", "path/to/audio.wav")
        
        # Speak with cloned voice
        audio_bytes = manager.speak("Hello!", "my_voice")
    """
    
    # API Configuration
    BASE_URL = "https://api.wavespeed.ai"
    CLONE_ENDPOINT = "/api/v3/minimax/voice-clone"
    TTS_ENDPOINT = "/api/v3/minimax/speech-2.6-turbo"
    
    # System voices (no cloning needed)
    SYSTEM_VOICES = [
        "Wise_Woman",
        "Friendly_Person", 
        "Deep_Voice_Man",
        "Calm_Woman",
        "Inspirational_girl"
    ]
    
    # Default TTS settings (optimized for natural speech)
    DEFAULT_SETTINGS = {
        "speed": 1.0,
        "volume": 1.0,
        "pitch": 0,
        "sample_rate": 24000,
        "format": "wav",
        "english_normalization": True
    }
    
    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize WaveSpeed manager.
        
        Args:
            api_key: WaveSpeed API key. If not provided, reads from 
                     WAVESPEED_API_KEY environment variable.
        """
        self.api_key = api_key or os.environ.get("WAVESPEED_API_KEY")
        if not self.api_key:
            raise ValueError(
                "API key required. Pass api_key or set WAVESPEED_API_KEY environment variable.\n"
                "Get your API key from: https://wavespeed.ai"
            )
        
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        # Store cloned voice IDs
        self._cloned_voices = {}
        
        logger.info("WaveSpeedManager initialized")
    
    def clone_voice(
        self, 
        voice_name: str, 
        audio_path: str,
        noise_reduction: bool = True,
        volume_normalization: bool = True
    ) -> str:
        """
        Clone a voice from an audio file.
        
        Args:
            voice_name: Name for this voice (will be used as ID).
                        Must be 8+ chars, start with letter, alphanumeric.
            audio_path: Path to audio file (MP3, M4A, or WAV, 10s-5min, max 20MB)
            noise_reduction: Auto-clean background noise (recommended)
            volume_normalization: Auto-level volume (recommended)
        
        Returns:
            The voice_id to use in speak() calls
        
        Example:
            manager.clone_voice("MyVoice01", "recording.wav")
        """
        import base64
        
        audio_file = Path(audio_path)
        if not audio_file.exists():
            raise FileNotFoundError(f"Audio file not found: {audio_path}")
        
        # Validate voice name format (min 8 chars, starts with letter, alphanumeric)
        voice_id = self._format_voice_id(voice_name)
        
        logger.info(f"Cloning voice '{voice_id}' from {audio_file.name}...")
        
        # Step 1: Upload audio file to WaveSpeed Media Upload API
        mime_type = self._get_mime_type(audio_file)
        with open(audio_file, "rb") as f:
            files = {"file": (audio_file.name, f, mime_type)}
            upload_response = requests.post(
                f"{self.BASE_URL}/api/v3/media/upload/binary",
                headers={"Authorization": f"Bearer {self.api_key}"},
                files=files
            )
        
        if upload_response.status_code != 200:
            raise Exception(f"Audio upload failed: {upload_response.status_code} - {upload_response.text}")
        
        upload_result = upload_response.json()
        
        # DEBUG: Log upload response
        logger.info(f"Upload response: {upload_result}")
        
        # Handle different response structures
        data_obj = upload_result.get("data") if isinstance(upload_result.get("data"), dict) else {}
        audio_url = (
            data_obj.get("download_url") or 
            upload_result.get("download_url") or 
            upload_result.get("url")
        )
        
        # If data is a string, it might be the URL directly
        if not audio_url and isinstance(upload_result.get("data"), str):
            audio_url = upload_result.get("data")
        
        if not audio_url:
            raise Exception(f"No download_url in upload response: {upload_result}")
        
        logger.info(f"Audio uploaded successfully: {audio_url}")
        
        # Step 2: Call voice clone endpoint with the uploaded audio URL
        payload = {
            "model": "speech-02-hd",
            "audio": audio_url,
            "custom_voice_id": voice_id,
            "text": "Hello, this is a test of my cloned voice."
        }
        
        response = requests.post(
            f"{self.BASE_URL}{self.CLONE_ENDPOINT}",
            headers=self.headers,
            json=payload
        )
        
        if response.status_code != 200:
            raise Exception(f"Voice cloning failed: {response.status_code} - {response.text}")
        
        result = response.json()
        
        # DEBUG: Save full response to file
        try:
            debug_path = Path(__file__).parent.parent / "data" / "debug_wavespeed_clone.json"
            with open(debug_path, "w", encoding="utf-8") as f:
                import json
                json.dump(result, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save debug logs: {e}")
        
        # Extract the actual voice_id from WaveSpeed's response
        # The API may assign a different ID than what we requested
        data_obj = result.get("data") if isinstance(result.get("data"), dict) else {}
        
        # Check if async (has polling URL)
        result_url = data_obj.get("urls", {}).get("get")
        if result_url:
            logger.info("Voice cloning initiated (async). Polling for completion...")
            import time
            max_attempts = 120  # Wait up to 120 seconds
            
            for attempt in range(max_attempts):
                time.sleep(1)
                poll_response = requests.get(result_url, headers=self.headers)
                
                if poll_response.status_code == 200:
                    poll_result = poll_response.json()
                    poll_data = poll_result.get("data") if isinstance(poll_result.get("data"), dict) else {}
                    status = poll_data.get("status") or poll_result.get("status")
                    
                    if status == "completed":
                        # Success!
                         # DEBUG: Save completed response
                        try:
                            debug_path = Path(__file__).parent.parent / "data" / "debug_wavespeed_clone_completed.json"
                            with open(debug_path, "w", encoding="utf-8") as f:
                                json.dump(poll_result, f, indent=2)
                        except: pass

                        # Extract voice ID from response
                        outputs = poll_data.get("outputs", [])
                        output_voice_id = None
                        if outputs and len(outputs) > 0:
                            first_output = outputs[0]
                            if isinstance(first_output, dict):
                                output_voice_id = first_output.get("voice_id")
                        
                        returned_voice_id = (
                            poll_data.get("voice_id") or 
                            poll_data.get("custom_voice_id") or
                            output_voice_id or
                            voice_id  # Fallback
                        )
                        break
                    elif status == "failed":
                        # DEBUG: Save failed response
                        try:
                            debug_path = Path(__file__).parent.parent / "data" / "debug_wavespeed_clone_failed.json"
                            with open(debug_path, "w", encoding="utf-8") as f:
                                json.dump(poll_result, f, indent=2)
                        except: pass
                        
                        error = poll_data.get("error") or poll_result.get("error", "Unknown error")
                        raise Exception(f"Voice cloning failed: {error}")
            else:
                raise Exception("Voice cloning timeout: process did not complete in 120 seconds")
        else:
            # Sync response (fallback parsing)
            returned_voice_id = (
                result.get("voice_id") or 
                data_obj.get("voice_id") or 
                data_obj.get("custom_voice_id") or
                voice_id  # Fallback to our requested ID
            )
        
        # Store the voice ID
        self._cloned_voices[voice_name] = returned_voice_id
        
        logger.info(f"Voice '{returned_voice_id}' cloned successfully! (Response: {result})")
        return returned_voice_id
    
    def speak(
        self, 
        text: str, 
        voice: str = "Deep_Voice_Man",
        **kwargs
    ) -> io.BytesIO:
        """
        Generate speech from text.
        
        Args:
            text: Text to speak (max 10,000 characters)
            voice: Voice name (system voice or cloned voice name)
            **kwargs: Optional overrides (speed, volume, pitch, emotion, etc.)
        
        Returns:
            BytesIO containing WAV audio data
        
        Example:
            audio = manager.speak("Hello world!", "MyVoice01")
            with open("output.wav", "wb") as f:
                f.write(audio.read())
        """
        if not text:
            raise ValueError("Text cannot be empty")
        
        if len(text) > 10000:
            raise ValueError("Text exceeds 10,000 character limit")
        
        # Resolve voice ID (check if it's a cloned voice name)
        voice_id = self._cloned_voices.get(voice, voice)
        
        # Build request with defaults + overrides
        payload = {
            "model": "speech-2.6-turbo",
            "text": text,
            "voice_id": voice_id,
            **self.DEFAULT_SETTINGS,
            **kwargs
        }
        
        logger.info(f"Generating speech with voice '{voice_id}'...")
        
        response = requests.post(
            f"{self.BASE_URL}{self.TTS_ENDPOINT}",
            headers=self.headers,
            json=payload
        )
        
        if response.status_code != 200:
            raise Exception(f"TTS failed: {response.status_code} - {response.text}")
        
        # Handle response - could be direct audio or async JSON with result URL
        content_type = response.headers.get("Content-Type", "")
        
        if "audio" in content_type:
            # Direct audio response
            buffer = io.BytesIO(response.content)
            buffer.seek(0)
            return buffer
        else:
            # Async JSON response - need to poll for result
            import time
            result = response.json()
            
            # Check for direct audio URL first
            audio_url = result.get("audio_url") or result.get("data", {}).get("audio_url")
            
            if audio_url:
                audio_response = requests.get(audio_url)
                buffer = io.BytesIO(audio_response.content)
                buffer.seek(0)
                return buffer
            
            # Otherwise poll the result URL (async pattern)
            data_obj = result.get("data") if isinstance(result.get("data"), dict) else {}
            result_url = data_obj.get("urls", {}).get("get")
            
            if result_url:
                # Poll for result with timeout
                max_attempts = 30
                for attempt in range(max_attempts):
                    time.sleep(1)  # Wait 1 second between polls
                    poll_response = requests.get(result_url, headers=self.headers)
                    if poll_response.status_code == 200:
                        poll_result = poll_response.json()
                        poll_data = poll_result.get("data") if isinstance(poll_result.get("data"), dict) else {}
                        
                        status = poll_data.get("status") or poll_result.get("status")
                        
                        if status == "completed":
                            # Get audio URL from outputs
                            outputs = poll_data.get("outputs") or poll_result.get("outputs", [])
                            if outputs and len(outputs) > 0:
                                # Handle both string URLs and dict objects
                                first_output = outputs[0]
                                if isinstance(first_output, str):
                                    audio_url = first_output
                                elif isinstance(first_output, dict):
                                    audio_url = first_output.get("audio") or first_output.get("url") or first_output.get("audio_url")
                                else:
                                    audio_url = None
                                
                                if audio_url and isinstance(audio_url, str) and audio_url.startswith("http"):
                                    audio_response = requests.get(audio_url)
                                    buffer = io.BytesIO(audio_response.content)
                                    buffer.seek(0)
                                    return buffer
                            raise Exception(f"No audio in completed response: {poll_result}")
                        elif status == "failed":
                            error = poll_data.get("error") or poll_result.get("error", "Unknown error")
                            raise Exception(f"TTS job failed: {error}")
                        # else: still processing, continue polling
                
                raise Exception("TTS timeout: job did not complete in 30 seconds")
            
            raise Exception(f"No audio in response: {result}")
    
    def list_voices(self) -> dict:
        """
        List available voices.
        
        Returns:
            Dict with 'system' and 'cloned' voice lists
        """
        return {
            "system": self.SYSTEM_VOICES.copy(),
            "cloned": list(self._cloned_voices.keys())
        }
    
    def _format_voice_id(self, name: str) -> str:
        """Format voice name to valid voice_id (8+ chars, starts with letter, alphanumeric)."""
        import time
        
        # Remove invalid characters
        clean = ''.join(c for c in name if c.isalnum() or c == '_')
        
        # Ensure starts with letter
        if not clean or not clean[0].isalpha():
            clean = "Voice" + clean
        
        # Add timestamp suffix for uniqueness
        timestamp = str(int(time.time()))[-6:]  # Last 6 digits of timestamp
        clean = clean + timestamp
        
        # Ensure minimum 8 characters
        if len(clean) < 8:
            clean = clean + "0" * (8 - len(clean))
        
        return clean
    
    def _get_mime_type(self, file_path: Path) -> str:
        """Get MIME type for audio file."""
        suffix = file_path.suffix.lower()
        mime_types = {
            ".wav": "audio/wav",
            ".mp3": "audio/mpeg",
            ".m4a": "audio/mp4"
        }
        return mime_types.get(suffix, "audio/wav")


# Convenience function for quick usage
def quick_speak(text: str, api_key: str, voice: str = "Deep_Voice_Man") -> io.BytesIO:
    """
    Quick one-liner TTS without creating a manager instance.
    
    Example:
        audio = quick_speak("Hello!", api_key="your-key")
    """
    manager = WaveSpeedManager(api_key=api_key)
    return manager.speak(text, voice)
