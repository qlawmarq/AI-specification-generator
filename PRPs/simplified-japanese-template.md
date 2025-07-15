name: "Simplified Japanese Specification Template Implementation"
description: |

## Purpose
Replace the current verbose Japanese specification template with a simplified version that reduces complexity while maintaining IT industry standards for Japanese documentation.

## Core Principles
1. **Context is King**: Include ALL necessary documentation, examples, and caveats
2. **Validation Loops**: Provide executable tests/lints the AI can run and fix
3. **Information Dense**: Use keywords and patterns from the codebase
4. **Progressive Success**: Start simple, validate, then enhance
5. **Global rules**: Be sure to follow all rules in CLAUDE.md

---

## Goal
Replace the current complex Japanese specification template with a simplified template that:
- Reduces document verbosity and removes unused elements
- Maintains Japanese IT industry standards
- Produces more focused and readable specifications
- Uses the specific template structure provided in TASK.md

## Why
- **Business value**: Current template is too verbose and contains many unused elements
- **User impact**: Generated specifications are more focused and easier to read
- **Integration**: Works with existing LangChain prompt system and generation pipeline
- **Problems solved**: Reduces noise in generated documents while maintaining essential structure

## What
Replace the existing template generation in `JapaneseSpecificationTemplate` and related prompt templates with a simplified structure that follows the new template format.

### Success Criteria
- [ ] New template generates documents with the specified 6-section structure
- [ ] All CLI commands produce specifications using the new template
- [ ] Generated documents are well-formed Japanese technical documents
- [ ] Mermaid diagrams are properly integrated
- [ ] Backward compatibility maintained for existing configurations

## All Needed Context

### Documentation & References (list all context needed to implement the feature)
```yaml
# MUST READ - Include these in your context window
- url: https://qiita.com/minimumskills/items/556e963c54e95c0a540a
  why: Japanese detailed design document structure and conventions
  
- url: https://qiita.com/y-some/items/90651c1e27f7798f87c6
  why: Best practices for writing design documents in Japanese IT industry
  
- file: src/spec_generator/templates/japanese_spec.py
  why: Current template implementation to understand existing patterns
  
- file: src/spec_generator/templates/prompts.py
  why: Current prompt templates that need to be updated for simplified format
  
- file: src/spec_generator/core/generator.py
  why: How templates are used in the generation pipeline
  
- file: src/spec_generator/core/updater.py
  why: How templates are used in the update pipeline
  
- docfile: TASK.md
  why: Contains the exact simplified template structure to implement

```

### Current Codebase tree (run `tree` in the root of the project) to get an overview of the codebase
```bash
AI-specification-generator/
├── src/spec_generator/
│   ├── templates/
│   │   ├── japanese_spec.py      # Current verbose template
│   │   └── prompts.py            # Current prompt templates
│   ├── core/
│   │   ├── generator.py          # Uses JapaneseSpecificationTemplate
│   │   └── updater.py            # Uses template for updates
│   ├── cli.py                    # CLI commands that trigger template usage
│   └── models.py                 # Data models
├── tests/
│   ├── test_generator.py         # Tests for generation functionality
│   └── test_cli.py              # CLI integration tests
└── TASK.md                      # New template specification
```

### Desired Codebase tree with files to be modified and responsibility of file
```bash
# NO NEW FILES NEEDED - MODIFY EXISTING:
src/spec_generator/templates/japanese_spec.py    # Replace template structure
src/spec_generator/templates/prompts.py          # Update prompt templates
# Tests will automatically use new template through existing test patterns
```

### Known Gotchas of our codebase & Library Quirks
```python
# CRITICAL: LangChain PromptTemplate requires exact input_variables match
# Current prompts.py uses specific variable names that must be preserved
# Example: JAPANESE_SPEC_PROMPT expects: analysis_results, document_title, project_overview, technical_requirements

# CRITICAL: JapaneseSpecificationTemplate.generate_complete_document expects specific document_data structure
# Must preserve the existing interface while changing internal implementation

# CRITICAL: Updater.py depends on specific section patterns for document parsing
# Section names like "詳細設計", "システム構成" are used for update targeting

# CRITICAL: CLI testing requires actual output verification
# Tests in test_cli.py execute commands and check output format

# CRITICAL: Template uses Japanese encoding (UTF-8) throughout
# All string handling must preserve Japanese characters properly

# CRITICAL: Mermaid diagram syntax must be properly escaped in markdown
# The new template requires Mermaid classDiagram, sequenceDiagram, flowchart syntax
```

## Implementation Blueprint

### Data models and structure

The core data models remain unchanged - we're modifying template output, not data structures:
```python
# Existing models in models.py remain the same:
# - SpecificationOutput
# - ProcessingStats  
# - CodeChunk
# - SpecificationConfig

# Template interface must remain compatible:
class JapaneseSpecificationTemplate:
    def generate_complete_document(self, document_data: dict[str, Any]) -> str:
        # Must still accept same document_data structure
        # But generate simplified output format
```

### list of tasks to be completed to fullfill the PRP in the order they should be completed

```yaml
Task 1: 
MODIFY src/spec_generator/templates/japanese_spec.py:
  - FIND: generate_complete_document method
  - REPLACE: Current 6-section verbose template with simplified 6-section template from TASK.md
  - PRESERVE: Method signature and document_data structure interface
  - ADD: Mermaid diagram generation for architecture and sequence diagrams

Task 2:
MODIFY src/spec_generator/templates/prompts.py:
  - FIND: JAPANESE_SPEC_PROMPT template
  - UPDATE: Output format instructions to match new simplified template
  - PRESERVE: All input_variables (analysis_results, document_title, project_overview, technical_requirements)
  - ADD: Instructions for Mermaid diagram generation

Task 3:
TEST CLI commands to verify simplified template output:
  - RUN: uv run python -m spec_generator.cli generate-single tests/fixtures/sample_code/sample.py --output test-simplified.md
  - VERIFY: Output follows new 6-section format
  - CHECK: Japanese technical terminology is preserved
  - CONFIRM: Mermaid diagrams are properly formatted

Task 4:
RUN existing unit tests and fix any breaking changes:
  - EXECUTE: uv run pytest tests/test_generator.py -v
  - FIX: Any test failures related to template structure changes
  - PRESERVE: All existing test logic, only update expected output formats

Task 5:
VERIFY full system integration:
  - TEST: uv run python -m spec_generator.cli generate src --output test-full-spec --project-name "テストシステム" --timeout 10
  - VERIFY: Generated specification uses simplified template
  - CHECK: All sections are properly populated with content
  - CONFIRM: Document is valid Japanese technical documentation
```


### Per task pseudocode as needed added to each task

```python
# Task 1: Template Replacement
def generate_complete_document(self, document_data: dict[str, Any]) -> str:
    """Generate simplified specification document."""
    sections = []
    
    # Header (preserve existing)
    sections.append(self.generate_header(document_data.get("document_type", "詳細設計書")))
    
    # 1. 概要 - Simplified overview
    sections.append("""## 1. 概要

- システム概要
- 対象範囲（ファイル）
- 前提条件・制約事項（もし必要な場合）
""")
    
    # 2. アーキテクチャ設計 - With Mermaid diagrams
    sections.append(self._generate_architecture_section_with_mermaid(document_data))
    
    # 3. クラス・メソッド設計 - Tabular format
    sections.append(self._generate_class_method_section_simplified(document_data))
    
    # 4. インターフェース設計 - API specs
    sections.append(self._generate_interface_section(document_data))
    
    # 5. データ設計 - Data structures
    sections.append(self._generate_data_design_section(document_data))
    
    # 6. 処理設計 - Processing flows with Mermaid
    sections.append(self._generate_processing_section_with_mermaid(document_data))
    
    return "\n\n".join(sections)

# Task 2: Prompt Template Update
JAPANESE_SPEC_PROMPT = PromptTemplate(
    input_variables=["analysis_results", "document_title", "project_overview", "technical_requirements"],
    template="""あなたは日本のIT業界で活躍する技術文書作成のエキスパートです。
以下の分析結果を基に、簡潔で実用的な詳細設計書を作成してください。

## 出力形式:
以下の6つのセクションに従って、詳細設計書をMarkdown形式で作成してください：

## 1. 概要
- システム概要
- 対象範囲（ファイル）
- 前提条件・制約事項（もし必要な場合）

## 2. アーキテクチャ設計
- システム構成図（Mermaidで作成）
- 処理フロー概要
- 主要コンポーネント間の関係
- 関連するファイルや処理・呼び出されるメソッド・呼び出し元のメソッド

## 3. クラス・メソッド設計
### 3.1 クラス・メソッド一覧表
| クラス名 | 役割 | 主要メソッド | 備考 |
| -------- | ---- | ------------ | ---- |

### 3.2 クラス・メソッド詳細仕様
各クラス・メソッドについて詳細を記載

## 4. インターフェース設計
- API 仕様
- 入出力データ形式
- エラーレスポンス仕様

## 5. データ設計
- データ構造
- データベーステーブル設計（該当する場合）
- データフロー図

## 6. 処理設計
### 6.1 主要処理フロー
- シーケンス図での表現（Mermaid sequenceDiagram使用）
- 処理ステップの詳細説明

【重要】
- 日本語で記述してください
- 図表は Mermaid 記法で作成してください
- 実装の詳細まで踏み込んで説明してください
- 保守性・拡張性の観点も含めてください"""
)
```

### Integration Points
```yaml
CLI_COMMANDS:
  - generate: Uses JapaneseSpecificationTemplate.generate_complete_document
  - generate-single: Uses same template for single file processing
  - update: Uses template sections for incremental updates
  
TEMPLATE_USAGE:
  - generator.py: Calls template.generate_complete_document(document_data)
  - updater.py: Parses sections by Japanese names like "詳細設計"
  
PROMPT_CHAIN:
  - ANALYSIS_PROMPT (unchanged): Analyzes code into structured JSON
  - JAPANESE_SPEC_PROMPT (modified): Generates specification using new template
  - UPDATE_SPEC_PROMPT (unchanged): Updates existing specifications
```

## Validation Loop

### Level 1: Syntax & Style
```bash
# Run these FIRST - fix any errors before proceeding
ruff check src/spec_generator/templates/japanese_spec.py --fix
mypy src/spec_generator/templates/japanese_spec.py
ruff check src/spec_generator/templates/prompts.py --fix
mypy src/spec_generator/templates/prompts.py

# Expected: No errors. If errors, READ the error and fix.
```

### Level 2: Unit Tests each new feature/file/function use existing test patterns
```python
# UPDATE test_generator.py to verify new template output:
def test_simplified_template_structure():
    """Verify new template generates 6 required sections"""
    generator = SpecificationGenerator(test_config)
    output = await generator.generate_specification(test_chunks, "テストプロジェクト")
    
    # Check for required sections
    assert "## 1. 概要" in output.content
    assert "## 2. アーキテクチャ設計" in output.content
    assert "## 3. クラス・メソッド設計" in output.content
    assert "## 4. インターフェース設計" in output.content
    assert "## 5. データ設計" in output.content
    assert "## 6. 処理設計" in output.content

def test_mermaid_diagrams_included():
    """Verify Mermaid diagrams are properly formatted"""
    generator = SpecificationGenerator(test_config)
    output = await generator.generate_specification(test_chunks, "テストプロジェクト")
    
    # Check for Mermaid syntax
    assert "```mermaid" in output.content
    assert "classDiagram" in output.content or "sequenceDiagram" in output.content
```

```bash
# Run and iterate until passing:
uv run pytest tests/test_generator.py -v
# If failing: Read error, understand root cause, fix code, re-run
```

### Level 3: Integration Test
```bash
# Test CLI with simplified template
uv run python -m spec_generator.cli config-info
uv run python -m spec_generator.cli install-parsers

# Test single file generation
uv run python -m spec_generator.cli generate-single tests/fixtures/sample_code/sample.py --output test-single-simplified.md

# Expected: File generated with 6-section structure
cat test-single-simplified.md | grep -E "^## [1-6]\."

# Test full generation with timeout
uv run python -m spec_generator.cli generate src --output test-full-simplified --project-name "テストシステム" --timeout 10

# Expected: Specifications generated in test-full-simplified directory
ls test-full-simplified/
```

## Final validation Checklist
- [ ] All tests pass: `uv run pytest tests/ -v`
- [ ] No linting errors: `uv run ruff check src/`
- [ ] No type errors: `uv run mypy src/`
- [ ] CLI generate-single produces simplified template: `cat test-single-simplified.md`
- [ ] CLI generate produces simplified specifications with timeout
- [ ] Generated documents contain all 6 required sections
- [ ] Mermaid diagrams are properly formatted
- [ ] Japanese technical terminology is preserved
- [ ] Update command still works with new template structure

---

## Anti-Patterns to Avoid
- ❌ Don't change the document_data interface - preserve backward compatibility
- ❌ Don't remove Japanese IT terminology - maintain industry standards
- ❌ Don't break existing section parsing logic in updater.py
- ❌ Don't ignore Mermaid diagram syntax requirements
- ❌ Don't skip CLI testing - must verify actual output
- ❌ Don't hardcode section content - use dynamic data from analysis

## Confidence Level: 9/10

**High confidence** because:
1. Clear requirements in TASK.md with exact template structure
2. Well-understood existing codebase patterns
3. Preserved interfaces ensure backward compatibility  
4. Japanese IT documentation standards researched
5. Comprehensive validation steps ensure working implementation
6. Existing test patterns can be adapted for validation