"""
File utilities for scanning and processing files in large codebases.

This module provides memory-efficient file scanning, language detection,
and file filtering capabilities for large repositories.
"""

import asyncio
import fnmatch
import logging
import os
from collections.abc import AsyncGenerator
from pathlib import Path
from typing import Any, Optional

import aiofiles

from ..models import Language

logger = logging.getLogger(__name__)


class LanguageDetector:
    """Detects programming language from file extensions and content."""

    # Mapping of file extensions to programming languages
    EXTENSION_MAP = {
        # Python
        ".py": Language.PYTHON,
        ".pyw": Language.PYTHON,
        ".pyi": Language.PYTHON,
        # JavaScript
        ".js": Language.JAVASCRIPT,
        ".jsx": Language.JAVASCRIPT,
        ".mjs": Language.JAVASCRIPT,
        ".cjs": Language.JAVASCRIPT,
        # TypeScript
        ".ts": Language.TYPESCRIPT,
        ".tsx": Language.TYPESCRIPT,
        ".mts": Language.TYPESCRIPT,
        ".cts": Language.TYPESCRIPT,
        # Java
        ".java": Language.JAVA,
        ".jav": Language.JAVA,
        # C++
        ".cpp": Language.CPP,
        ".cxx": Language.CPP,
        ".cc": Language.CPP,
        ".hpp": Language.CPP,
        ".hxx": Language.CPP,
        ".hh": Language.CPP,
        # C
        ".c": Language.C,
        ".h": Language.C,
    }

    # Content-based detection patterns
    CONTENT_PATTERNS = {
        Language.PYTHON: [
            b"#!/usr/bin/env python",
            b"#!/usr/bin/python",
            b"# -*- coding: utf-8 -*-",
            b"from __future__ import",
        ],
        Language.JAVASCRIPT: [
            b"#!/usr/bin/env node",
            b'"use strict";',
            b"'use strict';",
        ],
        Language.TYPESCRIPT: [
            b"interface ",
            b"type ",
            b"declare ",
        ],
    }

    def detect_language(self, file_path: Path) -> Optional[Language]:
        """
        Detect programming language from file path and content.

        Args:
            file_path: Path to the file.

        Returns:
            Detected Language or None if unknown.
        """
        # First try extension-based detection
        extension = file_path.suffix.lower()
        if extension in self.EXTENSION_MAP:
            return self.EXTENSION_MAP[extension]

        # Special cases for files without extensions
        if file_path.name in ["Makefile", "makefile"]:
            return None  # Not supported yet

        # Try content-based detection for ambiguous cases
        try:
            return self._detect_from_content(file_path)
        except Exception as e:
            logger.debug(f"Content detection failed for {file_path}: {e}")
            return None

    def _detect_from_content(self, file_path: Path) -> Optional[Language]:
        """Detect language from file content."""
        try:
            with open(file_path, "rb") as f:
                # Read first 1KB for detection
                content = f.read(1024)

            for language, patterns in self.CONTENT_PATTERNS.items():
                for pattern in patterns:
                    if pattern in content:
                        return language

            return None

        except Exception:
            return None

    def is_supported_file(
        self, file_path: Path, supported_languages: list[Language]
    ) -> bool:
        """
        Check if a file is supported for processing.

        Args:
            file_path: Path to the file.
            supported_languages: List of supported languages.

        Returns:
            True if file is supported, False otherwise.
        """
        language = self.detect_language(file_path)
        return language is not None and language in supported_languages


class FileFilter:
    """Filters files based on patterns and criteria."""

    def __init__(
        self, exclude_patterns: list[str] = None, max_file_size_mb: float = 50
    ):
        self.exclude_patterns = exclude_patterns or []
        self.max_file_size_bytes = max_file_size_mb * 1024 * 1024

        # Common patterns to always exclude
        self.default_exclude_patterns = [
            "*.pyc",
            "*.pyo",
            "*.pyd",
            "__pycache__/*",
            ".git/*",
            ".svn/*",
            ".hg/*",
            "node_modules/*",
            "venv/*",
            "env/*",
            ".env/*",
            "build/*",
            "dist/*",
            "target/*",
            "*.min.js",
            "*.bundle.js",
            "*.map",
            ".DS_Store",
            "Thumbs.db",
        ]

    def should_exclude_file(self, file_path: Path) -> bool:
        """
        Check if a file should be excluded from processing.

        Args:
            file_path: Path to the file.

        Returns:
            True if file should be excluded, False otherwise.
        """
        path_str = str(file_path)

        # Check size
        try:
            if file_path.stat().st_size > self.max_file_size_bytes:
                logger.debug(f"Excluding large file: {file_path}")
                return True
        except OSError:
            return True  # Can't access file

        # Check against exclude patterns
        all_patterns = self.default_exclude_patterns + self.exclude_patterns

        for pattern in all_patterns:
            if fnmatch.fnmatch(path_str, pattern) or fnmatch.fnmatch(
                file_path.name, pattern
            ):
                logger.debug(f"Excluding file by pattern '{pattern}': {file_path}")
                return True

            # Check if any parent directory matches the pattern
            for parent in file_path.parents:
                if fnmatch.fnmatch(str(parent), pattern) or fnmatch.fnmatch(
                    parent.name, pattern
                ):
                    logger.debug(
                        f"Excluding file by parent pattern '{pattern}': {file_path}"
                    )
                    return True

        return False

    def should_exclude_directory(self, dir_path: Path) -> bool:
        """
        Check if a directory should be excluded from scanning.

        Args:
            dir_path: Path to the directory.

        Returns:
            True if directory should be excluded, False otherwise.
        """
        dir_str = str(dir_path)
        dir_name = dir_path.name

        # Common directories to always skip
        skip_dirs = {
            ".git",
            ".svn",
            ".hg",
            "__pycache__",
            "node_modules",
            "venv",
            "env",
            ".env",
            "build",
            "dist",
            "target",
            ".pytest_cache",
            ".mypy_cache",
            ".coverage",
            ".tox",
        }

        if dir_name in skip_dirs:
            return True

        # Check against patterns
        all_patterns = self.default_exclude_patterns + self.exclude_patterns

        for pattern in all_patterns:
            if fnmatch.fnmatch(dir_str, pattern) or fnmatch.fnmatch(dir_name, pattern):
                return True

        return False


class FileScanner:
    """Scans directories for files to process."""

    def __init__(self, exclude_patterns: list[str] = None):
        self.language_detector = LanguageDetector()
        self.file_filter = FileFilter(exclude_patterns)
        self.stats = {
            "total_files": 0,
            "supported_files": 0,
            "excluded_files": 0,
            "error_files": 0,
        }

    async def scan_directory(
        self,
        directory: Path,
        supported_languages: list[Language],
        max_files: Optional[int] = None,
    ) -> AsyncGenerator[dict[str, Any], None]:
        """
        Scan directory for supported files.

        Args:
            directory: Directory to scan.
            supported_languages: List of supported languages.
            max_files: Maximum number of files to process (optional).

        Yields:
            Dictionary containing file information.
        """
        if not directory.exists() or not directory.is_dir():
            logger.error(f"Directory does not exist or is not a directory: {directory}")
            return

        logger.info(f"Scanning directory: {directory}")

        files_found = 0

        try:
            for root, dirs, files in os.walk(directory):
                root_path = Path(root)

                # Filter out excluded directories
                dirs[:] = [
                    d
                    for d in dirs
                    if not self.file_filter.should_exclude_directory(root_path / d)
                ]

                for file_name in files:
                    file_path = root_path / file_name

                    try:
                        self.stats["total_files"] += 1

                        # Check if file should be excluded
                        if self.file_filter.should_exclude_file(file_path):
                            self.stats["excluded_files"] += 1
                            continue

                        # Detect language
                        language = self.language_detector.detect_language(file_path)
                        if not language or language not in supported_languages:
                            continue

                        self.stats["supported_files"] += 1
                        files_found += 1

                        # Yield file information
                        file_info = {
                            "path": file_path,
                            "language": language,
                            "size_bytes": file_path.stat().st_size,
                            "modified_time": file_path.stat().st_mtime,
                        }

                        yield file_info

                        # Check max files limit
                        if max_files and files_found >= max_files:
                            logger.info(f"Reached max files limit: {max_files}")
                            return

                        # Yield control occasionally for async processing
                        if files_found % 100 == 0:
                            await asyncio.sleep(0)

                    except Exception as e:
                        logger.warning(f"Error processing file {file_path}: {e}")
                        self.stats["error_files"] += 1
                        continue

        except Exception as e:
            logger.error(f"Error scanning directory {directory}: {e}")
            raise

        logger.info(f"Scan completed. Stats: {self.stats}")

    def get_scan_stats(self) -> dict[str, int]:
        """Get scanning statistics."""
        return self.stats.copy()

    def reset_stats(self) -> None:
        """Reset scanning statistics."""
        self.stats = {
            "total_files": 0,
            "supported_files": 0,
            "excluded_files": 0,
            "error_files": 0,
        }


class FileReader:
    """Reads files with proper encoding handling."""

    @staticmethod
    async def read_file_async(file_path: Path) -> str:
        """
        Read file asynchronously with encoding detection.

        Args:
            file_path: Path to the file to read.

        Returns:
            File content as string.

        Raises:
            IOError: If file cannot be read.
        """
        encodings = ["utf-8", "utf-8-sig", "latin-1", "cp1252"]

        for encoding in encodings:
            try:
                async with aiofiles.open(file_path, encoding=encoding) as f:
                    content = await f.read()
                    logger.debug(f"Read {file_path} with encoding {encoding}")
                    return content
            except UnicodeDecodeError:
                continue
            except Exception as e:
                logger.error(f"Error reading {file_path} with {encoding}: {e}")
                continue

        raise OSError(f"Could not read file with any supported encoding: {file_path}")

    @staticmethod
    def read_file_sync(file_path: Path) -> str:
        """
        Read file synchronously with encoding detection.

        Args:
            file_path: Path to the file to read.

        Returns:
            File content as string.

        Raises:
            IOError: If file cannot be read.
        """
        encodings = ["utf-8", "utf-8-sig", "latin-1", "cp1252"]

        for encoding in encodings:
            try:
                with open(file_path, encoding=encoding) as f:
                    content = f.read()
                    logger.debug(f"Read {file_path} with encoding {encoding}")
                    return content
            except UnicodeDecodeError:
                continue
            except Exception as e:
                logger.error(f"Error reading {file_path} with {encoding}: {e}")
                continue

        raise OSError(f"Could not read file with any supported encoding: {file_path}")


class FileWriter:
    """Writes files with proper UTF-8 encoding."""

    @staticmethod
    async def write_file_async(file_path: Path, content: str) -> None:
        """
        Write file asynchronously with UTF-8 encoding.

        Args:
            file_path: Path to the file to write.
            content: Content to write.
        """
        # Ensure parent directory exists
        file_path.parent.mkdir(parents=True, exist_ok=True)

        async with aiofiles.open(file_path, "w", encoding="utf-8") as f:
            await f.write(content)

        logger.debug(f"Wrote file: {file_path}")

    @staticmethod
    def write_file_sync(file_path: Path, content: str) -> None:
        """
        Write file synchronously with UTF-8 encoding.

        Args:
            file_path: Path to the file to write.
            content: Content to write.
        """
        # Ensure parent directory exists
        file_path.parent.mkdir(parents=True, exist_ok=True)

        with open(file_path, "w", encoding="utf-8") as f:
            f.write(content)

        logger.debug(f"Wrote file: {file_path}")


def get_repository_info(repo_path: Path) -> dict[str, Any]:
    """
    Get basic information about a repository.

    Args:
        repo_path: Path to the repository.

    Returns:
        Dictionary with repository information.
    """
    try:
        FileScanner()
        detector = LanguageDetector()

        total_files = 0
        total_size = 0
        language_counts = {}

        for root, _dirs, files in os.walk(repo_path):
            root_path = Path(root)

            for file_name in files:
                file_path = root_path / file_name

                try:
                    total_files += 1
                    total_size += file_path.stat().st_size

                    language = detector.detect_language(file_path)
                    if language:
                        language_counts[language.value] = (
                            language_counts.get(language.value, 0) + 1
                        )

                except Exception:
                    continue

        return {
            "path": str(repo_path),
            "total_files": total_files,
            "total_size_mb": total_size / (1024 * 1024),
            "language_distribution": language_counts,
            "estimated_processing_time_minutes": total_files / 100,  # Rough estimate
        }

    except Exception as e:
        logger.error(f"Error getting repository info: {e}")
        return {"error": str(e)}
