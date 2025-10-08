import os
import shutil
import logging
import time
from typing import List, Optional, Dict, Any
from pathlib import Path
import asyncio
from concurrent.futures import ThreadPoolExecutor

logger = logging.getLogger(__name__)


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
        self.cleanup_dirs = [
            "/tmp/assets",
            "/tmp/visuals",
            "/tmp/audio",
            "/tmp/videos"
        ]

        # File age thresholds (in seconds)
        self.age_thresholds = {
            "assets": 24 * 3600,        # 24 hours
            "visuals": 24 * 3600,       # 24 hours
            "audio": 24 * 3600,         # 24 hours
            "videos": 7 * 24 * 3600,    # 7 days
            "temp": 3600                # 1 hour
        }

        # Size limits (in bytes)
        self.size_limits = {
            "assets": 100 * 1024 * 1024,    # 100MB
            "visuals": 500 * 1024 * 1024,   # 500MB
            "audio": 200 * 1024 * 1024,     # 200MB
            "videos": 2 * 1024 * 1024 * 1024,  # 2GB
            "temp": 50 * 1024 * 1024        # 50MB
        }

    def add_cleanup_directory(self, directory: str, age_threshold: int|None = None, size_limit: int|None = None):
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

    def cleanup_old_files(self, directory: str, max_age: int) -> Dict[str, Any]:
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

                        logger.debug(f"Removed old file: {file_path} (age: {file_age:.1f}s, size: {file_size} bytes)")

        except Exception as e:
            logger.error(f"Error cleaning old files in {directory}", extra={"error": str(e)})

        return {"files_removed": files_removed, "space_freed": space_freed}

    def cleanup_by_size(self, directory: str, size_limit: int) -> Dict[str, Any]:
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

                    logger.debug(f"Removed file by size limit: {file_path} (size: {file_size} bytes)")

                except Exception as e:
                    logger.error(f"Error removing file {file_path}", extra={"error": str(e)})

            return {"files_removed": files_removed, "space_freed": space_freed}

        except Exception as e:
            logger.error(f"Error cleaning directory by size: {directory}", extra={"error": str(e)})
            return {"files_removed": 0, "space_freed": 0}

    def cleanup_directory(self, directory: str) -> Dict[str, Any]:
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

        logger.info(f"Directory cleanup completed: {directory}", extra={
            "files_removed": total_files,
            "space_freed": total_space,
            "age_cleanup": age_result,
            "size_cleanup": size_result
        })

        return {
            "files_removed": total_files,
            "space_freed": total_space,
            "directory": directory
        }

    def cleanup_all_directories(self) -> Dict[str, Any]:
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

        logger.info("Full cleanup completed", extra={
            "total_files_removed": total_files,
            "total_space_freed": total_space,
            "directories_cleaned": len(results)
        })

        return {
            "total_files_removed": total_files,
            "total_space_freed": total_space,
            "results": results
        }

    async def async_cleanup_directory(self, directory: str) -> Dict[str, Any]:
        """
        Async version of directory cleanup using ThreadPoolExecutor.

        Args:
            directory: Directory to clean

        Returns:
            Dictionary with cleanup statistics
        """
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self.cleanup_directory, directory)

    async def async_cleanup_all(self) -> Dict[str, Any]:
        """
        Async version of full cleanup.

        Returns:
            Dictionary with overall cleanup statistics
        """
        loop = asyncio.get_event_loop()

        # Run cleanup tasks concurrently
        tasks = [self.async_cleanup_directory(dir) for dir in self.cleanup_dirs]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        total_files = 0
        total_space = 0
        successful_results = {}

        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error(f"Cleanup failed for {self.cleanup_dirs[i]}", extra={"error": str(result)})
            else:
                successful_results[self.cleanup_dirs[i]] = result
                if isinstance(result, dict):
                    total_files += result.get("files_removed", 0)
                    total_space += result.get("space_freed", 0)

        return {
            "total_files_removed": total_files,
            "total_space_freed": total_space,
            "results": successful_results
        }

    def get_directory_info(self, directory: str) -> Dict[str, Any]:
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

                    files.append({
                        "name": filename,
                        "size": file_size,
                        "modified": file_mtime
                    })

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
                "files": files
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
