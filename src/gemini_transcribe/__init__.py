"""
Gemini Chunked Transcribe - High-quality long audio transcription using Google's Gemini API.

Splits long audio files into chunks, transcribes each independently for better quality,
then merges and formats the final transcript.
"""

__version__ = "0.1.0"

from .transcriber import Transcriber
from .api import GeminiAPI

__all__ = ["Transcriber", "GeminiAPI", "__version__"]
