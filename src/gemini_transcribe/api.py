"""
Gemini API wrapper for file uploads and content generation.
"""

import os
import time
import json
import requests
from pathlib import Path
from typing import Optional, Tuple


class GeminiAPI:
    """Wrapper for Google's Gemini API with file upload support."""

    UPLOAD_URL = "https://generativelanguage.googleapis.com/upload/v1beta/files"
    FILES_URL = "https://generativelanguage.googleapis.com/v1beta/files"
    GENERATE_URL_TEMPLATE = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = "gemini-3-pro-preview"
    ):
        """
        Initialize the Gemini API client.

        Args:
            api_key: Google AI API key. If not provided, reads from GEMINI_API_KEY env var.
            model: Model to use for generation. Default is gemini-3-pro-preview.
        """
        self.api_key = api_key or os.getenv("GEMINI_API_KEY")
        if not self.api_key:
            raise ValueError(
                "API key required. Provide via api_key parameter or GEMINI_API_KEY environment variable."
            )
        self.model = model
        self.generate_url = self.GENERATE_URL_TEMPLATE.format(model=model)

    def check_existing_file(self, display_name: str) -> Tuple[Optional[str], Optional[str]]:
        """
        Check if a file with the given display name already exists.

        Args:
            display_name: The display name to search for.

        Returns:
            Tuple of (file_uri, file_name) if found, (None, None) otherwise.
        """
        response = requests.get(f"{self.FILES_URL}?key={self.api_key}")
        if response.status_code == 200:
            files = response.json().get("files", [])
            for f in files:
                if f.get("displayName") == display_name:
                    state = f.get("state")
                    if state == "ACTIVE":
                        return f.get("uri"), f.get("name")
        return None, None

    def upload_file(
        self,
        filepath: Path,
        mime_type: str = "audio/wav",
        reuse_existing: bool = True,
        verbose: bool = True
    ) -> Tuple[str, str]:
        """
        Upload a file to Gemini using the resumable upload API.

        Args:
            filepath: Path to the file to upload.
            mime_type: MIME type of the file.
            reuse_existing: If True, reuse existing upload with same name.
            verbose: If True, print progress messages.

        Returns:
            Tuple of (file_uri, file_name).
        """
        filepath = Path(filepath)
        file_size = filepath.stat().st_size
        display_name = filepath.stem

        # Check if file already exists
        if reuse_existing:
            existing_uri, existing_name = self.check_existing_file(display_name)
            if existing_uri:
                if verbose:
                    print(f"    Using existing upload: {existing_name}")
                return existing_uri, existing_name

        if verbose:
            print(f"    Uploading {filepath.name} ({file_size / (1024*1024):.1f} MB)...")

        # Initialize resumable upload
        headers = {
            "X-Goog-Upload-Protocol": "resumable",
            "X-Goog-Upload-Command": "start",
            "X-Goog-Upload-Header-Content-Length": str(file_size),
            "X-Goog-Upload-Header-Content-Type": mime_type,
            "Content-Type": "application/json",
        }

        metadata = {"file": {"display_name": display_name}}

        response = requests.post(
            f"{self.UPLOAD_URL}?key={self.api_key}",
            headers=headers,
            json=metadata
        )

        if response.status_code != 200:
            raise Exception(f"Failed to initialize upload: {response.status_code} {response.text}")

        upload_url = response.headers.get("X-Goog-Upload-URL")
        if not upload_url:
            raise Exception("No upload URL returned")

        # Upload the file data
        with open(filepath, 'rb') as f:
            file_data = f.read()

        headers = {
            "X-Goog-Upload-Command": "upload, finalize",
            "X-Goog-Upload-Offset": "0",
            "Content-Length": str(file_size),
        }

        response = requests.post(upload_url, headers=headers, data=file_data)

        if response.status_code != 200:
            raise Exception(f"Failed to upload file: {response.status_code} {response.text}")

        file_info = response.json()
        file_uri = file_info.get("file", {}).get("uri")
        file_name = file_info.get("file", {}).get("name")

        # Wait for processing
        self._wait_for_file_processing(file_name, verbose)

        return file_uri, file_name

    def _wait_for_file_processing(self, file_name: str, verbose: bool = True):
        """Wait for an uploaded file to finish processing."""
        file_id = file_name.replace("files/", "") if file_name.startswith("files/") else file_name

        while True:
            response = requests.get(f"{self.FILES_URL}/{file_id}?key={self.api_key}")
            if response.status_code != 200:
                raise Exception(f"Failed to check file status: {response.status_code}")

            state = response.json().get("state")
            if state == "ACTIVE":
                break
            elif state == "FAILED":
                raise Exception("File processing failed")

            if verbose:
                print(f"      Processing... (state: {state})")
            time.sleep(3)

    def generate(
        self,
        prompt: str,
        file_uri: Optional[str] = None,
        mime_type: str = "audio/wav",
        temperature: float = 0.2,
        max_output_tokens: int = 30000,
        timeout: int = 600
    ) -> str:
        """
        Generate content using Gemini.

        Args:
            prompt: The text prompt.
            file_uri: Optional URI of an uploaded file to include.
            mime_type: MIME type of the file (if file_uri provided).
            temperature: Generation temperature.
            max_output_tokens: Maximum tokens in response.
            timeout: Request timeout in seconds.

        Returns:
            Generated text response.
        """
        parts = []

        if file_uri:
            parts.append({"file_data": {"mime_type": mime_type, "file_uri": file_uri}})

        parts.append({"text": prompt})

        payload = {
            "contents": [{"parts": parts}],
            "generationConfig": {
                "temperature": temperature,
                "maxOutputTokens": max_output_tokens,
            }
        }

        response = requests.post(
            f"{self.generate_url}?key={self.api_key}",
            headers={"Content-Type": "application/json"},
            json=payload,
            timeout=timeout
        )

        if response.status_code != 200:
            raise Exception(f"Generation failed: {response.status_code} {response.text}")

        result = response.json()

        try:
            return result["candidates"][0]["content"]["parts"][0]["text"]
        except (KeyError, IndexError) as e:
            print(f"Response: {json.dumps(result, indent=2)[:2000]}")
            raise Exception(f"Failed to extract response: {e}")
