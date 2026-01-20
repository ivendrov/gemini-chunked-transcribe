# gemini-chunked-transcribe

High-quality transcription of long audio files using Google's Gemini API with intelligent chunking.

## TL;DR

```bash
# Install
pip install git+https://github.com/ivendrov/gemini-chunked-transcribe.git

# Set API key
export GEMINI_API_KEY="your-api-key-here"

# Transcribe (all options)
gemini-transcribe interview.wav \
  -o transcript.md \
  --model gemini-3-pro-preview \
  --chunk-duration 1200 \
  --overlap 10 \
  --instructions transcription_instructions.md \
  --header "# My Interview Title"
```

## Why Chunking?

Long audio (1+ hours) produces degraded transcription quality toward the end. This tool splits audio into 20-minute chunks, transcribes each independently, then merges with overlap handling and section headers.

## Prerequisites

- Python 3.8+
- `ffmpeg` installed (`brew install ffmpeg` / `apt install ffmpeg`)
- [Google AI API key](https://aistudio.google.com/app/apikey)

## Custom Instructions

Create `transcription_instructions.md` in your working directory:

```markdown
This is an interview between Dr. Jane Smith and Professor John Doe.
Please use **Jane:** and **John:** as speaker labels.
Topics: machine learning, career advice, future of AI.
```

The file is auto-detected, or pass `--instructions path/to/file.md`.

## CLI Options

| Option | Default | Description |
|--------|---------|-------------|
| `-o, --output` | `transcript.md` | Output file |
| `-m, --model` | `gemini-3-pro-preview` | Gemini model |
| `--chunk-duration` | `1200` | Chunk size in seconds |
| `--overlap` | `10` | Overlap between chunks |
| `-i, --instructions` | auto-detect | Custom instructions file |
| `--header` | none | Header text for transcript |
| `-q, --quiet` | false | Suppress progress |

## Resuming

Intermediate chunks are saved as `transcript_chunk_XX.md`. If interrupted, just re-run the same command to resume.

## License

MIT
