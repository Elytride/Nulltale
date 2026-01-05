"""
NullTale Voice Interface (CLI)
------------------------------
Wrapper for VoiceManager (TTS) and STTManager (STT).
Usage:
    python voice.py add <voice_name> <file1> [file2 ...]
    python voice.py speak <voice_name> "Text to speak"
    python voice.py transcribe <audio_file>
    
    # WaveSpeed (cloud TTS with voice cloning)
    python voice.py wavespeed clone <voice_name> <audio_file> --api-key <key>
    python voice.py wavespeed speak "Text" --voice <voice> --api-key <key>
    python voice.py wavespeed voices
"""
import sys
import os
import argparse
from pathlib import Path
from voice_manager import VoiceManager
from stt_manager import STTManager

def main():
    parser = argparse.ArgumentParser(description="NullTale Voice Cloning CLI")
    subparsers = parser.add_subparsers(dest="command", help="Command to run")

    # Add Voice Command
    add_parser = subparsers.add_parser("add", help="Create/Save a voice model from audio files")
    add_parser.add_argument("name", help="Name of the voice (e.g., 'alan', 'ada')")
    add_parser.add_argument("files", nargs="+", help="Path(s) to reference audio files (wav, mp3, m4a)")

    # Speak Command
    speak_parser = subparsers.add_parser("speak", help="Generate speech using a saved voice")
    speak_parser.add_argument("name", help="Name of the voice to use")
    speak_parser.add_argument("text", help="Text to speak")
    speak_parser.add_argument("--out", default="output/output.wav", help="Output filename (relative to Voice Testing)")

    # Speak Stream Command
    stream_parser = subparsers.add_parser("speak-stream", help="Generate speech using streaming (lower latency)")
    stream_parser.add_argument("name", help="Name of the voice to use")
    stream_parser.add_argument("text", help="Text to speak")
    stream_parser.add_argument("--out", default="output/output_stream.wav", help="Output filename (relative to Voice Testing)")

    # Transcribe Command (STT)
    transcribe_parser = subparsers.add_parser("transcribe", help="Transcribe audio to text")
    transcribe_parser.add_argument("file", help="Path to audio file to transcribe")
    transcribe_parser.add_argument("--lang", default=None, help="Language code (e.g., 'en', 'zh'). Auto-detects if omitted.")

    # ========================================
    # WaveSpeed Commands (Cloud TTS)
    # ========================================
    wavespeed_parser = subparsers.add_parser("wavespeed", help="WaveSpeed cloud TTS with voice cloning")
    wavespeed_sub = wavespeed_parser.add_subparsers(dest="wavespeed_cmd", help="WaveSpeed command")
    
    # WaveSpeed Clone
    ws_clone = wavespeed_sub.add_parser("clone", help="Clone your voice from an audio file")
    ws_clone.add_argument("name", help="Name for your cloned voice (e.g., 'MyVoice')")
    ws_clone.add_argument("audio", help="Path to audio file (10s-5min, MP3/WAV/M4A)")
    ws_clone.add_argument("--api-key", help="WaveSpeed API key (or set WAVESPEED_API_KEY env var)")
    
    # WaveSpeed Speak
    ws_speak = wavespeed_sub.add_parser("speak", help="Generate speech with WaveSpeed")
    ws_speak.add_argument("text", help="Text to speak")
    ws_speak.add_argument("--voice", default="Deep_Voice_Man", help="Voice to use (cloned name or system voice)")
    ws_speak.add_argument("--api-key", help="WaveSpeed API key (or set WAVESPEED_API_KEY env var)")
    ws_speak.add_argument("--out", default="output/wavespeed_output.wav", help="Output filename")
    
    # WaveSpeed List Voices
    ws_voices = wavespeed_sub.add_parser("voices", help="List available voices")

    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return

    # Handle TTS commands
    if args.command in ["add", "speak", "speak-stream"]:
        manager = VoiceManager()

        if args.command == "add":
            try:
                print(f"Adding voice '{args.name}' from files: {args.files}")
                path = manager.add_voice(args.name, args.files)
                print(f"Success! Voice saved to: {path}")
            except Exception as e:
                print(f"Error adding voice: {e}")

        elif args.command == "speak":
            try:
                print(f"Generating speech for '{args.name}'...")
                audio_buffer = manager.speak(args.text, args.name)
                
                # Resolve output path relative to script directory
                script_dir = Path(__file__).parent
                out_path = script_dir / args.out
                out_path.parent.mkdir(parents=True, exist_ok=True)
                
                # Write buffer to file
                with open(out_path, "wb") as f:
                    f.write(audio_buffer.read())
                
                print(f"Success! Audio saved to: {out_path}")
            except Exception as e:
                print(f"Error generating speech: {e}")

        elif args.command == "speak-stream":
            try:
                print(f"Generating speech (streaming) for '{args.name}'...")
                
                # Resolve output path relative to script directory
                script_dir = Path(__file__).parent
                out_path = script_dir / args.out
                out_path.parent.mkdir(parents=True, exist_ok=True)
                
                # Collect all chunks and write to file
                all_audio = b""
                chunk_count = 0
                for chunk_buffer in manager.speak_stream(args.text, args.name):
                    chunk_count += 1
                    print(f"  Received chunk {chunk_count}...")
                    all_audio += chunk_buffer.read()
                
                # Write combined audio to file
                with open(out_path, "wb") as f:
                    f.write(all_audio)
                
                print(f"Success! Streamed {chunk_count} chunks. Audio saved to: {out_path}")
            except Exception as e:
                print(f"Error generating speech (stream): {e}")

    # Handle STT commands
    elif args.command == "transcribe":
        stt = STTManager()
        try:
            result = stt.transcribe(args.file, language=args.lang)
            print(f"\n--- Transcription ---")
            print(f"Language: {result['language']}")
            print(f"Text: {result['text']}")
        except Exception as e:
            print(f"Error transcribing: {e}")

    # Handle WaveSpeed commands
    elif args.command == "wavespeed":
        from wavespeed_manager import WaveSpeedManager
        
        if not args.wavespeed_cmd:
            wavespeed_parser.print_help()
            return
        
        # Set API key from arg or env
        api_key = getattr(args, 'api_key', None) or os.environ.get("WAVESPEED_API_KEY")
        
        if args.wavespeed_cmd == "voices":
            # List voices doesn't need API key
            print("\n=== Available WaveSpeed Voices ===")
            print("\nSystem Voices (no cloning needed):")
            for v in WaveSpeedManager.SYSTEM_VOICES:
                print(f"  - {v}")
            print("\nTo clone your own voice:")
            print("  python voice.py wavespeed clone MyVoice audio.wav --api-key <key>")
            return
        
        if not api_key:
            print("Error: API key required. Use --api-key or set WAVESPEED_API_KEY env var.")
            print("Get your key from: https://wavespeed.ai")
            return
        
        try:
            manager = WaveSpeedManager(api_key=api_key)
            
            if args.wavespeed_cmd == "clone":
                print(f"Cloning voice '{args.name}' from {args.audio}...")
                voice_id = manager.clone_voice(args.name, args.audio)
                print(f"\nSuccess! Voice cloned.")
                print(f"Voice ID: {voice_id}")
                print(f"\nNow use it with:")
                print(f'  python voice.py wavespeed speak "Hello!" --voice {args.name}')
            
            elif args.wavespeed_cmd == "speak":
                print(f"Generating speech with voice '{args.voice}'...")
                audio_buffer = manager.speak(args.text, args.voice)
                
                # Save output
                script_dir = Path(__file__).parent
                out_path = script_dir / args.out
                out_path.parent.mkdir(parents=True, exist_ok=True)
                
                with open(out_path, "wb") as f:
                    f.write(audio_buffer.read())
                
                print(f"\nSuccess! Audio saved to: {out_path}")
        
        except Exception as e:
            print(f"Error: {e}")

if __name__ == "__main__":
    main()

