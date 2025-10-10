"""
File utilities for the text-to-video service.

This module provides:
- File upload validation
- Async file operations
- Temporary file management
- Cleanup utilities
"""

import asyncio
import hashlib
import logging
import os
import tempfile
import time
from pathlib import Path
from typing import Any

import aiofiles
from fastapi import UploadFile

logger = logging.getLogger(__name__)


# =============================================================================
# File Upload Validation
# =============================================================================


class FileValidationError(ValueError):
    """Raised when file validation fails."""

    pass


async def validate_upload_file(file: UploadFile) -> tuple[str, int, str]:
    """
    Validate uploaded file against constraints.

    Args:
        file: FastAPI UploadFile instance

    Returns:
        Tuple of (filename, size, file_type)

    Raises:
        FileValidationError: If validation fails
    """
    if not file:
        raise FileValidationError("File is required")

    filename = file.filename or ""
    if not filename:
        raise FileValidationError("Filename is required")

    # Validate file extension
    allowed_extensions = {".txt", ".pdf", ".md"}
    file_ext = Path(filename).suffix.lower()
    if file_ext not in allowed_extensions:
        raise FileValidationError(
            f"Invalid file type '{file_ext}'. Allowed: {', '.join(allowed_extensions)}"
        )

    # Map extension to file type
    ext_to_type = {".txt": "txt", ".pdf": "pdf", ".md": "md"}
    file_type = ext_to_type[file_ext]

    # Validate content type
    content_type = file.content_type or ""
    allowed_content_types = {
        "text/plain": [".txt", ".md"],
        "application/pdf": [".pdf"],
        "text/markdown": [".md"],
    }

    content_type_valid = False
    for allowed_ct, allowed_exts in allowed_content_types.items():
        if content_type.startswith(allowed_ct) and file_ext in allowed_exts:
            content_type_valid = True
            break

    if content_type and not content_type_valid:
        raise FileValidationError(
            f"Content type '{content_type}' does not match file extension '{file_ext}'"
        )

    # Read file size
    file.file.seek(0, os.SEEK_END)
    size = file.file.tell()
    file.file.seek(0)

    # Validate file size (50MB limit)
    max_size = 50 * 1024 * 1024  # 50MB
    if size > max_size:
        max_mb = max_size // (1024 * 1024)
        raise FileValidationError(f"File too large ({size} bytes). Maximum size: {max_mb}MB")

    if size == 0:
        raise FileValidationError("File is empty")

    return filename, size, file_type


async def save_upload_file(file: UploadFile, destination: str | Path) -> int:
    """
    Save uploaded file to destination asynchronously.

    Args:
        file: FastAPI UploadFile instance
        destination: Path to save file

    Returns:
        Number of bytes written

    Raises:
        IOError: If file write fails
    """
    destination = Path(destination)
    destination.parent.mkdir(parents=True, exist_ok=True)

    file.file.seek(0)
    bytes_written = 0

    async with aiofiles.open(destination, "wb") as f:
        while chunk := await asyncio.to_thread(file.file.read, 8192):
            await f.write(chunk)
            bytes_written += len(chunk)

    return bytes_written


async def compute_file_hash(file_path: str | Path, algorithm: str = "sha256") -> str:
    """
    Compute hash of file asynchronously.

    Args:
        file_path: Path to file
        algorithm: Hash algorithm (default: sha256)

    Returns:
        Hex digest of file hash

    Raises:
        FileNotFoundError: If file does not exist
    """
    file_path = Path(file_path)
    if not file_path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")

    hash_obj = hashlib.new(algorithm)

    async with aiofiles.open(file_path, "rb") as f:
        while chunk := await f.read(8192):
            await asyncio.to_thread(hash_obj.update, chunk)

    return hash_obj.hexdigest()


def create_temp_file(suffix: str = "", prefix: str = "t2v_", dir: str | None = None) -> Path:
    """
    Create a temporary file and return its path.

    Args:
        suffix: File suffix (e.g., '.txt')
        prefix: File prefix (default: 't2v_')
        dir: Directory to create file in (default: system temp)

    Returns:
        Path to temporary file
    """
    fd, path = tempfile.mkstemp(suffix=suffix, prefix=prefix, dir=dir)
    os.close(fd)
    return Path(path)


def create_temp_dir(prefix: str = "t2v_", dir: str | None = None) -> Path:
    """
    Create a temporary directory and return its path.

    Args:
        prefix: Directory prefix (default: 't2v_')
        dir: Parent directory (default: system temp)

    Returns:
        Path to temporary directory
    """
    path = tempfile.mkdtemp(prefix=prefix, dir=dir)
    return Path(path)


async def delete_file_async(file_path: str | Path) -> bool:
    """
    Delete file asynchronously.

    Args:
        file_path: Path to file to delete

    Returns:
        True if file was deleted, False if it didn't exist

    Raises:
        OSError: If deletion fails for reasons other than file not existing
    """
    file_path = Path(file_path)
    if not file_path.exists():
        return False

    await asyncio.to_thread(file_path.unlink)
    return True


def get_file_size(file_path: str | Path) -> int:
    """
    Get file size in bytes.

    Args:
        file_path: Path to file

    Returns:
        File size in bytes

    Raises:
        FileNotFoundError: If file does not exist
    """
    file_path = Path(file_path)
    if not file_path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")

    return file_path.stat().st_size


def ensure_dir(dir_path: str | Path) -> Path:
    """
    Ensure directory exists, creating it if necessary.

    Args:
        dir_path: Path to directory

    Returns:
        Path to directory
    """
    dir_path = Path(dir_path)
    dir_path.mkdir(parents=True, exist_ok=True)
    return dir_path


# =============================================================================
# Legacy File Utilities (FileContext, FileCleanupManager)
# =============================================================================


class FileContext:
    def __init__(self, contents, filename):
        self.contents = contents
        self.filename = filename
        self.file_size = len(self.contents)


class FileCleanupManager:
    """
    Manages cleanup of temporary files and directories for the text-to-video service.
    """

    def __init__(self):
        # Default directories to clean
        self.cleanup_dirs = ["/tmp/assets", "/tmp/visuals", "/tmp/audio", "/tmp/videos"]

        # File age thresholds (in seconds)
        self.age_thresholds = {
            "assets": 24 * 3600,  # 24 hours
            "visuals": 24 * 3600,  # 24 hours
            "audio": 24 * 3600,  # 24 hours
            "videos": 7 * 24 * 3600,  # 7 days
            "temp": 3600,  # 1 hour
        }

        # Size limits (in bytes)
        self.size_limits = {
            "assets": 100 * 1024 * 1024,  # 100MB
            "visuals": 500 * 1024 * 1024,  # 500MB
            "audio": 200 * 1024 * 1024,  # 200MB
            "videos": 2 * 1024 * 1024 * 1024,  # 2GB
            "temp": 50 * 1024 * 1024,  # 50MB
        }

    def add_cleanup_directory(
        self,
        directory: str,
        age_threshold: int | None = None,
        size_limit: int | None = None,
    ):
        """
        Add a directory to the cleanup list.

        Args:
            directory: Path to directory to clean
            age_threshold: File age threshold in seconds
            size_limit: Directory size limit in bytes
        """
        self.cleanup_dirs.append(directory)

        if age_threshold:
            dir_name = Path(directory).name
            self.age_thresholds[dir_name] = age_threshold

        if size_limit:
            dir_name = Path(directory).name
            self.size_limits[dir_name] = size_limit

    def remove_cleanup_directory(self, directory: str):
        """Remove a directory from the cleanup list."""
        if directory in self.cleanup_dirs:
            self.cleanup_dirs.remove(directory)

    def cleanup_old_files(self, directory: str, max_age: int) -> dict[str, Any]:
        """
        Remove files older than max_age from directory.

        Args:
            directory: Directory to clean
            max_age: Maximum age in seconds

        Returns:
            Dictionary with cleanup statistics
        """
        if not os.path.exists(directory):
            return {"files_removed": 0, "space_freed": 0}

        current_time = time.time()
        files_removed = 0
        space_freed = 0

        try:
            for filename in os.listdir(directory):
                file_path = os.path.join(directory, filename)

                if os.path.isfile(file_path):
                    file_age = current_time - os.path.getmtime(file_path)

                    if file_age > max_age:
                        file_size = os.path.getsize(file_path)
                        os.remove(file_path)
                        files_removed += 1
                        space_freed += file_size

                        logger.debug(
                            f"Removed old file: {file_path} (age: {file_age:.1f}s, size: {file_size} bytes)"
                        )

        except Exception as e:
            logger.error(f"Error cleaning old files in {directory}", extra={"error": str(e)})

        return {"files_removed": files_removed, "space_freed": space_freed}

    def cleanup_by_size(self, directory: str, size_limit: int) -> dict[str, Any]:
        """
        Remove oldest files if directory exceeds size limit.

        Args:
            directory: Directory to clean
            size_limit: Maximum directory size in bytes

        Returns:
            Dictionary with cleanup statistics
        """
        if not os.path.exists(directory):
            return {"files_removed": 0, "space_freed": 0}

        try:
            # Get all files with their modification times
            files = []
            current_size = 0

            for filename in os.listdir(directory):
                file_path = os.path.join(directory, filename)
                if os.path.isfile(file_path):
                    file_size = os.path.getsize(file_path)
                    file_mtime = os.path.getmtime(file_path)
                    files.append((file_path, file_size, file_mtime))
                    current_size += file_size

            if current_size <= size_limit:
                return {"files_removed": 0, "space_freed": 0}

            # Sort by modification time (oldest first)
            files.sort(key=lambda x: x[2])

            # Remove oldest files until under size limit
            files_removed = 0
            space_freed = 0

            for file_path, file_size, _ in files:
                if current_size <= size_limit:
                    break

                try:
                    os.remove(file_path)
                    current_size -= file_size
                    files_removed += 1
                    space_freed += file_size

                    logger.debug(
                        f"Removed file by size limit: {file_path} (size: {file_size} bytes)"
                    )

                except Exception as e:
                    logger.error(f"Error removing file {file_path}", extra={"error": str(e)})

            return {"files_removed": files_removed, "space_freed": space_freed}

        except Exception as e:
            logger.error(f"Error cleaning directory by size: {directory}", extra={"error": str(e)})
            return {"files_removed": 0, "space_freed": 0}

    def cleanup_directory(self, directory: str) -> dict[str, Any]:
        """
        Clean a directory using both age and size criteria.

        Args:
            directory: Directory to clean

        Returns:
            Dictionary with cleanup statistics
        """
        if not os.path.exists(directory):
            return {"files_removed": 0, "space_freed": 0}

        dir_name = Path(directory).name
        max_age = self.age_thresholds.get(dir_name, 24 * 3600)
        size_limit = self.size_limits.get(dir_name, 100 * 1024 * 1024)

        # First clean by age
        age_result = self.cleanup_old_files(directory, max_age)

        # Then clean by size if still needed
        size_result = self.cleanup_by_size(directory, size_limit)

        total_files = age_result["files_removed"] + size_result["files_removed"]
        total_space = age_result["space_freed"] + size_result["space_freed"]

        logger.info(
            f"Directory cleanup completed: {directory}",
            extra={
                "files_removed": total_files,
                "space_freed": total_space,
                "age_cleanup": age_result,
                "size_cleanup": size_result,
            },
        )

        return {"files_removed": total_files, "space_freed": total_space, "directory": directory}

    def cleanup_all_directories(self) -> dict[str, Any]:
        """
        Clean all configured directories.

        Returns:
            Dictionary with overall cleanup statistics
        """
        total_files = 0
        total_space = 0
        results = {}

        for directory in self.cleanup_dirs:
            result = self.cleanup_directory(directory)
            results[directory] = result
            total_files += result["files_removed"]
            total_space += result["space_freed"]

        logger.info(
            "Full cleanup completed",
            extra={
                "total_files_removed": total_files,
                "total_space_freed": total_space,
                "directories_cleaned": len(results),
            },
        )

        return {
            "total_files_removed": total_files,
            "total_space_freed": total_space,
            "results": results,
        }

    async def async_cleanup_directory(self, directory: str) -> dict[str, Any]:
        """
        Async version of directory cleanup using ThreadPoolExecutor.

        Args:
            directory: Directory to clean

        Returns:
            Dictionary with cleanup statistics
        """
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self.cleanup_directory, directory)

    async def async_cleanup_all(self) -> dict[str, Any]:
        """
        Async version of full cleanup.

        Returns:
            Dictionary with overall cleanup statistics
        """
        asyncio.get_event_loop()

        # Run cleanup tasks concurrently
        tasks = [self.async_cleanup_directory(dir) for dir in self.cleanup_dirs]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        total_files = 0
        total_space = 0
        successful_results = {}

        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error(
                    f"Cleanup failed for {self.cleanup_dirs[i]}", extra={"error": str(result)}
                )
            else:
                successful_results[self.cleanup_dirs[i]] = result
                if isinstance(result, dict):
                    total_files += result.get("files_removed", 0)
                    total_space += result.get("space_freed", 0)

        return {
            "total_files_removed": total_files,
            "total_space_freed": total_space,
            "results": successful_results,
        }

    def get_directory_info(self, directory: str) -> dict[str, Any]:
        """
        Get information about a directory.

        Args:
            directory: Directory to analyze

        Returns:
            Dictionary with directory information
        """
        if not os.path.exists(directory):
            return {"exists": False}

        try:
            files = []
            total_size = 0
            oldest_file = None
            newest_file = None

            for filename in os.listdir(directory):
                file_path = os.path.join(directory, filename)
                if os.path.isfile(file_path):
                    file_size = os.path.getsize(file_path)
                    file_mtime = os.path.getmtime(file_path)

                    files.append({"name": filename, "size": file_size, "modified": file_mtime})

                    total_size += file_size

                    if oldest_file is None or file_mtime < oldest_file:
                        oldest_file = file_mtime
                    if newest_file is None or file_mtime > newest_file:
                        newest_file = file_mtime

            return {
                "exists": True,
                "total_files": len(files),
                "total_size": total_size,
                "oldest_file": oldest_file,
                "newest_file": newest_file,
                "files": files,
            }

        except Exception as e:
            logger.error(f"Error getting directory info for {directory}", extra={"error": str(e)})
            return {"exists": True, "error": str(e)}


# Global cleanup manager instance
file_cleanup_manager = FileCleanupManager()


# Convenience functions
def cleanup_temp_files():
    """Clean up temporary files."""
    return file_cleanup_manager.cleanup_all_directories()


async def async_cleanup_temp_files():
    """Async cleanup of temporary files."""
    return await file_cleanup_manager.async_cleanup_all()


def get_cleanup_info():
    """Get cleanup information for all directories."""
    info = {}
    for directory in file_cleanup_manager.cleanup_dirs:
        info[directory] = file_cleanup_manager.get_directory_info(directory)
    return info
