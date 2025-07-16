name: "Improve Specification Generation Quality - Class Structure Recognition"
description: |

## Purpose
Fix the specification generation quality issues where a single Calculator class is incorrectly identified as multiple different classes, leading to poor specification accuracy and readability.

## Core Principles
1. **Context is King**: Maintain class-method relationships throughout the analysis pipeline
2. **Validation Loops**: Provide executable tests to validate specification quality
3. **Information Dense**: Use complete AST context for accurate structural analysis
4. **Progressive Success**: Enhance existing pipeline without breaking functionality
5. **Global rules**: Follow all rules in CLAUDE.md

---

## Goal
Enhance the AST analysis and specification generation pipeline to accurately identify and represent code structures, specifically ensuring that a single class is recognized as one unified entity rather than multiple fragmented classes.

## Why
- **Quality Issue**: Generated specifications incorrectly fragment single classes into multiple entities
- **User Impact**: Specifications are confusing and inaccurate, reducing trust in the tool
- **Business Value**: Accurate specifications are essential for documentation and code understanding
- **Integration**: Fixes core functionality that affects all specification generation

## What
Improve the code analysis pipeline to:
1. Properly aggregate semantic elements within class boundaries
2. Maintain class-method relationships during chunk creation
3. Enhance LLM prompts to better understand code structure
4. Generate accurate class diagrams without duplication

### Success Criteria
- [ ] Single Calculator class appears as one unified class in generated specifications
- [ ] Method relationships are correctly associated with their parent classes
- [ ] Mermaid class diagrams show accurate structure without duplication
- [ ] Generated specifications use proper class names instead of "不明" or "推測"

## All Needed Context

### Documentation & References
```yaml
# MUST READ - Include these in your context window
- url: https://tree-sitter.github.io/tree-sitter/using-parsers#query-syntax
  why: Advanced query patterns for comprehensive class extraction
  
- file: src/spec_generator/parsers/tree_sitter_parser.py
  why: Current AST parsing implementation and SemanticElement extraction
  
- url: https://docs.python.org/3/library/ast.html
  why: Python AST structure for understanding class-method relationships
  
- file: src/spec_generator/core/processor.py
  why: Current chunk creation logic that needs class context preservation
  
- url: https://python.langchain.com/docs/how_to/structured_output
  why: Structured output patterns for better LLM analysis
  
- file: src/spec_generator/templates/prompts.py
  why: Current prompt structure that needs enhancement for class recognition
  
- url: https://github.com/tree-sitter/tree-sitter-python/blob/master/queries/highlights.scm
  why: Reference for Python-specific Tree-sitter queries
```

### Current Codebase tree (relevant sections)
```bash
src/spec_generator/
├── core/
│   ├── processor.py          # LargeCodebaseProcessor, ChunkProcessor
│   ├── generator.py          # SpecificationGenerator, progressive prompting
│   └── diff_detector.py      # SemanticDiffDetector
├── parsers/
│   ├── tree_sitter_parser.py # TreeSitterParser, SemanticElement
│   └── ast_analyzer.py       # ASTAnalyzer, ModuleInfo
├── templates/
│   ├── prompts.py            # ANALYSIS_PROMPT, JAPANESE_SPEC_PROMPT
│   └── japanese_spec.py      # Japanese specification templates
└── models.py                 # CodeChunk, SemanticChange, SpecificationConfig
```

### Desired Codebase tree with files to be enhanced
```bash
src/spec_generator/
├── core/
│   ├── processor.py          # ENHANCE: Class-aware chunk creation
│   └── generator.py          # ENHANCE: Improved context aggregation
├── parsers/
│   ├── tree_sitter_parser.py # ENHANCE: Class-method relationship extraction
│   └── ast_analyzer.py       # ENHANCE: Full class structure analysis
├── templates/
│   └── prompts.py            # ENHANCE: Structure-aware prompts
└── models.py                 # ENHANCE: ClassStructure model
```

### Known Gotchas of our codebase & Library Quirks
```python
# CRITICAL: Tree-sitter queries are language-specific and case-sensitive
# Example: Python uses "class_definition" not "class_declaration"

# CRITICAL: SemanticElement extraction happens per-element, losing class context
# Current: Methods extracted individually without parent class info
# Needed: Class-method relationship preservation

# CRITICAL: Progressive prompting loses context between analysis and generation
# Current: Analysis stage outputs JSON, generation stage may lose class relationships
# Needed: Structured handoff with complete class information

# CRITICAL: LangChain LLMChain is deprecated
# Current: Uses deprecated LLMChain in generator.py:157
# Needed: Migration to RunnableSequence pattern

# CRITICAL: Pydantic v2 compatibility issues
# Current: Uses deprecated .dict() method
# Needed: Use .model_dump() instead
```

## Implementation Blueprint

### Data models and structure

Create enhanced models for class structure representation:
```python
# ADD to models.py
@dataclass
class ClassStructure:
    """Represents a complete class with all its methods and attributes"""
    name: str
    methods: List[SemanticElement]
    attributes: List[SemanticElement]
    docstring: Optional[str]
    start_line: int
    end_line: int
    file_path: str
    
    def to_unified_chunk(self) -> str:
        """Convert class structure to unified code chunk"""
        
@dataclass
class EnhancedCodeChunk:
    """Enhanced code chunk with class structure context"""
    original_chunk: CodeChunk
    class_structures: List[ClassStructure]
    is_complete_class: bool
    parent_class: Optional[str]
```

### List of tasks to be completed to fulfill the PRP in the order they should be completed

```yaml
Task 1:
ENHANCE src/spec_generator/parsers/tree_sitter_parser.py:
  - FIND pattern: "class TreeSitterParser"
  - ADD method: extract_class_structures() -> List[ClassStructure]
  - MODIFY: semantic_elements extraction to group by class
  - PRESERVE: existing SemanticElement interface

Task 2:
ENHANCE src/spec_generator/core/processor.py:
  - FIND pattern: "class ChunkProcessor"
  - ADD: class_aware_chunking() method
  - MODIFY: create_chunks() to preserve class boundaries
  - KEEP: existing memory management patterns

Task 3:
ENHANCE src/spec_generator/templates/prompts.py:
  - FIND pattern: "ANALYSIS_PROMPT"
  - MODIFY: Add class structure recognition instructions
  - ADD: class_structure_prompt template
  - PRESERVE: existing Japanese formatting patterns

Task 4:
ENHANCE src/spec_generator/core/generator.py:
  - FIND pattern: "class SpecificationGenerator"
  - MODIFY: _aggregate_analysis_results() for class grouping
  - FIX: Replace deprecated LLMChain with RunnableSequence
  - KEEP: progressive prompting strategy

Task 5:
CREATE tests/test_class_structure_recognition.py:
  - ADD: test_single_class_recognition()
  - ADD: test_class_method_association()
  - ADD: test_specification_quality()
  - MIRROR: existing test patterns from tests/test_integration.py
```

### Per task pseudocode as needed added to each task

```python
# Task 1: Enhanced Tree-sitter Parser
class TreeSitterParser:
    def extract_class_structures(self, code: str) -> List[ClassStructure]:
        """Extract complete class structures with method relationships"""
        # PATTERN: Use existing query system but aggregate by class
        class_query = """
        (class_definition
            name: (identifier) @class.name
            body: (block) @class.body) @class.def
        """
        
        method_query = """
        (function_definition
            name: (identifier) @method.name
            parameters: (parameters)? @method.params
            body: (block) @method.body) @method.def
        """
        
        # CRITICAL: Group methods by their parent class using line ranges
        classes = []
        for class_match in self.query(class_query):
            class_methods = self._extract_methods_in_range(
                class_match.start_line, class_match.end_line
            )
            classes.append(ClassStructure(
                name=class_match.name,
                methods=class_methods,
                # ... other attributes
            ))
        return classes

# Task 2: Class-aware Chunking
class ChunkProcessor:
    def class_aware_chunking(self, class_structures: List[ClassStructure]) -> List[EnhancedCodeChunk]:
        """Create chunks that preserve class boundaries"""
        # PATTERN: Use existing chunk size limits but respect class boundaries
        chunks = []
        for class_struct in class_structures:
            if class_struct.size < self.max_chunk_size:
                # Keep complete class in one chunk
                chunks.append(self._create_class_chunk(class_struct))
            else:
                # Split by methods but maintain class context
                chunks.extend(self._split_large_class(class_struct))
        return chunks

# Task 3: Enhanced Prompts
ENHANCED_ANALYSIS_PROMPT = """
あなたは日本のITエンジニアです。以下のコードを分析し、正確なクラス構造を特定してください。

重要な指示:
- 同じクラスのメソッドは必ず同じクラス名で関連付けてください
- "不明" や "推測" ではなく、実際のクラス名を使用してください
- メソッドとクラスの関係を明確に示してください

コード構造分析:
{code_chunk}

以下のJSON形式で回答してください:
{{
  "classes": [
    {{
      "name": "実際のクラス名",
      "methods": ["method1", "method2"],
      "purpose": "クラスの役割説明"
    }}
  ]
}}
"""

# Task 4: Enhanced Generator
class SpecificationGenerator:
    def _aggregate_analysis_results(self, analysis_results: List[dict]) -> dict:
        """Aggregate analysis results with class structure awareness"""
        # PATTERN: Group by class name instead of treating each method separately
        class_groups = defaultdict(list)
        for result in analysis_results:
            for class_info in result.get('classes', []):
                class_name = class_info['name']
                class_groups[class_name].append(class_info)
        
        # CRITICAL: Merge duplicate class entries
        unified_classes = []
        for class_name, class_infos in class_groups.items():
            unified_class = self._merge_class_infos(class_infos)
            unified_classes.append(unified_class)
        
        return {'unified_classes': unified_classes}
```

### Integration Points
```yaml
PARSING:
  - enhance: tree_sitter_parser.py query system
  - pattern: "Existing query infrastructure in _extract_semantic_elements"
  
CHUNKING:
  - modify: processor.py chunk creation
  - pattern: "Existing batch processing in LargeCodebaseProcessor"
  
PROMPTING:
  - enhance: prompts.py template system
  - pattern: "Existing Japanese formatting in JapanesePromptHelper"
  
GENERATION:
  - fix: generator.py deprecated LLMChain
  - pattern: "Existing progressive prompting strategy"
```

## Validation Loop

### Level 1: Syntax & Style
```bash
# Run these FIRST - fix any errors before proceeding
ruff check --fix src/spec_generator/parsers/tree_sitter_parser.py
ruff check --fix src/spec_generator/core/processor.py
ruff check --fix src/spec_generator/templates/prompts.py
ruff check --fix src/spec_generator/core/generator.py
mypy src/spec_generator/

# Expected: No errors. If errors, READ the error and fix.
```

### Level 2: Unit Tests each new feature/file/function use existing test patterns
```python
# CREATE tests/test_class_structure_recognition.py with these test cases:
def test_single_class_recognition():
    """Calculator class should be recognized as single entity"""
    parser = TreeSitterParser()
    code = open('samples/Python/test_sample.py').read()
    
    class_structures = parser.extract_class_structures(code)
    
    # Should find exactly one Calculator class
    assert len(class_structures) == 1
    calc_class = class_structures[0]
    assert calc_class.name == "Calculator"
    assert len(calc_class.methods) >= 8  # add, subtract, multiply, etc.

def test_class_method_association():
    """Methods should be correctly associated with Calculator class"""
    processor = ChunkProcessor()
    chunks = processor.class_aware_chunking(class_structures)
    
    # All Calculator methods should reference same class
    for chunk in chunks:
        if chunk.class_structures:
            assert all(cs.name == "Calculator" for cs in chunk.class_structures)

def test_specification_quality():
    """Generated specification should have accurate class representation"""
    generator = SpecificationGenerator()
    spec = generator.generate_specification('samples/Python/test_sample.py')
    
    # Should not contain ambiguous class names
    assert "不明" not in spec
    assert "推測" not in spec
    assert "Calculator" in spec
    # Should not duplicate Calculator class
    assert spec.count("Calculator") < 5  # Allow some repetition but not excessive
```

```bash
# Run and iterate until passing:
uv run pytest tests/test_class_structure_recognition.py -v
# If failing: Read error, understand root cause, fix code, re-run
```

### Level 3: Integration Test
```bash
# Test the enhanced generate command
uv run python -m spec_generator.cli generate samples/Python/test_sample.py --output test-enhanced-spec.md

# Validate specification quality
python -c "
import re
spec = open('test-enhanced-spec.md').read()
calculator_count = len(re.findall(r'Calculator', spec))
unknown_count = len(re.findall(r'不明', spec))
print(f'Calculator mentions: {calculator_count}')
print(f'Unknown mentions: {unknown_count}')
assert unknown_count == 0, 'Specification should not contain unknown classes'
assert calculator_count < 10, 'Calculator should not be excessively duplicated'
print('✓ Specification quality improved')
"
```

## Final validation Checklist
- [ ] All tests pass: `uv run pytest tests/ -v`
- [ ] No linting errors: `uv run ruff check src/`
- [ ] No type errors: `uv run mypy src/`
- [ ] Manual test successful: `uv run python -m spec_generator.cli generate samples/Python/test_sample.py`
- [ ] Generated spec has single Calculator class representation
- [ ] No "不明" or "推測" in generated specifications
- [ ] Mermaid diagrams show accurate class structure
- [ ] LangChain deprecation warnings resolved

---

## Anti-Patterns to Avoid
- ❌ Don't break existing chunk size limits - respect memory constraints
- ❌ Don't change Japanese output format - maintain cultural standards
- ❌ Don't ignore Tree-sitter language differences - Python vs JavaScript queries differ
- ❌ Don't create new data models without extending existing ones
- ❌ Don't remove progressive prompting - enhance it instead
- ❌ Don't fix only symptoms - address root cause of fragmented class recognition

## Confidence Score: 8/10

This PRP provides comprehensive context for successful implementation including:
- ✅ Detailed codebase analysis and patterns
- ✅ Specific files and methods to modify
- ✅ Executable validation gates
- ✅ Anti-patterns and gotchas
- ✅ Integration with existing architecture
- ✅ Progressive enhancement approach

The high confidence score reflects the thorough analysis of the existing codebase and clear implementation path that builds upon established patterns.