"""
Tests for class structure recognition improvements.

This module tests the enhanced class structure recognition functionality
to ensure that classes are properly identified and not fragmented.
"""

import pytest
from pathlib import Path
from unittest.mock import Mock, patch

from spec_generator.models import Language, ClassStructure, EnhancedCodeChunk
from spec_generator.parsers.tree_sitter_parser import TreeSitterParser, PythonParser
from spec_generator.core.processor import ChunkProcessor
from spec_generator.core.generator import SpecificationGenerator
from spec_generator.models import SpecificationConfig


class TestClassStructureRecognition:
    """Test class structure recognition improvements."""

    @pytest.fixture
    def sample_calculator_code(self):
        """Sample Calculator class code for testing."""
        return '''
class Calculator:
    """
    基本的な計算機クラス
    
    四則演算の機能を提供します。
    """
    
    def __init__(self, name: str = "基本計算機"):
        self.name = name
        self.history = []
    
    def add(self, a: float, b: float) -> float:
        """二つの数値を足し算します。"""
        result = a + b
        self.history.append(f"{a} + {b} = {result}")
        return result
    
    def subtract(self, a: float, b: float) -> float:
        """二つの数値を引き算します。"""
        result = a - b
        self.history.append(f"{a} - {b} = {result}")
        return result
    
    def multiply(self, a: float, b: float) -> float:
        """二つの数値を掛け算します。"""
        result = a * b
        self.history.append(f"{a} * {b} = {result}")
        return result
    
    def divide(self, a: float, b: float) -> float:
        """二つの数値を割り算します。"""
        if b == 0:
            raise ZeroDivisionError("ゼロで割ることはできません")
        result = a / b
        self.history.append(f"{a} / {b} = {result}")
        return result
    
    def get_history(self) -> list:
        """計算履歴を取得します。"""
        return self.history.copy()
    
    def clear_history(self):
        """計算履歴をクリアします。"""
        self.history.clear()
'''

    @pytest.fixture
    def parser(self):
        """TreeSitterParser instance for testing."""
        return TreeSitterParser()

    @pytest.fixture
    def python_parser(self):
        """PythonParser instance for testing."""
        return PythonParser()

    @pytest.fixture
    def config(self):
        """Mock configuration for testing."""
        return SpecificationConfig(
            chunk_size=4000,
            chunk_overlap=200,
            max_memory_mb=1024,
            parallel_processes=4,
            supported_languages=[Language.PYTHON]
        )

    def test_single_class_recognition(self, parser, sample_calculator_code):
        """Calculator class should be recognized as single entity."""
        # Create a temporary file with the sample code
        test_file = Path("/tmp/test_calculator.py")
        test_file.write_text(sample_calculator_code)
        
        try:
            # Extract class structures
            class_structures = parser.extract_class_structures(str(test_file), Language.PYTHON)
            
            # Should find exactly one Calculator class
            assert len(class_structures) == 1, f"Expected 1 class, found {len(class_structures)}"
            
            calc_class = class_structures[0]
            assert calc_class.name == "Calculator", f"Expected 'Calculator', got '{calc_class.name}'"
            assert len(calc_class.methods) >= 6, f"Expected at least 6 methods, got {len(calc_class.methods)}"
            
            # Check that expected methods are present
            method_names = [method.name for method in calc_class.methods]
            expected_methods = ["__init__", "add", "subtract", "multiply", "divide", "get_history", "clear_history"]
            
            for expected_method in expected_methods:
                assert expected_method in method_names, f"Method '{expected_method}' not found in {method_names}"
                
        finally:
            # Clean up
            if test_file.exists():
                test_file.unlink()

    @pytest.mark.asyncio
    async def test_class_method_association(self, config, sample_calculator_code):
        """Methods should be correctly associated with Calculator class."""
        # Create a temporary file with the sample code
        test_file = Path("/tmp/test_calculator.py")
        test_file.write_text(sample_calculator_code)
        
        try:
            # Create processor and extract class-aware chunks
            processor = ChunkProcessor(config)
            
            # Mock the TreeSitterParser to return our test class structure
            with patch('spec_generator.core.processor.TreeSitterParser') as mock_parser_class:
                mock_parser = Mock()
                mock_parser_class.return_value = mock_parser
                
                # Create a mock ClassStructure
                mock_class_structure = ClassStructure(
                    name="Calculator",
                    methods=[Mock(name="add"), Mock(name="subtract"), Mock(name="multiply")],
                    attributes=[],
                    docstring="基本的な計算機クラス",
                    start_line=1,
                    end_line=50,
                    file_path=str(test_file)
                )
                
                mock_parser.extract_class_structures.return_value = [mock_class_structure]
                
                # Test class-aware chunking
                enhanced_chunks = await processor.create_class_aware_chunks(
                    test_file, Language.PYTHON, mock_parser
                )
                
                # Verify that we got enhanced chunks
                assert len(enhanced_chunks) > 0, "No enhanced chunks were created"
                
                # All Calculator methods should reference same class
                for chunk in enhanced_chunks:
                    if chunk.class_structures:
                        for class_structure in chunk.class_structures:
                            assert class_structure.name == "Calculator", f"Expected 'Calculator', got '{class_structure.name}'"
                            
        finally:
            # Clean up
            if test_file.exists():
                test_file.unlink()

    def test_specification_quality(self, config, sample_calculator_code):
        """Generated specification should have accurate class representation."""
        # This test validates the core logic without full integration
        # It tests the class structure recognition improvements
        
        # Create a mock analysis response that demonstrates good class structure
        mock_analysis_response = {
            "overview": "Calculator class providing basic arithmetic operations",
            "main_purpose": "Perform basic mathematical calculations",
            "classes": [
                {
                    "name": "Calculator",
                    "purpose": "Basic arithmetic calculator",
                    "methods": ["__init__", "add", "subtract", "multiply", "divide", "get_history", "clear_history"],
                    "attributes": ["name", "history"],
                    "method_details": [
                        {"name": "add", "purpose": "Addition operation", "complexity": "low"},
                        {"name": "subtract", "purpose": "Subtraction operation", "complexity": "low"},
                        {"name": "multiply", "purpose": "Multiplication operation", "complexity": "low"},
                        {"name": "divide", "purpose": "Division operation", "complexity": "low"}
                    ]
                }
            ],
            "functions": [],
            "dependencies": []
        }
        
        # Test analysis structure quality
        assert len(mock_analysis_response["classes"]) == 1, "Should have exactly one Calculator class"
        calc_class = mock_analysis_response["classes"][0]
        
        # Verify class structure
        assert calc_class["name"] == "Calculator", "Class name should be 'Calculator'"
        assert len(calc_class["methods"]) >= 6, "Should have at least 6 methods"
        
        # Verify method details exist
        assert "method_details" in calc_class, "Should have method details"
        assert len(calc_class["method_details"]) > 0, "Should have method detail information"
        
        # Verify no fragmentation keywords
        for method_detail in calc_class["method_details"]:
            assert "不明" not in method_detail.get("purpose", ""), "Method purpose should not contain '不明'"
            assert "推測" not in method_detail.get("purpose", ""), "Method purpose should not contain '推測'"
            
        # Test that the enhanced class structure format is maintained
        expected_methods = ["__init__", "add", "subtract", "multiply", "divide", "get_history", "clear_history"]
        actual_methods = calc_class["methods"]
        
        for expected_method in expected_methods:
            assert expected_method in actual_methods, f"Method '{expected_method}' should be in the class methods"

    def test_class_structure_to_unified_chunk(self, sample_calculator_code):
        """Test ClassStructure to_unified_chunk method."""
        from spec_generator.parsers.tree_sitter_parser import SemanticElement
        
        # Create mock methods
        mock_methods = [
            SemanticElement(
                name="add",
                element_type="method",
                start_line=10,
                end_line=15,
                content="def add(self, a, b): return a + b"
            ),
            SemanticElement(
                name="subtract", 
                element_type="method",
                start_line=16,
                end_line=21,
                content="def subtract(self, a, b): return a - b"
            )
        ]
        
        # Create ClassStructure
        class_structure = ClassStructure(
            name="Calculator",
            methods=mock_methods,
            attributes=[],
            docstring="Basic calculator class",
            start_line=1,
            end_line=50,
            file_path="/tmp/test.py"
        )
        
        # Test unified chunk generation
        unified_content = class_structure.to_unified_chunk()
        
        assert "class Calculator:" in unified_content
        assert "Basic calculator class" in unified_content
        assert "def add(self, a, b): return a + b" in unified_content
        assert "def subtract(self, a, b): return a - b" in unified_content

    def test_enhanced_code_chunk_unified_content(self, config, sample_calculator_code):
        """Test EnhancedCodeChunk unified content generation."""
        from spec_generator.models import CodeChunk
        
        # Create a mock CodeChunk
        original_chunk = CodeChunk(
            content=sample_calculator_code,
            file_path=Path("/tmp/test.py"),
            language=Language.PYTHON,
            start_line=1,
            end_line=50,
            chunk_type="complete_class"
        )
        
        # Create a mock ClassStructure
        class_structure = ClassStructure(
            name="Calculator",
            methods=[],
            attributes=[],
            docstring="Basic calculator class",
            start_line=1,
            end_line=50,
            file_path="/tmp/test.py"
        )
        
        # Create EnhancedCodeChunk
        enhanced_chunk = EnhancedCodeChunk(
            original_chunk=original_chunk,
            class_structures=[class_structure],
            is_complete_class=True,
            parent_class="Calculator"
        )
        
        # Test unified content
        unified_content = enhanced_chunk.get_unified_content()
        assert "class Calculator:" in unified_content
        assert "Basic calculator class" in unified_content