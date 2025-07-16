"""
Command Line Interface for Japanese Specification Generator.

This module provides a comprehensive CLI using Typer with support for:
- generate: Full specification generation
- update: Incremental updates based on changes
- generate-single: Single file processing
- install-parsers: Tree-sitter parser installation
"""

import asyncio
import sys
import time
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.panel import Panel
from rich.progress import (
    BarColumn,
    Progress,
    SpinnerColumn,
    TaskProgressColumn,
    TextColumn,
)
from rich.table import Table

from . import __version__
from .config import load_config, setup_logging, validate_config
from .core.diff_detector import SemanticDiffDetector
from .core.generator import SpecificationGenerator
from .core.processor import LargeCodebaseProcessor
from .models import Language, SpecificationConfig
from .utils import get_repository_info, is_git_repository

# Create Typer app
app = typer.Typer(
    name="spec-generator",
    help="LangChain-based CLI tool for generating Japanese IT specification documents",
    add_completion=False,
    rich_markup_mode="rich",
)

# Rich console for output
console = Console()

# Global state
current_config: Optional[SpecificationConfig] = None


def version_callback(value: bool):
    """Show version information."""
    if value:
        console.print(
            f"[bold green]Japanese Specification Generator[/bold green] "
            f"version [bold]{__version__}[/bold]"
        )
        raise typer.Exit()


def verbose_callback(value: bool):
    """Set verbose logging."""
    if value:
        setup_logging("DEBUG")
    else:
        setup_logging("INFO")


@app.callback()
def main(
    version: Optional[bool] = typer.Option(
        None,
        "--version",
        "-v",
        callback=version_callback,
        is_eager=True,
        help="Show version and exit",
    ),
    verbose: bool = typer.Option(
        False,
        "--verbose",
        callback=verbose_callback,
        is_eager=True,
        help="Enable verbose logging",
    ),
):
    """Japanese Specification Generator CLI"""
    pass


@app.command()
def generate(
    repo_path: Path = typer.Argument(
        ...,
        help="Path to the repository to analyze",
        exists=True,
        file_okay=False,
        dir_okay=True,
    ),
    output: Path = typer.Option(
        "./specifications",
        "--output",
        "-o",
        help="Output directory for generated specifications",
    ),
    project_name: str = typer.Option(
        "システム", "--project-name", "-p", help="Name of the project"
    ),
    languages: Optional[list[str]] = typer.Option(
        None,
        "--languages",
        "-l",
        help="Programming languages to process (python, javascript, typescript, java, cpp, c)",
    ),
    use_semantic_chunking: bool = typer.Option(
        False,
        "--semantic-chunking",
        help="Use semantic chunking (requires OpenAI API key)",
    ),
    use_ast_chunking: bool = typer.Option(
        True, "--ast-chunking/--no-ast-chunking", help="Use AST-based chunking"
    ),
    max_files: Optional[int] = typer.Option(
        None, "--max-files", help="Maximum number of files to process"
    ),
    estimate_only: bool = typer.Option(
        False, "--estimate-only", help="Only estimate processing time and exit"
    ),
    timeout_minutes: Optional[int] = typer.Option(
        None, "--timeout", help="Overall timeout in minutes"
    ),
):
    """
    Generate complete specification documentation from a codebase.

    This command analyzes the entire repository and generates comprehensive
    Japanese specification documents using LangChain and Tree-sitter.
    """
    try:
        console.print(
            f"[bold blue]Japanese Specification Generator[/bold blue] v{__version__}"
        )
        console.print(f"Repository: [green]{repo_path}[/green]")
        console.print(f"Output: [green]{output}[/green]")

        # Load configuration
        global current_config
        current_config = load_config()

        # Override languages if provided
        if languages:
            try:
                current_config.supported_languages = [
                    Language(lang) for lang in languages
                ]
            except ValueError as e:
                console.print(f"[red]Invalid language: {e}[/red]")
                raise typer.Exit(1)

        # Validate configuration
        validate_config(current_config)

        # Show repository information
        repo_info = get_repository_info(repo_path)
        _display_repository_info(repo_info)

        # Create processor
        processor = LargeCodebaseProcessor(current_config)

        # Estimate processing time
        if estimate_only:
            estimate = processor.estimate_processing_time(repo_path)
            _display_estimate(estimate)
            return

        # Confirm processing
        if not typer.confirm(
            f"Process {repo_info.get('total_files', 'unknown')} files?"
        ):
            console.print("[yellow]Operation cancelled[/yellow]")
            raise typer.Exit()

        # Run generation
        timeout_seconds = timeout_minutes * 60 if timeout_minutes else None

        if timeout_seconds:
            asyncio.run(
                asyncio.wait_for(
                    _run_generation(
                        processor,
                        repo_path,
                        output,
                        project_name,
                        use_semantic_chunking,
                        use_ast_chunking,
                        max_files,
                    ),
                    timeout=timeout_seconds
                )
            )
        else:
            asyncio.run(
                _run_generation(
                    processor,
                    repo_path,
                    output,
                    project_name,
                    use_semantic_chunking,
                    use_ast_chunking,
                    max_files,
                )
            )

    except KeyboardInterrupt:
        console.print("\n[red]Operation cancelled by user[/red]")
        raise typer.Exit(1)
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        raise typer.Exit(1)


@app.command()
def update(
    repo_path: Path = typer.Argument(
        ...,
        help="Path to the Git repository",
        exists=True,
        file_okay=False,
        dir_okay=True,
    ),
    output: Path = typer.Option(
        "./spec-updates",
        "--output",
        "-o",
        help="Output directory for updated specifications",
    ),
    base_commit: str = typer.Option(
        "HEAD~1", "--base-commit", help="Base commit for comparison"
    ),
    target_commit: str = typer.Option(
        "HEAD", "--target-commit", help="Target commit for comparison"
    ),
    existing_spec: Optional[Path] = typer.Option(
        None,
        "--existing-spec",
        help="Path to existing specification to update",
        exists=True,
    ),
):
    """
    Update existing specification based on code changes.

    This command detects semantic changes between commits and updates
    the specification incrementally.
    """
    try:
        console.print("[bold blue]Updating Specification[/bold blue]")
        console.print(f"Repository: [green]{repo_path}[/green]")
        console.print(
            f"Comparing: [yellow]{base_commit}[/yellow] → [yellow]{target_commit}[/yellow]"
        )

        # Validate Git repository
        if not is_git_repository(repo_path):
            console.print(f"[red]Error: {repo_path} is not a Git repository[/red]")
            raise typer.Exit(1)

        # Load configuration
        global current_config
        current_config = load_config()
        validate_config(current_config)

        # Run update
        asyncio.run(
            _run_update(repo_path, output, base_commit, target_commit, existing_spec)
        )

    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        raise typer.Exit(1)


@app.command()
def generate_single(
    file_path: Path = typer.Argument(
        ...,
        help="Path to the file to analyze",
        exists=True,
        file_okay=True,
        dir_okay=False,
    ),
    output: Path = typer.Option(
        "./single-spec.md", "--output", "-o", help="Output file for the specification"
    ),
    use_semantic_chunking: bool = typer.Option(
        False, "--semantic-chunking", help="Use semantic chunking"
    ),
):
    """
    Generate specification for a single file.

    This command analyzes a single source file and generates
    a focused specification document.
    """
    try:
        console.print("[bold blue]Single File Analysis[/bold blue]")
        console.print(f"File: [green]{file_path}[/green]")
        console.print(f"Output: [green]{output}[/green]")

        # Load configuration
        global current_config
        current_config = load_config()
        validate_config(current_config)

        # Run single file processing
        asyncio.run(_run_single_file(file_path, output, use_semantic_chunking))

    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        raise typer.Exit(1)


@app.command()
def install_parsers(
    languages: Optional[list[str]] = typer.Option(
        None,
        "--languages",
        "-l",
        help="Specific languages to install (default: all supported)",
    ),
    force: bool = typer.Option(
        False, "--force", help="Force reinstallation of existing parsers"
    ),
):
    """
    Install Tree-sitter language parsers.

    This command installs the necessary Tree-sitter parsers for
    supported programming languages.
    """
    try:
        console.print("[bold blue]Installing Tree-sitter Parsers[/bold blue]")

        # Determine languages to install
        if languages:
            install_languages = languages
        else:
            install_languages = [
                "python",
                "javascript",
                "typescript",
                "java",
                "cpp",
                "c",
            ]

        console.print(
            f"Installing parsers for: [green]{', '.join(install_languages)}[/green]"
        )

        # Import and run installation script
        from scripts.install_tree_sitter import install_parsers_for_languages

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            transient=True,
        ) as progress:
            task = progress.add_task("Installing parsers...", total=None)
            success = install_parsers_for_languages(install_languages, force)
            progress.remove_task(task)

        if success:
            console.print("[green]✓[/green] Tree-sitter parsers installed successfully")
        else:
            console.print("[red]✗[/red] Some parsers failed to install")
            raise typer.Exit(1)

    except ImportError:
        console.print("[red]Error: Parser installation script not found[/red]")
        raise typer.Exit(1)
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        raise typer.Exit(1)


@app.command()
def config_info():
    """
    Display current configuration information.
    """
    try:
        console.print("[bold blue]Configuration Information[/bold blue]")

        # Load configuration
        current_config = load_config()

        # Display configuration
        _display_config_info(current_config)

    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        raise typer.Exit(1)


async def _run_generation(
    processor: LargeCodebaseProcessor,
    repo_path: Path,
    output: Path,
    project_name: str,
    use_semantic_chunking: bool,
    use_ast_chunking: bool,
    max_files: Optional[int],
):
    """Run the main generation process."""
    # Ensure output directory exists
    output.mkdir(parents=True, exist_ok=True)

    # Collect chunks
    chunks = []

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TaskProgressColumn(),
        console=console,
    ) as progress:

        # Process repository
        task = progress.add_task("Processing repository...", total=None)

        file_count = 0
        async for chunk in processor.process_repository(
            repo_path, use_semantic_chunking, use_ast_chunking
        ):
            chunks.append(chunk)
            file_count += 1

            progress.update(task, description=f"Processed {file_count} files...")

            # Check max files limit
            if max_files and file_count >= max_files:
                break

        progress.remove_task(task)

    if not chunks:
        console.print("[red]No code chunks found to process[/red]")
        return

    console.print(f"[green]Collected {len(chunks)} code chunks[/green]")

    # Generate specification
    generator = SpecificationGenerator(current_config)

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        task = progress.add_task("Generating specification...", total=None)

        spec_output = await generator.generate_specification(
            chunks, project_name, output / f"{project_name}_specification.md"
        )

        progress.remove_task(task)

    # Display results
    _display_generation_results(spec_output, output)


async def _run_update(
    repo_path: Path,
    output: Path,
    base_commit: str,
    target_commit: str,
    existing_spec: Optional[Path],
):
    """Run the update process."""
    # Create diff detector
    diff_detector = SemanticDiffDetector(current_config, repo_path)

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        task = progress.add_task("Detecting changes...", total=None)

        changes = diff_detector.detect_changes(base_commit, target_commit, True)

        progress.remove_task(task)

    if not changes:
        console.print("[yellow]No semantic changes detected[/yellow]")
        return

    # Display change summary
    summary = diff_detector.get_change_summary(changes)
    _display_change_summary(summary)

    # Generate update if existing spec provided
    if existing_spec:
        generator = SpecificationGenerator(current_config)

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            task = progress.add_task("Updating specification...", total=None)

            change_data = [change.dict() for change in changes]
            output_path = output / f"updated_specification_{int(time.time())}.md"

            await generator.update_specification(
                existing_spec, change_data, output_path
            )

            progress.remove_task(task)

        console.print(
            f"[green]✓[/green] Updated specification saved to [green]{output_path}[/green]"
        )


async def _run_single_file(file_path: Path, output: Path, use_semantic_chunking: bool):
    """Run single file processing."""
    processor = LargeCodebaseProcessor(current_config)

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        task = progress.add_task("Processing file...", total=None)

        chunks = await processor.process_single_file(
            file_path, use_semantic_chunking, True
        )

        progress.remove_task(task)

    if not chunks:
        console.print("[red]No chunks generated from file[/red]")
        return

    # Generate specification
    generator = SpecificationGenerator(current_config)

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        task = progress.add_task("Generating specification...", total=None)

        await generator.generate_specification(
            chunks, file_path.stem, output
        )

        progress.remove_task(task)

    console.print(f"[green]✓[/green] Specification saved to [green]{output}[/green]")


def _display_repository_info(repo_info: dict):
    """Display repository information."""
    table = Table(title="Repository Information")
    table.add_column("Property", style="bold")
    table.add_column("Value")

    table.add_row("Total Files", str(repo_info.get("total_files", "unknown")))
    table.add_row("Total Size", f"{repo_info.get('total_size_mb', 0):.1f} MB")
    table.add_row(
        "Estimated Time",
        f"{repo_info.get('estimated_processing_time_minutes', 0):.1f} minutes",
    )

    # Language distribution
    if lang_dist := repo_info.get("language_distribution"):
        for lang, count in lang_dist.items():
            table.add_row(f"  {lang} files", str(count))

    console.print(table)


def _display_estimate(estimate: dict):
    """Display processing time estimate."""
    panel = Panel.fit(
        f"""[bold]Processing Estimate[/bold]

Total Files: {estimate.get('total_files', 'unknown')}
Total Size: {estimate.get('total_size_mb', 0):.1f} MB
Estimated Time: {estimate.get('estimated_minutes', 0):.1f} minutes ({estimate.get('estimated_hours', 0):.1f} hours)
""",
        title="Estimation Results",
        border_style="blue",
    )
    console.print(panel)


def _display_generation_results(spec_output, output_dir: Path):
    """Display generation results."""
    stats = spec_output.processing_stats

    table = Table(title="Generation Results")
    table.add_column("Metric", style="bold")
    table.add_column("Value")

    table.add_row("Files Processed", str(stats.files_processed))
    table.add_row("Lines Processed", str(stats.lines_processed))
    table.add_row("Chunks Created", str(stats.chunks_created))
    table.add_row("Processing Time", f"{stats.processing_time_seconds:.2f} seconds")
    table.add_row("Peak Memory", f"{stats.memory_peak_mb:.1f} MB")
    table.add_row("Errors", str(len(stats.errors_encountered)))

    console.print(table)

    if stats.errors_encountered:
        console.print("\n[yellow]Errors encountered:[/yellow]")
        for error in stats.errors_encountered[:5]:  # Show first 5 errors
            console.print(f"  • {error}")
        if len(stats.errors_encountered) > 5:
            console.print(f"  ... and {len(stats.errors_encountered) - 5} more")


def _display_change_summary(summary: dict):
    """Display change summary."""
    table = Table(title="Change Summary")
    table.add_column("Change Type", style="bold")
    table.add_column("Count")

    for change_type, count in summary.get("by_type", {}).items():
        table.add_row(change_type, str(count))

    console.print(table)

    impact_dist = summary.get("impact_distribution", {})
    console.print("\nImpact Distribution:")
    console.print(f"  Low: {impact_dist.get('low', 0)}")
    console.print(f"  Medium: {impact_dist.get('medium', 0)}")
    console.print(f"  High: {impact_dist.get('high', 0)}")


def _display_config_info(config: SpecificationConfig):
    """Display configuration information."""
    table = Table(title="Configuration")
    table.add_column("Setting", style="bold")
    table.add_column("Value")

    table.add_row("Chunk Size", str(config.chunk_size))
    table.add_row("Chunk Overlap", str(config.chunk_overlap))
    table.add_row("Max Memory (MB)", str(config.max_memory_mb))
    table.add_row("Parallel Processes", str(config.parallel_processes))
    table.add_row("Request Timeout (sec)", str(config.performance_settings.request_timeout))
    table.add_row("Output Format", config.output_format)
    table.add_row("OpenAI API Key", "Set" if config.openai_api_key else "Not set")
    table.add_row(
        "Azure Endpoint", "Set" if config.azure_openai_endpoint else "Not set"
    )

    # Supported languages
    languages = ", ".join([lang.value for lang in config.supported_languages])
    table.add_row("Languages", languages)

    console.print(table)


def main_cli():
    """Main CLI entry point."""
    try:
        app()
    except KeyboardInterrupt:
        console.print("\n[red]Operation cancelled by user[/red]")
        sys.exit(1)
    except Exception as e:
        console.print(f"[red]Unexpected error: {e}[/red]")
        sys.exit(1)


if __name__ == "__main__":
    main_cli()
