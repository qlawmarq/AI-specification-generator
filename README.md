# AI Specification Generator

LangChain-based CLI tool for generating specification documents from large codebases using semantic analysis and progressive prompting.

## 🌟 Features

- **🔍 Semantic Code Analysis**: Uses Tree-sitter for AST-based parsing of multiple programming languages
- **🤖 LangChain Integration**: Progressive prompting strategy (analysis → generation) with GPT-4
- **📝 Documentation Generation**: Generates IT industry standard specification documents
- **💾 Large Codebase Support**: Memory-efficient streaming processing for 4GB+ repositories
- **⚡ Incremental Updates**: Git-based semantic diff detection for specification updates
- **🔧 CLI Interface**: Rich command-line interface with progress indicators and error handling
- **🌐 Multi-Provider LLM**: Support for OpenAI, Azure OpenAI, and Google Gemini with rate limiting

## 🏗️ Architecture

```
CLI Layer (Typer + Rich)
    ↓
Core Processing (AsyncGenerator + Streaming)
    ↓
Semantic Analysis (Tree-sitter + AST)
    ↓
LLM Generation (LangChain + Progressive Prompting)
    ↓
Japanese Templates (IT Industry Standards)
    ↓
Output Generation (Markdown + Metadata)
```

## 🚀 Quick Start

### Prerequisites

- Python
- One of the following LLM providers:
  - OpenAI API key (for specification generation)
  - Azure OpenAI access
  - Google Gemini API key
- Git (for incremental updates)

### Installation

1. **Clone the repository:**

```bash
git clone https://github.com/your-username/AI-specification-generator.git
cd AI-specification-generator
```

2. **Install dependencies:**

```bash
pip install -e .
```

3. **Install Tree-sitter parsers:**

```bash
spec-generator install-parsers
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
spec-generator generate src/main.py \
  --output specification.md
```

**Update existing specification:**

```bash
spec-generator update /path/to/repo \
  --existing-spec specifications/current-spec.md \
  --base-commit HEAD~1 \
  --target-commit HEAD
```

**View configuration:**

```bash
spec-generator config-info
```

## 📋 Commands

### `generate`

Generate specification documentation for a single file.

```bash
spec-generator generate [FILE_PATH] [OPTIONS]
```

**Options:**

- `--output, -o`: Output file (default: `./specification.md`)
- `--semantic-chunking`: Use semantic chunking (requires OpenAI API)

### `update`

Update existing specification based on code changes.

```bash
spec-generator update [REPO_PATH] [OPTIONS]
```

**Options:**

- `--output, -o`: Output directory (default: `./spec-updates`)
- `--base-commit`: Base commit for comparison (default: `HEAD~1`)
- `--target-commit`: Target commit (default: `HEAD`)
- `--existing-spec`: Path to existing specification

### `install-parsers`

Install Tree-sitter language parsers.

```bash
spec-generator install-parsers [OPTIONS]
```

**Options:**

- `--languages, -l`: Specific languages to install
- `--force`: Force reinstallation

## ⚙️ Configuration

Configuration is managed entirely through environment variables. Copy `.env.example` to `.env` and configure your settings.

## 🧪 Development

### Running Tests

```bash
# Install development dependencies
pip install -e ".[dev]"

# Run all tests
pytest tests/ -v

# Run specific test categories
pytest tests/test_models.py -v
pytest tests/test_integration.py -k "not slow" -v

# Run with coverage
pytest tests/ --cov=spec_generator --cov-report=html
```

### Code Quality

```bash
# Format code
black src/ tests/

# Lint code
ruff check src/ tests/

# Type checking
mypy src/
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
echo "SUPPORTED_LANGUAGES=python,typescript" >> my-project/.env

# Use with the project
cd my-project
source .env
spec-generator generate src/main.py
```

### Processing Multiple Files

For processing multiple files, use the generate command for each file:

```bash
# Process individual files
spec-generator generate src/main.py --output main-spec.md
spec-generator generate src/utils.py --output utils-spec.md
spec-generator generate src/models.py --output models-spec.md
```

### Incremental Updates

Set up automated specification updates:

```bash
#!/bin/bash
# update-specs.sh
spec-generator update /path/to/repo \
  --existing-spec docs/current-spec.md \
  --output docs/updated-specs/ \
  --base-commit $(git rev-parse HEAD~1) \
  --target-commit $(git rev-parse HEAD)
```

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit changes (`git commit -m 'Add amazing feature'`)
4. Push to branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

### Development Guidelines

- Follow PEP 8 style guidelines
- Add tests for new features
- Update documentation for API changes
- Use type hints throughout
- Write meaningful commit messages

## License

MIT

## Acknowledgments

- [LangChain](https://github.com/langchain-ai/langchain) for LLM integration framework
- [Tree-sitter](https://tree-sitter.github.io/) for syntax tree parsing
- [Typer](https://typer.tiangolo.com/) for CLI framework
- [Rich](https://github.com/Textualize/rich) for beautiful terminal output
- [Pydantic](https://pydantic-docs.helpmanual.io/) for data validation
