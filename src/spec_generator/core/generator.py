"""
Specification Generator using LangChain for IT documentation.

This module implements the SpecificationGenerator that uses progressive prompting
with LangChain to generate high-quality specification documents from
code analysis results.
"""

import logging
import time
from pathlib import Path
from typing import Any, Optional

from ..models import (
    CodeChunk,
    EnhancedCodeChunk,
    ProcessingStats,
    SpecificationConfig,
    SpecificationOutput,
)
from ..templates.specification import SpecificationTemplate
from ..templates.prompts import JapanesePromptHelper, PromptTemplates
from .analysis_processor import AnalysisProcessor
from .llm_provider import LLMProvider

logger = logging.getLogger(__name__)


class SpecificationGenerator:
    """
    Main specification generator using LangChain and progressive prompting.

    Implements a two-stage process:
    1. Code analysis using specialized prompts
    2. specification generation using templates
    """

    def __init__(self, config: SpecificationConfig):
        self.config = config
        self.llm_provider = LLMProvider(config)
        self.analysis_processor = AnalysisProcessor(self.llm_provider)
        self.spec_template = SpecificationTemplate("システム仕様書", config=config)
        self.prompt_templates = PromptTemplates()
        # Make actual_model_name accessible
        self._actual_model_name = self.llm_provider._actual_model_name

        # Statistics
        self.stats = ProcessingStats()

        logger.info("SpecificationGenerator initialized")

    async def generate_specification(
        self,
        chunks: list[CodeChunk],
        project_name: str = "システム",
        output_path: Optional[Path] = None,
    ) -> SpecificationOutput:
        """
        Generate specification document from code chunks.

        Args:
            chunks: List of code chunks to analyze.
            project_name: Name of the project.
            output_path: Optional path to save the specification.

        Returns:
            SpecificationOutput with generated document and metadata.
        """
        return await self._generate_specification_internal(chunks, project_name, output_path)

    async def generate_specification_from_enhanced_chunks(
        self,
        enhanced_chunks: list[EnhancedCodeChunk],
        project_name: str = "システム",
        output_path: Optional[Path] = None,
    ) -> SpecificationOutput:
        """Generate specification from enhanced chunks with class structure awareness."""
        # Convert EnhancedCodeChunk to CodeChunk for processing
        code_chunks = []
        for enhanced_chunk in enhanced_chunks:
            # Use unified content that preserves class structure
            unified_content = enhanced_chunk.get_unified_content()

            # Create a new CodeChunk with the unified content
            code_chunk = CodeChunk(
                content=unified_content,
                file_path=enhanced_chunk.original_chunk.file_path,
                language=enhanced_chunk.original_chunk.language,
                start_line=enhanced_chunk.original_chunk.start_line,
                end_line=enhanced_chunk.original_chunk.end_line,
                chunk_type=enhanced_chunk.original_chunk.chunk_type
            )
            code_chunks.append(code_chunk)

        return await self._generate_specification_internal(code_chunks, project_name, output_path)

    async def _generate_specification_internal(
        self,
        chunks: list[CodeChunk],
        project_name: str = "システム",
        output_path: Optional[Path] = None,
    ) -> SpecificationOutput:
        """
        Internal method to generate specification document.
        
        Args:
            chunks: List of code chunks to analyze.
            project_name: Name of the project.
            output_path: Optional path to save the specification.

        Returns:
            SpecificationOutput with generated document and metadata.
        """
        start_time = time.time()

        try:
            logger.info(f"Generating specification for {len(chunks)} chunks")

            # Stage 1: Analyze code chunks
            analyses = await self._analyze_chunks(chunks)

            # Stage 2: Combine analyses
            combined_analysis = await self.analysis_processor.combine_analyses(analyses)

            # Stage 3: Generate specification
            spec_content = await self._generate_specification_document(
                combined_analysis, project_name
            )

            # Stage 4: Create output
            output = self._create_specification_output(
                spec_content, chunks, project_name, start_time
            )

            # Stage 5: Save if path provided
            if output_path:
                await self._save_specification(output, output_path)

            logger.info(
                f"Specification generation completed in "
                f"{output.processing_stats.processing_time_seconds:.2f}s"
            )


            return output

        except Exception as e:
            logger.error(f"Specification generation failed: {e}")
            raise

    def _calculate_optimal_batch_size(self, total_chunks: int) -> int:
        """Calculate optimal batch size based on total chunks and configuration."""
        configured_batch_size = self.config.performance_settings.batch_size

        # For small numbers of chunks, process all at once
        if total_chunks <= 5:
            return total_chunks

        # For medium numbers, use configured batch size
        if total_chunks <= configured_batch_size:
            return configured_batch_size

        # For large numbers, cap at a reasonable limit to prevent timeouts
        max_batch_size = min(configured_batch_size, 20)
        return max_batch_size

    async def _analyze_chunks(self, chunks: list[CodeChunk]) -> list[dict[str, Any]]:
        """Analyze all code chunks using optimized batch processing."""
        if not chunks:
            return []

        analyses = []

        # Calculate optimal batch size for this processing run
        optimal_batch_size = self._calculate_optimal_batch_size(len(chunks))

        logger.info(f"Processing {len(chunks)} chunks with batch size {optimal_batch_size}")

        # Process chunks in optimized batches
        for i in range(0, len(chunks), optimal_batch_size):
            batch = chunks[i : i + optimal_batch_size]
            batch_num = i // optimal_batch_size + 1
            total_batches = (len(chunks) + optimal_batch_size - 1) // optimal_batch_size

            logger.info(f"Processing batch {batch_num}/{total_batches} ({len(batch)} chunks)")

            try:
                # Use the new batch processing method
                start_time = time.time()
                batch_results = await self.analysis_processor.analyze_code_chunks_batch(batch)
                batch_duration = time.time() - start_time

                logger.info(f"Batch {batch_num} completed in {batch_duration:.2f}s "
                           f"({batch_duration/len(batch):.2f}s per chunk)")

                # Collect results
                analyses.extend(batch_results)

            except Exception as e:
                logger.error(f"Batch {batch_num} failed: {e}")
                self.stats.errors_encountered.append(f"Batch {batch_num}: {str(e)}")

                # Add placeholder analyses for failed batch
                for chunk in batch:
                    analyses.append({
                        "overview": f"Batch processing failed: {str(e)}",
                        "functions": [],
                        "classes": [],
                        "dependencies": [],
                        "data_flow": "Unknown",
                        "error_handling": "Unknown",
                    })

        self.stats.chunks_created = len(analyses)
        logger.info(f"Total analysis completed: {len(analyses)} chunks processed")
        return analyses

    async def _generate_specification_document(
        self, analysis: dict[str, Any], project_name: str
    ) -> str:
        """Generate the specification document."""
        try:
            # Prepare analysis summary
            analysis_summary = JapanesePromptHelper.create_analysis_summary(analysis)

            # Generate specification using LangChain
            spec_content = await self.llm_provider.generate(
                self.prompt_templates.JAPANESE_SPEC_PROMPT.format(
                    analysis_results=analysis_summary,
                    document_title=f"{project_name} 詳細設計書",
                    project_overview=analysis.get("overview", ""),
                    technical_requirements="標準的な技術要件を適用",
                )
            )

            return spec_content

        except Exception as e:
            logger.error(f"Document generation failed: {e}")
            # Generate fallback document using template
            return self._generate_fallback_document(analysis, project_name)

    def _generate_fallback_document(
        self, analysis: dict[str, Any], project_name: str
    ) -> str:
        """Generate fallback document using templates when LLM fails."""
        document_data = {
            "document_type": "詳細設計書",
            "overview": {
                "purpose": "システムの詳細設計を記述する",
                "target_audience": "開発チーム、運用チーム",
                "system_overview": analysis.get(
                    "overview", "システム概要が生成できませんでした"
                ),
            },
            "modules": analysis.get("modules", {}),
            "nonfunctional": {
                "performance": "性能要件は別途定義されます",
                "security": "セキュリティ要件は別途定義されます",
                "availability": "可用性要件は別途定義されます",
                "maintainability": "保守性要件は別途定義されます",
            },
            "operations": {
                "deployment": "デプロイメント方式は別途定義されます",
                "monitoring": "監視方式は別途定義されます",
                "backup": "バックアップ方式は別途定義されます",
            },
        }

        self.spec_template.project_name = project_name
        return self.spec_template.generate_complete_document(document_data)

    def _create_specification_output(
        self,
        content: str,
        source_chunks: list[CodeChunk],
        project_name: str,
        start_time: float,
    ) -> SpecificationOutput:
        """Create SpecificationOutput object."""
        # Update processing stats
        self.stats.processing_time_seconds = time.time() - start_time
        self.stats.files_processed = len({chunk.file_path for chunk in source_chunks})
        self.stats.lines_processed = sum(
            chunk.end_line - chunk.start_line + 1 for chunk in source_chunks
        )

        # Extract source files
        source_files = list({chunk.file_path for chunk in source_chunks})

        return SpecificationOutput(
            title=f"{project_name} 詳細設計書",
            content=content,
            language="ja",
            created_at=time.strftime("%Y-%m-%d %H:%M:%S"),
            source_files=source_files,
            processing_stats=self.stats,
            metadata={
                "generator_version": "1.0",
                "llm_model": self._actual_model_name or "unknown",
                "chunk_count": len(source_chunks),
            },
            language_distribution=self._calculate_language_distribution(source_chunks),
        )

    def _calculate_language_distribution(
        self, chunks: list[CodeChunk]
    ) -> dict[str, int]:
        """Calculate distribution of programming languages in chunks."""
        distribution = {}
        for chunk in chunks:
            lang = chunk.language.value
            distribution[lang] = distribution.get(lang, 0) + 1
        return distribution

    async def _save_specification(
        self, output: SpecificationOutput, output_path: Path
    ) -> None:
        """Save specification to file."""
        try:
            # Ensure directory exists
            output_path.parent.mkdir(parents=True, exist_ok=True)

            # Write specification content
            with open(output_path, "w", encoding="utf-8") as f:
                f.write(output.content)

            # Log metadata information instead of writing to file
            logger.info(f"Specification saved to {output_path}")
            logger.info(f"Title: {output.title}")
            logger.info(f"Created at: {output.created_at}")
            logger.info(f"Source files: {[str(f) for f in output.source_files]}")
            logger.info(f"Processing stats: Files processed: {output.processing_stats.files_processed}, "
                       f"Lines processed: {output.processing_stats.lines_processed}, "
                       f"Chunks created: {output.processing_stats.chunks_created}, "
                       f"Processing time: {output.processing_stats.processing_time_seconds:.2f}s")
            if output.metadata:
                logger.info(f"Additional metadata: {output.metadata}")

        except Exception as e:
            logger.error(f"Failed to save specification: {e}")
            raise