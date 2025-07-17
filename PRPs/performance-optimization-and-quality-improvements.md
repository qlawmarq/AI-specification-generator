# PRP: Performance Optimization and Quality Improvements

**Feature:** Fix command timeout errors and generation time issues  
**Priority:** High  
**Estimated Effort:** 3-4 hours  

## Goal
Resolve the critical performance issues where the `generate` command times out after 2 minutes and takes excessive time (95+ seconds) to process small files (267 lines, 14 chunks). Target performance should be under 30 seconds for similar workloads with reliable completion.

## Why
- **User Experience**: Current 95+ second processing times make the tool impractical for daily use
- **Reliability**: Command timeouts result in incomplete specifications, wasting user time
- **Production Readiness**: Performance issues prevent adoption in CI/CD pipelines and batch processing scenarios
- **Resource Efficiency**: Current implementation may be making inefficient API calls and not utilizing async capabilities

## What
Transform the specification generator from sequential LLM processing to optimized batch processing with proper timeout handling, retry logic, and performance monitoring.

### Success Criteria
- [ ] `generate` command completes in under 30 seconds for 267-line files (67% improvement)
- [ ] No more timeout errors for files under 500 lines
- [ ] Proper progress indicators and error recovery
- [ ] Configurable timeout settings that work reliably
- [ ] Batch processing reduces API calls by 50%+

## All Needed Context

### Documentation & References
```yaml
# MUST READ - Include these in your context window
- url: https://python.langchain.com/docs/concepts/chat_models/
  why: Standard API for async programming and efficient batching
  critical: Built-in batch() methods for parallel execution
  
- url: https://python.langchain.com/docs/concepts/runnables/
  why: Runnable interface with optimized parallel execution
  section: batch and batch_as_completed methods
  critical: ThreadPoolExecutor for I/O-bound operations
  
- url: https://medium.com/@hey_16878/efficient-batch-processing-with-langchain-and-openai-overcoming-ratelimiterror-daa9de4bbd8b
  why: Best practices for rate limiting and token counting
  critical: Dynamic batch size calculation and retry logic
  
- file: src/spec_generator/core/generator.py:525-552
  why: Current sequential chunk analysis implementation 
  critical: _analyze_chunks method processes chunks one by one
  
- file: src/spec_generator/core/generator.py:107-141  
  why: Current LLM timeout implementation
  critical: Uses asyncio.wait_for with request_timeout
  
- file: src/spec_generator/models.py:85-99
  why: PerformanceSettings model with timeout configurations
  critical: request_timeout=300 but CLI times out at 120
  
- file: src/spec_generator/cli.py:331-366
  why: Current single file processing flow
  critical: No timeout handling at CLI level
```

### Current Codebase Overview
```bash
src/spec_generator/
├── cli.py                  # CLI interface with timeout issues
├── config.py              # Configuration loading
├── models.py               # PerformanceSettings model
├── core/
│   ├── generator.py        # Sequential LLM processing
│   ├── processor.py        # Chunk creation (working well)
│   └── diff_detector.py    # Change detection
├── parsers/               # AST and Tree-sitter parsing
├── templates/             # Japanese spec templates
└── utils/                 # Utilities and memory management
```

### Known Gotchas & Library Quirks
```python
# CRITICAL: LangChain RunnableSequence supports batch operations
# Current code: Uses sequential await calls instead of batch()
# Fix: Use llm.batch() or abatch() for parallel processing

# CRITICAL: asyncio.wait_for timeout at 300s but CLI times out at 120s  
# Issue: CLI level timeout (likely in subprocess/shell) overrides config
# Fix: Add CLI-level timeout configuration and proper signal handling

# CRITICAL: Gemini API rate limits (2.5-flash model specifics)
# Current: No rate limiting implementation visible
# Fix: Implement token counter and request throttling

# CRITICAL: Progress indication missing for long operations
# User sees no feedback during 95-second processing
# Fix: Add Rich progress bars with ETA and chunk progress

# IMPORTANT: Error handling needs improvement
# Current: Generic "Analysis failed for chunk" messages
# Fix: Specific error types, retry logic, and fallback strategies
```

## Implementation Blueprint

### Performance Optimization Architecture
```python
# NEW: Batch processing manager
class BatchProcessor:
    async def process_chunks_batch(self, chunks: List[CodeChunk]) -> List[dict]:
        """Process chunks in optimized batches with rate limiting."""
        
# ENHANCED: LLM provider with batch support  
class LLMProvider:
    async def generate_batch(self, prompts: List[str]) -> List[str]:
        """Use LangChain's native batch processing."""
        
# NEW: Timeout management
class TimeoutManager:
    def __init__(self, cli_timeout: int, request_timeout: int):
        """Manage nested timeout hierarchies."""
```

### Task List (Implementation Order)

```yaml
Task 1 - Add CLI Timeout Configuration:
  MODIFY src/spec_generator/cli.py:
    - FIND: @app.command() def generate(
    - ADD: timeout parameter with default 600 seconds  
    - WRAP: _run_single_file() with asyncio.wait_for(timeout=timeout)
    - PRESERVE: existing error handling patterns

Task 2 - Implement Batch Processing in Generator:
  MODIFY src/spec_generator/core/generator.py:
    - FIND: async def _analyze_chunks(self, chunks: list[CodeChunk])
    - REPLACE: sequential processing with LangChain batch()
    - ADD: dynamic batch size calculation based on tier/limits
    - KEEP: existing error handling structure

Task 3 - Add Progress Indicators:
  MODIFY src/spec_generator/cli.py:
    - FIND: Progress components imports
    - ADD: Rich ProgressBar with task tracking
    - INTEGRATE: with batch processing for real-time updates
    - PATTERN: Follow existing Progress usage in update command

Task 4 - Enhance Error Handling and Retries:
  MODIFY src/spec_generator/core/generator.py:
    - CREATE: RetryManager class with exponential backoff
    - ADD: specific exception handling for rate limits, timeouts
    - IMPLEMENT: graceful degradation for partial failures
    - PATTERN: Mirror existing error patterns in processor.py

Task 5 - Add Performance Monitoring:
  CREATE src/spec_generator/utils/performance_monitor.py:
    - TRACK: API call counts, response times, batch efficiency
    - LOG: performance metrics for optimization
    - PROVIDE: recommendations for optimal batch sizes

Task 6 - Update Configuration Models:
  MODIFY src/spec_generator/models.py:
    - ADD: cli_timeout_seconds to PerformanceSettings
    - ADD: enable_batch_processing flag
    - ADD: batch_optimization_strategy enum
    - VALIDATE: timeout hierarchy (cli > request > operation)
```

### Core Implementation Patterns

```python
# Task 1: CLI Timeout Management
@app.command()
def generate(
    file_path: Path,
    output: Path,
    timeout: int = typer.Option(600, "--timeout", help="Overall timeout in seconds"),
    use_semantic_chunking: bool = False,
):
    """Generate specification with configurable timeout."""
    try:
        # Wrap with overall timeout
        asyncio.run(
            asyncio.wait_for(
                _run_single_file(file_path, output, use_semantic_chunking), 
                timeout=timeout
            )
        )
    except asyncio.TimeoutError:
        console.print(f"[red]Generation timed out after {timeout}s[/red]")
        raise typer.Exit(1)

# Task 2: Batch Processing 
async def _analyze_chunks_batch(self, chunks: list[CodeChunk]) -> list[dict]:
    """Optimized batch analysis using LangChain's batch API."""
    batch_size = self._calculate_optimal_batch_size(len(chunks))
    
    all_analyses = []
    for i in range(0, len(chunks), batch_size):
        batch = chunks[i:i + batch_size]
        
        # Prepare all prompts for batch
        prompts = [
            self.prompt_templates.ANALYSIS_PROMPT.format(
                code_content=chunk.content,
                file_path=str(chunk.file_path),
                language=chunk.language.value,
                ast_info=self._create_ast_info(chunk)
            ) for chunk in batch
        ]
        
        # CRITICAL: Use LangChain's batch processing
        try:
            batch_results = await self.llm_provider.llm.abatch(prompts)
            analyses = [self._parse_analysis_response(result.content) for result in batch_results]
            all_analyses.extend(analyses)
            
        except Exception as e:
            # Fallback to sequential for this batch
            logger.warning(f"Batch failed, falling back to sequential: {e}")
            for chunk in batch:
                analysis = await self.analysis_processor.analyze_code_chunk(chunk)
                all_analyses.append(analysis)
    
    return all_analyses

# Task 3: Progress Tracking
async def _run_single_file_with_progress(file_path, output, use_semantic_chunking):
    """Enhanced single file processing with progress tracking."""
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        PercentageColumn(),
        TimeElapsedColumn(),
        console=console,
    ) as progress:
        
        # Stage 1: Processing
        process_task = progress.add_task("Processing file...", total=100)
        chunks = await processor.process_single_file(file_path, use_semantic_chunking, True)
        progress.update(process_task, completed=30)
        
        # Stage 2: Analysis (with batch tracking)
        analysis_task = progress.add_task("Analyzing chunks...", total=len(chunks))
        analyses = await generator._analyze_chunks_with_progress(chunks, progress, analysis_task)
        progress.update(process_task, completed=70)
        
        # Stage 3: Generation
        generation_task = progress.add_task("Generating specification...", total=100)
        spec_content = await generator._generate_specification_document(combined_analysis, project_name)
        progress.update(process_task, completed=100)
```

### Integration Points
```yaml
CONFIGURATION:
  - add to: src/spec_generator/models.py PerformanceSettings
  - fields: "cli_timeout_seconds: int = 600, enable_batch_processing: bool = True"
  
CLI:
  - modify: src/spec_generator/cli.py generate command
  - add: --timeout parameter and progress indicators
  
LOGGING:
  - enhance: Performance metrics logging
  - pattern: "logger.info(f'Batch {i}: {len(batch)} chunks in {duration:.2f}s')"
```

## Validation Loop

### Level 1: Syntax & Style  
```bash
# Run these FIRST - fix any errors before proceeding
ruff check src/spec_generator/ --fix
mypy src/spec_generator/
# Expected: No errors. If errors, READ and fix immediately.
```

### Level 2: Unit Tests
```python
# CREATE tests/test_performance_optimization.py
def test_batch_processing_performance():
    """Batch processing is faster than sequential."""
    chunks = create_test_chunks(10)
    
    start_time = time.time()
    batch_results = await generator._analyze_chunks_batch(chunks)
    batch_duration = time.time() - start_time
    
    # Should be significantly faster than sequential
    assert batch_duration < 30  # Target: under 30s for 10 chunks
    assert len(batch_results) == 10

def test_timeout_handling():
    """CLI timeout prevents infinite hanging."""
    with pytest.raises(asyncio.TimeoutError):
        await asyncio.wait_for(
            mock_long_running_generation(), 
            timeout=1  # Force timeout
        )

def test_progress_tracking():
    """Progress indicators provide user feedback."""
    progress_updates = []
    
    async def capture_progress(task_id, completed):
        progress_updates.append((task_id, completed))
    
    await generator._analyze_chunks_with_progress(test_chunks, mock_progress)
    assert len(progress_updates) > 0  # Progress was reported

def test_batch_size_optimization():
    """Batch size adapts to chunk count and limits."""
    assert generator._calculate_optimal_batch_size(5) == 5    # Small batches
    assert generator._calculate_optimal_batch_size(100) <= 20  # Large batches limited
```

### Level 3: Performance Integration Test
```bash
# Test with the actual problematic file
uv run python -m spec_generator.cli generate samples/Python/test_sample.py \
  --output test-performance.md \
  --timeout 180  # 3 minutes max

# Expected: Completes in under 30 seconds, no timeout
# If failing: Check logs for specific bottlenecks
```

## Final Validation Checklist
- [ ] All tests pass: `uv run pytest tests/ -v`
- [ ] No linting errors: `uv run ruff check src/`
- [ ] No type errors: `uv run mypy src/`
- [ ] Performance test: `time uv run python -m spec_generator.cli generate samples/Python/test_sample.py --output test.md` < 30s
- [ ] Timeout test: Generate with `--timeout 10` fails gracefully
- [ ] Progress indicators show real-time updates
- [ ] Batch processing logs show efficiency gains
- [ ] Error recovery works for partial failures

---

## Anti-Patterns to Avoid
- ❌ Don't disable timeouts - fix the underlying performance issues
- ❌ Don't increase timeouts without implementing batch processing  
- ❌ Don't ignore rate limits - implement proper throttling
- ❌ Don't remove error handling during optimization
- ❌ Don't skip progress indicators for long operations
- ❌ Don't make API calls synchronously in async functions

## Quality Score: 9/10

**Confidence for one-pass implementation:** High

**Reasoning:** 
- Comprehensive research into LangChain batch processing APIs
- Clear identification of bottlenecks in current sequential processing  
- Specific implementation patterns with error handling
- Executable validation gates ensure quality
- Real-world performance targets (30s vs 95s)
- Proper timeout hierarchy (CLI > request > operation)
- Progressive enhancement approach (batch → progress → monitoring)

The PRP provides sufficient context for an AI agent to implement performant, reliable specification generation with proper user feedback and error handling.