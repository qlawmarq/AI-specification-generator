name: "Timeout Configuration Fixes and Testing Requirements"
description: |
Fix timeout handling issues preventing successful specification generation for large codebases and establish comprehensive testing protocols.

---

## Goal

Fix the core timeout configuration issues that cause the `generate` command to fail with 2-minute timeouts during LLM processing, and establish comprehensive testing requirements to prevent similar issues in the future.

## Why

- **Critical User Impact**: The main `generate` command fails for projects with 269+ code chunks, making the tool unusable for real-world codebases
- **Configuration Mismatch**: Performance environment variables are documented but not loaded, causing users' timeout configurations to be ignored
- **Missing LLM Provider Coverage**: Gemini provider lacks timeout configuration entirely
- **Quality Assurance Gap**: No systematic testing requirements for CLI commands

## What

Fix timeout configuration loading, add missing LLM provider timeout support, and establish comprehensive testing protocols as specified in TEST_REQ.md.

### Success Criteria

- [ ] All documented performance environment variables are loaded and functional
- [ ] Gemini LLM provider respects timeout configurations
- [ ] Generate command successfully processes 269+ code chunks without timeout
- [ ] All CLI commands pass comprehensive testing as per TEST_REQ.md
- [ ] CLAUDE.md updated with testing requirements for future development

## All Needed Context

### Documentation & References

```yaml
- url: https://python.langchain.com/api_reference/openai/chat_models/langchain_openai.chat_models.base.ChatOpenAI.html
  why: Official LangChain ChatOpenAI timeout parameter documentation

- url: https://superfastpython.com/asyncio-timeout-best-practices/
  why: Python asyncio timeout best practices for 2025

- url: https://betterstack.com/community/guides/scaling-python/python-timeouts/
  why: Complete guide to timeouts in Python including async patterns

- file: src/spec_generator/models.py
  why: Contains PerformanceSettings class and ConfigLoader.load_from_env() method that needs fixing

- file: src/spec_generator/core/generator.py
  why: Shows existing timeout implementation patterns and Gemini provider gap

- file: tests/test_config.py
  why: Existing configuration testing patterns to follow

- file: src/spec_generator/cli.py
  why: CLI implementation patterns and async command handling

- docfile: README.md
  why: Documents performance environment variables that should be loaded but aren't
```

### Current Codebase Tree (relevant sections)

```bash
src/spec_generator/
├── models.py                   # PerformanceSettings class and ConfigLoader (NEEDS FIX)
├── config.py                   # Configuration loading and validation
├── cli.py                      # CLI commands with async patterns (NEEDS TIMEOUT)
├── core/
│   └── generator.py           # LLM provider timeout implementations (GEMINI MISSING)
└── utils/
    └── common.py              # Common utilities

tests/
├── test_config.py             # Configuration testing patterns
├── test_cli.py               # CLI testing patterns
└── test_processor.py         # Async testing patterns

PRPs/
└── templates/
    └── prp_base.md           # PRP template structure
```

### Desired Codebase Tree (no new files needed)

```bash
# All fixes are modifications to existing files
src/spec_generator/
├── models.py                   # FIXED: Load all performance env vars
├── cli.py                      # ENHANCED: Add timeout options
├── core/
│   └── generator.py           # FIXED: Gemini provider timeout support
├── CLAUDE.md                  # UPDATED: Add testing requirements
└── tests/
    ├── test_config.py         # ENHANCED: Test performance settings loading
    └── test_timeout.py        # NEW: Timeout-specific tests
```

### Known Gotchas & Library Quirks

```python
# CRITICAL: Pydantic v2 Field constraints and validation patterns
# Example: Field(default=30, ge=1, description="...") for timeout values

# CRITICAL: LangChain timeout parameter differences between providers
# ChatOpenAI: timeout=int (seconds)
# AzureChatOpenAI: timeout=int (seconds)
# ChatGoogleGenerativeAI: timeout=NOT_SUPPORTED (needs custom httpx.Client)

# CRITICAL: Environment variable type conversion patterns in ConfigLoader
# Pattern: int(os.getenv("VAR_NAME")) can raise ValueError if not numeric
# Must use: int(os.getenv("VAR_NAME", "default_value"))

# CRITICAL: Async timeout patterns in Python 3.9+
# Use: asyncio.wait_for() for backward compatibility
# Avoid: asyncio.timeout() (Python 3.11+ only)

# CRITICAL: Testing environment variable overrides
# Pattern: patch.dict(os.environ, {...}) in test context
# Always test both with and without environment variables set
```

## Implementation Blueprint

### Data Models and Structure

The PerformanceSettings class already exists with correct field definitions. The issue is in the ConfigLoader.load_from_env() method not loading these values from environment variables.

```python
# In models.py PerformanceSettings - ALREADY CORRECT
class PerformanceSettings(BaseModel):
    request_timeout: int = Field(default=30, ge=1, description="Request timeout in seconds")
    max_retries: int = Field(default=3, ge=0, description="Maximum retry attempts")
    retry_delay: int = Field(default=1, ge=0, description="Delay between retries in seconds")
    rate_limit_rpm: int = Field(default=200, ge=1, description="Rate limit requests per minute")
    batch_size: int = Field(default=10, ge=1, description="Batch size for processing")
```

### List of Tasks (Completion Order)

```yaml
Task 1: Fix Environment Variable Loading in ConfigLoader
MODIFY src/spec_generator/models.py:
  - FIND method: "def load_from_env(cls) -> SpecificationConfig"
  - LOCATE section with comment: "# Processing Configuration"
  - ADD performance settings environment variable loading after max_memory_mb
  - PATTERN: Follow existing int() conversion pattern with defaults
  - PRESERVE all existing functionality

Task 2: Add Gemini Provider Timeout Support
MODIFY src/spec_generator/core/generator.py:
  - FIND method: "_setup_gemini_llm"
  - LOCATE ChatGoogleGenerativeAI instantiation
  - ADD custom httpx.AsyncClient with timeout configuration
  - PATTERN: Follow existing Azure/OpenAI timeout patterns
  - PRESERVE existing model and API key configuration

Task 3: Add CLI Timeout Options
MODIFY src/spec_generator/cli.py:
  - FIND command: "def generate(...)"
  - ADD timeout parameter to command options
  - ADD asyncio.wait_for() wrapper around _run_generation call
  - PATTERN: Follow existing CLI option patterns
  - PRESERVE existing command functionality

Task 4: Create Comprehensive Timeout Tests
CREATE tests/test_timeout_configuration.py:
  - MIRROR testing patterns from: tests/test_config.py
  - ADD environment variable loading tests for all performance settings
  - ADD LLM provider timeout integration tests
  - ADD CLI timeout option tests
  - KEEP error handling patterns identical

Task 5: Update Testing Requirements Documentation
MODIFY CLAUDE.md:
  - FIND section: "### Testing & Reliability"
  - ADD timeout-specific testing requirements
  - ADD CLI command testing requirements from TEST_REQ.md
  - PATTERN: Follow existing documentation structure
  - PRESERVE existing content and formatting
```

### Per Task Pseudocode

#### Task 1: Environment Variable Loading Fix

```python
# CRITICAL: Add after max_memory_mb processing in load_from_env()
@staticmethod
def load_from_env() -> SpecificationConfig:
    load_dotenv()
    config_dict: dict[str, Any] = {}

    # Existing processing config...

    # PATTERN: Add performance settings loading
    performance_dict = {}
    if request_timeout := os.getenv("REQUEST_TIMEOUT"):
        performance_dict["request_timeout"] = int(request_timeout)
    if max_retries := os.getenv("MAX_RETRIES"):
        performance_dict["max_retries"] = int(max_retries)
    if retry_delay := os.getenv("RETRY_DELAY"):
        performance_dict["retry_delay"] = int(retry_delay)
    if rate_limit_rpm := os.getenv("RATE_LIMIT_RPM"):
        performance_dict["rate_limit_rpm"] = int(rate_limit_rpm)
    if batch_size := os.getenv("BATCH_SIZE"):
        performance_dict["batch_size"] = int(batch_size)

    if performance_dict:
        config_dict["performance_settings"] = PerformanceSettings(**performance_dict)

    return SpecificationConfig(**config_dict)
```

#### Task 2: Gemini Timeout Implementation

Use same pattern as Azure/OpenAI and other providers.

```python
# CRITICAL: Add httpx client with timeout to Gemini provider
def _setup_gemini_llm(self) -> ChatGoogleGenerativeAI:
    import httpx

    # PATTERN: Create async client with timeout (like existing providers)
    timeout_config = httpx.Timeout(
        timeout=self.config.performance_settings.request_timeout,
        connect=5.0,
        read=self.config.performance_settings.request_timeout - 5.0
    )

    async_client = httpx.AsyncClient(timeout=timeout_config)

    return ChatGoogleGenerativeAI(
        model=model,
        google_api_key=self.config.gemini_api_key,
        temperature=0.3,
        max_retries=self.config.performance_settings.max_retries,
        http_async_client=async_client  # CRITICAL: Add timeout support
    )
```

### Integration Points

```yaml
ENVIRONMENT_VARIABLES:
  - add to: .env.example (already present)
  - verify: README.md documentation (already documented)

TESTING:
  - add to: tests/test_timeout_configuration.py
  - pattern: "patch.dict(os.environ, {...}) for environment testing"

DOCUMENTATION:
  - update: CLAUDE.md with testing requirements
  - add: CLI timeout usage examples in README.md
```

## Validation Loop

### Level 1: Syntax & Style

```bash
# Run these FIRST - fix any errors before proceeding
ruff check src/spec_generator/models.py src/spec_generator/core/generator.py src/spec_generator/cli.py --fix
mypy src/spec_generator/models.py src/spec_generator/core/generator.py src/spec_generator/cli.py

# Expected: No errors. If errors, READ the error and fix.
```

### Level 2: Unit Tests

```python
# CREATE tests/test_timeout_configuration.py with these critical test cases:
def test_performance_settings_environment_loading():
    """Environment variables properly load into PerformanceSettings"""
    with patch.dict(os.environ, {
        "REQUEST_TIMEOUT": "45",
        "MAX_RETRIES": "5",
        "BATCH_SIZE": "15"
    }):
        config = SpecificationConfig.load_from_env()
        assert config.performance_settings.request_timeout == 45
        assert config.performance_settings.max_retries == 5
        assert config.performance_settings.batch_size == 15

def test_gemini_provider_timeout_configuration():
    """Gemini provider respects timeout settings"""
    config = SpecificationConfig(
        gemini_api_key="test-key",
        performance_settings=PerformanceSettings(request_timeout=60)
    )
    generator = SpecificationGenerator(config)
    llm = generator._setup_gemini_llm()
    # Verify httpx client has timeout set
    assert hasattr(llm, 'http_async_client')

def test_cli_timeout_option():
    """CLI timeout option is parsed and applied"""
    from spec_generator.cli import app
    runner = CliRunner()
    # Test timeout parameter is accepted
    result = runner.invoke(app, ["generate", ".", "--timeout", "10"])
    assert "--timeout" in str(app.commands["generate"].params)
```

```bash
# Run and iterate until passing:
uv run pytest tests/test_timeout_configuration.py -v
# If failing: Read error, understand root cause, fix code, re-run
```

### Level 3: Integration Test (Following TEST_REQ.md)

Also, add how to run the command for testing to CLAUDE.md.

```bash
# Test 1: Verify environment variable loading works
export REQUEST_TIMEOUT=60
export BATCH_SIZE=5
uv run python -m spec_generator.cli config-info
# Expected: Show timeout=60, batch_size=5 in configuration output

# Test 2: Test generate command with timeout option
uv run python -m spec_generator.cli generate src --output test-output --timeout 5
# Expected: Command respects 5-minute timeout

# Test 3: Test full specification generation (per TEST_REQ.md requirement)
uv run python -m spec_generator.cli generate src --output docs --project-name "AI仕様書ジェネレーター"
# Expected: Successfully generates specification without timeout errors

# Test 4: Verify generated specification content quality (per TEST_REQ.md)
cat docs/AI仕様書ジェネレーター_specification.md
# Expected: Well-formed Japanese specification document with proper structure
```

## Final Validation Checklist

- [ ] All performance environment variables load correctly: `uv run python -c "from spec_generator.config import load_config; c=load_config(); print(c.performance_settings)"`
- [ ] All CLI commands work: Test each command in `src/spec_generator/cli.py`
- [ ] No linting errors: `uv run ruff check src/`
- [ ] No type errors: `uv run mypy src/`
- [ ] All tests pass: `uv run pytest tests/ -v`
- [ ] Generate command completes without timeout: Test with project codebase
- [ ] Generated specification quality verified: Content review per TEST_REQ.md
- [ ] Documentation updated: CLAUDE.md contains testing requirements

---

## Anti-Patterns to Avoid

- ❌ Don't add new fields to PerformanceSettings - they already exist
- ❌ Don't modify default timeout values - fix the loading mechanism
- ❌ Don't create new LLM provider classes - enhance existing ones
- ❌ Don't skip integration testing - timeout issues only show under load
- ❌ Don't ignore Gemini provider - it needs timeout support too
- ❌ Don't forget to update CLAUDE.md - testing requirements are critical

## PRP Quality Score: 9/10

**Confidence Level**: Very High - All necessary context provided, existing patterns identified, specific implementation details included, and comprehensive validation strategy defined. The fixes address root causes rather than symptoms, and the testing requirements ensure long-term quality.
