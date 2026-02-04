"""
AlterEcho STT Manager
--------------------
Handles Speech-to-Text using Google Cloud Speech-to-Text API.
Transcribes audio files to text.
"""
import os
import io
import logging
from pathlib import Path
from typing import Optional
from google.cloud import speech
from pydub import AudioSegment

# Setup logging
logging.basicConfig(level=logging.WARNING)
logger = logging.getLogger("STTManager")


class STTManager:
    # ---------------------------------------------------------
    # CONFIGURATION
    # ---------------------------------------------------------
    DEFAULT_LANGUAGE = "en-US"  # e.g., "en-US", "zh-CN", "ms-MY"
    # ---------------------------------------------------------
    
    def __init__(self):
        # Uses GOOGLE_APPLICATION_CREDENTIALS env var automatically
        self.client = speech.SpeechClient()
        print("STTManager initialized (Google Cloud Speech-to-Text)")

    def _convert_to_linear16(self, audio_path: str) -> tuple[bytes, int]:
        """Converts audio to LINEAR16 format required by Google STT."""
        audio = AudioSegment.from_file(audio_path)
        
        # Convert to mono, 16kHz, 16-bit
        audio = audio.set_channels(1)
        audio = audio.set_frame_rate(16000)
        audio = audio.set_sample_width(2)  # 16-bit = 2 bytes
        
        # Export to bytes
        buffer = io.BytesIO()
        audio.export(buffer, format="wav")
        buffer.seek(0)
        
        # Skip WAV header (44 bytes) to get raw PCM
        buffer.read(44)
        raw_audio = buffer.read()
        
        return raw_audio, 16000

    def transcribe(self, audio_path: str, language: Optional[str] = None) -> dict:
        """
        Transcribes audio file to text using Google Cloud STT.
        
        Args:
            audio_path: Path to audio file (wav, mp3, m4a, etc.)
            language: Language code (e.g., "en-US", "zh-CN"). Uses DEFAULT_LANGUAGE if None.
            
        Returns:
            dict with keys: "text", "language", "confidence"
        """
        path = Path(audio_path)
        if not path.exists():
            raise FileNotFoundError(f"Audio file not found: {audio_path}")

        print(f"Transcribing: {path.name}...")
        
        # Convert to LINEAR16
        audio_content, sample_rate = self._convert_to_linear16(str(path))
        
        # Build request
        audio = speech.RecognitionAudio(content=audio_content)
        config = speech.RecognitionConfig(
            encoding=speech.RecognitionConfig.AudioEncoding.LINEAR16,
            sample_rate_hertz=sample_rate,
            language_code=language or self.DEFAULT_LANGUAGE,
            enable_automatic_punctuation=True,
        )
        
        # Call API
        response = self.client.recognize(config=config, audio=audio)
        
        # Extract results
        if not response.results:
            return {
                "text": "",
                "language": language or self.DEFAULT_LANGUAGE,
                "confidence": 0.0
            }
        
        # Combine all transcripts
        full_text = " ".join(
            result.alternatives[0].transcript 
            for result in response.results
        )
        
        avg_confidence = sum(
            result.alternatives[0].confidence 
            for result in response.results
        ) / len(response.results)
        
        return {
            "text": full_text.strip(),
            "language": language or self.DEFAULT_LANGUAGE,
            "confidence": avg_confidence
        }
