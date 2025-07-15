# AI Specification Generator

LangChain-based CLI tool for generating specification documents from large codebases using semantic analysis and progressive prompting.

## 🌟 Features

- **🔍 Semantic Code Analysis**: Uses Tree-sitter for AST-based parsing of multiple programming languages
- **🤖 LangChain Integration**: Progressive prompting strategy (analysis → generation) with GPT-4
- **📝 Japanese Documentation**: Generates IT industry standard specification documents in Japanese
- **💾 Large Codebase Support**: Memory-efficient streaming processing for 4GB+ repositories
- **⚡ Incremental Updates**: Git-based semantic diff detection for specification updates
- **🔧 CLI Interface**: Rich command-line interface with progress indicators and error handling
- **🌐 Multi-Provider LLM**: Support for OpenAI, Azure OpenAI, and Google Gemini with rate limiting
- **📊 Memory Management**: Real-time monitoring with configurable limits and batch processing

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

- Python 3.9+
- One of the following LLM providers:
  - OpenAI API key (for specification generation)
  - Azure OpenAI access
  - Google Gemini API key
- Git (for incremental updates)

#### Setting up Gemini API

1. **Get Gemini API Key:**

   - Visit [Google AI Studio](https://ai.google.dev/gemini-api/docs/api-key)
   - Create a new project or select an existing one
   - Generate an API key

2. **Configure Gemini:**

   ```bash
   # Set environment variable
   export GEMINI_API_KEY="your-gemini-api-key"
   export LLM_PROVIDER="gemini"
   export LLM_MODEL="gemini-2.0-flash"  # Optional: defaults to gemini-2.0-flash
   ```

3. **Supported Gemini Models:**
   - `gemini-2.0-flash` (default, fast and efficient)
   - `gemini-2.5-pro-preview-03-25` (advanced capabilities)
   - `gemini-2.5-flash-preview-04-17` (optimized for speed)

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

**Generate specification for entire repository:**

```bash
spec-generator generate /path/to/your/repo \
  --output ./specifications \
  --project-name "マイシステム" \
  --languages python javascript
```

**Generate specification for single file:**

```bash
spec-generator generate-single src/main.py \
  --output single-spec.md
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

Generate complete specification documentation from a codebase.

```bash
spec-generator generate [REPO_PATH] [OPTIONS]
```

**Options:**

- `--output, -o`: Output directory (default: `./specifications`)
- `--project-name, -p`: Project name in Japanese (default: `システム`)
- `--languages, -l`: Programming languages to process
- `--semantic-chunking`: Use semantic chunking (requires OpenAI API)
- `--max-files`: Maximum number of files to process
- `--estimate-only`: Only estimate processing time

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

### `generate-single`

Generate specification for a single file.

```bash
spec-generator generate-single [FILE_PATH] [OPTIONS]
```

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

### Environment Variables

```bash
# OpenAI Configuration
OPENAI_API_KEY=your-openai-api-key

# Azure OpenAI Configuration (alternative to OpenAI)
AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com/
AZURE_OPENAI_KEY=your-azure-key
AZURE_OPENAI_VERSION=2024-02-01

# Gemini API Configuration (alternative to OpenAI)
GEMINI_API_KEY=your-gemini-api-key

# LLM Provider Selection
LLM_PROVIDER=openai  # Options: openai, azure, gemini
LLM_MODEL=gpt-4  # Optional: override default model

# Processing Configuration
CHUNK_SIZE=4000
CHUNK_OVERLAP=200
MAX_MEMORY_MB=1024
PARALLEL_PROCESSES=4
SUPPORTED_LANGUAGES=python,javascript,typescript,java,cpp,c

# Output Configuration
OUTPUT_FORMAT=japanese_detailed_design
DOCUMENT_TITLE=システム仕様書

# Performance Settings
REQUEST_TIMEOUT=30
MAX_RETRIES=3
RETRY_DELAY=1
RATE_LIMIT_RPM=200
BATCH_SIZE=10
```

### Configuration Setup

1. **Copy the example configuration:**

   ```bash
   cp .env.example .env
   ```

2. **Edit the .env file with your API keys and preferences:**

   ```bash
   # Required: Set your LLM provider
   OPENAI_API_KEY=sk-your-actual-api-key
   LLM_PROVIDER=openai

   # Optional: Adjust processing settings
   MAX_MEMORY_MB=2048
   PARALLEL_PROCESSES=8
   ```

3. **Load the configuration:**
   ```bash
   source .env  # or use direnv for automatic loading
   ```

## 📖 Output Examples

### Generated Specification Structure

```markdown
# プロジェクト名 詳細設計書

**文書バージョン**: 1.0
**作成日**: 2025 年 07 月 15 日
**最終更新日**: 2025 年 07 月 15 日

---

## 目次

1. [概要](#概要)
2. [システム構成](#システム構成)
3. [詳細設計](#詳細設計)
4. [非機能要件](#非機能要件)
5. [運用設計](#運用設計)
6. [付録](#付録)

---

## 1. 概要

### 1.1 文書の目的

システムの詳細設計を記述する

### 1.2 システム概要

[Generated system overview in Japanese]

### 1.3 対象読者

開発チーム、運用チーム

## 2. システム構成

### 2.1 全体アーキテクチャ

[Generated architecture description]

### 2.2 主要コンポーネント

[Component descriptions]

### 2.3 技術スタック

[Technology stack details]

## 3. 詳細設計

### 3.1 モジュール設計

[Module design details]

### 3.2 データ設計

[Data structure definitions]

### 3.3 処理設計

[Processing flow descriptions]
```

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

### Project Structure

```
src/spec_generator/
├── __init__.py                 # Package initialization
├── cli.py                      # Main CLI interface
├── config.py                   # Configuration management
├── models.py                   # Pydantic data models
├── core/                       # Core processing modules
│   ├── processor.py            # Large codebase processor
│   ├── generator.py            # Specification generator
│   ├── diff_detector.py        # Semantic diff detection
│   └── updater.py              # Specification updater
├── parsers/                    # Code parsing modules
│   ├── tree_sitter_parser.py   # Tree-sitter integration
│   └── ast_analyzer.py         # AST analysis
├── templates/                  # Document templates
│   ├── japanese_spec.py        # Japanese spec templates
│   └── prompts.py              # LangChain prompts
└── utils/                      # Utility modules
    ├── file_utils.py           # File operations
    ├── git_utils.py            # Git operations
    ├── simple_memory.py        # Simple memory tracking
    └── common.py               # Common utilities
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
spec-generator generate ./src
```

### Processing Large Repositories

For repositories larger than 1GB, use these optimizations:

```bash
# Use estimation mode first
spec-generator generate /large/repo --estimate-only

# Process with limits (set via environment)
export MAX_MEMORY_MB=4096
export PARALLEL_PROCESSES=2
spec-generator generate /large/repo \
  --max-files 1000 \
  --semantic-chunking
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

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- [LangChain](https://github.com/langchain-ai/langchain) for LLM integration framework
- [Tree-sitter](https://tree-sitter.github.io/) for syntax tree parsing
- [Typer](https://typer.tiangolo.com/) for CLI framework
- [Rich](https://github.com/Textualize/rich) for beautiful terminal output
- [Pydantic](https://pydantic-docs.helpmanual.io/) for data validation

## 📞 Support

- **Documentation**: [Project Wiki](https://github.com/your-username/AI-specification-generator/wiki)
- **Issues**: [GitHub Issues](https://github.com/your-username/AI-specification-generator/issues)
- **Discussions**: [GitHub Discussions](https://github.com/your-username/AI-specification-generator/discussions)

---

**Built with ❤️ for the Japanese IT community**
