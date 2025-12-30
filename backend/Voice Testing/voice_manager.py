"""
NullTale Voice Manager
----------------------
Handles:
1. Loading Coqui XTTS model (Zero-shot).
2. 'Training' voices: Computing conditioning latents from reference audio once and saving them.
3. Synthesis: Using saved latents to generate speech (faster, consistent).
4. Output: Returning audio generation as in-memory bytes.
"""
import os
import io
import torch
import shutil
import logging
import torchaudio
from pathlib import Path
from typing import List, Union, Optional
import numpy as np
from TTS.api import TTS
from TTS.tts.configs.xtts_config import XttsConfig
from TTS.tts.models.xtts import XttsAudioConfig
from pydub import AudioSegment

# Setup logging (WARNING level to reduce noise)
logging.basicConfig(level=logging.WARNING)
logger = logging.getLogger("VoiceManager")

# Fix for PyTorch 2.6+ weights_only=True
torch.serialization.add_safe_globals([XttsConfig, XttsAudioConfig])

class VoiceManager:
    # ---------------------------------------------------------
    # CONFIGURATION: Default voice to use when none specified
    # Change this to match your saved voice name
    # ---------------------------------------------------------
    DEFAULT_VOICE = "test_voice"  # e.g., "alan", "ada", etc.
    # ---------------------------------------------------------
    
    def __init__(self, storage_dir: str = "voices", model_name: str = "tts_models/multilingual/multi-dataset/xtts_v2"):
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.model_name = model_name
        self._tts = None  # Lazy load
        
        # Directory to store computed speaker embeddings (latents)
        self.storage_dir = Path(__file__).parent / storage_dir
        self.storage_dir.mkdir(exist_ok=True)
        
        self._setup_ffmpeg()
        logger.info(f"VoiceManager initialized. Device: {self.device}, Storage: {self.storage_dir}")

    def list_voices(self) -> List[str]:
        """Returns a list of available saved voice names."""
        voices = [f.stem for f in self.storage_dir.glob("*.pth")]
        return voices

    def _setup_ffmpeg(self):
        """Ensures ffmpeg is available for audio conversion."""
        # Check local ffmpeg
        local_ffmpeg = Path(__file__).parent / "ffmpeg.exe"
        if local_ffmpeg.exists():
            AudioSegment.converter = str(local_ffmpeg)
            os.environ["PATH"] += os.pathsep + str(local_ffmpeg.parent)
            return

        if not shutil.which("ffmpeg"):
            logger.warning("ffmpeg not found! Audio conversion may fail.")

    @property
    def model(self):
        """Lazy loads the TTS model."""
        if self._tts is None:
            logger.info(f"Loading TTS model: {self.model_name}...")
            self._tts = TTS(self.model_name).to(self.device)
            logger.info("Model loaded.")
        return self._tts

    def _ensure_wav_paths(self, file_paths: List[str]) -> List[str]:
        """Converts any non-wav files to wav and returns valid paths."""
        valid_paths = []
        for fp in file_paths:
            path = Path(fp)
            if not path.exists():
                logger.warning(f"Reference file not found: {fp}")
                continue
                
            if path.suffix.lower() == ".wav":
                valid_paths.append(str(path))
            else:
                # Convert
                wav_path = path.with_suffix(".wav")
                try:
                    # Only convert if wav doesn't exist or we want to overwrite? 
                    # For now, just convert if needed.
                    if not wav_path.exists():
                        logger.info(f"Converting {path.name} to WAV...")
                        audio = AudioSegment.from_file(str(path))
                        audio.export(str(wav_path), format="wav")
                    valid_paths.append(str(wav_path))
                except Exception as e:
                    logger.error(f"Failed to convert {path}: {e}")
        return valid_paths

    def add_voice(self, voice_name: str, reference_files: List[str]):
        """
        Computes speaker embeddings from reference files and saves them to disk.
        This represents 'saving the voice model' so we don't process audio every time.
        """
        refs = self._ensure_wav_paths(reference_files)
        if not refs:
            raise ValueError("No valid reference audio files provided.")

        logger.info(f"Computing embeddings for voice '{voice_name}' using {len(refs)} files...")
        
        # Access the underlying XTTS model to compute latents
        # Correct path from debug: synthesizer.tts_model
        gpt_cond_latent, speaker_embedding = self.model.synthesizer.tts_model.get_conditioning_latents(
            audio_path=refs
        )
        
        # Save tensors to disk
        save_path = self.storage_dir / f"{voice_name}.pth"
        torch.save({
            "gpt_cond_latent": gpt_cond_latent,
            "speaker_embedding": speaker_embedding
        }, save_path)
        
        logger.info(f"Voice '{voice_name}' saved to {save_path}")
        return str(save_path)

    def speak(self, text: str, voice_name: str, language: str = "en") -> io.BytesIO:
        """
        Generates speech using a saved voice profile.
        Returns: BytesIO object containing the WAV audio.
        """
        voice_path = self.storage_dir / f"{voice_name}.pth"
        if not voice_path.exists():
            raise ValueError(f"Voice '{voice_name}' not found. Call add_voice() first.")

        # Load latents
        latents = torch.load(voice_path, weights_only=True)
        gpt_cond_latent = latents["gpt_cond_latent"]
        speaker_embedding = latents["speaker_embedding"]
        
        logger.info(f"Synthesizing text for '{voice_name}'...")
        
        # Run inference directly on the model
        out = self.model.synthesizer.tts_model.inference(
            text=text,
            language=language,
            gpt_cond_latent=gpt_cond_latent,
            speaker_embedding=speaker_embedding,
            enable_text_splitting=True
        )
        
        # Output is commonly a dictionary with "wav" key
        wav_data = out["wav"]
        
        # Convert to tensor if it's a numpy array
        if isinstance(wav_data, np.ndarray):
            wav_tensor = torch.from_numpy(wav_data)
        else:
            wav_tensor = wav_data
        
        # Tensor should be [Channels, N] for torchaudio. XTTS outputs [N]
        if wav_tensor.dim() == 1:
            wav_tensor = wav_tensor.unsqueeze(0)
            
        # Move to CPU for saving
        wav_tensor = wav_tensor.cpu().float()
        
        # Save to buffer
        buffer = io.BytesIO()
        torchaudio.save(buffer, wav_tensor, 24000, format="wav") # XTTS sample rate is 24000
        buffer.seek(0)
        
        return buffer
