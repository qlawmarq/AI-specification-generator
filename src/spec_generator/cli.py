"""
Command Line Interface for Specification Generator.

This module provides a comprehensive CLI using Typer with support for:
- generate-single: Single file processing (main command)
- update: Incremental updates based on changes
- install-parsers: Tree-sitter parser installation
"""

import asyncio
import sys
import time
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.progress import (
    BarColumn,
    Progress,
    SpinnerColumn,
    TextColumn,
    TimeElapsedColumn,
    TimeRemainingColumn,
    TaskProgressColumn,
)
from rich.table import Table

from . import __version__
from .config import load_config, setup_logging, validate_config
from .core.diff_detector import SemanticDiffDetector
from .core.generator import SpecificationGenerator
from .core.processor import LargeCodebaseProcessor
from .models import SpecificationConfig
from .utils import is_git_repository

# Create Typer app
app = typer.Typer(
    name="spec-generator",
    help="LangChain-based CLI tool for generating IT specification documents",
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
            f"[bold green]Specification Generator[/bold green] "
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
    """Specification Generator CLI"""
    pass




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
def generate(
    file_path: Path = typer.Argument(
        ...,
        help="Path to the file to analyze",
        exists=True,
        file_okay=True,
        dir_okay=False,
    ),
    output: Path = typer.Option(
        "./specification.md", "--output", "-o", help="Output file for the specification"
    ),
    use_semantic_chunking: bool = typer.Option(
        False, "--semantic-chunking", help="Use semantic chunking"
    ),
    timeout: int = typer.Option(
        600, "--timeout", "-t", help="Overall timeout in seconds (default: 600)"
    ),
):
    """
    Generate specification for a single file.

    This command analyzes a single source file and generates
    a focused specification document.
    """
    try:
        console.print("[bold blue]Specification Generation[/bold blue]")
        console.print(f"File: [green]{file_path}[/green]")
        console.print(f"Output: [green]{output}[/green]")
        console.print(f"Timeout: [yellow]{timeout}s[/yellow]")

        # Load configuration
        global current_config
        current_config = load_config()
        validate_config(current_config)

        # Run single file processing with timeout
        try:
            asyncio.run(
                asyncio.wait_for(
                    _run_single_file(file_path, output, use_semantic_chunking),
                    timeout=timeout
                )
            )
        except asyncio.TimeoutError:
            console.print(f"[red]Generation timed out after {timeout} seconds[/red]")
            console.print(
                "[yellow]Try increasing the timeout with --timeout option or check for performance issues[/yellow]"
            )
            raise typer.Exit(1)

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

            change_data = [change.model_dump(mode='json') for change in changes]
            output_path = output / f"updated_specification_{int(time.time())}.md"

            await generator.update_specification(
                existing_spec, change_data, output_path
            )

            progress.remove_task(task)

        console.print(
            f"[green]✓[/green] Updated specification saved to [green]{output_path}[/green]"
        )


async def _run_single_file(file_path: Path, output: Path, use_semantic_chunking: bool):
    """Run single file processing with enhanced progress tracking."""
    processor = LargeCodebaseProcessor(current_config)

    # Enhanced progress tracking with detailed stages
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TaskProgressColumn(),
        TimeElapsedColumn(),
        TimeRemainingColumn(),
        console=console,
    ) as progress:

        # Overall progress task
        overall_task = progress.add_task(
            description="[bold blue]Overall Progress", total=100
        )

        # Stage 1: File Processing (30% of total)
        progress.update(overall_task, description="[blue]Stage 1: Processing file...")
        file_task = progress.add_task(description="Processing file chunks...", total=100)

        chunks = await processor.process_single_file(
            file_path, use_semantic_chunking, True
        )

        progress.update(file_task, completed=100)
        progress.update(overall_task, completed=30)

        if not chunks:
            console.print("[red]No chunks generated from file[/red]")
            return

        # Stage 2: Analysis (50% of total)
        progress.update(overall_task, description="[yellow]Stage 2: Analyzing code chunks...")
        analysis_task = progress.add_task(
            description=f"Analyzing {len(chunks)} chunks...", total=len(chunks)
        )

        # Create generator and start analysis with progress callback
        generator = SpecificationGenerator(current_config)

        # Monkey patch to track analysis progress
        original_analyze_chunks = generator._analyze_chunks

        async def analyze_chunks_with_progress(chunks_to_analyze):
            """Wrapper to track analysis progress."""
            analyses = []
            optimal_batch_size = generator._calculate_optimal_batch_size(len(chunks_to_analyze))

            for i in range(0, len(chunks_to_analyze), optimal_batch_size):
                batch = chunks_to_analyze[i : i + optimal_batch_size]
                batch_results = await generator.analysis_processor.analyze_code_chunks_batch(batch)
                analyses.extend(batch_results)

                # Update progress
                completed = min(i + len(batch), len(chunks_to_analyze))
                progress.update(analysis_task, completed=completed)

            return analyses

        # Use the enhanced analysis method
        generator._analyze_chunks = analyze_chunks_with_progress

        # Stage 3: Generation (20% of total)
        progress.update(overall_task, completed=80, description="[green]Stage 3: Generating specification...")
        gen_task = progress.add_task(description="Generating specification...", total=100)

        await generator.generate_specification(chunks, file_path.stem, output)

        progress.update(gen_task, completed=100)
        progress.update(overall_task, completed=100, description="[green]✓ Complete!")

        # Brief pause to show completion
        import asyncio
        await asyncio.sleep(0.5)

    console.print(f"[green]✓[/green] Specification saved to [green]{output}[/green]")
    console.print(f"[dim]Processed {len(chunks)} code chunks successfully[/dim]")




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
    table.add_row(
        "Request Timeout (sec)", str(config.performance_settings.request_timeout)
    )
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
