"""
NullTale Voice Interface (CLI)
------------------------------
Wrapper for VoiceManager (TTS) and STTManager (STT).
Usage:
    python voice.py add <voice_name> <file1> [file2 ...]
    python voice.py speak <voice_name> "Text to speak"
    python voice.py transcribe <audio_file>
"""
import sys
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

    # Transcribe Command (STT)
    transcribe_parser = subparsers.add_parser("transcribe", help="Transcribe audio to text")
    transcribe_parser.add_argument("file", help="Path to audio file to transcribe")
    transcribe_parser.add_argument("--lang", default=None, help="Language code (e.g., 'en', 'zh'). Auto-detects if omitted.")

    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return

    # Handle TTS commands
    if args.command in ["add", "speak"]:
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

if __name__ == "__main__":
    main()
