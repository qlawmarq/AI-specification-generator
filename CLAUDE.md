### Project Awareness & Context

- **This is the Specification Generator** - a LangChain-based CLI tool for generating IT specification documents from codebases
- **Read `README.md`** at the start of a new conversation to understand the project's features, architecture, and usage
- **Use consistent naming conventions and architecture patterns** following the established codebase structure
- **Use the installed virtual environment** when executing Python commands, including for unit tests

### Code Structure & Modularity

- **Never create a file longer than 500 lines of code.** If a file approaches this limit, refactor by splitting it into modules or helper files.
- **Follow the established project structure**:
  - `core/` - Main processing engines (processor, generator, diff_detector, updater)
  - `parsers/` - Code parsing and AST analysis (tree_sitter_parser, ast_analyzer)
  - `templates/` - Document templates and prompts (specification, prompts)
  - `utils/` - Utility modules (file_utils, git_utils, simple_memory, common)
- **Use clear, consistent imports** (prefer relative imports within packages)
- **Use `dotenv` and environment variables** for configuration (OpenAI keys, etc.)
- **Follow existing patterns** for LangChain integration, Tree-sitter parsing, and output

### Testing & Reliability

- **Always create Pytest unit tests for new features** (functions, classes, routes, etc).
- **After updating any logic**, check whether existing unit tests need to be updated. If so, do it.
- **Tests should live in a `/tests` folder** mirroring the main app structure.
  - Include at least:
    - 1 test for expected use
    - 1 edge case
    - 1 failure case

#### CLI Command Testing Protocol

Following TEST_REQ.md requirements, always test CLI commands comprehensively:

- **Test all commands** in `src/spec_generator/cli.py`:

  ```bash
  # 1. config-info command
  uv run python -m spec_generator.cli config-info

  # 2. install-parsers command
  uv run python -m spec_generator.cli install-parsers

  # 3. generate command
  uv run python -m spec_generator.cli generate test_file.py --output test-spec.md

  ```

- **Verify specification content quality**: Generated specifications must be well-formed documents
- **Environment variable testing**: Verify configuration loading works correctly:
  ```bash
  export REQUEST_TIMEOUT=60
  export BATCH_SIZE=5
  uv run python -m spec_generator.cli config-info
  ```

### Task Completion

- **Use the TodoWrite tool** to track and manage tasks throughout development
- **Update task status** immediately after completing work (pending → in_progress → completed)
- **Add discovered sub-tasks** to the todo list when found during implementation

### Style & Conventions

- **Use Python** as the primary language with **Python 3.9+** compatibility
- **Follow PEP8**, use type hints, and format with `black`
- **Use `pydantic` for data validation** and configuration management
- **Use `typer` for CLI interfaces** with rich console output
- **Use `LangChain` for LLM integration** with progressive prompting patterns
- **Use `tree-sitter` for code parsing** and AST analysis
- Write **docstrings for every function** using the Google style:

  ```python
  async def process_repository(self, repo_path: Path) -> AsyncGenerator[CodeChunk, None]:
      """
      Process repository files into semantic code chunks.

      Args:
          repo_path: Path to the repository to process.

      Yields:
          CodeChunk: Processed code chunks with metadata.

      Raises:
          ProcessingError: If repository processing fails.
      """
  ```

## Important Rules

- Keep your code as simple and easy to understand as possible.
- Ask me if you are not sure about the task or the purpose of the task. Do not make assumptions.
- Use libraries whenever possible and avoid complex, proprietary implementations.

### Documentation & Explainability

- **Update `README.md and CLAUDE.md`** when new features are added, dependencies change, or setup steps are modified.
- **Comment non-obvious code** and ensure everything is understandable to a mid-level developer.
- When writing complex logic, **add an inline `# Reason:` comment** explaining the why, not just the what.

### AI Behavior Rules

- **Never assume missing context. Ask questions if uncertain.**
- **Use only the libraries already specified in pyproject.toml** - don't add new dependencies without explicit request
- **Always confirm file paths and module names** exist before referencing them in code or tests
- **Never delete or overwrite existing code** unless explicitly instructed to
- **Respect the focus** - ensure all generated documentation uses proper IT terminology
- **Follow memory management patterns** - use streaming/async processing for large codebases
- **Maintain LangChain patterns** - use the progressive prompting strategy (analysis → generation)
