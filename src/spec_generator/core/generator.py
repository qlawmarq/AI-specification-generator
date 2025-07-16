"""
Specification Generator using LangChain for Japanese IT documentation.

This module implements the SpecificationGenerator that uses progressive prompting
with LangChain to generate high-quality Japanese specification documents from
code analysis results.
"""

import asyncio
import json
import logging
import re
import time
from pathlib import Path
from typing import Any, Optional

from langchain.chains import LLMChain
from langchain_openai import ChatOpenAI

from ..models import (
    CodeChunk,
    ProcessingStats,
    SpecificationConfig,
    SpecificationOutput,
)
from ..templates.japanese_spec import (
    JapaneseSpecificationTemplate,
)
from ..templates.prompts import JapanesePromptHelper, PromptTemplates

logger = logging.getLogger(__name__)


class LLMProvider:
    """LLM provider abstraction for different OpenAI configurations."""

    def __init__(self, config: SpecificationConfig):
        self.config = config
        self.llm = self._create_llm()
        self.request_count = 0
        self.last_request_time = 0.0

    def _create_llm(self) -> Any:
        """Create LLM instance based on configuration."""
        # Determine provider
        provider = self.config.llm_provider or self._detect_provider()

        if provider == "gemini" and self.config.gemini_api_key:
            # Gemini API
            import httpx
            from langchain_google_genai import ChatGoogleGenerativeAI

            # Use gemini-specific model names
            model = self.config.llm_model or "gemini-2.0-flash"

            # Create async client with timeout configuration
            timeout_config = httpx.Timeout(
                timeout=self.config.performance_settings.request_timeout,
                connect=5.0,
                read=self.config.performance_settings.request_timeout - 5.0
            )
            async_client = httpx.AsyncClient(timeout=timeout_config)

            return ChatGoogleGenerativeAI(
                model=model,
                temperature=0.3,
                google_api_key=self.config.gemini_api_key,
                max_retries=self.config.performance_settings.max_retries,
                http_async_client=async_client,
            )
        elif (
            provider == "azure"
            and self.config.azure_openai_endpoint
            and self.config.azure_openai_key
        ):
            # Azure OpenAI
            model = self.config.llm_model or "gpt-4"
            return ChatOpenAI(
                model=model,
                temperature=0.3,
                azure_endpoint=self.config.azure_openai_endpoint,
                api_key=self.config.azure_openai_key,
                api_version=self.config.azure_openai_version,
                timeout=self.config.performance_settings.request_timeout,
                max_retries=self.config.performance_settings.max_retries,
            )
        elif provider == "openai" and self.config.openai_api_key:
            # Standard OpenAI
            model = self.config.llm_model or "gpt-4"
            return ChatOpenAI(
                model=model,
                temperature=0.3,
                api_key=self.config.openai_api_key,
                timeout=self.config.performance_settings.request_timeout,
                max_retries=self.config.performance_settings.max_retries,
            )
        else:
            raise ValueError(f"No valid configuration found for provider: {provider}")

    def _detect_provider(self) -> str:
        """Auto-detect provider based on available credentials."""
        if self.config.gemini_api_key:
            return "gemini"
        elif self.config.azure_openai_endpoint and self.config.azure_openai_key:
            return "azure"
        elif self.config.openai_api_key:
            return "openai"
        return "unknown"

    async def generate(self, prompt: str, **kwargs) -> str:
        """Generate response with rate limiting."""
        await self._rate_limit()

        try:
            # Use async execution with timeout to avoid blocking
            # Reason: Apply configured timeout to LLM operations to prevent infinite waits
            timeout_seconds = self.config.performance_settings.request_timeout
            response = await asyncio.wait_for(
                asyncio.get_event_loop().run_in_executor(
                    None, self.llm.predict, prompt
                ),
                timeout=timeout_seconds
            )

            self.request_count += 1
            logger.debug(f"LLM request {self.request_count} completed")
            return response

        except Exception as e:
            logger.error(f"LLM generation failed: {e}")
            raise

    async def _rate_limit(self) -> None:
        """Implement rate limiting based on RPM."""
        current_time = time.time()
        time_since_last = current_time - self.last_request_time
        min_interval = 60.0 / self.config.performance_settings.rate_limit_rpm

        if time_since_last < min_interval:
            sleep_time = min_interval - time_since_last
            logger.debug(f"Rate limiting: sleeping for {sleep_time:.2f}s")
            await asyncio.sleep(sleep_time)

        self.last_request_time = time.time()


class AnalysisProcessor:
    """Processes code chunks and generates analysis results."""

    def __init__(self, llm_provider: LLMProvider):
        self.llm_provider = llm_provider
        self.prompt_templates = PromptTemplates()
        self.analysis_chain = LLMChain(
            llm=llm_provider.llm, prompt=self.prompt_templates.ANALYSIS_PROMPT
        )

    async def analyze_code_chunk(self, chunk: CodeChunk) -> dict[str, Any]:
        """Analyze a single code chunk."""
        try:
            # Prepare AST info (simplified for now)
            ast_info = (
                f"ファイル: {chunk.file_path}\n"
                f"言語: {chunk.language.value}\n"
                f"行数: {chunk.start_line}-{chunk.end_line}"
            )

            # Run analysis
            analysis_result = await self.llm_provider.generate(
                self.prompt_templates.ANALYSIS_PROMPT.format(
                    code_content=chunk.content,
                    file_path=str(chunk.file_path),
                    language=chunk.language.value,
                    ast_info=ast_info,
                )
            )

            # Parse JSON response with multiple fallback strategies
            return self._parse_analysis_response(analysis_result)

        except Exception as e:
            logger.error(f"Analysis failed for chunk {chunk.file_path}: {e}")
            return {
                "overview": f"Analysis failed: {str(e)}",
                "functions": [],
                "classes": [],
                "dependencies": [],
                "data_flow": "Unknown",
                "error_handling": "Unknown",
            }

    async def combine_analyses(self, analyses: list[dict[str, Any]]) -> dict[str, Any]:
        """Combine multiple analysis results into a cohesive summary."""
        combined = {
            "overview": "",
            "modules": {},
            "functions": [],
            "classes": [],
            "dependencies": [],
            "data_flows": [],
            "error_handling_strategies": [],
            "performance_considerations": [],
            "security_considerations": [],
        }

        # Group analyses by file/module
        module_analyses = {}
        for analysis in analyses:
            # Extract module name from overview or create generic
            module_name = self._extract_module_name(analysis)
            if module_name not in module_analyses:
                module_analyses[module_name] = []
            module_analyses[module_name].append(analysis)

        # Combine module analyses
        for module_name, module_analysis_list in module_analyses.items():
            combined_module = self._combine_module_analyses(module_analysis_list)
            combined["modules"][module_name] = combined_module

            # Aggregate functions and classes
            for analysis in module_analysis_list:
                combined["functions"].extend(analysis.get("functions", []))
                combined["classes"].extend(analysis.get("classes", []))
                combined["dependencies"].extend(analysis.get("dependencies", []))

        # Create overall overview
        combined["overview"] = self._create_combined_overview(combined)

        return combined

    def _extract_module_name(self, analysis: dict[str, Any]) -> str:
        """Extract module name from analysis."""
        # Try to extract from overview or use generic name
        overview = analysis.get("overview", "")
        if "module" in overview.lower() or "モジュール" in overview:
            # Simple extraction - could be improved
            return "extracted_module"
        return "general_module"

    def _combine_module_analyses(
        self, analyses: list[dict[str, Any]]
    ) -> dict[str, Any]:
        """Combine analyses for a single module."""
        combined = {
            "purpose": "",
            "functions": [],
            "classes": [],
            "dependencies": [],
            "complexity": "medium",
        }

        purposes = []
        for analysis in analyses:
            if overview := analysis.get("overview"):
                purposes.append(overview)
            combined["functions"].extend(analysis.get("functions", []))
            combined["classes"].extend(analysis.get("classes", []))
            combined["dependencies"].extend(analysis.get("dependencies", []))

        # Combine purposes
        # Reason: Ensure all purposes are strings before joining to avoid type errors
        purposes_str = [str(p) if not isinstance(p, str) else p for p in purposes]
        combined["purpose"] = " ".join(purposes_str)

        # Calculate complexity based on function/class count
        total_elements = len(combined["functions"]) + len(combined["classes"])
        if total_elements > 10:
            combined["complexity"] = "high"
        elif total_elements > 5:
            combined["complexity"] = "medium"
        else:
            combined["complexity"] = "low"

        return combined

    def _create_combined_overview(self, combined: dict[str, Any]) -> str:
        """Create overall system overview."""
        module_count = len(combined["modules"])
        function_count = len(combined["functions"])
        class_count = len(combined["classes"])

        return PromptTemplates.SYSTEM_OVERVIEW_PROMPT.format(
            module_count=module_count,
            function_count=function_count,
            class_count=class_count
        )

    def _parse_analysis_response(self, analysis_result: str) -> dict[str, Any]:
        """Parse LLM analysis response with multiple fallback strategies."""
        try:
            # Strategy 1: Direct JSON parsing
            return json.loads(analysis_result)
        except json.JSONDecodeError:
            try:
                # Strategy 2: Extract from markdown code blocks
                json_match = re.search(
                    r'```json\s*(\{.*?\})\s*```', analysis_result, re.DOTALL
                )
                if json_match:
                    return json.loads(json_match.group(1))
            except json.JSONDecodeError:
                pass

            try:
                # Strategy 3: Find JSON object in text
                json_match = re.search(r'\{.*\}', analysis_result, re.DOTALL)
                if json_match:
                    return json.loads(json_match.group(0))
            except json.JSONDecodeError:
                pass

            # Strategy 4: Structured fallback
            logger.warning("Failed to parse analysis JSON, using fallback structure")
            return {
                "overview": (
                    analysis_result[:500] + "..."
                    if len(analysis_result) > 500
                    else analysis_result
                ),
                "functions": [],
                "classes": [],
                "dependencies": [],
                "data_flow": "Unknown",
                "error_handling": "Unknown",
                "key_components": ["Unable to parse detailed analysis"],
                "recommendations": ["Review LLM response format"],
                "complexity_score": 5  # Default medium complexity
            }


class SpecificationGenerator:
    """
    Main specification generator using LangChain and progressive prompting.

    Implements a two-stage process:
    1. Code analysis using specialized prompts
    2. Japanese specification generation using templates
    """

    def __init__(self, config: SpecificationConfig):
        self.config = config
        self.llm_provider = LLMProvider(config)
        self.analysis_processor = AnalysisProcessor(self.llm_provider)
        self.spec_template = JapaneseSpecificationTemplate("システム仕様書")
        self.prompt_templates = PromptTemplates()

        # Create generation chain
        self.generation_chain = LLMChain(
            llm=self.llm_provider.llm, prompt=self.prompt_templates.JAPANESE_SPEC_PROMPT
        )

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
        Generate Japanese specification document from code chunks.

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

    async def _analyze_chunks(self, chunks: list[CodeChunk]) -> list[dict[str, Any]]:
        """Analyze all code chunks."""
        analyses = []

        # Process chunks in batches to manage rate limits
        batch_size = self.config.performance_settings.batch_size

        for i in range(0, len(chunks), batch_size):
            batch = chunks[i : i + batch_size]
            logger.debug(f"Processing analysis batch {i // batch_size + 1}")

            # Process batch concurrently
            batch_tasks = [
                self.analysis_processor.analyze_code_chunk(chunk) for chunk in batch
            ]

            batch_results = await asyncio.gather(*batch_tasks, return_exceptions=True)

            # Collect successful results
            for result in batch_results:
                if isinstance(result, Exception):
                    logger.error(f"Chunk analysis failed: {result}")
                    self.stats.errors_encountered.append(str(result))
                else:
                    analyses.append(result)

        self.stats.chunks_created = len(analyses)
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
                "llm_model": "gpt-4",
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

            # Write metadata file
            metadata_path = output_path.with_suffix(".metadata.json")
            metadata = {
                "title": output.title,
                "created_at": output.created_at,
                "source_files": [str(f) for f in output.source_files],
                "processing_stats": output.processing_stats.dict(),
                "metadata": output.metadata,
            }

            with open(metadata_path, "w", encoding="utf-8") as f:
                json.dump(metadata, f, ensure_ascii=False, indent=2)

            logger.info(f"Specification saved to {output_path}")

        except Exception as e:
            logger.error(f"Failed to save specification: {e}")
            raise

    async def update_specification(
        self,
        existing_spec_path: Path,
        changes: list[dict[str, Any]],
        output_path: Optional[Path] = None,
    ) -> SpecificationOutput:
        """Update existing specification with changes."""
        try:
            # Read existing specification
            with open(existing_spec_path, encoding="utf-8") as f:
                existing_content = f.read()

            # Create change summary
            change_summary = self._create_change_summary(changes)

            # Generate update using LLM
            updated_content = await self.llm_provider.generate(
                self.prompt_templates.UPDATE_SPEC_PROMPT.format(
                    existing_spec=existing_content,
                    changes=json.dumps(changes, ensure_ascii=False, indent=2),
                    change_summary=change_summary,
                )
            )

            # Create output
            output = SpecificationOutput(
                title="更新された仕様書",
                content=updated_content,
                language="ja",
                created_at=time.strftime("%Y-%m-%d %H:%M:%S"),
                source_files=[existing_spec_path],
                processing_stats=ProcessingStats(),
                metadata={"update_type": "incremental", "change_count": len(changes)},
            )

            # Save if path provided
            if output_path:
                await self._save_specification(output, output_path)

            return output

        except Exception as e:
            logger.error(f"Specification update failed: {e}")
            raise

    def _create_change_summary(self, changes: list[dict[str, Any]]) -> str:
        """Create summary of changes for update prompt."""
        summary_parts = []

        change_types = {}
        for change in changes:
            change_type = change.get("change_type", "unknown")
            change_types[change_type] = change_types.get(change_type, 0) + 1

        for change_type, count in change_types.items():
            summary_parts.append(f"- {change_type}: {count}件")

        return "\n".join(summary_parts)
