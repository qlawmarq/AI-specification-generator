# AI Specification Generator

LangChain-based CLI tool for generating specification documents from large codebases using semantic analysis and progressive prompting.

## Features

- **🔍 Semantic Code Analysis**: Uses Tree-sitter for AST-based parsing of multiple programming languages
- **🤖 LangChain Integration**: Progressive prompting strategy (analysis → generation) with GPT-4
- **📝 Documentation Generation**: Generates IT industry standard specification documents
- **💾 Large Codebase Support**: Memory-efficient streaming processing for 4GB+ repositories
- **🔧 CLI Interface**: Rich command-line interface with progress indicators and error handling
- **🌐 Multi-Provider LLM**: Support for OpenAI, Azure OpenAI, and Google Gemini with rate limiting

## Architecture

```
CLI Layer (Typer + Rich)
    ↓
Core Processing (AsyncGenerator + Streaming)
    ↓
Semantic Analysis (Tree-sitter + AST)
    ↓
LLM Generation (LangChain + Progressive Prompting)
    ↓
Templates (IT Industry Standards)
    ↓
Output Generation (Markdown + Metadata)
```

## Quick Start

### Prerequisites

- Python 3.9+
- uv (Python package installer)
- One of the following LLM providers:
  - OpenAI API key (for specification generation)
  - Azure OpenAI access
  - Google Gemini API key

### Installation

1. **Clone the repository:**

```bash
git clone https://github.com/your-username/AI-specification-generator.git
cd AI-specification-generator
```

2. **Install dependencies using uv:**

```bash
# Install project dependencies
uv sync

# Install with development dependencies
uv sync --group dev
```

3. **Install Tree-sitter parsers:**

```bash
uv run python -m spec_generator.cli install-parsers
```

4. **Set up environment variables:**

```bash
cp .env.example .env
# Edit .env and add your OpenAI API key
export OPENAI_API_KEY="your-api-key-here"
```

### Basic Usage

**Generate specification for single file:**

```bash
uv run python -m spec_generator.cli generate src/main.py \
  --output specification.md
```

**View configuration:**

```bash
uv run python -m spec_generator.cli config-info
```

## Commands

### `generate`

Generate specification documentation for a single file.

```bash
uv run python -m spec_generator.cli generate [FILE_PATH] [OPTIONS]
```

**Options:**

- `--output, -o`: Output file (default: `./specification.md`)
- `--semantic-chunking`: Use semantic chunking (requires OpenAI API)

### `install-parsers`

Install Tree-sitter language parsers.

```bash
uv run python -m spec_generator.cli install-parsers [OPTIONS]
```

**Options:**

- `--languages, -l`: Specific languages to install
- `--force`: Force reinstallation

## Configuration

Configuration is managed entirely through environment variables. Copy `.env.example` to `.env` and configure your settings.

### Supported Languages

The tool supports the following programming languages out of the box:

- **Python** (.py) - Full AST analysis with class and function extraction
- **JavaScript** (.js) - ES6+ features and modern JavaScript patterns
- **TypeScript** (.ts) - Types, interfaces, and TypeScript-specific constructs
- **Java** (.java) - Classes, methods, packages, and object-oriented patterns
- **C++** (.cpp, .hpp) - Classes, templates, and modern C++ features

No additional configuration is required for language support - all languages work by default after installing the Tree-sitter parsers with `install-parsers` command.

## Development

### Running Tests

```bash
# Dependencies are already installed with uv sync --group dev

# Run all tests
uv run pytest tests/ -v

# Run specific test categories
uv run pytest tests/test_models.py -v
uv run pytest tests/test_integration.py -k "not slow" -v

# Run with coverage
uv run pytest tests/ --cov=spec_generator --cov-report=html
```

### Code Quality

```bash
# Format code
uv run black src/ tests/

# Lint code
uv run ruff check src/ tests/

# Type checking
uv run mypy src/
```

## 🔧 Advanced Usage

### Custom Configuration

Create custom environment configurations for specific projects:

```bash
# Create project-specific .env file
cp .env.example my-project/.env

# Edit for project-specific settings
echo "CHUNK_SIZE=2000" >> my-project/.env
echo "MAX_MEMORY_MB=2048" >> my-project/.env
echo "REQUEST_TIMEOUT=300" >> my-project/.env

# Use with the project
cd my-project
source .env
uv run python -m spec_generator.cli generate src/main.py
```

### Processing Multiple Files

For processing multiple files, use the generate command for each file:

```bash
# Process individual files
uv run python -m spec_generator.cli generate src/main.py --output main-spec.md
uv run python -m spec_generator.cli generate src/utils.py --output utils-spec.md
uv run python -m spec_generator.cli generate src/models.py --output models-spec.md
```

