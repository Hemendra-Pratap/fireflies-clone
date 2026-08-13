import os
from abc import ABC, abstractmethod
from pathlib import Path
from uuid import uuid4

from fastapi import UploadFile

from app.core.config import settings

# 100 MB default max upload size limit
DEFAULT_MAX_FILE_SIZE = 100 * 1024 * 1024
CHUNK_SIZE = 64 * 1024  # 64 KB chunks for memory efficiency

ALLOWED_MIME_TYPES = {
    "audio/mpeg",
    "audio/mp3",
    "audio/wav",
    "audio/x-wav",
    "audio/m4a",
    "audio/x-m4a",
    "audio/ogg",
    "audio/webm",
    "audio/mp4",
    "audio/aac",
    "audio/flac",
    "audio/x-flac",
}

ALLOWED_EXTENSIONS = {
    ".mp3",
    ".wav",
    ".m4a",
    ".ogg",
    ".webm",
    ".mp4",
    ".aac",
    ".flac",
}


class StorageService(ABC):
    @abstractmethod
    async def save_file(
        self,
        file: UploadFile,
        max_size_bytes: int = DEFAULT_MAX_FILE_SIZE,
    ) -> tuple[str, str, int]:
        """Saves an uploaded file and returns (relative_path, safe_filename, size_bytes)."""
        pass

    @abstractmethod
    def delete_file(self, relative_path: str) -> bool:
        """Deletes a file given its stored relative path."""
        pass

    @abstractmethod
    def get_full_path(self, relative_path: str) -> Path:
        """Resolves a stored relative path to its absolute filesystem path."""
        pass


class LocalStorageService(StorageService):
    def __init__(self, storage_dir: Path | None = None):
        if storage_dir is None:
            self.storage_dir = settings.backend_dir / "storage" / "audio"
        else:
            self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(parents=True, exist_ok=True)

    def _extract_safe_extension(self, filename: str | None) -> str:
        if not filename:
            return ".mp3"
        safe_name = Path(filename).name  # Strips directory traversal components
        ext = Path(safe_name).suffix.lower()
        if ext in ALLOWED_EXTENSIONS:
            return ext
        return ".mp3"

    async def save_file(
        self,
        file: UploadFile,
        max_size_bytes: int | None = None,
    ) -> tuple[str, str, int]:
        effective_max_size = max_size_bytes if max_size_bytes is not None else DEFAULT_MAX_FILE_SIZE
        ext = self._extract_safe_extension(file.filename)
        safe_filename = f"{uuid4().hex}{ext}"
        target_path = self.storage_dir / safe_filename

        # Path traversal prevention: verify target path is inside storage_dir
        if not target_path.resolve().is_relative_to(self.storage_dir.resolve()):
            raise ValueError("Invalid target storage path (path traversal detected).")

        size_bytes = 0
        try:
            with open(target_path, "wb") as out_file:
                while chunk := await file.read(CHUNK_SIZE):
                    size_bytes += len(chunk)
                    if size_bytes > effective_max_size:
                        out_file.close()
                        if target_path.exists():
                            target_path.unlink()
                        raise ValueError(
                            f"File size exceeds maximum allowed limit of {effective_max_size} bytes."
                        )
                    out_file.write(chunk)
        except Exception:
            if target_path.exists():
                target_path.unlink()
            raise

        relative_path = f"audio/{safe_filename}"
        return relative_path, safe_filename, size_bytes

    def delete_file(self, relative_path: str) -> bool:
        full_path = self.get_full_path(relative_path)
        if full_path.exists() and full_path.is_file():
            full_path.unlink()
            return True
        return False

    def get_full_path(self, relative_path: str) -> Path:
        # Strip leading "audio/" prefix if present
        clean_path = relative_path
        if clean_path.startswith("audio/") or clean_path.startswith("audio\\"):
            clean_path = clean_path[6:]
        full_path = (self.storage_dir / clean_path).resolve()
        if not full_path.is_relative_to(self.storage_dir.resolve()):
            raise ValueError("Path traversal attempt detected.")
        return full_path


# Global storage service instance
storage_service = LocalStorageService()
