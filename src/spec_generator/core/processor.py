"""
Large Codebase Processor for streaming and memory-efficient processing.

This module implements the LargeCodebaseProcessor that can handle 4GB+ repositories
with memory-efficient streaming, chunking, and parallel processing.
"""

import asyncio
import logging
import time
from collections.abc import AsyncGenerator
from pathlib import Path
from typing import Optional

from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_experimental.text_splitter import SemanticChunker
from langchain_openai.embeddings import OpenAIEmbeddings

from ..models import CodeChunk, Language, ProcessingStats, SpecificationConfig
from ..parsers import ASTAnalyzer
from ..utils.file_utils import FileScanner, LanguageDetector
from ..utils.simple_memory import SimpleMemoryTracker

logger = logging.getLogger(__name__)


class ProcessingContext:
    """Context for processing operations."""

    def __init__(self, config: SpecificationConfig):
        self.config = config
        self.start_time = time.time()
        self.stats = ProcessingStats()
        self.memory_tracker = SimpleMemoryTracker(config.max_memory_mb)
        self.processed_files: set[str] = set()
        self.failed_files: set[str] = set()

    def update_stats(
        self,
        files_count: int = 0,
        lines_count: int = 0,
        chunks_count: int = 0,
        error: Optional[str] = None,
    ) -> None:
        """Update processing statistics."""
        self.stats.files_processed += files_count
        self.stats.lines_processed += lines_count
        self.stats.chunks_created += chunks_count

        if error:
            self.stats.errors_encountered.append(error)

        # Update timing and memory
        self.stats.processing_time_seconds = time.time() - self.start_time
        self.stats.memory_peak_mb = max(
            self.stats.memory_peak_mb, self.memory_tracker.get_current_usage_mb()
        )


class ChunkProcessor:
    """Processor for creating code chunks using different strategies."""

    def __init__(self, config: SpecificationConfig):
        self.config = config

        # Initialize text splitter
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=config.chunk_size,
            chunk_overlap=config.chunk_overlap,
            separators=["\n\n", "\n", " ", ""],  # Code-friendly separators
            length_function=len,
        )

        # Initialize semantic chunker (if OpenAI key available)
        self.semantic_chunker = None
        if config.openai_api_key:
            try:
                self.semantic_chunker = SemanticChunker(
                    OpenAIEmbeddings(openai_api_key=config.openai_api_key),
                    breakpoint_threshold_type="percentile",
                )
                logger.info("Semantic chunker initialized")
            except Exception as e:
                logger.warning(f"Failed to initialize semantic chunker: {e}")

    async def create_chunks_from_content(
        self,
        content: str,
        file_path: Path,
        language: Language,
        use_semantic: bool = False,
    ) -> list[CodeChunk]:
        """
        Create chunks from file content.

        Args:
            content: File content as string.
            file_path: Path to the source file.
            language: Programming language.
            use_semantic: Whether to use semantic chunking.

        Returns:
            List of CodeChunk objects.
        """
        chunks = []

        try:
            if use_semantic and self.semantic_chunker:
                # Use semantic chunking with timeout
                # Reason: Apply timeout to prevent blocking on large content processing
                timeout_seconds = 60  # Reasonable timeout for text chunking
                semantic_chunks = await asyncio.wait_for(
                    asyncio.get_event_loop().run_in_executor(
                        None, self.semantic_chunker.split_text, content
                    ),
                    timeout=timeout_seconds
                )

                for _i, chunk_text in enumerate(semantic_chunks):
                    chunk = CodeChunk(
                        content=chunk_text,
                        file_path=file_path,
                        language=language,
                        start_line=1,  # TODO: Calculate actual line numbers
                        end_line=chunk_text.count("\n") + 1,
                        chunk_type="semantic_chunk",
                    )
                    chunks.append(chunk)

            else:
                # Use recursive character splitting
                text_chunks = self.text_splitter.split_text(content)

                for _i, chunk_text in enumerate(text_chunks):
                    chunk = CodeChunk(
                        content=chunk_text,
                        file_path=file_path,
                        language=language,
                        start_line=1,  # TODO: Calculate actual line numbers
                        end_line=chunk_text.count("\n") + 1,
                        chunk_type="text_chunk",
                    )
                    chunks.append(chunk)

            logger.debug(f"Created {len(chunks)} chunks from {file_path}")
            return chunks

        except Exception as e:
            logger.error(f"Failed to create chunks from {file_path}: {e}")
            return []

    async def create_chunks_from_ast(
        self, file_path: Path, language: Language, ast_analyzer: ASTAnalyzer
    ) -> list[CodeChunk]:
        """
        Create chunks based on AST semantic elements.

        Args:
            file_path: Path to the source file.
            language: Programming language.
            ast_analyzer: AST analyzer instance.

        Returns:
            List of CodeChunk objects based on semantic elements.
        """
        try:
            module_info = ast_analyzer.analyze_file(file_path, language)
            if not module_info:
                return []

            chunks = []
            for element in module_info.elements:
                chunk = CodeChunk(
                    content=element.content,
                    file_path=file_path,
                    language=language,
                    start_line=element.start_line,
                    end_line=element.end_line,
                    chunk_type=element.element_type,
                )
                chunks.append(chunk)

            logger.debug(f"Created {len(chunks)} AST-based chunks from {file_path}")
            return chunks

        except Exception as e:
            logger.error(f"Failed to create AST chunks from {file_path}: {e}")
            return []


class LargeCodebaseProcessor:
    """
    Processor for handling large codebases with memory-efficient streaming.

    Supports processing repositories up to 4GB+ with memory usage under 2GB
    through streaming, batching, and parallel processing.
    """

    def __init__(self, config: SpecificationConfig):
        self.config = config
        self.file_scanner = FileScanner(config.exclude_patterns)
        self.language_detector = LanguageDetector()
        self.chunk_processor = ChunkProcessor(config)
        self.ast_analyzer = ASTAnalyzer()

        # Processing limits
        self.batch_size = min(config.parallel_processes * 2, 20)
        self.max_file_size_mb = 50  # Skip files larger than 50MB

        logger.info(
            f"Initialized LargeCodebaseProcessor with batch size {self.batch_size}"
        )

    async def process_repository(
        self,
        repo_path: Path,
        use_semantic_chunking: bool = False,
        use_ast_chunking: bool = True,
    ) -> AsyncGenerator[CodeChunk, None]:
        """
        Process a repository and yield code chunks.

        Args:
            repo_path: Path to the repository root.
            use_semantic_chunking: Whether to use semantic chunking.
            use_ast_chunking: Whether to use AST-based chunking.

        Yields:
            CodeChunk objects for processing.
        """
        context = ProcessingContext(self.config)

        try:
            logger.info(f"Starting repository processing: {repo_path}")

            # Scan for files
            files_to_process = []
            async for file_info in self.file_scanner.scan_directory(
                repo_path, self.config.supported_languages
            ):
                files_to_process.append(file_info)

            logger.info(f"Found {len(files_to_process)} files to process")

            # Process files in batches
            async for chunk in self._process_files_in_batches(
                files_to_process, context, use_semantic_chunking, use_ast_chunking
            ):
                yield chunk

                # Check memory usage and trigger GC if needed
                if context.memory_tracker.should_trigger_gc():
                    context.memory_tracker.trigger_gc()

            logger.info(f"Repository processing completed. Stats: {context.stats}")

        except Exception as e:
            error_msg = f"Repository processing failed: {e}"
            logger.error(error_msg)
            context.update_stats(error=error_msg)
            raise

    async def _process_files_in_batches(
        self,
        files: list[dict],
        context: ProcessingContext,
        use_semantic_chunking: bool,
        use_ast_chunking: bool,
    ) -> AsyncGenerator[CodeChunk, None]:
        """Process files in memory-efficient batches."""

        for i in range(0, len(files), self.batch_size):
            batch = files[i : i + self.batch_size]

            logger.debug(
                f"Processing batch {i // self.batch_size + 1} " f"({len(batch)} files)"
            )

            # Process batch concurrently
            tasks = []
            for file_info in batch:
                task = asyncio.create_task(
                    self._process_single_file(
                        file_info, context, use_semantic_chunking, use_ast_chunking
                    )
                )
                tasks.append(task)

            # Wait for batch completion
            batch_results = await asyncio.gather(*tasks, return_exceptions=True)

            # Yield chunks from successful processing
            for result in batch_results:
                if isinstance(result, Exception):
                    logger.error(f"Batch processing error: {result}")
                    context.update_stats(error=str(result))
                elif result:
                    for chunk in result:
                        yield chunk

            # Memory management between batches
            if context.memory_tracker.should_trigger_gc():
                context.memory_tracker.trigger_gc()
                await asyncio.sleep(0.1)  # Allow cleanup

    async def _process_single_file(
        self,
        file_info: dict,
        context: ProcessingContext,
        use_semantic_chunking: bool,
        use_ast_chunking: bool,
    ) -> list[CodeChunk]:
        """Process a single file and return chunks."""
        file_path = Path(file_info["path"])
        language = file_info["language"]

        try:
            # Check file size
            if file_path.stat().st_size > self.max_file_size_mb * 1024 * 1024:
                logger.warning(f"Skipping large file: {file_path}")
                return []

            # Read file content
            try:
                with open(file_path, encoding="utf-8") as f:
                    content = f.read()
            except UnicodeDecodeError:
                # Try with different encoding
                with open(file_path, encoding="latin-1") as f:
                    content = f.read()

            line_count = content.count("\n") + 1
            chunks = []

            if use_ast_chunking:
                # Create AST-based chunks
                ast_chunks = await self.chunk_processor.create_chunks_from_ast(
                    file_path, language, self.ast_analyzer
                )
                chunks.extend(ast_chunks)

            else:
                # Create text-based chunks
                text_chunks = await self.chunk_processor.create_chunks_from_content(
                    content, file_path, language, use_semantic_chunking
                )
                chunks.extend(text_chunks)

            # Update statistics
            context.update_stats(
                files_count=1, lines_count=line_count, chunks_count=len(chunks)
            )
            context.processed_files.add(str(file_path))

            logger.debug(
                f"Processed {file_path}: {len(chunks)} chunks, {line_count} lines"
            )
            return chunks

        except Exception as e:
            error_msg = f"Failed to process {file_path}: {e}"
            logger.error(error_msg)
            context.update_stats(error=error_msg)
            context.failed_files.add(str(file_path))
            return []

    async def process_single_file(
        self,
        file_path: Path,
        use_semantic_chunking: bool = False,
        use_ast_chunking: bool = True,
    ) -> list[CodeChunk]:
        """
        Process a single file and return chunks.

        Args:
            file_path: Path to the file to process.
            use_semantic_chunking: Whether to use semantic chunking.
            use_ast_chunking: Whether to use AST-based chunking.

        Returns:
            List of CodeChunk objects.
        """
        # Detect language
        language = self.language_detector.detect_language(file_path)
        if not language or language not in self.config.supported_languages:
            logger.warning(f"Unsupported language for file: {file_path}")
            return []

        file_info = {"path": file_path, "language": language}
        context = ProcessingContext(self.config)

        return await self._process_single_file(
            file_info, context, use_semantic_chunking, use_ast_chunking
        )

    async def get_processing_stats(self) -> ProcessingStats:
        """Get current processing statistics."""
        # This would be called from an active processing context
        # For now, return empty stats
        return ProcessingStats()


    def estimate_processing_time(self, repo_path: Path) -> dict[str, float]:
        """
        Estimate processing time for a repository.

        Args:
            repo_path: Path to the repository.

        Returns:
            Dictionary with time estimates.
        """
        try:
            # Quick scan to count files and estimate size
            total_files = 0
            total_size_mb = 0

            for file_path in repo_path.rglob("*"):
                if file_path.is_file():
                    language = self.language_detector.detect_language(file_path)
                    if language in self.config.supported_languages:
                        total_files += 1
                        total_size_mb += file_path.stat().st_size / (1024 * 1024)

            # Rough estimates based on benchmarks
            # Assume ~100 files/minute and ~50MB/minute processing rate
            time_by_files = total_files / 100  # minutes
            time_by_size = total_size_mb / 50  # minutes

            estimated_time = max(time_by_files, time_by_size)

            return {
                "total_files": total_files,
                "total_size_mb": total_size_mb,
                "estimated_minutes": estimated_time,
                "estimated_hours": estimated_time / 60,
            }

        except Exception as e:
            logger.error(f"Failed to estimate processing time: {e}")
            return {"error": str(e)}
