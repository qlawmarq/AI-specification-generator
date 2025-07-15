"""
Unit tests for spec_generator.core.diff_detector module.

Tests for SemanticDiffDetector and Git integration functionality.
"""

import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from spec_generator.core.diff_detector import SemanticDiffDetector
from spec_generator.models import Language, SemanticChange, SpecificationConfig
from spec_generator.utils.git_utils import GitRepository


class TestSemanticDiffDetector:
    """Test SemanticDiffDetector functionality."""

    def setup_method(self):
        """Setup for each test method."""
        self.config = SpecificationConfig(
            openai_api_key="test-key",
            supported_languages=[Language.PYTHON, Language.JAVASCRIPT],
        )

        # Create a temporary directory for testing
        self.temp_dir = tempfile.mkdtemp()
        self.repo_path = Path(self.temp_dir)

        self.detector = SemanticDiffDetector(self.config, self.repo_path)

    def teardown_method(self):
        """Cleanup after each test."""
        import shutil

        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_detector_initialization(self):
        """Test SemanticDiffDetector initialization."""
        assert self.detector.config == self.config
        assert self.detector.repo_path == self.repo_path
        assert self.detector.git_repo is not None
        assert self.detector.ast_analyzer is not None

    def test_get_changed_files_mocked(self):
        """Test getting changed files with mocked Git operations."""
        mock_files = ["src/main.py", "src/utils.js", "README.md", "docs/api.py"]

        with patch.object(
            self.detector.git_repo, "get_changed_files", return_value=mock_files
        ):
            changed_files = self.detector.get_changed_files("HEAD~1", "HEAD")

            # Should filter to only supported file types
            python_files = [f for f in changed_files if f.endswith(".py")]
            js_files = [f for f in changed_files if f.endswith(".js")]

            assert len(python_files) >= 2  # main.py and api.py
            assert len(js_files) >= 1  # utils.js
            assert "README.md" not in changed_files  # Should be filtered out

    def test_filter_supported_files(self):
        """Test filtering files by supported languages."""
        files = [
            Path("src/main.py"),
            Path("src/utils.js"),
            Path("src/component.tsx"),
            Path("src/styles.css"),
            Path("README.md"),
            Path("config.json"),
            Path("app.java"),
            Path("script.cpp"),
        ]

        filtered = self.detector._filter_supported_files(files)

        # Should include files from supported languages
        filtered_names = [f.name for f in filtered]
        assert "main.py" in filtered_names
        assert "utils.js" in filtered_names

        # Should exclude unsupported file types
        assert "styles.css" not in filtered_names
        assert "README.md" not in filtered_names
        assert "config.json" not in filtered_names

    def test_analyze_file_changes_basic(self):
        """Test basic file change analysis."""
        # Create test files
        old_content = """
def calculate_sum(a, b):
    return a + b

class Calculator:
    def multiply(self, x, y):
        return x * y
"""

        new_content = """
def calculate_sum(a, b, c=0):
    # Added optional parameter
    return a + b + c

def calculate_average(numbers):
    # New function
    return sum(numbers) / len(numbers)

class Calculator:
    def multiply(self, x, y):
        return x * y

    def divide(self, x, y):
        # New method
        if y == 0:
            raise ValueError("Cannot divide by zero")
        return x / y
"""

        with patch.object(
            self.detector.git_repo, "get_file_content"
        ) as mock_get_content:
            # Mock old and new file content
            mock_get_content.side_effect = lambda commit, file_path: (
                old_content if commit == "HEAD~1" else new_content
            )

            file_path = Path("calculator.py")
            changes = self.detector._analyze_file_changes(file_path, "HEAD~1", "HEAD")

            # Should detect changes
            assert len(changes) > 0

            # Should detect function signature change
            function_changes = [c for c in changes if c.element_type == "function"]
            assert len(function_changes) >= 1

            # Should detect new function
            added_changes = [c for c in changes if c.change_type == "added"]
            assert len(added_changes) >= 1

    def test_detect_changes_integration(self):
        """Test change detection with mocked Git repository."""
        changed_files = [Path("src/main.py"), Path("src/utils.js")]

        with (
            patch.object(
                self.detector, "get_changed_files", return_value=changed_files
            ),
            patch.object(self.detector, "_analyze_file_changes") as mock_analyze,
        ):

            # Mock analysis results
            mock_analyze.return_value = [
                SemanticChange(
                    change_type="modified",
                    element_type="function",
                    element_name="main_function",
                    file_path=Path("src/main.py"),
                    impact_score=5.0,
                    description="Modified main function",
                )
            ]

            changes = self.detector.detect_changes("HEAD~1", "HEAD")

            assert len(changes) >= 1
            assert changes[0].change_type == "modified"
            assert changes[0].element_name == "main_function"

    def test_calculate_impact_score(self):
        """Test impact score calculation."""
        # Test different scenarios
        scenarios = [
            ("function", "added", "public_api_function", 7.0),
            ("function", "modified", "internal_helper", 3.0),
            ("class", "added", "NewMainClass", 8.0),
            ("class", "removed", "DeprecatedClass", 6.0),
            ("variable", "modified", "config_var", 2.0),
        ]

        for element_type, change_type, element_name, _expected_min_score in scenarios:
            score = self.detector._calculate_impact_score(
                element_type, change_type, element_name
            )

            assert score >= 1.0
            assert score <= 10.0

            # Check that public API changes get higher scores
            if "api" in element_name.lower() or "main" in element_name.lower():
                assert score >= 5.0

    def test_get_change_summary(self):
        """Test generating change summary."""
        changes = [
            SemanticChange(
                change_type="added",
                element_type="function",
                element_name="new_function",
                file_path=Path("src/main.py"),
                impact_score=4.0,
                description="Added new function",
            ),
            SemanticChange(
                change_type="modified",
                element_type="class",
                element_name="DataProcessor",
                file_path=Path("src/processor.py"),
                impact_score=7.5,
                description="Modified data processor",
            ),
            SemanticChange(
                change_type="removed",
                element_type="function",
                element_name="deprecated_func",
                file_path=Path("src/utils.py"),
                impact_score=2.0,
                description="Removed deprecated function",
            ),
        ]

        summary = self.detector.get_change_summary(changes)

        assert summary["total_changes"] == 3
        assert summary["by_type"]["added"] == 1
        assert summary["by_type"]["modified"] == 1
        assert summary["by_type"]["removed"] == 1

        assert summary["impact_distribution"]["low"] == 1
        assert summary["impact_distribution"]["medium"] == 1
        assert summary["impact_distribution"]["high"] == 1

        assert len(summary["affected_files"]) == 3

    def test_analyze_ast_differences_python(self):
        """Test AST difference analysis for Python code."""
        old_code = """
def process_data(data):
    result = []
    for item in data:
        result.append(item * 2)
    return result

class Processor:
    def __init__(self):
        self.multiplier = 2
"""

        new_code = """
def process_data(data, multiplier=2):
    # Added parameter with default
    result = []
    for item in data:
        result.append(item * multiplier)
    return result

def validate_data(data):
    # New function
    return all(isinstance(x, (int, float)) for x in data)

class Processor:
    def __init__(self, multiplier=2):
        self.multiplier = multiplier

    def get_multiplier(self):
        # New method
        return self.multiplier
"""

        with patch.object(
            self.detector.ast_analyzer, "extract_semantic_elements"
        ) as mock_extract:
            # Mock AST analysis results
            old_elements = {
                "functions": [{"name": "process_data", "parameters": ["data"]}],
                "classes": [{"name": "Processor", "methods": ["__init__"]}],
            }
            new_elements = {
                "functions": [
                    {"name": "process_data", "parameters": ["data", "multiplier"]},
                    {"name": "validate_data", "parameters": ["data"]},
                ],
                "classes": [
                    {"name": "Processor", "methods": ["__init__", "get_multiplier"]}
                ],
            }

            mock_extract.side_effect = [old_elements, new_elements]

            changes = self.detector._analyze_ast_differences(
                old_code, new_code, Path("test.py"), Language.PYTHON
            )

            # Should detect function parameter change
            param_changes = [c for c in changes if "parameter" in c.description.lower()]
            assert len(param_changes) >= 1

            # Should detect new function
            new_func_changes = [
                c
                for c in changes
                if c.change_type == "added" and c.element_type == "function"
            ]
            assert len(new_func_changes) >= 1

    def test_compare_ast_elements(self):
        """Test comparing AST elements between versions."""
        old_elements = {
            "functions": [
                {"name": "func_a", "parameters": ["x"], "return_type": "int"},
                {"name": "func_b", "parameters": ["y", "z"], "return_type": "str"},
            ],
            "classes": [{"name": "ClassA", "methods": ["method1", "method2"]}],
        }

        new_elements = {
            "functions": [
                {
                    "name": "func_a",
                    "parameters": ["x", "default_param"],
                    "return_type": "int",
                },
                {"name": "func_c", "parameters": ["a"], "return_type": "bool"},
            ],
            "classes": [
                {"name": "ClassA", "methods": ["method1", "method2", "method3"]},
                {"name": "ClassB", "methods": ["new_method"]},
            ],
        }

        changes = self.detector._compare_ast_elements(
            old_elements, new_elements, Path("test.py")
        )

        # Should detect modified function (func_a)
        modified_funcs = [
            c
            for c in changes
            if c.change_type == "modified" and c.element_name == "func_a"
        ]
        assert len(modified_funcs) == 1

        # Should detect removed function (func_b)
        removed_funcs = [
            c
            for c in changes
            if c.change_type == "removed" and c.element_name == "func_b"
        ]
        assert len(removed_funcs) == 1

        # Should detect added function (func_c)
        added_funcs = [
            c
            for c in changes
            if c.change_type == "added" and c.element_name == "func_c"
        ]
        assert len(added_funcs) == 1

        # Should detect added class (ClassB)
        added_classes = [
            c
            for c in changes
            if c.change_type == "added" and c.element_name == "ClassB"
        ]
        assert len(added_classes) == 1

    def test_is_significant_change(self):
        """Test determining if a change is significant."""
        # Test significant changes
        significant_cases = [
            ("function", "added", "public_api_method"),
            ("class", "removed", "CoreProcessor"),
            ("function", "modified", "main_entry_point"),
            ("method", "added", "critical_validation"),
        ]

        for element_type, change_type, element_name in significant_cases:
            assert self.detector._is_significant_change(
                element_type, change_type, element_name
            )

        # Test insignificant changes
        insignificant_cases = [
            ("variable", "modified", "temp_var"),
            ("comment", "added", "# Added comment"),
            ("import", "modified", "import statement"),
        ]

        for element_type, change_type, element_name in insignificant_cases:
            assert not self.detector._is_significant_change(
                element_type, change_type, element_name
            )


class TestGitRepositoryIntegration:
    """Test Git repository integration functionality."""

    def test_git_repository_mock(self):
        """Test GitRepository with mocked operations."""
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_path = Path(temp_dir)

            with patch("spec_generator.utils.git_utils.subprocess.run") as mock_run:
                # Mock successful git operations
                mock_run.return_value = MagicMock(
                    returncode=0, stdout="file1.py\nfile2.js\n", stderr=""
                )

                git_repo = GitRepository(repo_path)

                # Test getting changed files
                changed_files = git_repo.get_changed_files("HEAD~1", "HEAD")
                assert "file1.py" in changed_files
                assert "file2.js" in changed_files

    def test_git_repository_error_handling(self):
        """Test GitRepository error handling."""
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_path = Path(temp_dir)

            with patch("spec_generator.utils.git_utils.subprocess.run") as mock_run:
                # Mock failed git operation
                mock_run.return_value = MagicMock(
                    returncode=1, stdout="", stderr="fatal: not a git repository"
                )

                git_repo = GitRepository(repo_path)

                # Should handle errors gracefully
                with pytest.raises(Exception):
                    git_repo.get_changed_files("HEAD~1", "HEAD")


# Integration tests
class TestDiffDetectorIntegration:
    """Integration tests for SemanticDiffDetector."""

    def setup_method(self):
        """Setup for integration tests."""
        self.config = SpecificationConfig(
            openai_api_key="test-key",
            supported_languages=[Language.PYTHON, Language.JAVASCRIPT],
        )

    def test_end_to_end_change_detection(self):
        """Test end-to-end change detection workflow."""
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_path = Path(temp_dir)

            detector = SemanticDiffDetector(self.config, repo_path)

            # Mock the entire workflow
            with (
                patch.object(detector, "get_changed_files") as mock_get_files,
                patch.object(detector.git_repo, "get_file_content") as mock_get_content,
                patch.object(
                    detector.ast_analyzer, "extract_semantic_elements"
                ) as mock_extract,
            ):

                # Setup mocks
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

                # Run detection
                changes = detector.detect_changes(
                    "HEAD~1", "HEAD", analyze_semantic=True
                )

                # Verify results
                assert len(changes) >= 1
                added_functions = [
                    c
                    for c in changes
                    if c.change_type == "added" and c.element_type == "function"
                ]
                assert len(added_functions) >= 1
                assert any(c.element_name == "new_function" for c in added_functions)

    def test_performance_with_many_files(self):
        """Test performance with many changed files."""
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_path = Path(temp_dir)

            detector = SemanticDiffDetector(self.config, repo_path)

            # Create many mock files
            many_files = [Path(f"src/file_{i}.py") for i in range(100)]

            with (
                patch.object(detector, "get_changed_files", return_value=many_files),
                patch.object(detector, "_analyze_file_changes") as mock_analyze,
            ):

                # Mock minimal changes per file
                mock_analyze.return_value = [
                    SemanticChange(
                        change_type="modified",
                        element_type="function",
                        element_name="test_func",
                        file_path=Path("test.py"),
                        impact_score=3.0,
                        description="Minor change",
                    )
                ]

                import time

                start_time = time.time()

                changes = detector.detect_changes("HEAD~1", "HEAD")

                end_time = time.time()
                processing_time = end_time - start_time

                # Should process many files reasonably quickly (under 10 seconds in test)
                assert processing_time < 10.0
                assert len(changes) <= 100  # At most one change per file


# Fixtures
@pytest.fixture
def sample_python_code_old():
    """Sample old Python code for testing."""
    return """
import os
import sys

def calculate_total(items):
    total = 0
    for item in items:
        total += item
    return total

class DataProcessor:
    def __init__(self):
        self.processed_count = 0

    def process_item(self, item):
        self.processed_count += 1
        return item * 2
"""


@pytest.fixture
def sample_python_code_new():
    """Sample new Python code for testing."""
    return """
import os
import sys
import json

def calculate_total(items, tax_rate=0.0):
    # Added tax calculation
    total = 0
    for item in items:
        total += item

    if tax_rate > 0:
        total *= (1 + tax_rate)

    return total

def validate_items(items):
    # New validation function
    return all(isinstance(item, (int, float)) and item >= 0 for item in items)

class DataProcessor:
    def __init__(self, batch_size=100):
        self.processed_count = 0
        self.batch_size = batch_size

    def process_item(self, item):
        self.processed_count += 1
        return item * 2

    def process_batch(self, items):
        # New batch processing method
        results = []
        for item in items:
            results.append(self.process_item(item))
        return results

    def reset_counter(self):
        # New method
        self.processed_count = 0
"""


def test_diff_detector_with_sample_code(sample_python_code_old, sample_python_code_new):
    """Test diff detector with realistic code samples."""
    config = SpecificationConfig(openai_api_key="test-key")

    with tempfile.TemporaryDirectory() as temp_dir:
        repo_path = Path(temp_dir)
        detector = SemanticDiffDetector(config, repo_path)

        with patch.object(detector.git_repo, "get_file_content") as mock_get_content:
            mock_get_content.side_effect = lambda commit, file: (
                sample_python_code_old if commit == "HEAD~1" else sample_python_code_new
            )

            changes = detector._analyze_file_changes(
                Path("processor.py"), "HEAD~1", "HEAD"
            )

            # Should detect various types of changes
            assert len(changes) > 0

            # Should detect function parameter additions
            param_changes = [c for c in changes if "parameter" in c.description.lower()]
            assert len(param_changes) >= 1

            # Should detect new functions
            new_functions = [
                c
                for c in changes
                if c.change_type == "added" and c.element_type == "function"
            ]
            assert len(new_functions) >= 1

            # Should detect new methods
            new_methods = [
                c
                for c in changes
                if c.change_type == "added" and c.element_type == "method"
            ]
            assert len(new_methods) >= 1
