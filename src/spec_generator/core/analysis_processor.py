"""
Analysis processor for code chunks.

This module processes code chunks and generates analysis results
using LLM providers with JSON parsing and fallback strategies.
"""

import json
import logging
import re
from typing import Any

from ..models import CodeChunk
from ..templates.prompts import PromptTemplates
from .llm_provider import LLMProvider

logger = logging.getLogger(__name__)


class AnalysisProcessor:
    """Processes code chunks and generates analysis results."""

    def __init__(self, llm_provider: LLMProvider):
        self.llm_provider = llm_provider
        self.prompt_templates = PromptTemplates()

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

    async def analyze_code_chunks_batch(self, chunks: list[CodeChunk]) -> list[dict[str, Any]]:
        """Analyze multiple code chunks using batch processing."""
        if not chunks:
            return []

        try:
            # Prepare all prompts for batch processing
            prompts = []
            for chunk in chunks:
                ast_info = (
                    f"ファイル: {chunk.file_path}\n"
                    f"言語: {chunk.language.value}\n"
                    f"行数: {chunk.start_line}-{chunk.end_line}"
                )

                prompt = self.prompt_templates.ANALYSIS_PROMPT.format(
                    code_content=chunk.content,
                    file_path=str(chunk.file_path),
                    language=chunk.language.value,
                    ast_info=ast_info,
                )
                prompts.append(prompt)

            # Use batch generation
            logger.info(f"Processing {len(chunks)} chunks in batch")
            batch_results = await self.llm_provider.generate_batch(prompts)

            # Parse all responses
            analyses = []
            for i, result in enumerate(batch_results):
                try:
                    analysis = self._parse_analysis_response(result)
                    analyses.append(analysis)
                except Exception as e:
                    logger.error(f"Failed to parse analysis for chunk {i}: {e}")
                    analyses.append({
                        "overview": f"Parsing failed: {str(e)}",
                        "functions": [],
                        "classes": [],
                        "dependencies": [],
                        "data_flow": "Unknown",
                        "error_handling": "Unknown",
                    })

            return analyses

        except Exception as e:
            logger.error(f"Batch analysis failed: {e}")
            # Fallback to individual processing
            logger.warning("Falling back to individual chunk processing")
            analyses = []
            for chunk in chunks:
                analysis = await self.analyze_code_chunk(chunk)
                analyses.append(analysis)
            return analyses

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
            class_count=class_count,
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
                    r"```json\s*(\{.*?\})\s*```", analysis_result, re.DOTALL
                )
                if json_match:
                    return json.loads(json_match.group(1))
            except json.JSONDecodeError:
                pass

            try:
                # Strategy 3: Find JSON object in text
                json_match = re.search(r"\{.*\}", analysis_result, re.DOTALL)
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
                "complexity_score": 5,  # Default medium complexity
            }