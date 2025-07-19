"""
Core data models for the Specification Generator.

This module defines Pydantic models for type safety and configuration management.
"""

import os
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any, Optional, Union

from dotenv import load_dotenv
from pydantic import BaseModel, Field, validator


class Language(Enum):
    """Supported programming languages for specification generation."""

    PYTHON = "python"
    JAVASCRIPT = "javascript"
    TYPESCRIPT = "typescript"
    JAVA = "java"
    CPP = "cpp"


class CodeChunk(BaseModel):
    """Represents a chunk of code for processing."""

    content: str = Field(..., description="The code content")
    file_path: Path = Field(..., description="Path to the source file")
    language: Language = Field(..., description="Programming language")
    start_line: int = Field(..., ge=1, description="Starting line number")
    end_line: int = Field(..., ge=1, description="Ending line number")
    chunk_type: str = Field(
        ..., description="Type of chunk (function, class, module, etc.)"
    )

    @validator("end_line")
    def end_line_must_be_greater_than_start_line(
        cls, v: int, values: dict[str, Any]
    ) -> int:
        """Ensure end_line is greater than or equal to start_line."""
        if "start_line" in values and v < values["start_line"]:
            raise ValueError("end_line must be greater than or equal to start_line")
        return v


class SemanticChange(BaseModel):
    """Represents a semantic change detected in code."""

    file_path: Path = Field(..., description="Path to the changed file")
    change_type: str = Field(
        ..., description="Type of change (added, removed, modified)"
    )
    element_name: str = Field(..., description="Name of the changed element")
    element_type: str = Field(
        ..., description="Type of element (function, class, etc.)"
    )
    impact_score: float = Field(..., ge=0.0, le=10.0, description="Impact score (0-10)")
    dependencies: list[str] = Field(
        default_factory=list, description="List of dependencies"
    )

    @validator("change_type")
    def validate_change_type(cls, v: str) -> str:
        """Validate change type."""
        allowed_types = {"added", "removed", "modified"}
        if v not in allowed_types:
            raise ValueError(f"change_type must be one of {allowed_types}")
        return v


class TableFormattingSettings(BaseModel):
    """Configuration for table cell content formatting."""
    
    max_cell_length: int = Field(default=80, description="Maximum characters per table cell")
    max_methods_per_cell: int = Field(default=5, description="Maximum methods shown per cell")
    method_separator: str = Field(default=", ", description="Separator for method lists")
    truncation_suffix: str = Field(default="...", description="Suffix for truncated content")
    preserve_japanese: bool = Field(default=True, description="Preserve character integrity")


class JapaneseSpecSettings(BaseModel):
    """Settings for specification generation."""

    document_title: str = Field(default="システム仕様書", description="Document title")


class PerformanceSettings(BaseModel):
    """Performance and rate limiting settings."""

    request_timeout: int = Field(
        default=300, ge=1, description="Request timeout in seconds"
    )
    max_retries: int = Field(default=3, ge=0, description="Maximum retry attempts")
    retry_delay: int = Field(
        default=1, ge=0, description="Delay between retries in seconds"
    )
    rate_limit_rpm: int = Field(
        default=200, ge=1, description="Rate limit requests per minute"
    )
    batch_size: int = Field(default=10, ge=1, description="Batch size for processing")


class SpecificationConfig(BaseModel):
    """Configuration for the specification generator."""

    # LLM Configuration
    openai_api_key: Optional[str] = Field(default=None, description="OpenAI API key")
    azure_openai_endpoint: Optional[str] = Field(
        default=None, description="Azure OpenAI endpoint"
    )
    azure_openai_key: Optional[str] = Field(
        default=None, description="Azure OpenAI key"
    )
    azure_openai_version: str = Field(
        default="2024-02-01", description="Azure OpenAI API version"
    )
    gemini_api_key: Optional[str] = Field(default=None, description="Gemini API key")
    llm_provider: Optional[str] = Field(
        default=None, description="LLM provider (openai, azure, gemini)"
    )
    llm_model: Optional[str] = Field(default=None, description="Override default model")

    # Processing Configuration
    chunk_size: int = Field(default=4000, ge=100, description="Text chunk size")
    chunk_overlap: int = Field(default=200, ge=0, description="Chunk overlap size")
    max_memory_mb: int = Field(
        default=1024, ge=64, description="Maximum memory usage in MB"
    )
    parallel_processes: int = Field(
        default=4, ge=1, le=16, description="Number of parallel processes"
    )

    # Language Support
    supported_languages: list[Language] = Field(
        default_factory=lambda: [
            Language.PYTHON, 
            Language.JAVASCRIPT, 
            Language.TYPESCRIPT, 
            Language.JAVA, 
            Language.CPP
        ],
        description="List of supported programming languages",
    )

    # Output Configuration
    output_format: str = Field(
        default="japanese_detailed_design", description="Output format"
    )

    # File Processing
    exclude_patterns: list[str] = Field(
        default_factory=lambda: [
            "*/node_modules/*",
            "*/venv/*",
            "*/.*",
            "*.pyc",
            "__pycache__",
            "*/build/*",
            "*/dist/*",
            "*/target/*",
            "*.min.js",
            "*.bundle.js",
        ],
        description="Patterns to exclude from processing",
    )


    # Specification Settings
    japanese_spec_settings: JapaneseSpecSettings = Field(
        default_factory=JapaneseSpecSettings,
        description="specification generation settings",
    )

    # Performance Settings
    performance_settings: PerformanceSettings = Field(
        default_factory=PerformanceSettings,
        description="Performance and rate limiting settings",
    )

    # Table Formatting Settings
    table_formatting: TableFormattingSettings = Field(
        default_factory=TableFormattingSettings,
        description="Table cell content formatting settings",
    )

    @validator("chunk_overlap")
    def chunk_overlap_must_be_less_than_chunk_size(
        cls, v: int, values: dict[str, Any]
    ) -> int:
        """Ensure chunk_overlap is less than chunk_size."""
        if "chunk_size" in values and v >= values["chunk_size"]:
            raise ValueError("chunk_overlap must be less than chunk_size")
        return v

    @validator("llm_provider")
    def validate_llm_provider(cls, v: Optional[str]) -> Optional[str]:
        """Validate LLM provider."""
        if v is None:
            return v
        allowed_providers = {"openai", "azure", "gemini"}
        if v not in allowed_providers:
            raise ValueError(f"llm_provider must be one of {allowed_providers}")
        return v


class ConfigLoader:
    """Loads configuration from various sources."""

    @staticmethod
    def load_from_env() -> SpecificationConfig:
        """Load configuration from environment variables."""
        load_dotenv()

        config_dict: dict[str, Any] = {}

        # LLM Configuration - using simplified pattern
        env_mappings = {
            "OPENAI_API_KEY": "openai_api_key",
            "AZURE_OPENAI_ENDPOINT": "azure_openai_endpoint", 
            "AZURE_OPENAI_KEY": "azure_openai_key",
            "AZURE_OPENAI_VERSION": "azure_openai_version",
            "GEMINI_API_KEY": "gemini_api_key",
            "LLM_PROVIDER": "llm_provider",
            "LLM_MODEL": "llm_model",
            "OUTPUT_FORMAT": "output_format",
        }

        for env_key, config_key in env_mappings.items():
            if value := os.getenv(env_key):
                config_dict[config_key] = value

        # Processing Configuration - integer values
        int_mappings = {
            "MAX_MEMORY_MB": "max_memory_mb",
            "PARALLEL_PROCESSES": "parallel_processes",
            "CHUNK_SIZE": "chunk_size", 
            "CHUNK_OVERLAP": "chunk_overlap",
        }

        for env_key, config_key in int_mappings.items():
            if value := os.getenv(env_key):
                config_dict[config_key] = int(value)

        # Performance Settings
        performance_mappings = {
            "REQUEST_TIMEOUT": "request_timeout",
            "MAX_RETRIES": "max_retries",
            "RETRY_DELAY": "retry_delay",
            "RATE_LIMIT_RPM": "rate_limit_rpm",
            "BATCH_SIZE": "batch_size",
        }

        performance_dict = {}
        for env_key, config_key in performance_mappings.items():
            if value := os.getenv(env_key):
                performance_dict[config_key] = int(value)

        if performance_dict:
            config_dict["performance_settings"] = PerformanceSettings(**performance_dict)

        return SpecificationConfig(**config_dict)


class ProcessingStats(BaseModel):
    """Statistics for processing operations."""

    files_processed: int = Field(default=0, description="Number of files processed")
    lines_processed: int = Field(default=0, description="Number of lines processed")
    chunks_created: int = Field(default=0, description="Number of chunks created")
    processing_time_seconds: float = Field(
        default=0.0, description="Total processing time"
    )
    errors_encountered: list[str] = Field(
        default_factory=list, description="List of errors"
    )


@dataclass
class ClassStructure:
    """Represents a complete class with all its methods and attributes."""
    name: str
    methods: list
    attributes: list
    docstring: Optional[str]
    start_line: int
    end_line: int
    file_path: str

    def to_unified_chunk(self) -> str:
        """Convert class structure to unified code chunk."""
        # Construct a unified representation of the class
        lines = []
        if self.docstring:
            lines.append(f'"""\n{self.docstring}\n"""')

        lines.append(f"class {self.name}:")

        # Add methods
        for method in self.methods:
            method_content = getattr(method, 'content', str(method))
            lines.append(f"    {method_content}")

        # Add attributes info
        for attr in self.attributes:
            attr_content = getattr(attr, 'content', str(attr))
            lines.append(f"    # Attribute: {attr_content}")

        return "\n".join(lines)

    def get_method_names(self) -> list[str]:
        """Get list of method names."""
        return [getattr(method, 'name', str(method)) for method in self.methods]


@dataclass
class EnhancedCodeChunk:
    """Enhanced code chunk with class structure context."""
    original_chunk: "CodeChunk"
    class_structures: list[ClassStructure]
    is_complete_class: bool
    parent_class: Optional[str]

    def get_unified_content(self) -> str:
        """Get unified content that preserves class structure."""
        if self.is_complete_class and self.class_structures:
            # Return unified class representation
            return "\n\n".join([
                cls.to_unified_chunk() for cls in self.class_structures
            ])
        return self.original_chunk.content


class SpecificationOutput(BaseModel):
    """Output specification document."""

    title: str = Field(..., description="Document title")
    content: str = Field(..., description="Document content in markdown")
    language: str = Field(default="ja", description="Document language")
    created_at: str = Field(..., description="Creation timestamp")
    source_files: list[Path] = Field(..., description="List of source files analyzed")
    processing_stats: ProcessingStats = Field(..., description="Processing statistics")
    metadata: dict[str, Union[str, int, float]] = Field(
        default_factory=dict, description="Additional metadata"
    )
    language_distribution: dict[str, int] = Field(
        default_factory=dict, description="Programming language distribution"
    )
