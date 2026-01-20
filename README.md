# gemini-chunked-transcribe

High-quality transcription of long audio files using Google's Gemini API with intelligent chunking.

## Why Chunking?

When transcribing long audio files (1+ hours), AI models often produce degraded quality toward the end of the file. This tool solves that problem by:

1. **Splitting** the audio into manageable chunks (default: 20 minutes)
2. **Transcribing** each chunk independently with full attention
3. **Merging** the chunks with overlap handling and adding section headers
4. **Cleaning** the final transcript with a formatting pass

The result is consistently high-quality transcription throughout the entire recording.

## Features

- Automatic audio chunking with configurable duration and overlap
- Resumable transcription (intermediate chunks are saved)
- Custom transcription instructions via file or command line
- Section headers automatically added every 15-20 minutes
- Filler word and backchanneling removal
- Intelligent overlap deduplication at chunk boundaries
- Reuses existing Gemini file uploads (no re-uploading on retry)

## Installation

### Prerequisites

- Python 3.8+
- `ffmpeg` installed and available in PATH
- Google AI API key ([get one here](https://aistudio.google.com/app/apikey))

### Install via pip

```bash
pip install gemini-chunked-transcribe
```

### Install from source

```bash
git clone https://github.com/ivendrov/gemini-chunked-transcribe.git
cd gemini-chunked-transcribe
pip install -e .
```

## Quick Start

1. Set your API key:
```bash
export GEMINI_API_KEY="your-api-key-here"
```

2. Transcribe an audio file:
```bash
gemini-transcribe interview.wav
```

3. Find your transcript in `transcript.md`

## Usage

### Basic Usage

```bash
gemini-transcribe audio.wav
```

### With Custom Output File

```bash
gemini-transcribe audio.wav -o my_transcript.md
```

### With Custom Instructions

Create a file called `transcription_instructions.md`:

```markdown
This is an interview between Dr. Jane Smith (interviewer) and Professor John Doe (interviewee).

The interview covers topics including:
- Machine learning research
- Academic career advice
- Future of AI

Please use **Jane:** and **John:** as speaker labels.
```

Then run:

```bash
gemini-transcribe audio.wav --instructions transcription_instructions.md
```

Or simply place `transcription_instructions.md` in the current directory - it will be detected automatically.

### With Header Text

```bash
gemini-transcribe audio.wav --header "# Interview: Dr. Smith & Prof. Doe\n## January 15, 2026"
```

### Adjust Chunk Size

For very long interviews, you might want shorter chunks:

```bash
# 15-minute chunks
gemini-transcribe audio.wav --chunk-duration 900
```

### Use a Different Model

```bash
gemini-transcribe audio.wav --model gemini-2.0-flash-exp
```

## Python API

```python
from gemini_transcribe import Transcriber

# Initialize
transcriber = Transcriber(
    api_key="your-api-key",  # or set GEMINI_API_KEY env var
    model="gemini-2.5-pro-preview-05-06",
    chunk_duration=20 * 60,  # 20 minutes
    overlap=10,  # 10 seconds
)

# Transcribe
transcript = transcriber.transcribe(
    audio_file="interview.wav",
    output_file="transcript.md",
    instructions_file="transcription_instructions.md",
    header="# My Interview\n"
)
```

## How It Works

### 1. Audio Splitting

The audio file is split into chunks using `ffmpeg`:
- Default chunk size: 20 minutes
- Default overlap: 10 seconds
- Chunks are saved to `audio_chunks/` directory

### 2. Chunk Transcription

Each chunk is:
- Uploaded to Gemini's File API (reused if already uploaded)
- Transcribed with cleaning instructions
- Saved to `transcript_chunk_XX.md` for resumability

### 3. Merging & Formatting

The final pass:
- Combines all chunk transcripts
- Removes duplicate text at overlap boundaries
- Adds section headers every 15-20 minutes
- Fixes transcription errors using context
- Ensures consistent formatting

## Resuming Interrupted Transcriptions

If transcription is interrupted, simply run the same command again. The tool will:
- Skip audio splitting if chunks already exist
- Skip transcription for chunks that have `transcript_chunk_XX.md` files
- Only run the merge step if all chunks are complete

To force re-transcription, delete the `transcript_chunk_*.md` files.

## Configuration

### Environment Variables

| Variable | Description |
|----------|-------------|
| `GEMINI_API_KEY` | Your Google AI API key |

### CLI Options

| Option | Default | Description |
|--------|---------|-------------|
| `-o, --output` | `transcript.md` | Output file path |
| `-k, --api-key` | env var | Gemini API key |
| `-m, --model` | `gemini-2.5-pro-preview-05-06` | Model to use |
| `--chunk-duration` | `1200` (20 min) | Chunk duration in seconds |
| `--overlap` | `10` | Overlap between chunks in seconds |
| `-i, --instructions` | auto-detect | Custom instructions file |
| `--header` | none | Header text for transcript |
| `--chunks-dir` | `audio_chunks` | Directory for audio chunks |
| `-q, --quiet` | false | Suppress progress messages |

## Default Transcription Behavior

By default, the transcriber:

1. **Removes filler words**: "um", "uh", "like", "you know", "sort of", "kind of"
2. **Removes backchanneling**: "right", "yeah", "uh-huh", "mm-hmm", "okay", "sure" (when just acknowledgments)
3. **Cleans up**: false starts, stutters, repetitions
4. **Preserves**: all substantive content and nuance
5. **Formats**: speaker labels in bold, proper paragraphing

## Supported Audio Formats

Any format supported by `ffmpeg`, including:
- WAV
- MP3
- M4A
- FLAC
- OGG
- And many more

## Troubleshooting

### "ffmpeg not found"

Install ffmpeg:
- macOS: `brew install ffmpeg`
- Ubuntu: `sudo apt install ffmpeg`
- Windows: Download from [ffmpeg.org](https://ffmpeg.org/download.html)

### "API key required"

Set your API key:
```bash
export GEMINI_API_KEY="your-key"
```

Or pass it directly:
```bash
gemini-transcribe audio.wav --api-key "your-key"
```

### Transcription quality degrades

Try shorter chunks:
```bash
gemini-transcribe audio.wav --chunk-duration 600  # 10 minutes
```

### Rate limiting errors

The tool includes automatic retry logic, but for very long files you may need to wait between runs.

## License

MIT License - see [LICENSE](LICENSE) for details.

## Contributing

Contributions welcome! Please open an issue or PR on GitHub.
