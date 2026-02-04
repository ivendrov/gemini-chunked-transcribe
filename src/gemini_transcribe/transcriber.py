"""
Main transcriber class for chunked audio transcription.
"""

import os
import subprocess
from pathlib import Path
from typing import Optional, List, Dict, Any

from .api import GeminiAPI


def get_chunk_prompt(speakers: Optional[List[str]] = None) -> str:
    """Generate the chunk transcription prompt with optional speaker names."""
    if speakers and len(speakers) >= 2:
        speaker_format = ", ".join([f"**{name}:**" for name in speakers])
    else:
        speaker_format = "**Speaker 1:** and **Speaker 2:** (or use actual names if identifiable)"

    return f"""Please transcribe this audio interview/conversation segment.

FORMAT:
- Speaker names in bold: {speaker_format}
- Use proper paragraphing for longer responses

CLEANING INSTRUCTIONS:
1. Remove filler words: "um", "uh", "like", "you know", "sort of", "kind of" (when used as fillers)
2. Remove pure backchanneling: "right", "yeah", "uh-huh", "mm-hmm", "okay", "sure", "interesting" when they're just acknowledgments (not substantive responses)
3. Keep "right" or "yeah" only when part of making a substantive point
4. Clean up false starts, stutters, and repetitions for readability
5. Preserve all intellectual content and nuance
6. Keep substantive questions and responses only

Provide the complete transcript for this segment."""


DEFAULT_CHUNK_PROMPT = get_chunk_prompt()


DEFAULT_MERGE_PROMPT = """Below is a transcript assembled from multiple audio chunks. Please:

1. Clean up any duplicate text at chunk boundaries (there was overlap between chunks)
2. Add section headers (## Header) every 15-20 minutes of conversation
   - Section headers should be 5-6 words capturing that section's main topic
   - Example: "## Discussion of Main Research Goals" or "## Addressing Common Misconceptions"
3. Ensure consistent formatting throughout
4. Fix any obvious transcription errors you can identify from context
5. Maintain speaker labels in bold format

Here is the raw transcript to clean up:

---

{transcript}

---

Please output the cleaned, formatted transcript with section headers."""


class Transcriber:
    """
    Transcribe long audio files by splitting into chunks.

    This approach produces higher quality transcriptions for long audio
    by processing shorter segments independently, then merging them.
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = "gemini-3-pro-preview",
        chunk_duration: int = 20 * 60,  # 20 minutes in seconds
        overlap: int = 10,  # 10 seconds overlap
        chunks_dir: str = "audio_chunks",
        verbose: bool = True
    ):
        """
        Initialize the transcriber.

        Args:
            api_key: Google AI API key. If not provided, reads from GEMINI_API_KEY env var.
            model: Gemini model to use.
            chunk_duration: Duration of each chunk in seconds (default: 20 minutes).
            overlap: Overlap between chunks in seconds (default: 10 seconds).
            chunks_dir: Directory to store audio chunks.
            verbose: Whether to print progress messages.
        """
        self.api = GeminiAPI(api_key=api_key, model=model)
        self.chunk_duration = chunk_duration
        self.overlap = overlap
        self.chunks_dir = Path(chunks_dir)
        self.verbose = verbose

    def _log(self, message: str):
        """Print message if verbose mode is on."""
        if self.verbose:
            print(message)

    def get_audio_duration(self, filepath: Path) -> float:
        """Get audio duration in seconds using ffprobe."""
        cmd = [
            "ffprobe", "-v", "error", "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1", str(filepath)
        ]
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            raise Exception(f"ffprobe failed: {result.stderr}")
        return float(result.stdout.strip())

    def split_audio(self, filepath: Path) -> List[Dict[str, Any]]:
        """
        Split audio file into chunks with overlap.

        Args:
            filepath: Path to the audio file.

        Returns:
            List of chunk dictionaries with 'file', 'start', 'end', 'num' keys.
        """
        self.chunks_dir.mkdir(exist_ok=True)
        filepath = Path(filepath)

        duration = self.get_audio_duration(filepath)
        self._log(f"Total audio duration: {duration/60:.1f} minutes")

        chunks = []
        start = 0
        chunk_num = 1

        while start < duration:
            end = min(start + self.chunk_duration, duration)
            chunk_file = self.chunks_dir / f"chunk_{chunk_num:02d}.wav"

            # Use ffmpeg to extract chunk
            cmd = [
                "ffmpeg", "-y", "-i", str(filepath),
                "-ss", str(start), "-t", str(self.chunk_duration),
                "-acodec", "copy", str(chunk_file)
            ]
            result = subprocess.run(cmd, capture_output=True)
            if result.returncode != 0:
                raise Exception(f"ffmpeg failed: {result.stderr.decode()}")

            chunks.append({
                "file": chunk_file,
                "start": start,
                "end": end,
                "num": chunk_num
            })

            self._log(f"  Created chunk {chunk_num}: {start/60:.1f}m - {end/60:.1f}m")

            # Move start, accounting for overlap
            start = end - self.overlap
            chunk_num += 1

            if end >= duration:
                break

        self._log(f"Created {len(chunks)} chunks")
        return chunks

    def transcribe_chunk(
        self,
        file_uri: str,
        chunk_num: int,
        total_chunks: int,
        prompt: str
    ) -> str:
        """Transcribe a single audio chunk."""
        self._log(f"  Transcribing chunk {chunk_num}/{total_chunks}...")

        return self.api.generate(
            prompt=prompt,
            file_uri=file_uri,
            mime_type="audio/wav",
            temperature=0.2,
            max_output_tokens=30000,
            timeout=600
        )

    def merge_transcripts(self, transcripts: List[str], merge_prompt: str) -> str:
        """
        Merge chunk transcripts with a final formatting pass.

        Args:
            transcripts: List of transcript strings from each chunk.
            merge_prompt: Prompt template for merging (must contain {transcript} placeholder).

        Returns:
            Merged and formatted transcript.
        """
        self._log("\nMerging and formatting final transcript...")

        # Combine all transcripts with chunk markers
        combined = "\n\n---\n\n".join([
            f"[Chunk {i+1}]\n\n{t}" for i, t in enumerate(transcripts)
        ])

        return self.api.generate(
            prompt=merge_prompt.format(transcript=combined),
            temperature=0.3,
            max_output_tokens=100000,
            timeout=900
        )

    def transcribe(
        self,
        audio_file: str,
        output_file: str = "transcript.md",
        chunk_prompt: Optional[str] = None,
        merge_prompt: Optional[str] = None,
        instructions_file: Optional[str] = None,
        header: Optional[str] = None,
        speakers: Optional[str] = None
    ) -> str:
        """
        Transcribe a long audio file.

        Args:
            audio_file: Path to the audio file.
            output_file: Path to save the final transcript.
            chunk_prompt: Custom prompt for transcribing each chunk.
            merge_prompt: Custom prompt for merging chunks.
            instructions_file: Path to a file containing custom instructions
                              (appended to chunk prompt).
            header: Optional header text to prepend to the transcript.
            speakers: Comma-separated list of speaker names (e.g., "Ivan Vendrov,Robin Hanson").

        Returns:
            The final transcript text.
        """
        audio_path = Path(audio_file)
        if not audio_path.exists():
            raise FileNotFoundError(f"Audio file not found: {audio_file}")

        # Load custom instructions if provided
        custom_instructions = ""
        if instructions_file:
            instructions_path = Path(instructions_file)
            if instructions_path.exists():
                custom_instructions = instructions_path.read_text()
                self._log(f"Loaded custom instructions from {instructions_file}")

        # Parse speaker names if provided
        speaker_list = None
        if speakers:
            speaker_list = [s.strip() for s in speakers.split(",")]

        # Set up prompts
        if chunk_prompt is None:
            chunk_prompt = get_chunk_prompt(speaker_list)
        if custom_instructions:
            chunk_prompt = chunk_prompt + "\n\nADDITIONAL INSTRUCTIONS:\n" + custom_instructions

        if merge_prompt is None:
            merge_prompt = DEFAULT_MERGE_PROMPT

        # Step 1: Split audio
        self._log("Step 1: Splitting audio into chunks...")
        chunks = self.split_audio(audio_path)

        # Step 2: Transcribe each chunk (or load existing)
        self._log("\nStep 2: Loading/transcribing chunks...")
        transcripts = []

        for chunk in chunks:
            chunk_transcript_file = f"transcript_chunk_{chunk['num']:02d}.md"

            # Check if we already have this chunk transcribed
            if os.path.exists(chunk_transcript_file):
                self._log(f"\nChunk {chunk['num']}/{len(chunks)}: Loading existing from {chunk_transcript_file}")
                with open(chunk_transcript_file, 'r') as f:
                    transcript = f.read()
                self._log(f"    Loaded {len(transcript):,} chars")
            else:
                self._log(f"\nProcessing chunk {chunk['num']}/{len(chunks)} "
                         f"({chunk['start']/60:.0f}m - {chunk['end']/60:.0f}m):")

                file_uri, file_name = self.api.upload_file(chunk["file"])
                transcript = self.transcribe_chunk(
                    file_uri, chunk["num"], len(chunks), chunk_prompt
                )

                # Save intermediate progress
                with open(chunk_transcript_file, 'w') as f:
                    f.write(transcript)
                self._log(f"    Saved chunk {chunk['num']} transcript ({len(transcript):,} chars)")

            transcripts.append(transcript)

        # Step 3: Merge and format
        self._log("\nStep 3: Merging and final formatting pass...")
        final_transcript = self.merge_transcripts(transcripts, merge_prompt)

        # Save final transcript
        with open(output_file, 'w', encoding='utf-8') as f:
            if header:
                f.write(header)
                f.write("\n\n---\n\n")
            f.write(final_transcript)

        self._log(f"\nFinal transcript saved to: {output_file}")
        self._log(f"Length: {len(final_transcript):,} characters")

        return final_transcript
