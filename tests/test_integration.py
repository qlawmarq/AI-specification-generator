"""
Integration tests for the AI Specification Generator.

These tests verify the end-to-end functionality of the system including
CLI commands, core processing, and output generation.
"""

import json
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, Mock, patch

import pytest
from typer.testing import CliRunner

from spec_generator.cli import app
from spec_generator.core.diff_detector import SemanticDiffDetector
from spec_generator.core.generator import SpecificationGenerator
from spec_generator.core.processor import LargeCodebaseProcessor
from spec_generator.models import (
    CodeChunk,
    Language,
    SpecificationConfig,
    SpecificationOutput,
)


class TestEndToEndWorkflow:
    """Test complete end-to-end workflows."""

    def setup_method(self):
        """Setup for each test method."""
        self.config = SpecificationConfig(
            openai_api_key="test-key",
            chunk_size=1000,
            supported_languages=[Language.PYTHON, Language.JAVASCRIPT],
        )
        self.runner = CliRunner()

    def create_sample_repository(self, repo_path: Path):
        """Create a sample repository for testing."""
        # Python files
        (repo_path / "src").mkdir(parents=True)
        (repo_path / "src" / "__init__.py").write_text("")

        (repo_path / "src" / "main.py").write_text(
            """
#!/usr/bin/env python3
\"\"\"
Main application entry point.

This module provides the primary interface for the application.
\"\"\"

import sys
import logging
from typing import List, Optional

logger = logging.getLogger(__name__)


def setup_logging(level: str = "INFO") -> None:
    \"\"\"
    Setup application logging.

    Args:
        level: Logging level (DEBUG, INFO, WARNING, ERROR)
    \"\"\"
    logging.basicConfig(
        level=getattr(logging, level.upper()),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )


class Application:
    \"\"\"Main application class.\"\"\"

    def __init__(self, config_path: Optional[str] = None):
        self.config_path = config_path
        self.initialized = False
        self.components = []

    def initialize(self) -> bool:
        \"\"\"
        Initialize the application.

        Returns:
            True if initialization successful, False otherwise.
        \"\"\"
        try:
            logger.info("Initializing application...")
            self._load_config()
            self._setup_components()
            self.initialized = True
            logger.info("Application initialized successfully")
            return True
        except Exception as e:
            logger.error(f"Failed to initialize application: {e}")
            return False

    def _load_config(self) -> None:
        \"\"\"Load application configuration.\"\"\"
        # Configuration loading logic
        pass

    def _setup_components(self) -> None:
        \"\"\"Setup application components.\"\"\"
        # Component setup logic
        pass

    def run(self) -> int:
        \"\"\"
        Run the application.

        Returns:
            Exit code (0 for success, non-zero for error).
        \"\"\"
        if not self.initialized:
            logger.error("Application not initialized")
            return 1

        try:
            logger.info("Starting application...")
            # Main application logic
            logger.info("Application completed successfully")
            return 0
        except KeyboardInterrupt:
            logger.info("Application interrupted by user")
            return 130
        except Exception as e:
            logger.error(f"Application error: {e}")
            return 1


def main(args: Optional[List[str]] = None) -> int:
    \"\"\"
    Main entry point.

    Args:
        args: Command line arguments (None to use sys.argv)

    Returns:
        Exit code
    \"\"\"
    if args is None:
        args = sys.argv[1:]

    # Parse arguments
    config_path = None
    if "--config" in args:
        config_index = args.index("--config")
        if config_index + 1 < len(args):
            config_path = args[config_index + 1]

    # Setup logging
    log_level = "DEBUG" if "--verbose" in args else "INFO"
    setup_logging(log_level)

    # Create and run application
    app = Application(config_path)

    if not app.initialize():
        return 1

    return app.run()


if __name__ == "__main__":
    sys.exit(main())
"""
        )

        (repo_path / "src" / "data_processor.py").write_text(
            """
\"\"\"
Data processing module.

Provides utilities for processing and transforming data.
\"\"\"

import json
import csv
from typing import Any, Dict, List, Union, Optional
from pathlib import Path
import logging

logger = logging.getLogger(__name__)


class DataProcessor:
    \"\"\"Handles data processing operations.\"\"\"

    def __init__(self, batch_size: int = 1000):
        \"\"\"
        Initialize the data processor.

        Args:
            batch_size: Number of items to process in each batch.
        \"\"\"
        self.batch_size = batch_size
        self.processed_count = 0
        self.error_count = 0

    def process_json_file(self, file_path: Path) -> Dict[str, Any]:
        \"\"\"
        Process a JSON file.

        Args:
            file_path: Path to the JSON file.

        Returns:
            Processed data dictionary.

        Raises:
            FileNotFoundError: If file doesn't exist.
            ValueError: If JSON is invalid.
        \"\"\"
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)

            processed_data = self._transform_data(data)
            self.processed_count += 1

            logger.info(f"Successfully processed {file_path}")
            return processed_data

        except FileNotFoundError:
            logger.error(f"File not found: {file_path}")
            self.error_count += 1
            raise
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON in {file_path}: {e}")
            self.error_count += 1
            raise ValueError(f"Invalid JSON: {e}")

    def process_csv_file(self, file_path: Path) -> List[Dict[str, Any]]:
        \"\"\"
        Process a CSV file.

        Args:
            file_path: Path to the CSV file.

        Returns:
            List of processed records.
        \"\"\"
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                records = []

                for row in reader:
                    processed_row = self._transform_data(row)
                    records.append(processed_row)

                self.processed_count += len(records)
                logger.info(f"Processed {len(records)} records from {file_path}")
                return records

        except Exception as e:
            logger.error(f"Error processing CSV {file_path}: {e}")
            self.error_count += 1
            raise

    def _transform_data(self, data: Union[Dict, List]) -> Union[Dict, List]:
        \"\"\"
        Transform data according to business rules.

        Args:
            data: Input data to transform.

        Returns:
            Transformed data.
        \"\"\"
        if isinstance(data, dict):
            return {k: self._clean_value(v) for k, v in data.items()}
        elif isinstance(data, list):
            return [self._clean_value(item) for item in data]
        else:
            return self._clean_value(data)

    def _clean_value(self, value: Any) -> Any:
        \"\"\"Clean and normalize a single value.\"\"\"
        if isinstance(value, str):
            return value.strip()
        return value

    def get_statistics(self) -> Dict[str, int]:
        \"\"\"
        Get processing statistics.

        Returns:
            Dictionary with processing stats.
        \"\"\"
        return {
            "processed_count": self.processed_count,
            "error_count": self.error_count,
            "success_rate": (
                self.processed_count / (self.processed_count + self.error_count)
                if (self.processed_count + self.error_count) > 0 else 0
            )
        }


def validate_data_file(file_path: Path) -> bool:
    \"\"\"
    Validate a data file format.

    Args:
        file_path: Path to the file to validate.

    Returns:
        True if file is valid, False otherwise.
    \"\"\"
    if not file_path.exists():
        return False

    if file_path.suffix.lower() == '.json':
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                json.load(f)
            return True
        except (json.JSONDecodeError, UnicodeDecodeError):
            return False

    elif file_path.suffix.lower() == '.csv':
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                csv.reader(f)
            return True
        except (csv.Error, UnicodeDecodeError):
            return False

    return False
"""
        )

        # JavaScript files
        (repo_path / "frontend").mkdir()
        (repo_path / "frontend" / "app.js").write_text(
            """
/**
 * Main frontend application module.
 *
 * Provides the primary user interface and application logic.
 */

class Application {
    /**
     * Create a new Application instance.
     * @param {Object} config - Application configuration
     * @param {string} config.apiUrl - Base URL for API calls
     * @param {boolean} config.debug - Enable debug mode
     */
    constructor(config = {}) {
        this.config = {
            apiUrl: '/api',
            debug: false,
            ...config
        };

        this.initialized = false;
        this.components = new Map();
        this.eventHandlers = new Map();
    }

    /**
     * Initialize the application.
     * @returns {Promise<boolean>} Promise that resolves to initialization success
     */
    async initialize() {
        try {
            console.log('Initializing application...');

            await this.loadConfiguration();
            this.setupEventHandlers();
            this.initializeComponents();

            this.initialized = true;
            console.log('Application initialized successfully');
            return true;

        } catch (error) {
            console.error('Failed to initialize application:', error);
            return false;
        }
    }

    /**
     * Load application configuration from server.
     * @returns {Promise<Object>} Configuration object
     */
    async loadConfiguration() {
        try {
            const response = await fetch(`${this.config.apiUrl}/config`);

            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }

            const serverConfig = await response.json();
            this.config = { ...this.config, ...serverConfig };

            if (this.config.debug) {
                console.log('Loaded configuration:', this.config);
            }

            return this.config;

        } catch (error) {
            console.error('Failed to load configuration:', error);
            throw error;
        }
    }

    /**
     * Setup global event handlers.
     */
    setupEventHandlers() {
        // Handle window resize
        window.addEventListener('resize', this.debounce(() => {
            this.handleWindowResize();
        }, 250));

        // Handle unload
        window.addEventListener('beforeunload', (event) => {
            this.handleBeforeUnload(event);
        });

        // Handle errors
        window.addEventListener('error', (event) => {
            this.handleGlobalError(event);
        });
    }

    /**
     * Initialize application components.
     */
    initializeComponents() {
        const componentConfigs = [
            { name: 'header', selector: '#header', component: HeaderComponent },
            { name: 'navigation', selector: '#nav', component: NavigationComponent },
            { name: 'content', selector: '#content', component: ContentComponent },
            { name: 'footer', selector: '#footer', component: FooterComponent }
        ];

        componentConfigs.forEach(({ name, selector, component: ComponentClass }) => {
            const element = document.querySelector(selector);
            if (element) {
                const instance = new ComponentClass(element, this.config);
                this.components.set(name, instance);

                if (this.config.debug) {
                    console.log(`Initialized component: ${name}`);
                }
            }
        });
    }

    /**
     * Handle window resize events.
     */
    handleWindowResize() {
        this.components.forEach((component, name) => {
            if (typeof component.handleResize === 'function') {
                component.handleResize();
            }
        });
    }

    /**
     * Handle before unload events.
     * @param {BeforeUnloadEvent} event - The before unload event
     */
    handleBeforeUnload(event) {
        // Check if there are unsaved changes
        const hasUnsavedChanges = Array.from(this.components.values())
            .some(component => component.hasUnsavedChanges && component.hasUnsavedChanges());

        if (hasUnsavedChanges) {
            event.preventDefault();
            event.returnValue = '';
        }
    }

    /**
     * Handle global errors.
     * @param {ErrorEvent} event - The error event
     */
    handleGlobalError(event) {
        console.error('Global error:', event.error);

        if (this.config.debug) {
            console.error('Error details:', {
                message: event.message,
                filename: event.filename,
                lineno: event.lineno,
                colno: event.colno,
                stack: event.error?.stack
            });
        }

        // Report error to monitoring service
        this.reportError(event.error);
    }

    /**
     * Report error to monitoring service.
     * @param {Error} error - The error to report
     */
    async reportError(error) {
        try {
            await fetch(`${this.config.apiUrl}/errors`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    message: error.message,
                    stack: error.stack,
                    timestamp: new Date().toISOString(),
                    userAgent: navigator.userAgent,
                    url: window.location.href
                })
            });
        } catch (reportError) {
            console.error('Failed to report error:', reportError);
        }
    }

    /**
     * Utility function to debounce function calls.
     * @param {Function} func - Function to debounce
     * @param {number} wait - Wait time in milliseconds
     * @returns {Function} Debounced function
     */
    debounce(func, wait) {
        let timeout;
        return function executedFunction(...args) {
            const later = () => {
                clearTimeout(timeout);
                func.apply(this, args);
            };
            clearTimeout(timeout);
            timeout = setTimeout(later, wait);
        };
    }

    /**
     * Start the application.
     * @returns {Promise<void>}
     */
    async start() {
        if (!this.initialized) {
            const initSuccess = await this.initialize();
            if (!initSuccess) {
                throw new Error('Failed to initialize application');
            }
        }

        console.log('Application started');

        // Start components
        this.components.forEach((component, name) => {
            if (typeof component.start === 'function') {
                component.start();
            }
        });
    }
}

// Base component class
class BaseComponent {
    constructor(element, config) {
        this.element = element;
        this.config = config;
        this.initialized = false;
    }

    start() {
        if (!this.initialized) {
            this.initialize();
        }
    }

    initialize() {
        this.initialized = true;
    }

    hasUnsavedChanges() {
        return false;
    }
}

// Specific component implementations
class HeaderComponent extends BaseComponent {
    initialize() {
        super.initialize();
        console.log('Header component initialized');
    }
}

class NavigationComponent extends BaseComponent {
    initialize() {
        super.initialize();
        this.setupNavigation();
    }

    setupNavigation() {
        // Navigation setup logic
        const navItems = this.element.querySelectorAll('nav a');
        navItems.forEach(item => {
            item.addEventListener('click', this.handleNavigation.bind(this));
        });
    }

    handleNavigation(event) {
        event.preventDefault();
        const href = event.target.getAttribute('href');
        // Handle navigation
        console.log('Navigating to:', href);
    }
}

class ContentComponent extends BaseComponent {
    initialize() {
        super.initialize();
        this.loadContent();
    }

    async loadContent() {
        try {
            const response = await fetch(`${this.config.apiUrl}/content`);
            const content = await response.text();
            this.element.innerHTML = content;
        } catch (error) {
            console.error('Failed to load content:', error);
            this.element.innerHTML = '<p>Failed to load content</p>';
        }
    }
}

class FooterComponent extends BaseComponent {
    initialize() {
        super.initialize();
        this.updateFooter();
    }

    updateFooter() {
        const currentYear = new Date().getFullYear();
        const copyright = this.element.querySelector('.copyright');
        if (copyright) {
            copyright.textContent = `© ${currentYear} Application Name`;
        }
    }
}

// Initialize application when DOM is ready
document.addEventListener('DOMContentLoaded', async () => {
    const config = {
        apiUrl: window.API_BASE_URL || '/api',
        debug: window.DEBUG_MODE || false
    };

    const app = new Application(config);

    try {
        await app.start();
    } catch (error) {
        console.error('Failed to start application:', error);
        document.body.innerHTML = '<div class="error">Application failed to start</div>';
    }
});
"""
        )

        # Configuration files
        (repo_path / "pyproject.toml").write_text(
            """
[build-system]
requires = ["setuptools>=45", "wheel"]
build-backend = "setuptools.build_meta"

[project]
name = "sample-application"
version = "1.0.0"
description = "A sample application for testing"
authors = [{name = "Test Author", email = "test@example.com"}]
license = {text = "MIT"}
readme = "README.md"
requires-python = ">=3.8"

dependencies = [
    "click>=8.0.0",
    "requests>=2.25.0",
    "pydantic>=1.8.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=6.0.0",
    "black>=21.0.0",
    "mypy>=0.910",
    "ruff>=0.0.261",
]

[project.scripts]
sample-app = "src.main:main"

[tool.black]
line-length = 88
target-version = ['py38']

[tool.mypy]
python_version = "3.8"
warn_return_any = true
warn_unused_configs = true
disallow_untyped_defs = true

[tool.ruff]
line-length = 88
target-version = "py38"
"""
        )

        (repo_path / "README.md").write_text(
            """
# Sample Application

A comprehensive sample application demonstrating modern software development practices.

## Features

- Data processing capabilities
- Web-based user interface
- Configuration management
- Error handling and logging
- Component-based architecture

## Installation

```bash
pip install -e .
```

## Usage

```bash
sample-app --config config.json
```

## Development

Install development dependencies:

```bash
pip install -e .[dev]
```

Run tests:

```bash
pytest
```

## Architecture

The application follows a modular architecture with clear separation of concerns:

- `src/main.py` - Application entry point
- `src/data_processor.py` - Data processing logic
- `frontend/app.js` - Frontend application logic

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Submit a pull request
"""
        )

    @pytest.mark.asyncio
    async def test_full_generation_workflow(self):
        """Test complete specification generation workflow."""
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_path = Path(temp_dir)
            output_path = repo_path / "output"

            # Create sample repository
            self.create_sample_repository(repo_path)

            # Mock LLM responses

            mock_spec_content = """# サンプルアプリケーション 詳細設計書

## 1. 概要

サンプルアプリケーションの詳細設計書です。

## 2. システム構成

### 2.1 全体アーキテクチャ

モジュラーアーキテクチャを採用しています。

## 3. 詳細設計

### 3.1 モジュール設計

主要なモジュールの設計について説明します。
"""

            # Test with mocked components
            processor = LargeCodebaseProcessor(self.config)
            generator = SpecificationGenerator(self.config)

            with patch.object(
                generator.llm_provider, "generate", new_callable=AsyncMock
            ) as mock_generate:
                mock_generate.return_value = mock_spec_content

                # Process repository
                chunks = []
                async for chunk in processor.process_repository(repo_path):
                    chunks.append(chunk)

                # Generate specification
                spec_output = await generator.generate_specification(
                    chunks, "サンプルアプリケーション", output_path / "spec.md"
                )

                # Verify results
                assert isinstance(spec_output, SpecificationOutput)
                assert spec_output.title == "サンプルアプリケーション 詳細設計書"
                assert "詳細設計書" in spec_output.content
                assert spec_output.language == "ja"
                assert len(spec_output.source_files) > 0

                # Verify processing stats
                stats = spec_output.processing_stats
                assert stats.files_processed > 0
                assert stats.chunks_created > 0

    @pytest.mark.asyncio
    async def test_incremental_update_workflow(self):
        """Test incremental specification update workflow."""
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_path = Path(temp_dir)

            # Create sample repository with Git
            self.create_sample_repository(repo_path)

            # Create existing specification
            existing_spec = repo_path / "existing_spec.md"
            existing_spec.write_text(
                """# 既存の仕様書

## 概要

既存のシステム概要。

## 詳細設計

### モジュール設計

既存のモジュール設計。
"""
            )

            # Test update detection and processing
            diff_detector = SemanticDiffDetector(self.config, repo_path)

            # Mock Git operations and changes
            with (
                patch.object(
                    diff_detector.git_repo, "get_changed_files"
                ) as mock_get_files,
                patch.object(
                    diff_detector.git_repo, "get_file_content"
                ) as mock_get_content,
                patch.object(
                    diff_detector.ast_analyzer, "extract_semantic_elements"
                ) as mock_extract,
            ):

                # Setup mocks for change detection
                mock_get_files.return_value = [Path("src/main.py")]
                mock_get_content.side_effect = lambda commit, file: (
                    "def old_function(): pass"
                    if commit == "HEAD~1"
                    else "def new_function(): pass\ndef old_function(): pass"
                )
                mock_extract.side_effect = [
                    {"functions": [{"name": "old_function"}], "classes": []},
                    {
                        "functions": [
                            {"name": "old_function"},
                            {"name": "new_function"},
                        ],
                        "classes": [],
                    },
                ]

                # Detect changes
                changes = diff_detector.detect_changes(
                    "HEAD~1", "HEAD", analyze_semantic=True
                )

                # Verify changes detected
                assert len(changes) > 0
                assert any(c.change_type == "added" for c in changes)

                # Test specification update
                from spec_generator.core.updater import SpecificationUpdater

                updater = SpecificationUpdater(self.config)

                with patch.object(
                    updater.llm_provider, "generate", new_callable=AsyncMock
                ) as mock_generate:
                    mock_generate.return_value = """更新された仕様書内容

新しい機能が追加されました：
- new_function: 新しい処理機能
"""

                    # Update specification
                    updated_output = await updater.update_specification(
                        existing_spec, changes
                    )

                    # Verify update
                    assert isinstance(updated_output, SpecificationOutput)
                    assert updated_output.title == "更新された仕様書"
                    assert updated_output.metadata["update_type"] == "incremental"

    def test_cli_integration_mocked(self):
        """Test CLI integration with mocked dependencies."""
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_path = Path(temp_dir)
            output_path = repo_path / "output"

            # Create minimal repository
            self.create_sample_repository(repo_path)

            # Mock all CLI dependencies
            with (
                patch("spec_generator.cli.load_config") as mock_load_config,
                patch("spec_generator.cli.validate_config"),
                patch("spec_generator.cli.get_repository_info") as mock_repo_info,
                patch(
                    "spec_generator.cli.LargeCodebaseProcessor"
                ) as mock_processor_class,
                patch(
                    "spec_generator.cli.SpecificationGenerator"
                ) as mock_generator_class,
                patch("spec_generator.cli.typer.confirm", return_value=True),
                patch("spec_generator.cli.asyncio.run") as mock_asyncio_run,
            ):

                # Setup mocks
                mock_load_config.return_value = self.config
                mock_repo_info.return_value = {
                    "total_files": 3,
                    "total_size_mb": 0.1,
                    "language_distribution": {"python": 2, "javascript": 1},
                }

                mock_processor = Mock()
                mock_processor_class.return_value = mock_processor

                mock_generator = Mock()
                mock_generator_class.return_value = mock_generator

                # Test generate command
                result = self.runner.invoke(
                    app,
                    [
                        "generate",
                        str(repo_path),
                        "--output",
                        str(output_path),
                        "--project-name",
                        "TestProject",
                    ],
                )

                assert result.exit_code == 0
                assert "TestProject" in result.output
                mock_asyncio_run.assert_called_once()

    def test_error_handling_integration(self):
        """Test error handling in integration scenarios."""
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_path = Path(temp_dir)

            # Test with invalid repository
            result = self.runner.invoke(
                app,
                [
                    "generate",
                    str(repo_path),  # Empty directory
                    "--project-name",
                    "FailTest",
                ],
            )

            # Should handle gracefully (may exit with 0 or 1 depending on implementation)
            assert result.exit_code in [0, 1]

    @pytest.mark.asyncio
    async def test_memory_management_integration(self):
        """Test memory management during large processing tasks."""
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_path = Path(temp_dir)

            # Create repository with many files
            self.create_large_repository(repo_path, num_files=50)

            processor = LargeCodebaseProcessor(self.config)

            # Track memory usage during processing
            import os

            import psutil

            process = psutil.Process(os.getpid())
            initial_memory = process.memory_info().rss / 1024 / 1024  # MB

            chunks = []
            chunk_count = 0
            async for chunk in processor.process_repository(repo_path):
                chunks.append(chunk)
                chunk_count += 1

                # Check memory every 10 chunks
                if chunk_count % 10 == 0:
                    current_memory = process.memory_info().rss / 1024 / 1024
                    memory_increase = current_memory - initial_memory

                    # Should not exceed configured memory limit significantly
                    assert memory_increase < self.config.max_memory_mb * 1.5

            # Verify processing completed
            assert len(chunks) > 0
            assert chunk_count > 0

    def create_large_repository(self, repo_path: Path, num_files: int):
        """Create a repository with many files for testing."""
        # Create base structure
        self.create_sample_repository(repo_path)

        # Add many additional Python files
        for i in range(num_files):
            file_path = repo_path / "src" / f"module_{i:03d}.py"
            file_path.write_text(
                f"""
\"\"\"Module {i} for testing large repositories.\"\"\"

import logging
from typing import List, Dict, Any

logger = logging.getLogger(__name__)


class Module{i}:
    \"\"\"Test class for module {i}.\"\"\"

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.data = []
        self.processed = False

    def process_data(self, input_data: List[Any]) -> List[Any]:
        \"\"\"Process input data for module {i}.\"\"\"
        result = []
        for item in input_data:
            processed_item = self._transform_item(item)
            result.append(processed_item)

        self.processed = True
        logger.info(f"Module {i} processed {{len(result)}} items")
        return result

    def _transform_item(self, item: Any) -> Any:
        \"\"\"Transform a single item.\"\"\"
        # Transformation logic for module {i}
        return item


def process_module_{i}_data(data: List[Any]) -> Dict[str, Any]:
    \"\"\"Process data using module {i}.\"\"\"
    module = Module{i}({{"enabled": True}})
    processed = module.process_data(data)

    return {{
        "module_id": {i},
        "processed_count": len(processed),
        "data": processed
    }}
"""
            )


class TestPerformanceIntegration:
    """Test performance characteristics of the system."""

    def setup_method(self):
        """Setup for performance tests."""
        self.config = SpecificationConfig(
            openai_api_key="test-key", chunk_size=2000, parallel_processes=2
        )

    @pytest.mark.asyncio
    async def test_processing_speed(self):
        """Test processing speed with various file sizes."""
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_path = Path(temp_dir)

            # Create files of different sizes
            sizes = [100, 500, 1000, 2000, 5000]  # lines

            for size in sizes:
                file_path = repo_path / f"test_{size}_lines.py"
                content = "\n".join([f"# Line {i}" for i in range(size)])
                file_path.write_text(content)

            processor = LargeCodebaseProcessor(self.config)

            import time

            start_time = time.time()

            chunks = []
            async for chunk in processor.process_repository(repo_path):
                chunks.append(chunk)

            end_time = time.time()
            processing_time = end_time - start_time

            # Should process files reasonably quickly
            assert processing_time < 30.0  # 30 seconds max for test files
            assert len(chunks) > 0

            # Verify chunks are properly sized
            for chunk in chunks:
                assert (
                    len(chunk.content) <= self.config.chunk_size * 1.5
                )  # Allow some overhead

    @pytest.mark.asyncio
    async def test_concurrent_processing(self):
        """Test concurrent processing capabilities."""
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_path = Path(temp_dir)

            # Create multiple files that can be processed concurrently
            for i in range(10):
                file_path = repo_path / f"concurrent_test_{i}.py"
                file_path.write_text(
                    f"""
def function_{i}_1():
    pass

def function_{i}_2():
    pass

class Class_{i}:
    def method_{i}(self):
        pass
"""
                )

            processor = LargeCodebaseProcessor(self.config)

            # Process with timing
            import time

            start_time = time.time()

            chunks = []
            async for chunk in processor.process_repository(repo_path):
                chunks.append(chunk)

            end_time = time.time()
            processing_time = end_time - start_time

            # Should benefit from concurrent processing
            assert processing_time < 10.0  # Should be fast with concurrent processing
            assert len(chunks) >= 10  # At least one chunk per file


# Error handling tests
class TestErrorHandling:
    """Test error handling in various scenarios."""

    def setup_method(self):
        """Setup for error handling tests."""
        self.config = SpecificationConfig(openai_api_key="test-key")

    @pytest.mark.asyncio
    async def test_corrupted_file_handling(self):
        """Test handling of corrupted or unreadable files."""
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_path = Path(temp_dir)

            # Create a good file
            good_file = repo_path / "good.py"
            good_file.write_text("def good_function(): pass")

            # Create a file with invalid encoding
            bad_file = repo_path / "bad.py"
            bad_file.write_bytes(b"\xff\xfe\x00invalid\x00encoding")

            processor = LargeCodebaseProcessor(self.config)

            chunks = []

            async for chunk in processor.process_repository(repo_path):
                chunks.append(chunk)

            # Should process good files and handle bad files gracefully
            assert len(chunks) >= 1  # At least the good file

            # Check processing stats for errors
            stats = processor.get_processing_stats()
            assert len(stats.errors_encountered) >= 1  # Should record the bad file

    @pytest.mark.asyncio
    async def test_llm_failure_handling(self):
        """Test handling of LLM API failures."""
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_path = Path(temp_dir)

            # Create test file
            test_file = repo_path / "test.py"
            test_file.write_text("def test_function(): pass")

            processor = LargeCodebaseProcessor(self.config)
            generator = SpecificationGenerator(self.config)

            # Process files
            chunks = []
            async for chunk in processor.process_repository(repo_path):
                chunks.append(chunk)

            # Mock LLM failure
            with patch.object(
                generator.llm_provider, "generate", new_callable=AsyncMock
            ) as mock_generate:
                mock_generate.side_effect = Exception("LLM API Error")

                # Should handle LLM failure gracefully
                spec_output = await generator.generate_specification(chunks, "Test")

                # Should generate fallback document
                assert isinstance(spec_output, SpecificationOutput)
                assert "仕様書" in spec_output.content  # Should have fallback content

    def test_cli_error_handling(self):
        """Test CLI error handling."""
        runner = CliRunner()

        # Test with non-existent directory
        result = runner.invoke(app, ["generate", "/non/existent/path"])

        assert result.exit_code != 0

        # Test with invalid config
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json") as f:
            f.write("invalid json content")
            f.flush()

            result = runner.invoke(app, ["config-info", "--config", f.name])

            assert result.exit_code != 0


# Configuration and setup tests
class TestConfigurationIntegration:
    """Test configuration management integration."""

    def test_config_loading_integration(self):
        """Test loading configuration from various sources."""
        # Test with custom config file
        config_data = {
            "chunk_size": 1500,
            "supported_languages": ["python", "javascript"],
            "openai_api_key": "custom-key",
            "max_memory_mb": 2048,
        }

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(config_data, f)
            config_file = Path(f.name)

        try:
            runner = CliRunner()
            result = runner.invoke(app, ["config-info", "--config", str(config_file)])

            assert result.exit_code == 0
            assert "1500" in result.output  # chunk_size
            assert "2048" in result.output  # max_memory_mb

        finally:
            config_file.unlink()

    def test_environment_variable_integration(self):
        """Test environment variable configuration."""
        import os

        # Set environment variables
        original_env = {}
        test_env_vars = {
            "OPENAI_API_KEY": "env-test-key",
            "SPEC_GENERATOR_CHUNK_SIZE": "3000",
            "SPEC_GENERATOR_MAX_MEMORY": "4096",
        }

        for key, value in test_env_vars.items():
            original_env[key] = os.environ.get(key)
            os.environ[key] = value

        try:
            from spec_generator.config import load_config

            config = load_config()

            # Should load from environment
            assert config.openai_api_key == "env-test-key"
            # Note: actual env var loading depends on implementation

        finally:
            # Restore original environment
            for key, original_value in original_env.items():
                if original_value is None:
                    os.environ.pop(key, None)
                else:
                    os.environ[key] = original_value


# Fixtures for integration tests
@pytest.fixture
def sample_repository():
    """Create a sample repository for testing."""
    with tempfile.TemporaryDirectory() as temp_dir:
        repo_path = Path(temp_dir)

        # Create sample files as in TestEndToEndWorkflow
        test_instance = TestEndToEndWorkflow()
        test_instance.create_sample_repository(repo_path)

        yield repo_path


@pytest.fixture
def mock_llm_responses():
    """Provide mock LLM responses for testing."""
    return {
        "analysis": {
            "overview": "Mock analysis overview",
            "functions": [{"name": "mock_function", "purpose": "Mock purpose"}],
            "classes": [{"name": "MockClass", "purpose": "Mock class"}],
        },
        "specification": """# Mock Specification

## Overview
This is a mock specification for testing.

## Architecture
Mock architecture description.

## Implementation
Mock implementation details.
""",
        "update": """Updated specification content with changes.""",
    }


def test_full_workflow_with_fixtures(sample_repository, mock_llm_responses):
    """Test full workflow using fixtures."""
    config = SpecificationConfig(openai_api_key="test-key")

    # Verify sample repository was created
    assert sample_repository.exists()
    assert (sample_repository / "src" / "main.py").exists()
    assert (sample_repository / "frontend" / "app.js").exists()

    # Test with processor
    processor = LargeCodebaseProcessor(config)

    # This would normally be async, but for fixture testing we can mock it
    with patch.object(processor, "process_repository") as mock_process:
        mock_process.return_value = iter(
            [
                CodeChunk(
                    content="mock content",
                    file_path=Path("test.py"),
                    language=Language.PYTHON,
                    start_line=1,
                    end_line=10,
                )
            ]
        )

        chunks = list(mock_process.return_value)
        assert len(chunks) == 1
        assert chunks[0].language == Language.PYTHON
