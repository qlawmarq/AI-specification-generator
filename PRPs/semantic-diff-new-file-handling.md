name: "SemanticDiffDetector: Fix New File Handling in Update Command"
description: |

## Purpose
Fix the critical issue where the `update` command fails to detect semantic changes in newly added files due to git operations failing when trying to access files that don't exist in the previous commit.

## Core Principles
1. **Context is King**: Include ALL necessary documentation, examples, and caveats
2. **Validation Loops**: Provide executable tests/lints the AI can run and fix
3. **Information Dense**: Use keywords and patterns from the codebase
4. **Progressive Success**: Start simple, validate, then enhance
5. **Global rules**: Follow all rules in CLAUDE.md

---

## Goal
Fix the `SemanticDiffDetector` class to properly handle newly added files in the `update` command by implementing robust file categorization and git operations that can distinguish between new, modified, and deleted files without throwing errors.

## Why
- **Business value**: Enables incremental specification updates for new code additions
- **User impact**: Fixes the "No semantic changes detected" error when adding new files
- **Integration**: Critical for the update command's core functionality
- **Problems solved**: Allows developers to incrementally update specifications as they add new features

## What
The system should:
- Pre-categorize files using `git diff --name-status` before processing 
- Handle new files (A), modified files (M), and deleted files (D) appropriately
- Detect semantic changes in newly added methods, classes, and functions
- Generate proper specification updates for new code additions

### Success Criteria
- [ ] New files are properly detected and processed as semantic additions
- [ ] The update command successfully processes the sample scenario (new methods in existing files)
- [ ] No "git show HEAD~1" errors for non-existent files
- [ ] Semantic changes are correctly identified and specification updates generated
- [ ] All existing functionality continues to work (no regressions)

## All Needed Context

### Documentation & References
```yaml
# MUST READ - Include these in your context window
- file: /Users/masaki/Codes/AI-specification-generator/TODO.md
  why: Contains the exact problem description and reproduction steps
  
- file: /Users/masaki/Codes/AI-specification-generator/src/spec_generator/core/diff_detector.py
  why: Main SemanticDiffDetector implementation that needs fixing
  
- file: /Users/masaki/Codes/AI-specification-generator/src/spec_generator/utils/git_utils.py
  why: Git operations layer where the core issue manifests
  
- file: /Users/masaki/Codes/AI-specification-generator/tests/test_diff_detector.py
  why: Existing test patterns to follow for new file scenarios
  
- url: https://git-scm.com/docs/git-diff
  why: Official documentation for git diff --name-status usage patterns
  
- url: https://stackoverflow.com/questions/54828777/for-git-diff-name-status-what-does-the-output-mean
  why: Explanation of git diff --name-status output format (A/M/D status codes)
```

### Current Codebase tree
```bash
.
├── src/
│   └── spec_generator/
│       ├── cli.py                      # CLI with update command
│       ├── core/
│       │   ├── diff_detector.py        # SemanticDiffDetector (MAIN FIX)
│       │   ├── generator.py
│       │   └── processor.py
│       └── utils/
│           ├── git_utils.py           # GitOperations (CORE FIX)
│           └── file_utils.py
├── tests/
│   ├── test_diff_detector.py         # Tests to enhance
│   └── test_git_utils.py             # Git operations tests
└── samples/
    └── Python/
        └── test_sample.py             # Sample file for testing
```

### Desired Codebase tree (no new files needed)
```bash
# No new files - enhancing existing ones:
# - src/spec_generator/utils/git_utils.py (enhance file categorization)
# - src/spec_generator/core/diff_detector.py (improve new file handling)
# - tests/test_diff_detector.py (add new file test cases)
```

### Known Gotchas & Library Quirks
```python
# CRITICAL: git show HEAD~1:filepath fails for new files - use git diff --name-status first
# CRITICAL: The codebase uses relative paths from repo root for file operations
# CRITICAL: Error handling pattern uses GitError exception for all git failures
# CRITICAL: File content retrieval has UTF-8 with latin-1 fallback encoding
# CRITICAL: Methods return None for missing files instead of throwing errors
# CRITICAL: Language detection relies on file extensions and content analysis
# CRITICAL: SemanticDiffDetector expects files to exist in working directory
# CRITICAL: The include_untracked parameter must be True for new files
```

## Implementation Blueprint

### Data models and structure
No new data models needed - using existing:
```python
# Existing models in models.py:
# - SemanticChange: Represents detected changes
# - ChangeType: Enum for ADDED, MODIFIED, DELETED
# - CodeElement: Represents parsed code elements
```

### List of tasks to be completed

```yaml
Task 1: Enhance GitOperations with File Categorization
MODIFY src/spec_generator/utils/git_utils.py:
  - ADD method get_file_status_map() using git diff --name-status
  - ENHANCE get_changed_files() to use status categorization
  - IMPROVE error handling in get_file_at_commit() for new files
  - KEEP all existing method signatures unchanged

Task 2: Improve SemanticDiffDetector File Processing
MODIFY src/spec_generator/core/diff_detector.py:
  - ENHANCE _analyze_file_changes() to handle pre-categorized files
  - IMPROVE file processing flow to use status information
  - ENSURE proper handling of new file creation scenarios
  - PRESERVE all existing error handling patterns

Task 3: Add Comprehensive New File Test Cases
MODIFY tests/test_diff_detector.py:
  - ADD test_detect_changes_new_file() for new file scenarios
  - ADD test_analyze_file_changes_new_file() for specific new file handling
  - ADD test_file_creation_detection() for semantic element detection
  - FOLLOW existing test patterns and mock structures

Task 4: Validate Fix with Sample Scenario
CREATE temporary test scenario:
  - RECREATE the exact issue from TODO.md
  - VERIFY fix works with samples/Python/test_sample.py
  - ENSURE no regressions in existing functionality
  - VALIDATE semantic changes are properly detected
```

### Per task pseudocode

```python
# Task 1: git_utils.py enhancement
def get_file_status_map(
    self, 
    base_commit: str = "HEAD~1", 
    target_commit: str = "HEAD"
) -> Dict[str, str]:
    """
    Get file status mapping using git diff --name-status.
    Returns: {"filepath": "A|M|D", ...}
    """
    # PATTERN: Use existing _run_git_command with proper error handling
    try:
        result = self._run_git_command([
            "diff", "--name-status", base_commit, target_commit
        ])
        
        # CRITICAL: Parse A/M/D status codes from git output
        status_map = {}
        for line in result.stdout.strip().split('\n'):
            if line:
                parts = line.split('\t')
                if len(parts) >= 2:
                    status, filepath = parts[0], parts[1]
                    status_map[filepath] = status
        
        return status_map
    except GitError:
        # PATTERN: Return empty dict on error, don't fail
        return {}

# Task 2: diff_detector.py enhancement  
def _analyze_file_changes(
    self, 
    file_path: str, 
    base_commit: str, 
    target_commit: str,
    file_status: Optional[str] = None  # NEW: A/M/D status
) -> list[SemanticChange]:
    """Enhanced file analysis with pre-categorization."""
    
    # PATTERN: Use status to optimize file content retrieval
    if file_status == "A":  # New file
        # SKIP trying to get old content for new files
        old_content = None
        new_content = self.git_ops.get_current_file_content(file_path)
    elif file_status == "D":  # Deleted file
        # SKIP trying to get new content for deleted files
        old_content = self.git_ops.get_file_at_commit(file_path, base_commit)
        new_content = None
    else:  # Modified file or unknown status
        # PATTERN: Use existing logic for modified files
        old_content = self.git_ops.get_file_at_commit(file_path, base_commit)
        new_content = self.git_ops.get_current_file_content(file_path)
    
    # PRESERVE existing file creation/deletion/modification logic
    if old_content is None and new_content is not None:
        return self._handle_file_creation(file_path, new_content, language)
    # ... rest of existing logic
```

### Integration Points
```yaml
CLI:
  - No changes needed - existing update command should work
  - Pattern: cli.py calls diff_detector.detect_changes() unchanged
  
GIT_OPERATIONS:
  - Enhanced with file status categorization
  - Maintains backward compatibility
  - Improved error handling for edge cases
  
DIFF_DETECTOR:
  - Enhanced file processing pipeline
  - Maintains existing public API
  - Improved handling of new file scenarios
  
TESTING:
  - Comprehensive test coverage for new file scenarios
  - Mock git operations for reliable testing
  - Validate end-to-end update command functionality
```

## Validation Loop

### Level 1: Syntax & Style
```bash
# Run these FIRST - fix any errors before proceeding
uv run ruff check src/spec_generator/utils/git_utils.py --fix
uv run ruff check src/spec_generator/core/diff_detector.py --fix
uv run mypy src/spec_generator/

# Expected: No errors. If errors, READ and fix.
```

### Level 2: Unit Tests
```python
# test_diff_detector.py - Add these critical test cases:

async def test_detect_changes_new_file():
    """Test detection of changes in newly added files."""
    # PATTERN: Mock git operations like existing tests
    mock_git_ops = MagicMock()
    mock_git_ops.get_file_status_map.return_value = {
        "new_file.py": "A"  # New file
    }
    mock_git_ops.get_current_file_content.return_value = "def new_function(): pass"
    
    detector = SemanticDiffDetector(git_ops=mock_git_ops)
    changes = detector.detect_changes()
    
    # VALIDATE: Should detect new function as semantic change
    assert len(changes) > 0
    assert changes[0].change_type == ChangeType.ADDED
    assert changes[0].element_name == "new_function"

def test_analyze_file_changes_new_file():
    """Test file analysis handles new files without git errors."""
    # PATTERN: Follow existing test structure
    mock_git_ops = MagicMock()
    mock_git_ops.get_file_at_commit.side_effect = GitError("File not found")
    mock_git_ops.get_current_file_content.return_value = "class NewClass: pass"
    
    detector = SemanticDiffDetector(git_ops=mock_git_ops)
    changes = detector._analyze_file_changes("new_file.py", "HEAD~1", "HEAD", "A")
    
    # VALIDATE: Should handle new file creation gracefully
    assert len(changes) == 1
    assert changes[0].change_type == ChangeType.ADDED
    assert "NewClass" in changes[0].element_name

def test_git_file_status_map():
    """Test git diff --name-status parsing."""
    # PATTERN: Mock git command output
    mock_git_ops = GitOperations("/test/repo")
    mock_git_ops._run_git_command = MagicMock()
    mock_git_ops._run_git_command.return_value = MagicMock(
        stdout="A\tnew_file.py\nM\tmodified_file.py\nD\tdeleted_file.py\n"
    )
    
    status_map = mock_git_ops.get_file_status_map()
    
    # VALIDATE: Should parse status codes correctly
    assert status_map["new_file.py"] == "A"
    assert status_map["modified_file.py"] == "M"
    assert status_map["deleted_file.py"] == "D"
```

```bash
# Run iteratively until passing:
uv run pytest tests/test_diff_detector.py::test_detect_changes_new_file -v
uv run pytest tests/test_diff_detector.py::test_analyze_file_changes_new_file -v
uv run pytest tests/test_diff_detector.py::test_git_file_status_map -v

# If failing: Read error, fix implementation, re-run
```

### Level 3: Integration Test
```bash
# Test the exact scenario from TODO.md
cd /Users/masaki/Codes/AI-specification-generator

# Setup: Create test file with new methods
echo "def square(x): return x*x" >> samples/Python/test_sample.py
echo "def cube(x): return x*x*x" >> samples/Python/test_sample.py

# Commit changes
git add samples/Python/test_sample.py
git commit -m "Add new methods for testing"

# Run update command - should now work
uv run python -m spec_generator.cli update . --output spec-updates --existing-spec test-spec.md

# Expected output: 
# - Should detect semantic changes in new methods
# - Should generate specification updates
# - Should NOT show "No semantic changes detected"
# - Should NOT show git command errors

# Validate: Check spec-updates contains new method documentation
grep -i "square\|cube" spec-updates/
```

## Final Validation Checklist
- [ ] All tests pass: `uv run pytest tests/test_diff_detector.py -v`
- [ ] No linting errors: `uv run ruff check src/spec_generator/`
- [ ] No type errors: `uv run mypy src/spec_generator/`
- [ ] Sample scenario works: Update command processes new files
- [ ] No regressions: Existing functionality still works
- [ ] Error handling: Git errors are handled gracefully
- [ ] Performance: No significant slowdown in processing

---

## Anti-Patterns to Avoid
- ❌ Don't create new patterns when existing ones work
- ❌ Don't change public API signatures unnecessarily
- ❌ Don't skip error handling for edge cases
- ❌ Don't ignore existing test patterns
- ❌ Don't hardcode file paths or git commands
- ❌ Don't assume files exist without checking

## Confidence Score: 8/10

High confidence due to:
- Clear understanding of the root cause
- Existing codebase patterns to follow
- Comprehensive error handling strategy
- Well-defined validation gates
- Minimal changes to existing API

Minor uncertainty on:
- Edge cases in git operations
- Performance impact of status pre-categorization
- Potential interactions with other git workflows