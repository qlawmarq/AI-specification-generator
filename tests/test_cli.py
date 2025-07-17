"""
Unit tests for spec_generator.cli module.

Tests for CLI functionality including command parsing, option handling,
and integration with core modules.
"""

import json
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, Mock, patch

import pytest
from typer.testing import CliRunner

from spec_generator.cli import app, main_cli
from spec_generator.models import (
    Language,
    ProcessingStats,
    SpecificationConfig,
    SpecificationOutput,
)


class TestCLI:
    """Test CLI functionality."""

    def setup_method(self):
        """Setup for each test method."""
        self.runner = CliRunner()

    def test_cli_help(self):
        """Test CLI help output."""
        result = self.runner.invoke(app, ["--help"])

        assert result.exit_code == 0
        assert "Specification Generator" in result.output
        assert "generate" in result.output
        assert "update" in result.output
        assert "install-parsers" in result.output

    def test_version_callback(self):
        """Test version display."""
        result = self.runner.invoke(app, ["--version"])

        assert result.exit_code == 0
        assert "Specification Generator" in result.output
        assert "version" in result.output

    def test_config_info_command(self):
        """Test config-info command."""
        with patch('spec_generator.cli.load_config') as mock_load_config:
            mock_config = SpecificationConfig(
                chunk_size=1500,
                openai_api_key="test-key"
            )
            mock_load_config.return_value = mock_config

            result = self.runner.invoke(app, ["config-info"])

            assert result.exit_code == 0
            assert "Configuration Information" in result.output
            assert "1500" in result.output  # chunk_size

    def test_config_info_with_custom_config(self):
        """Test config-info command with custom config file."""
        config_data = {
            "chunk_size": 2000,
            "supported_languages": ["python", "javascript"],
            "openai_api_key": "custom-key"
        }

        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(config_data, f)
            config_file = Path(f.name)

        try:
            result = self.runner.invoke(app, ["config-info", "--config", str(config_file)])

            assert result.exit_code == 0
            assert "Configuration Information" in result.output
            assert "2000" in result.output  # chunk_size

        finally:
            config_file.unlink()

    def test_install_parsers_command(self):
        """Test install-parsers command."""
        with patch('spec_generator.cli.install_parsers_for_languages') as mock_install:
            mock_install.return_value = True

            result = self.runner.invoke(app, ["install-parsers"])

            assert result.exit_code == 0
            assert "Installing Tree-sitter Parsers" in result.output
            assert "successfully" in result.output

            # Verify install function was called with default languages
            mock_install.assert_called_once()
            call_args = mock_install.call_args[0]
            assert "python" in call_args[0]
            assert "javascript" in call_args[0]

    def test_install_parsers_specific_languages(self):
        """Test install-parsers command with specific languages."""
        with patch('spec_generator.cli.install_parsers_for_languages') as mock_install:
            mock_install.return_value = True

            result = self.runner.invoke(app, [
                "install-parsers",
                "--languages", "python",
                "--languages", "javascript"
            ])

            assert result.exit_code == 0
            mock_install.assert_called_once_with(["python", "javascript"], False)

    def test_install_parsers_force(self):
        """Test install-parsers command with force flag."""
        with patch('spec_generator.cli.install_parsers_for_languages') as mock_install:
            mock_install.return_value = True

            result = self.runner.invoke(app, ["install-parsers", "--force"])

            assert result.exit_code == 0
            # Verify force flag was passed
            call_args = mock_install.call_args
            assert call_args[0][1] is True  # force parameter

    def test_install_parsers_failure(self):
        """Test install-parsers command when installation fails."""
        with patch('spec_generator.cli.install_parsers_for_languages') as mock_install:
            mock_install.return_value = False

            result = self.runner.invoke(app, ["install-parsers"])

            assert result.exit_code == 1
            assert "failed to install" in result.output

    def test_generate_command_basic(self):
        """Test basic generate command."""
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_path = Path(temp_dir)
            (repo_path / "test.py").write_text("def hello(): pass")

            with patch('spec_generator.cli.load_config') as mock_load_config, \
                 patch('spec_generator.cli.validate_config') as mock_validate, \
                 patch('spec_generator.cli.get_repository_info') as mock_repo_info, \
                 patch('spec_generator.cli.LargeCodebaseProcessor'), \
                 patch('spec_generator.cli.SpecificationGenerator'), \
                 patch('spec_generator.cli.asyncio.run') as mock_asyncio_run:

                # Setup mocks
                mock_config = SpecificationConfig(openai_api_key="test-key")
                mock_load_config.return_value = mock_config
                mock_repo_info.return_value = {"total_files": 1, "total_size_mb": 0.001}

                # Mock user confirmation
                with patch('spec_generator.cli.typer.confirm', return_value=True):
                    result = self.runner.invoke(app, [
                        "generate",
                        str(repo_path),
                        "--output", str(repo_path / "output")
                    ])

                assert result.exit_code == 0
                mock_validate.assert_called_once_with(mock_config)
                mock_asyncio_run.assert_called_once()

    def test_generate_command_with_options(self):
        """Test generate command with various options."""
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_path = Path(temp_dir)
            (repo_path / "test.py").write_text("def hello(): pass")

            with patch('spec_generator.cli.load_config') as mock_load_config, \
                 patch('spec_generator.cli.validate_config'), \
                 patch('spec_generator.cli.get_repository_info') as mock_repo_info, \
                 patch('spec_generator.cli.asyncio.run'), \
                 patch('spec_generator.cli.typer.confirm', return_value=True):

                mock_config = SpecificationConfig(openai_api_key="test-key")
                mock_load_config.return_value = mock_config
                mock_repo_info.return_value = {"total_files": 1}

                result = self.runner.invoke(app, [
                    "generate",
                    str(repo_path),
                    "--output", str(repo_path / "output"),
                    "--project-name", "TestProject",
                    "--languages", "python",
                    "--languages", "javascript",
                    "--semantic-chunking",
                    "--max-files", "10"
                ])

                assert result.exit_code == 0

                # Verify config was updated with languages
                updated_config = mock_load_config.return_value
                assert Language.PYTHON in updated_config.supported_languages
                assert Language.JAVASCRIPT in updated_config.supported_languages

    def test_generate_command_invalid_language(self):
        """Test generate command with invalid language."""
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_path = Path(temp_dir)
            (repo_path / "test.py").write_text("def hello(): pass")

            with patch('spec_generator.cli.load_config') as mock_load_config:
                mock_config = SpecificationConfig(openai_api_key="test-key")
                mock_load_config.return_value = mock_config

                result = self.runner.invoke(app, [
                    "generate",
                    str(repo_path),
                    "--languages", "invalid_language"
                ])

                assert result.exit_code == 1
                assert "Invalid language" in result.output

    def test_generate_command_estimate_only(self):
        """Test generate command with estimate-only flag."""
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_path = Path(temp_dir)
            (repo_path / "test.py").write_text("def hello(): pass")

            with patch('spec_generator.cli.load_config') as mock_load_config, \
                 patch('spec_generator.cli.validate_config'), \
                 patch('spec_generator.cli.get_repository_info') as mock_repo_info, \
                 patch('spec_generator.cli.LargeCodebaseProcessor') as mock_processor_class:

                mock_config = SpecificationConfig(openai_api_key="test-key")
                mock_load_config.return_value = mock_config
                mock_repo_info.return_value = {"total_files": 1}

                mock_processor = Mock()
                mock_processor.estimate_processing_time.return_value = {
                    "total_files": 1,
                    "total_size_mb": 0.001,
                    "estimated_minutes": 0.1,
                    "estimated_hours": 0.002
                }
                mock_processor_class.return_value = mock_processor

                result = self.runner.invoke(app, [
                    "generate",
                    str(repo_path),
                    "--estimate-only"
                ])

                assert result.exit_code == 0
                assert "Processing Estimate" in result.output
                assert "0.1 minutes" in result.output

    def test_generate_single_command(self):
        """Test generate-single command."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write("def hello(): pass")
            test_file = Path(f.name)

        try:
            with patch('spec_generator.cli.load_config') as mock_load_config, \
                 patch('spec_generator.cli.validate_config'), \
                 patch('spec_generator.cli.asyncio.run') as mock_asyncio_run:

                mock_config = SpecificationConfig(openai_api_key="test-key")
                mock_load_config.return_value = mock_config

                result = self.runner.invoke(app, [
                    "generate-single",
                    str(test_file),
                    "--output", str(test_file.with_suffix('.md'))
                ])

                assert result.exit_code == 0
                mock_asyncio_run.assert_called_once()

        finally:
            test_file.unlink()

    def test_update_command(self):
        """Test update command."""
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_path = Path(temp_dir)

            # Create a git repository structure
            (repo_path / ".git").mkdir()
            (repo_path / "test.py").write_text("def hello(): pass")

            existing_spec = repo_path / "existing_spec.md"
            existing_spec.write_text("# Existing Specification")

            with patch('spec_generator.cli.load_config') as mock_load_config, \
                 patch('spec_generator.cli.validate_config'), \
                 patch('spec_generator.cli.is_git_repository', return_value=True), \
                 patch('spec_generator.cli.asyncio.run') as mock_asyncio_run:

                mock_config = SpecificationConfig(openai_api_key="test-key")
                mock_load_config.return_value = mock_config

                result = self.runner.invoke(app, [
                    "update",
                    str(repo_path),
                    "--existing-spec", str(existing_spec),
                    "--base-commit", "HEAD~1",
                    "--target-commit", "HEAD"
                ])

                assert result.exit_code == 0
                mock_asyncio_run.assert_called_once()

    def test_update_command_not_git_repo(self):
        """Test update command with non-git repository."""
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_path = Path(temp_dir)

            with patch('spec_generator.cli.is_git_repository', return_value=False):
                result = self.runner.invoke(app, [
                    "update",
                    str(repo_path)
                ])

                assert result.exit_code == 1
                assert "not a Git repository" in result.output

    def test_keyboard_interrupt_handling(self):
        """Test handling of keyboard interrupt (Ctrl+C)."""
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_path = Path(temp_dir)
            (repo_path / "test.py").write_text("def hello(): pass")

            with patch('spec_generator.cli.load_config') as mock_load_config, \
                 patch('spec_generator.cli.validate_config'), \
                 patch('spec_generator.cli.get_repository_info'), \
                 patch('spec_generator.cli.asyncio.run', side_effect=KeyboardInterrupt()):

                mock_config = SpecificationConfig(openai_api_key="test-key")
                mock_load_config.return_value = mock_config

                result = self.runner.invoke(app, [
                    "generate",
                    str(repo_path)
                ])

                assert result.exit_code == 1
                assert "cancelled by user" in result.output

    def test_main_cli_exception_handling(self):
        """Test main CLI exception handling."""
        with patch('spec_generator.cli.app', side_effect=Exception("Unexpected error")):
            with pytest.raises(SystemExit) as exc_info:
                main_cli()

            assert exc_info.value.code == 1


class TestCLIHelpers:
    """Test CLI helper functions."""

    def test_display_repository_info(self):
        """Test repository info display."""
        from spec_generator.cli import _display_repository_info

        repo_info = {
            "total_files": 50,
            "total_size_mb": 2.5,
            "estimated_processing_time_minutes": 5.0,
            "language_distribution": {
                "python": 30,
                "javascript": 20
            }
        }

        # This test verifies the function runs without error
        # In a real test environment, you might capture console output
        _display_repository_info(repo_info)

    def test_display_generation_results(self):
        """Test generation results display."""
        from spec_generator.cli import _display_generation_results

        stats = ProcessingStats(
            files_processed=10,
            lines_processed=1000,
            chunks_created=50,
            processing_time_seconds=30.5,
            memory_peak_mb=256.0,
            errors_encountered=["Error 1", "Error 2"]
        )

        spec_output = SpecificationOutput(
            title="Test Specification",
            content="# Test Content",
            language="ja",
            created_at="2024-01-01 12:00:00",
            source_files=[Path("test.py")],
            processing_stats=stats
        )

        output_dir = Path("/tmp")

        # This test verifies the function runs without error
        _display_generation_results(spec_output, output_dir)

    def test_display_config_info(self):
        """Test config info display."""
        from spec_generator.cli import _display_config_info

        config = SpecificationConfig(
            chunk_size=1500,
            chunk_overlap=150,
            max_memory_mb=4096,
            parallel_processes=4,
            output_format="markdown",
            openai_api_key="test-key",
            supported_languages=[Language.PYTHON, Language.JAVASCRIPT]
        )

        # This test verifies the function runs without error
        _display_config_info(config)


# Integration tests
class TestCLIIntegration:
    """Integration tests for CLI with mocked dependencies."""

    def setup_method(self):
        """Setup for each test method."""
        self.runner = CliRunner()

    @pytest.mark.asyncio
    async def test_full_generate_workflow_mocked(self):
        """Test complete generate workflow with mocked components."""
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_path = Path(temp_dir)
            output_path = repo_path / "output"

            # Create test files
            (repo_path / "main.py").write_text("def main(): pass")
            (repo_path / "utils.js").write_text("function util() {}")

            # Mock all major components
            with patch('spec_generator.cli.load_config') as mock_load_config, \
                 patch('spec_generator.cli.validate_config'), \
                 patch('spec_generator.cli.get_repository_info') as mock_repo_info, \
                 patch('spec_generator.cli.LargeCodebaseProcessor') as mock_processor_class, \
                 patch('spec_generator.cli.SpecificationGenerator') as mock_generator_class, \
                 patch('spec_generator.cli.typer.confirm', return_value=True):

                # Setup config
                mock_config = SpecificationConfig(
                    openai_api_key="test-key",
                    supported_languages=[Language.PYTHON, Language.JAVASCRIPT]
                )
                mock_load_config.return_value = mock_config

                # Setup repository info
                mock_repo_info.return_value = {
                    "total_files": 2,
                    "total_size_mb": 0.002,
                    "estimated_processing_time_minutes": 0.1,
                    "language_distribution": {"python": 1, "javascript": 1}
                }

                # Setup processor
                mock_processor = Mock()
                mock_processor_class.return_value = mock_processor

                # Setup generator with async mock
                mock_generator = Mock()
                mock_spec_output = SpecificationOutput(
                    title="Generated Specification",
                    content="# Generated Content",
                    language="ja",
                    created_at="2024-01-01 12:00:00",
                    source_files=[Path("main.py"), Path("utils.js")],
                    processing_stats=ProcessingStats(
                        files_processed=2,
                        chunks_created=5,
                        processing_time_seconds=10.0
                    )
                )
                mock_generator.generate_specification = AsyncMock(return_value=mock_spec_output)
                mock_generator_class.return_value = mock_generator

                # Mock the async processing function
                async def mock_run_generation(*args, **kwargs):
                    # Simulate the async generation process
                    pass

                with patch('spec_generator.cli._run_generation', side_effect=mock_run_generation):
                    result = self.runner.invoke(app, [
                        "generate",
                        str(repo_path),
                        "--output", str(output_path),
                        "--project-name", "TestProject"
                    ])

                assert result.exit_code == 0
                assert "TestProject" in result.output

                # Verify components were called
                mock_load_config.assert_called()
                mock_processor_class.assert_called_once_with(mock_config)
                mock_generator_class.assert_called_once_with(mock_config)


# Fixtures
@pytest.fixture
def temp_repo_with_files():
    """Create a temporary repository with sample files."""
    with tempfile.TemporaryDirectory() as temp_dir:
        repo_path = Path(temp_dir)

        # Create sample files
        (repo_path / "main.py").write_text("""
def main():
    print("Hello, World!")

if __name__ == "__main__":
    main()
""")

        (repo_path / "utils.py").write_text("""
def calculate_sum(a, b):
    return a + b

class Calculator:
    def multiply(self, x, y):
        return x * y
""")

        (repo_path / "app.js").write_text("""
function greet(name) {
    return `Hello, ${name}!`;
}

class App {
    constructor() {
        this.name = "Test App";
    }
}
""")

        yield repo_path


def test_cli_with_sample_repository(temp_repo_with_files):
    """Test CLI with a complete sample repository."""
    runner = CliRunner()

    with patch('spec_generator.cli.load_config') as mock_load_config, \
         patch('spec_generator.cli.validate_config'), \
         patch('spec_generator.cli.get_repository_info') as mock_repo_info, \
         patch('spec_generator.cli.asyncio.run'), \
         patch('spec_generator.cli.typer.confirm', return_value=True):

        mock_config = SpecificationConfig(
            openai_api_key="test-key",
            supported_languages=[Language.PYTHON, Language.JAVASCRIPT]
        )
        mock_load_config.return_value = mock_config

        mock_repo_info.return_value = {
            "total_files": 3,
            "total_size_mb": 0.005,
            "estimated_processing_time_minutes": 0.2,
            "language_distribution": {"python": 2, "javascript": 1}
        }

        result = runner.invoke(app, [
            "generate",
            str(temp_repo_with_files),
            "--output", str(temp_repo_with_files / "specs"),
            "--project-name", "SampleProject"
        ])

        assert result.exit_code == 0
        assert "SampleProject" in result.output
        assert "3 files" in result.output
