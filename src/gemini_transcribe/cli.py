"""
Command-line interface for gemini-transcribe.
"""

import argparse
import sys
from pathlib import Path

from . import __version__
from .transcriber import Transcriber


def main():
    """Main CLI entrypoint."""
    parser = argparse.ArgumentParser(
        prog="gemini-transcribe",
        description="Transcribe long audio files using Google's Gemini API with chunking for quality.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Basic usage
  gemini-transcribe interview.wav

  # With custom output file
  gemini-transcribe interview.wav -o my_transcript.md

  # With custom instructions file
  gemini-transcribe interview.wav --instructions transcription_instructions.md

  # With custom chunk size (30 minutes)
  gemini-transcribe interview.wav --chunk-duration 1800

  # With header text
  gemini-transcribe interview.wav --header "# Interview with Dr. Smith"

Environment Variables:
  GEMINI_API_KEY    Your Google AI API key (required)
"""
    )

    parser.add_argument(
        "audio_file",
        help="Path to the audio file to transcribe"
    )

    parser.add_argument(
        "-o", "--output",
        default="transcript.md",
        help="Output file path (default: transcript.md)"
    )

    parser.add_argument(
        "-k", "--api-key",
        help="Gemini API key (or set GEMINI_API_KEY env var)"
    )

    parser.add_argument(
        "-m", "--model",
        default="gemini-3-pro-preview",
        help="Gemini model to use (default: gemini-3-pro-preview)"
    )

    parser.add_argument(
        "--chunk-duration",
        type=int,
        default=1200,
        help="Chunk duration in seconds (default: 1200 = 20 minutes)"
    )

    parser.add_argument(
        "--overlap",
        type=int,
        default=10,
        help="Overlap between chunks in seconds (default: 10)"
    )

    parser.add_argument(
        "-i", "--instructions",
        help="Path to custom transcription instructions file"
    )

    parser.add_argument(
        "--header",
        help="Header text to prepend to the transcript"
    )

    parser.add_argument(
        "--chunks-dir",
        default="audio_chunks",
        help="Directory to store audio chunks (default: audio_chunks)"
    )

    parser.add_argument(
        "-q", "--quiet",
        action="store_true",
        help="Suppress progress messages"
    )

    parser.add_argument(
        "-v", "--version",
        action="version",
        version=f"%(prog)s {__version__}"
    )

    args = parser.parse_args()

    # Check for instructions file in default location
    instructions_file = args.instructions
    if not instructions_file:
        default_instructions = Path("transcription_instructions.md")
        if default_instructions.exists():
            instructions_file = str(default_instructions)
            if not args.quiet:
                print(f"Using instructions from {default_instructions}")

    try:
        transcriber = Transcriber(
            api_key=args.api_key,
            model=args.model,
            chunk_duration=args.chunk_duration,
            overlap=args.overlap,
            chunks_dir=args.chunks_dir,
            verbose=not args.quiet
        )

        transcriber.transcribe(
            audio_file=args.audio_file,
            output_file=args.output,
            instructions_file=instructions_file,
            header=args.header
        )

        if not args.quiet:
            print("\nDone!")

    except FileNotFoundError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
    except KeyboardInterrupt:
        print("\nInterrupted.", file=sys.stderr)
        sys.exit(130)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
