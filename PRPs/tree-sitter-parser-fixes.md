name: "Tree-sitter Parser Core Functionality Fixes"
description: |

## Purpose
Fix the core tree-sitter parser functionality to enable proper code parsing and chunk generation for the Japanese Specification Generator. This addresses critical failures that prevent the system from functioning.

## Core Principles
1. **Context is King**: Include ALL necessary documentation, examples, and caveats
2. **Validation Loops**: Provide executable tests/lints the AI can run and fix
3. **Information Dense**: Use keywords and patterns from the codebase
4. **Progressive Success**: Start simple, validate, then enhance
5. **Global rules**: Be sure to follow all rules in CLAUDE.md

---

## Goal
Fix the tree-sitter parser installation, initialization, and code chunk generation to restore core functionality of the Japanese Specification Generator.

## Why
- **Critical System Failure**: The `install-parsers` command fails completely due to missing `__version__` attribute
- **Zero Code Processing**: Tree-sitter parser falls back to mock mode, preventing any code chunk generation
- **Broken Core Feature**: Specification generation is non-functional without proper code parsing
- **User Impact**: CLI commands return "No code chunks found to process" making the tool unusable

## What
Fix three interconnected issues:
1. **Parser Installation**: Replace `tree_sitter.__version__` with proper version detection
2. **Parser Initialization**: Implement actual tree-sitter language loading instead of mock placeholders
3. **Code Chunk Generation**: Ensure parsed code creates proper CodeChunk objects

### Success Criteria
- [ ] `install-parsers` command executes successfully and installs language parsers
- [ ] Tree-sitter parser loads actual language parsers without falling back to mock mode
- [ ] `generate` and `generate-single` commands produce code chunks from parsed files
- [ ] All existing CLI functionality works without errors
- [ ] Unit tests pass for parser functionality

## All Needed Context

### Documentation & References (list all context needed to implement the feature)
```yaml
# MUST READ - Include these in your context window
- url: https://tree-sitter.github.io/py-tree-sitter/
  why: Official Python bindings documentation for tree-sitter
  
- url: https://pypi.org/project/tree-sitter/
  why: Package information shows current version is 0.24.0, confirms __version__ doesn't exist
  
- file: src/spec_generator/parsers/tree_sitter_parser.py
  why: Contains mock implementation that needs to be replaced with actual parser
  
- file: scripts/install_tree_sitter.py
  why: Has the failing __version__ reference on line 78 that needs to be fixed
  
- file: src/spec_generator/models.py
  why: Contains Language enum and CodeChunk model definitions
  
- file: tests/test_tree_sitter_parser.py
  why: Shows expected behavior and test patterns for parser functionality
  
- file: src/spec_generator/core/processor.py
  why: Shows how parser integrates with chunk generation and AST analysis
  
- doc: https://tree-sitter.github.io/tree-sitter/creating-parsers
  section: Language binding patterns and initialization
  critical: tree-sitter languages must be imported individually (tree_sitter_python.language)

- doc: https://github.com/tree-sitter/py-tree-sitter#example-usage
  section: Basic usage patterns
  critical: Shows proper Language.from_library() usage and parser.set_language()
```

### Current Codebase tree (run `tree` in the root of the project) to get an overview of the codebase
```bash
src/
├── spec_generator/
│   ├── __init__.py
│   ├── cli.py
│   ├── config.py
│   ├── core/
│   │   ├── __init__.py
│   │   ├── diff_detector.py
│   │   ├── generator.py
│   │   ├── processor.py
│   │   └── updater.py
│   ├── models.py
│   ├── parsers/
│   │   ├── __init__.py
│   │   ├── ast_analyzer.py
│   │   └── tree_sitter_parser.py
│   ├── templates/
│   │   ├── __init__.py
│   │   ├── japanese_spec.py
│   │   └── prompts.py
│   └── utils/
│       ├── __init__.py
│       ├── common.py
│       ├── file_utils.py
│       ├── git_utils.py
│       └── simple_memory.py
scripts/
├── __init__.py
├── install_tree_sitter.py
└── run_tests.py
tests/
├── test_tree_sitter_parser.py
└── ... (other test files)
```

### Desired Codebase tree with files to be added and responsibility of file
```bash
# NO NEW FILES NEEDED - only modifications to existing files
# Key files to modify:
# - scripts/install_tree_sitter.py: Fix version detection
# - src/spec_generator/parsers/tree_sitter_parser.py: Replace mock with real implementation
# - tests/test_tree_sitter_parser.py: Update tests to match new implementation
```

### Known Gotchas of our codebase & Library Quirks
```python
# CRITICAL: tree-sitter module does NOT have __version__ attribute
# Must use importlib.metadata.version('tree-sitter') instead

# CRITICAL: tree-sitter language parsers are separate packages
# tree_sitter_python, tree_sitter_javascript, etc. must be imported individually
# from tree_sitter_python import language as python_language

# CRITICAL: Language.from_library() is the proper way to load parsers
# NOT the mock _get_language() method currently in tree_sitter_parser.py

# CRITICAL: Parser queries use specific tree-sitter query syntax
# Different from the mock implementation in current parser

# CRITICAL: SemanticElement signature differs from tests
# Tests expect SemanticElement without node parameter, but current implementation requires it

# CRITICAL: Parser.set_language() must be called before parsing
# Current mock implementation skips this step

# CRITICAL: Code chunk generation depends on proper AST element extraction
# Mock parser returns empty lists, breaking the entire pipeline
```

## Implementation Blueprint

### Data models and structure

The core data models are already properly defined in `src/spec_generator/models.py`:
```python
# CodeChunk model is correct - no changes needed
# Language enum is correct - no changes needed
# SemanticElement in tree_sitter_parser.py needs to match test expectations
```

### list of tasks to be completed to fullfill the PRP in the order they should be completed

```yaml
Task 1:
MODIFY scripts/install_tree_sitter.py:
  - FIND line 78: "logger.info(f"Tree-sitter version {tree_sitter.__version__} found")"
  - REPLACE with proper version detection using importlib.metadata
  - PRESERVE all existing functionality and error handling
  - KEEP the same logging pattern

Task 2:
MODIFY src/spec_generator/parsers/tree_sitter_parser.py:
  - FIND _get_language() method that returns None (mock implementation)
  - REPLACE with actual tree-sitter language loading using Language.from_library()
  - PRESERVE existing SemanticElement class and method signatures
  - KEEP the same error handling patterns

Task 3:
MODIFY src/spec_generator/parsers/tree_sitter_parser.py:
  - FIND mock parser initialization in LanguageParser.__init__()
  - REPLACE with actual tree-sitter Parser() and set_language() calls
  - PRESERVE existing exception handling and logging patterns
  - KEEP the same class structure and inheritance

Task 4:
MODIFY src/spec_generator/parsers/tree_sitter_parser.py:
  - FIND mock query methods in PythonParser and JavaScriptParser
  - REPLACE with actual tree-sitter query execution
  - PRESERVE existing extraction patterns and return types
  - KEEP the same SemanticElement creation patterns

Task 5:
UPDATE tests/test_tree_sitter_parser.py:
  - FIND tests that expect mock behavior
  - MODIFY to work with actual tree-sitter functionality
  - PRESERVE existing test patterns and assertions
  - KEEP the same test structure and coverage
```

### Per task pseudocode as needed added to each task

```python
# Task 1 - Fix version detection
def check_tree_sitter_available(self) -> bool:
    """Check if tree-sitter is available in the environment."""
    try:
        import tree_sitter
        # CRITICAL: Use importlib.metadata instead of __version__
        import importlib.metadata
        version = importlib.metadata.version('tree-sitter')
        logger.info(f"Tree-sitter version {version} found")
        return True
    except ImportError:
        logger.error("tree-sitter package not found. Please install it first:")
        return False
    except Exception as e:
        logger.error(f"Error checking tree-sitter version: {e}")
        return False

# Task 2 - Fix language loading
def _get_language(self, language: Language):
    """Get Tree-sitter language object."""
    # CRITICAL: Import actual language parsers
    language_map = {
        Language.PYTHON: "tree_sitter_python",
        Language.JAVASCRIPT: "tree_sitter_javascript",
        Language.TYPESCRIPT: "tree_sitter_typescript",
        # ... other languages
    }
    
    try:
        module_name = language_map[language]
        # PATTERN: Dynamic import with error handling
        module = importlib.import_module(module_name)
        # CRITICAL: Use Language.from_library() method
        return tree_sitter.Language.from_library(module.language())
    except ImportError as e:
        logger.error(f"Language parser not installed: {module_name}")
        raise
    except Exception as e:
        logger.error(f"Failed to load language {language.value}: {e}")
        raise

# Task 3 - Fix parser initialization
def __init__(self, language: Language):
    self.language = language
    try:
        # CRITICAL: Create actual parser instance
        self.parser = tree_sitter.Parser()
        self.ts_language = self._get_language(language)
        # CRITICAL: Set language before parsing
        self.parser.set_language(self.ts_language)
        logger.info(f"Initialized TreeSitter parser for {language.value}")
    except Exception as e:
        logger.error(f"Failed to initialize parser for {language.value}: {e}")
        raise

# Task 4 - Fix query execution
def extract_functions(self, root_node: tree_sitter.Node) -> list[SemanticElement]:
    """Extract function definitions from the AST."""
    try:
        # CRITICAL: Use actual tree-sitter query syntax
        query = self.ts_language.query("""
            (function_definition
                name: (identifier) @function.name
                body: (block) @function.body) @function.def
        """)
        
        # PATTERN: Execute query and process captures
        captures = query.captures(root_node)
        functions = []
        
        for node, capture_name in captures:
            if capture_name == "function.def":
                # PATTERN: Extract semantic information
                element = self._create_semantic_element(node, "function")
                functions.append(element)
        
        return functions
    except Exception as e:
        logger.error(f"Failed to extract functions: {e}")
        return []
```

### Integration Points
```yaml
CONFIG:
  - file: pyproject.toml
  - dependencies: Already includes tree-sitter>=0.20.0
  - note: No changes needed to dependencies
  
MODELS:
  - file: src/spec_generator/models.py
  - pattern: Language enum and CodeChunk model remain unchanged
  - note: SemanticElement class in tree_sitter_parser.py needs consistency
  
PROCESSOR:
  - file: src/spec_generator/core/processor.py
  - integration: Uses ASTAnalyzer which depends on TreeSitterParser
  - note: No changes needed - existing integration will work once parser is fixed
  
CLI:
  - file: src/spec_generator/cli.py
  - commands: install-parsers, generate, generate-single
  - note: No changes needed - existing CLI will work once parser is fixed
```

## Validation Loop

### Level 1: Syntax & Style
```bash
# Run these FIRST - fix any errors before proceeding
ruff check src/spec_generator/parsers/tree_sitter_parser.py --fix
ruff check scripts/install_tree_sitter.py --fix
mypy src/spec_generator/parsers/tree_sitter_parser.py
mypy scripts/install_tree_sitter.py

# Expected: No errors. If errors, READ the error and fix.
```

### Level 2: Unit Tests each new feature/file/function use existing test patterns
```bash
# Test the parser functionality
uv run pytest tests/test_tree_sitter_parser.py -v

# Test the installation script
uv run python scripts/install_tree_sitter.py --default

# Expected: All tests pass, installation succeeds
# If failing: Read error, understand root cause, fix code, re-run
```

### Level 3: Integration Test
```bash
# Install parsers first
uv run python -m spec_generator.cli install-parsers --default

# Test code generation
uv run python -m spec_generator.cli generate tests/fixtures/sample_code/sample.py

# Expected: Code chunks generated, no "No code chunks found" error
# If error: Check logs for parser initialization failures
```

## Final validation Checklist
- [ ] All tests pass: `uv run pytest tests/test_tree_sitter_parser.py -v`
- [ ] No linting errors: `uv run ruff check src/spec_generator/parsers/`
- [ ] No type errors: `uv run mypy src/spec_generator/parsers/`
- [ ] Parser installation works: `uv run python -m spec_generator.cli install-parsers --default`
- [ ] Code generation works: `uv run python -m spec_generator.cli generate-single tests/fixtures/sample_code/sample.py`
- [ ] Config info shows parser status: `uv run python -m spec_generator.cli config-info`
- [ ] No mock warnings in logs
- [ ] CodeChunk objects are created from parsed code

---

## Anti-Patterns to Avoid
- ❌ Don't keep mock implementations - replace with actual tree-sitter calls
- ❌ Don't skip version detection - use importlib.metadata properly
- ❌ Don't ignore ImportError - handle language parser installation gracefully
- ❌ Don't hardcode language mappings - use the existing patterns
- ❌ Don't break existing interfaces - maintain SemanticElement compatibility
- ❌ Don't remove error handling - enhance existing patterns

## PRP Quality Score: 9/10

This PRP provides comprehensive context with:
- ✅ Exact file paths and line numbers for changes
- ✅ Specific error messages and root causes
- ✅ Working code examples and patterns
- ✅ Executable validation steps
- ✅ Integration test scenarios
- ✅ All necessary documentation URLs
- ✅ Detailed gotchas and library quirks
- ✅ Progressive implementation approach
- ✅ Maintains existing codebase patterns
- ✅ Clear success criteria