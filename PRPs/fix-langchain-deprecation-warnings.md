# Fix LangChain Deprecation Warnings and Google AI Parameter Issue PRP

## Goal
Fix critical deprecation warnings and parameter issues in the AI Specification Generator to ensure:
- **Zero LangChain deprecation warnings**: Migrate from deprecated `predict()` to `invoke()` method
- **Clean Google AI integration**: Remove invalid `http_async_client` parameter warning
- **Future compatibility**: Ensure codebase works with latest LangChain versions
- **Maintained functionality**: All existing features work without regression

## Why
- **Breaking Changes Risk**: `BaseChatModel.predict()` is deprecated since langchain-core 0.1.7 and will be removed in 1.0
- **Warning Pollution**: Current warnings make it hard to identify real issues in production
- **Parameter Validation**: Invalid `http_async_client` parameter suggests configuration issues
- **Maintainability**: Clean codebase without deprecated methods improves long-term maintenance

## What
**Technical Requirements:**
- Replace `self.llm.predict(prompt)` with `self.llm.invoke(prompt)` in generator.py:125
- Remove invalid `http_async_client` parameter from ChatGoogleGenerativeAI configuration
- Update all test mocks to use `invoke` instead of `predict`
- Ensure async operations work correctly with new method
- Validate no functional regression in generation quality

### Success Criteria
- [ ] Zero deprecation warnings when running generate command
- [ ] Zero parameter warnings from ChatGoogleGenerativeAI
- [ ] All existing tests pass with updated mock expectations
- [ ] Generate command produces identical output quality
- [ ] No performance regression in generation speed

## All Needed Context

### Documentation & References
```yaml
# MUST READ - Include these in your context window
- url: https://python.langchain.com/api_reference/core/language_models/langchain_core.language_models.chat_models.BaseChatModel.html
  why: Official documentation for BaseChatModel.invoke() method
  critical: Shows invoke() accepts same string input as predict() but returns AIMessage
  
- url: https://python.langchain.com/docs/concepts/chat_models/
  why: Updated chat model usage patterns showing invoke() examples
  critical: Examples of proper invoke() usage with string and message inputs
  
- url: https://python.langchain.com/api_reference/google_genai/chat_models/langchain_google_genai.chat_models.ChatGoogleGenerativeAI.html
  why: Official ChatGoogleGenerativeAI parameters documentation
  critical: Valid parameters are transport, timeout, max_retries - NOT http_async_client
  
- file: src/spec_generator/core/generator.py
  why: Main file containing the deprecated predict() call and invalid parameter
  critical: Lines 125 (predict call), 59-73 (Google AI config), 115-137 (generate method)
  
- file: tests/test_generator.py
  why: Test patterns for mocking LLM interactions
  critical: Lines 87, 111, 144 (predict mocks), Shows existing mock structure to update
  
- file: tests/test_gemini_integration.py
  why: Google AI specific test patterns
  critical: Lines 106, 119, 125, 157 (predict mock calls), Gemini-specific test setup
```

### Current Codebase Structure
```bash
src/spec_generator/
├── core/
│   └── generator.py          # MAIN TARGET: Contains predict() call (line 125)
└── config.py                 # Configuration patterns for reference

tests/
├── test_generator.py         # NEEDS UPDATE: predict mocks (lines 87, 111, 144)
└── test_gemini_integration.py # NEEDS UPDATE: predict mocks (lines 106, 119, 125, 157)
```

### Known Gotchas & Library Quirks
```python
# CRITICAL: LangChain predict() vs invoke() return types
# OLD: result = llm.predict("prompt")  # Returns string directly
# NEW: result = llm.invoke("prompt")   # Returns AIMessage object
# SOLUTION: Extract content with result.content if AIMessage

# CRITICAL: ChatGoogleGenerativeAI parameter changes
# INVALID: http_async_client=async_client  # Not supported, causes warnings
# VALID: Remove this parameter entirely, library handles async internally

# CRITICAL: Async wrapper behavior
# CURRENT: run_in_executor(None, self.llm.predict, prompt)
# UPDATED: run_in_executor(None, self.llm.invoke, prompt)
# NOTE: Still need executor wrapper for sync-to-async conversion

# CRITICAL: Test mock updates
# OLD: mock_llm.predict.return_value = "response"
# NEW: mock_llm.invoke.return_value = "response" 
# NOTE: Tests can still return strings, real invoke() returns AIMessage

# CRITICAL: httpx import still needed
# Current httpx.AsyncClient is used for timeout configuration
# Only remove http_async_client parameter, keep httpx import and timeout setup
```

## Implementation Blueprint

### Data Models and Structure
```python
# No new data models needed - this is a method migration
# AIMessage return type is handled internally by LangChain
# Our code expects string responses, which invoke() provides when mocked
```

### List of Tasks to Complete (in order)

```yaml
Task 1:
MODIFY src/spec_generator/core/generator.py:
  - FIND pattern: "None, self.llm.predict, prompt" (line 125)
  - REPLACE with: "None, self.llm.invoke, prompt"
  - PRESERVE: All surrounding async wrapper logic
  - PRESERVE: Exception handling and logging

Task 2:
MODIFY src/spec_generator/core/generator.py:
  - FIND pattern: "http_async_client=async_client," (line 72)
  - DELETE: This entire line
  - PRESERVE: All other ChatGoogleGenerativeAI parameters
  - PRESERVE: httpx.AsyncClient creation for timeout config

Task 3:
MODIFY tests/test_generator.py:
  - FIND pattern: "mock_llm.predict.return_value" (lines 87, 111)
  - REPLACE with: "mock_llm.invoke.return_value"
  - FIND pattern: "mock_llm.predict.side_effect" (line 144)
  - REPLACE with: "mock_llm.invoke.side_effect"
  - PRESERVE: All test logic and assertions

Task 4:
MODIFY tests/test_gemini_integration.py:
  - FIND pattern: "mock_instance.predict.return_value" (lines 106, 157)
  - REPLACE with: "mock_instance.invoke.return_value"
  - FIND pattern: "mock_instance.predict.assert_called_once_with" (line 119)
  - REPLACE with: "mock_instance.invoke.assert_called_once_with"
  - FIND pattern: "mock_instance.predict.side_effect" (line 125)
  - REPLACE with: "mock_instance.invoke.side_effect"
  - PRESERVE: All test setup and validation logic

Task 5:
VALIDATE functionality:
  - RUN: uv run python -m spec_generator.cli generate samples/Python/test_sample.py --output test-validation.md
  - VERIFY: No deprecation warnings in output
  - VERIFY: No "Unexpected argument" warnings
  - VERIFY: Generated specification content matches previous quality
```

### Task 1 Pseudocode
```python
# In generator.py generate() method
async def generate(self, prompt: str, **kwargs) -> str:
    """Generate response with rate limiting."""
    await self._rate_limit()

    try:
        timeout_seconds = self.config.performance_settings.request_timeout
        response = await asyncio.wait_for(
            asyncio.get_event_loop().run_in_executor(
                None, self.llm.invoke, prompt  # CHANGED: predict -> invoke
            ),
            timeout=timeout_seconds,
        )
        # NOTE: invoke() returns AIMessage in real usage, but executor wrapper 
        # and test mocks will still provide string responses as expected
```

### Task 2 Pseudocode
```python
# In generator.py _create_llm() method
def _create_llm(self):
    if provider == "gemini" and self.config.gemini_api_key:
        # Create timeout config for httpx (keep this)
        timeout_config = httpx.Timeout(
            timeout=self.config.performance_settings.request_timeout,
            connect=5.0,
            read=self.config.performance_settings.request_timeout - 5.0,
        )
        async_client = httpx.AsyncClient(timeout=timeout_config)

        return ChatGoogleGenerativeAI(
            model=model,
            temperature=0.3,
            google_api_key=self.config.gemini_api_key,
            max_retries=self.config.performance_settings.max_retries,
            # REMOVED: http_async_client=async_client,  # This line deleted
        )
```

### Integration Points
```yaml
NO DATABASE CHANGES: This is a method signature update only

NO CONFIG CHANGES: Parameters remain the same from user perspective

NO ROUTE CHANGES: CLI interface remains identical

TESTING IMPACT: 
  - Update all predict() mocks to invoke()
  - Verify test isolation still works
  - Check integration tests for warnings
```

## Validation Loop

### Level 1: Syntax & Style
```bash
# Run these FIRST - fix any errors before proceeding
ruff check src/spec_generator/core/generator.py --fix
mypy src/spec_generator/core/generator.py
ruff check tests/test_generator.py tests/test_gemini_integration.py --fix
mypy tests/test_generator.py tests/test_gemini_integration.py

# Expected: No errors. If mypy complains about invoke return types, 
# add type ignore or update type hints as needed
```

### Level 2: Unit Tests 
```bash
# Run specific test files that were modified
uv run pytest tests/test_generator.py -v
uv run pytest tests/test_gemini_integration.py -v

# Expected: All tests pass. If failing:
# - Check mock method names (predict vs invoke)
# - Verify return value expectations match
# - Ensure exception handling still works

# If any tests fail, read error carefully and fix test logic
```

### Level 3: Integration Test - Warning Verification
```bash
# Test for absence of warnings
uv run python -m spec_generator.cli generate samples/Python/test_sample.py --output test-no-warnings.md 2>&1 | grep -i "warning\|deprecated"

# Expected: No output (empty result means no warnings)
# If warnings appear, check which ones remain and trace their source

# Test functionality preservation
diff test-spec.md test-no-warnings.md

# Expected: Files should be identical or very similar in content quality
```

### Level 4: Full Test Suite
```bash
# Run complete test suite to ensure no regression
uv run pytest tests/ -v

# Expected: All tests pass with no failures
# If integration tests fail, may need to update more mocks elsewhere
```

## Final Validation Checklist
- [ ] All tests pass: `uv run pytest tests/ -v`
- [ ] No linting errors: `uv run ruff check src/`
- [ ] No type errors: `uv run mypy src/`
- [ ] No deprecation warnings: `uv run python -m spec_generator.cli generate samples/Python/test_sample.py --output test.md 2>&1 | grep -i deprecated`
- [ ] No parameter warnings: `uv run python -m spec_generator.cli generate samples/Python/test_sample.py --output test.md 2>&1 | grep -i "unexpected argument"`
- [ ] Generated content quality maintained
- [ ] Performance not degraded

## Anti-Patterns to Avoid
- ❌ Don't change invoke() to return strings - let LangChain handle AIMessage conversion
- ❌ Don't remove httpx import entirely - still needed for timeout configuration  
- ❌ Don't modify async wrapper pattern - keep run_in_executor for sync compatibility
- ❌ Don't update return type annotations hastily - verify actual behavior first
- ❌ Don't mock invoke() to return AIMessage in tests - keep string returns for simplicity
- ❌ Don't add unnecessary parameters to ChatGoogleGenerativeAI - remove invalid ones only

---

**Confidence Level**: 9/10 - This is a straightforward method migration with clear documentation and well-defined scope. The changes are minimal, isolated, and have comprehensive validation steps.