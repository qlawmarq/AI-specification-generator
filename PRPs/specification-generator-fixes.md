name: "Specification Generator Critical Fixes"
description: |

## Purpose
Fix critical validation errors and operational issues in the AI仕様書ジェネレーター to restore full specification generation functionality. Address blocking Pydantic validation errors, JSON parsing issues, and environment compatibility problems.

## Core Principles
1. **Context is King**: Include ALL necessary documentation, examples, and caveats
2. **Validation Loops**: Provide executable tests/lints the AI can run and fix
3. **Information Dense**: Use keywords and patterns from the codebase
4. **Progressive Success**: Start simple, validate, then enhance
5. **Global rules**: Be sure to follow all rules in CLAUDE.md

---

## Goal
Fix critical blocking issues preventing specification generation from completing successfully, restore JSON parsing reliability, and improve environment compatibility.

## Why
- **BLOCKING ISSUE**: Specification generation fails completely due to Pydantic validation errors
- **Poor Reliability**: JSON parsing fails frequently causing degraded output quality
- **Environment Issues**: Installation script incompatible with uv environments
- **User Impact**: Core functionality is broken - specification generation returns validation errors instead of documents

## What
Fix four interconnected issues in priority order:
1. **Pydantic Validation Error**: Fix `language_distribution` type mismatch in SpecificationOutput model
2. **JSON Parsing Reliability**: Improve LLM response parsing and error handling
3. **Installation Script**: Update to work with uv instead of pip
4. **Performance Optimization**: Improve processing speed and user experience

### Success Criteria
- [ ] `generate-single` command produces valid specification documents without validation errors
- [ ] `generate` command completes for small repositories (< 50 files) successfully
- [ ] JSON parsing warnings reduced by 80% or more
- [ ] `install-parsers` command works in uv environments
- [ ] All existing unit tests pass
- [ ] Integration tests demonstrate end-to-end functionality

## All Needed Context

### Documentation & References
```yaml
# MUST READ - Include these in your context window
- url: https://docs.pydantic.dev/2.0/concepts/models/
  why: Pydantic v2 model field types and validation patterns
  critical: Union types, nested models, and field customization

- url: https://docs.pydantic.dev/2.0/concepts/json/
  why: JSON parsing and serialization with Pydantic
  critical: Custom serializers and field type handling

- file: src/spec_generator/models.py
  why: Contains SpecificationOutput model with the problematic metadata field definition (line 271-273)
  critical: Current metadata field only accepts primitive types, not nested dictionaries

- file: src/spec_generator/core/generator.py  
  why: Contains _calculate_language_distribution() method and metadata assignment (lines 470-488)
  critical: Language distribution is calculated as dict[str, int] but assigned to primitive-only metadata field

- file: scripts/install_tree_sitter.py
  why: Contains pip-based installation that fails in uv environments (line 134)
  critical: Uses subprocess with pip instead of uv commands

- file: pyproject.toml
  why: Already includes core tree-sitter dependencies
  critical: tree-sitter-python and tree-sitter-javascript are pre-installed

- doc: https://github.com/astral-sh/uv/blob/main/docs/pip.md
  section: uv add vs pip install commands
  critical: uv environments don't include pip by default

- doc: https://docs.python.org/3/library/json.html#json.JSONDecodeError
  section: JSON error handling patterns
  critical: Robust parsing with fallback strategies
```

### Current Codebase Structure
```bash
src/spec_generator/
├── models.py                   # Contains problematic SpecificationOutput model
├── core/
│   └── generator.py           # Contains language_distribution calculation and assignment
├── cli.py                     # Entry points for testing
└── utils/
    └── file_utils.py          # Additional language_distribution usage

scripts/
└── install_tree_sitter.py    # Problematic pip usage

tests/
└── test_*.py                  # Validation targets
```

### Known Gotchas of our codebase & Library Quirks
```python
# CRITICAL: Pydantic v2 validation is strict about Union types
# metadata: dict[str, Union[str, int, float]] only accepts primitives
# Nested dictionaries like {'python': 4} will fail validation

# CRITICAL: LLM responses often contain non-JSON text
# Current JSON parsing assumes clean JSON responses
# Need robust parsing with regex extraction and fallbacks

# CRITICAL: uv environments don't include pip
# subprocess.run([sys.executable, "-m", "pip", ...]) will fail
# Must use uv commands or check for pip availability

# CRITICAL: Language distribution appears in multiple places
# generator.py, file_utils.py, and cli.py all reference it
# Changes must be consistent across all usage points

# CRITICAL: Existing tests may assume current metadata structure
# Model changes might break existing test assertions
# Need to check and update test expectations

# CRITICAL: Processing performance is CPU-bound on analysis
# Current parallel processing may not be optimal
# Memory management is already implemented
```

## Implementation Blueprint

### Data Models and Structure Fixes

The current problematic model definition:
```python
# CURRENT - BROKEN (models.py:271-273)
metadata: dict[str, Union[str, int, float]] = Field(
    default_factory=dict, description="Additional metadata"
)

# PROPOSED SOLUTION - Option A: Allow nested structures  
metadata: dict[str, Union[str, int, float, dict[str, int]]] = Field(
    default_factory=dict, description="Additional metadata"
)

# PROPOSED SOLUTION - Option B: Separate field for complex data
metadata: dict[str, Union[str, int, float]] = Field(
    default_factory=dict, description="Additional metadata"
)
language_distribution: dict[str, int] = Field(
    default_factory=dict, description="Programming language distribution"
)

# PROPOSED SOLUTION - Option C: JSON string serialization
# Convert dict to JSON string for storage in metadata
metadata: dict[str, Union[str, int, float]] = Field(
    default_factory=dict, description="Additional metadata"
)
# Store as: metadata["language_distribution"] = json.dumps(lang_dist)
```

### List of tasks to be completed to fulfill the PRP in the order they should be completed

```yaml
Task 1: Fix SpecificationOutput Model Validation
MODIFY src/spec_generator/models.py:
  - FIND line 271: "metadata: dict[str, Union[str, int, float]]"
  - DECISION: Choose between Option A (expand Union), Option B (separate field), or Option C (JSON serialization)
  - IMPLEMENT chosen solution with proper field definition and validation
  - PRESERVE existing metadata functionality for other fields
  - ADD proper docstring explaining the change

Task 2: Update Language Distribution Assignment
MODIFY src/spec_generator/core/generator.py:
  - FIND lines 474-476: language_distribution assignment in metadata
  - UPDATE to match new model definition from Task 1
  - IF Option A: Keep current assignment pattern
  - IF Option B: Assign to new separate field
  - IF Option C: JSON serialize before assignment
  - PRESERVE other metadata fields (generator_version, llm_model, chunk_count)

Task 3: Fix Inconsistent Usage Patterns
MODIFY src/spec_generator/utils/file_utils.py and src/spec_generator/cli.py:
  - FIND line 511 in file_utils.py: "language_distribution": language_counts
  - FIND line 563 in cli.py: language_distribution usage
  - UPDATE both to match new model pattern from Tasks 1-2
  - ENSURE consistency across all language_distribution usage

Task 4: Improve JSON Parsing Reliability  
MODIFY src/spec_generator/core/generator.py:
  - FIND line 163-169: JSON parsing with basic exception handling
  - REPLACE with robust parsing strategy:
    * Try direct JSON parsing first
    * Extract JSON from markdown code blocks if needed
    * Use regex to find JSON objects in text
    * Provide structured fallback data
  - PRESERVE existing fallback structure (lines 168-180)
  - ADD debug logging for parsing failures

Task 5: Update Installation Script for uv Compatibility
MODIFY scripts/install_tree_sitter.py:
  - FIND line 134: pip install command construction
  - ADD detection for uv vs pip environments
  - IMPLEMENT uv-compatible installation commands
  - PRESERVE fallback to pip for non-uv environments  
  - KEEP existing error handling and logging patterns

Task 6: Add Performance Monitoring and Optimization
MODIFY src/spec_generator/core/generator.py:
  - ADD progress tracking for LLM calls
  - IMPLEMENT batch size optimization based on chunk count
  - ADD timeout handling for long-running LLM requests
  - PRESERVE existing memory management patterns
```

### Per task pseudocode as needed added to each task

```python
# Task 1 - Fix SpecificationOutput Model (Option B recommended)
class SpecificationOutput(BaseModel):
    """Output specification document."""
    title: str = Field(..., description="Document title")
    content: str = Field(..., description="Document content in markdown")
    language: str = Field(default="ja", description="Document language")
    created_at: str = Field(..., description="Creation timestamp")
    source_files: list[Path] = Field(..., description="List of source files analyzed")
    processing_stats: ProcessingStats = Field(..., description="Processing statistics")
    # CRITICAL: Keep metadata for primitive types only
    metadata: dict[str, Union[str, int, float]] = Field(
        default_factory=dict, description="Additional metadata"
    )
    # CRITICAL: Add separate field for complex language distribution
    language_distribution: dict[str, int] = Field(
        default_factory=dict, description="Programming language distribution"
    )

# Task 2 - Update generator assignment
def _create_specification_output(...) -> SpecificationOutput:
    return SpecificationOutput(
        title=title,
        content=result,
        created_at=datetime.now().isoformat(),
        source_files=[Path(f) for f in source_files],
        processing_stats=processing_stats,
        metadata={
            "generator_version": "1.0",
            "llm_model": "gpt-4", 
            "chunk_count": len(source_chunks),
            # CRITICAL: Remove language_distribution from metadata
        },
        # CRITICAL: Assign to new dedicated field
        language_distribution=self._calculate_language_distribution(source_chunks),
    )

# Task 4 - Robust JSON parsing
def _parse_analysis_response(self, analysis_result: str) -> dict[str, Any]:
    """Parse LLM analysis response with multiple fallback strategies."""
    try:
        # Strategy 1: Direct JSON parsing
        return json.loads(analysis_result)
    except json.JSONDecodeError:
        try:
            # Strategy 2: Extract from markdown code blocks
            import re
            json_match = re.search(r'```json\s*(\{.*?\})\s*```', analysis_result, re.DOTALL)
            if json_match:
                return json.loads(json_match.group(1))
        except json.JSONDecodeError:
            pass
        
        try:
            # Strategy 3: Find JSON object in text
            json_match = re.search(r'\{.*\}', analysis_result, re.DOTALL)
            if json_match:
                return json.loads(json_match.group(0))
        except json.JSONDecodeError:
            pass
        
        # Strategy 4: Structured fallback
        logger.warning(f"Failed to parse analysis JSON, using fallback structure")
        return {
            "overview": analysis_result[:500] + "..." if len(analysis_result) > 500 else analysis_result,
            "key_components": ["Unable to parse detailed analysis"],
            "recommendations": ["Review LLM response format"],
            "complexity_score": 5  # Default medium complexity
        }

# Task 5 - uv-compatible installation
def install_parser_package(self, language: str) -> tuple[bool, str]:
    """Install parser package using uv or pip."""
    package_name = LANGUAGE_PARSERS.get(language)
    if not package_name:
        return False, f"No package mapping for language: {language}"
    
    try:
        # CRITICAL: Detect uv environment
        if self._is_uv_environment():
            cmd = ["uv", "add", package_name]
        else:
            cmd = [sys.executable, "-m", "pip", "install", package_name]
        
        logger.info(f"Installing {package_name} using {cmd[0]}...")
        
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
        
        if result.returncode == 0:
            return True, f"Installed {package_name}"
        else:
            return False, f"Failed: {result.stderr}"
    except Exception as e:
        return False, f"Error: {str(e)}"

def _is_uv_environment(self) -> bool:
    """Check if running in uv environment."""
    try:
        subprocess.run(["uv", "--version"], capture_output=True, check=True)
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False
```

### Integration Points
```yaml
MODELS:
  - file: src/spec_generator/models.py
  - pattern: Pydantic BaseModel with field validation
  - note: Must maintain backward compatibility for existing metadata fields

GENERATOR:
  - file: src/spec_generator/core/generator.py  
  - integration: Creates SpecificationOutput instances with metadata
  - note: All language_distribution references must be updated consistently

CLI:
  - file: src/spec_generator/cli.py
  - integration: Displays language_distribution in repository information
  - note: Output formatting must handle new model structure

TESTS:
  - files: tests/test_models.py, tests/test_generator.py
  - integration: Validate model changes and generation pipeline
  - note: Existing assertions may need updates for new field structure
```

## Validation Loop

### Level 1: Syntax & Style  
```bash
# Run these FIRST - fix any errors before proceeding
ruff check src/spec_generator/models.py --fix
ruff check src/spec_generator/core/generator.py --fix
ruff check scripts/install_tree_sitter.py --fix
mypy src/spec_generator/models.py
mypy src/spec_generator/core/generator.py

# Expected: No errors. If errors, READ the error and fix.
```

### Level 2: Unit Tests
```bash
# Test model changes
uv run pytest tests/test_models.py -v -k "SpecificationOutput"

# Test generator functionality  
uv run pytest tests/test_generator.py -v

# Test installation script
uv run python scripts/install_tree_sitter.py --list

# Expected: All tests pass, installation listing works
# If failing: Read error, understand root cause, fix code, re-run
```

### Level 3: Integration Test
```bash
# Create test file for validation
echo 'def test(): return "hello"' > test_validation.py

# Test single file generation
uv run python -m spec_generator.cli generate-single test_validation.py --output test_spec.md

# Test installation
uv run python -m spec_generator.cli install-parsers --languages python

# Clean up
rm test_validation.py test_spec.md

# Expected: No validation errors, specification generated successfully
# If error: Check logs for validation failures or JSON parsing issues
```

## Final Validation Checklist
- [ ] All tests pass: `uv run pytest tests/ -v`
- [ ] No linting errors: `uv run ruff check src/`
- [ ] No type errors: `uv run mypy src/`
- [ ] Single file generation works: No Pydantic validation errors
- [ ] JSON parsing warnings reduced significantly
- [ ] Installation script works in uv environment
- [ ] Config info shows correct settings
- [ ] Language distribution data preserved in output
- [ ] All existing functionality maintained

---

## Anti-Patterns to Avoid
- ❌ Don't break existing metadata fields - only fix language_distribution
- ❌ Don't remove JSON parsing fallbacks - enhance them
- ❌ Don't hardcode installation commands - detect environment dynamically  
- ❌ Don't ignore performance implications - monitor processing time
- ❌ Don't skip validation - use proper Pydantic patterns
- ❌ Don't change CLI interfaces - maintain backward compatibility

## PRP Quality Score: 9/10

This PRP provides comprehensive context with:
- ✅ Exact error messages and root causes
- ✅ Multiple solution options with trade-offs
- ✅ Specific file paths and line numbers
- ✅ Working code examples and patterns
- ✅ Executable validation steps
- ✅ Integration test scenarios
- ✅ External documentation references
- ✅ Environment compatibility considerations
- ✅ Progressive implementation approach
- ✅ Clear success criteria and validation loops