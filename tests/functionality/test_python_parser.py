"""
Unit tests for the Python file parser.

This module contains tests for the AST-based Python parser that extracts
classes, methods, and functions from Python source files.
"""

import pytest
import tempfile
from pathlib import Path
from app.utils.python_parser import (
    PythonFileParser,
    ParseResult,
    ClassInfo,
    FunctionInfo
)


@pytest.fixture
def parser():
    """Create a PythonFileParser instance for testing."""
    return PythonFileParser()


@pytest.fixture
def temp_python_file():
    """Create a temporary Python file for testing."""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False, encoding='utf-8') as f:
        yield f
    Path(f.name).unlink(missing_ok=True)


class TestPythonFileParser:
    """Test suite for PythonFileParser class."""
    
    def test_parse_simple_function(self, parser, temp_python_file):
        """Test parsing a file with a simple function."""
        code = '''
def hello_world():
    """Say hello to the world."""
    return "Hello, World!"
'''
        temp_python_file.write(code)
        temp_python_file.flush()
        
        result = parser.parse_file(temp_python_file.name)
        
        assert result.parse_error is None
        assert len(result.functions) == 1
        assert len(result.classes) == 0
        
        func = result.functions[0]
        assert func.name == "hello_world"
        assert func.docstring == "Say hello to the world."
        assert func.is_method is False
        assert func.is_async is False
    
    def test_parse_function_without_docstring(self, parser, temp_python_file):
        """Test parsing a function without a docstring."""
        code = '''
def no_docs():
    return 42
'''
        temp_python_file.write(code)
        temp_python_file.flush()
        
        result = parser.parse_file(temp_python_file.name)
        
        assert result.parse_error is None
        assert len(result.functions) == 1
        
        func = result.functions[0]
        assert func.name == "no_docs"
        assert func.docstring is None
    
    def test_parse_async_function(self, parser, temp_python_file):
        """Test parsing an async function."""
        code = '''
async def fetch_data():
    """Fetch data asynchronously."""
    return await some_async_call()
'''
        temp_python_file.write(code)
        temp_python_file.flush()
        
        result = parser.parse_file(temp_python_file.name)
        
        assert result.parse_error is None
        assert len(result.functions) == 1
        
        func = result.functions[0]
        assert func.name == "fetch_data"
        assert func.is_async is True
        assert func.docstring == "Fetch data asynchronously."
    
    def test_parse_function_with_parameters(self, parser, temp_python_file):
        """Test parsing a function with parameters."""
        code = '''
def add(a, b, c=0):
    """Add three numbers."""
    return a + b + c
'''
        temp_python_file.write(code)
        temp_python_file.flush()
        
        result = parser.parse_file(temp_python_file.name)
        
        assert result.parse_error is None
        assert len(result.functions) == 1
        
        func = result.functions[0]
        assert func.name == "add"
        assert func.parameters == ["a", "b", "c"]
    
    def test_parse_simple_class(self, parser, temp_python_file):
        """Test parsing a file with a simple class."""
        code = '''
class MyClass:
    """A simple test class."""
    
    def __init__(self):
        """Initialize the class."""
        pass
    
    def method_one(self):
        """First method."""
        pass
'''
        temp_python_file.write(code)
        temp_python_file.flush()
        
        result = parser.parse_file(temp_python_file.name)
        
        assert result.parse_error is None
        assert len(result.classes) == 1
        assert len(result.functions) == 0
        
        cls = result.classes[0]
        assert cls.name == "MyClass"
        assert cls.docstring == "A simple test class."
        assert len(cls.methods) == 2
        
        init_method = cls.methods[0]
        assert init_method.name == "__init__"
        assert init_method.docstring == "Initialize the class."
        assert init_method.is_method is True
        assert init_method.class_name == "MyClass"
        
        method_one = cls.methods[1]
        assert method_one.name == "method_one"
        assert method_one.docstring == "First method."
    
    def test_parse_class_without_docstring(self, parser, temp_python_file):
        """Test parsing a class without a docstring."""
        code = '''
class NoDocsClass:
    def method(self):
        pass
'''
        temp_python_file.write(code)
        temp_python_file.flush()
        
        result = parser.parse_file(temp_python_file.name)
        
        assert result.parse_error is None
        assert len(result.classes) == 1
        
        cls = result.classes[0]
        assert cls.name == "NoDocsClass"
        assert cls.docstring is None
        assert len(cls.methods) == 1
    
    def test_parse_class_with_inheritance(self, parser, temp_python_file):
        """Test parsing a class with base classes."""
        code = '''
class Parent:
    """Parent class."""
    pass

class Child(Parent):
    """Child class."""
    pass
'''
        temp_python_file.write(code)
        temp_python_file.flush()
        
        result = parser.parse_file(temp_python_file.name)
        
        assert result.parse_error is None
        assert len(result.classes) == 2
        
        parent = result.classes[0]
        assert parent.name == "Parent"
        assert len(parent.base_classes) == 0
        
        child = result.classes[1]
        assert child.name == "Child"
        assert len(child.base_classes) == 1
        assert child.base_classes[0] == "Parent"
    
    def test_parse_mixed_content(self, parser, temp_python_file):
        """Test parsing a file with both classes and functions."""
        code = '''
"""Module docstring."""

def standalone_function():
    """A standalone function."""
    pass

class MyClass:
    """A class."""
    
    def method(self):
        """A method."""
        pass

def another_function():
    """Another standalone function."""
    pass
'''
        temp_python_file.write(code)
        temp_python_file.flush()
        
        result = parser.parse_file(temp_python_file.name)
        
        assert result.parse_error is None
        assert len(result.functions) == 2
        assert len(result.classes) == 1
        
        assert result.functions[0].name == "standalone_function"
        assert result.functions[1].name == "another_function"
        assert result.classes[0].name == "MyClass"
    
    def test_parse_syntax_error(self, parser, temp_python_file):
        """Test parsing a file with syntax errors."""
        code = '''
def broken_function(
    # Missing closing parenthesis
    pass
'''
        temp_python_file.write(code)
        temp_python_file.flush()
        
        result = parser.parse_file(temp_python_file.name)
        
        assert result.parse_error is not None
        assert "Syntax error" in result.parse_error
    
    def test_parse_nonexistent_file(self, parser):
        """Test parsing a file that doesn't exist."""
        with pytest.raises(FileNotFoundError):
            parser.parse_file("/nonexistent/file.py")
    
    def test_parse_empty_file(self, parser, temp_python_file):
        """Test parsing an empty file."""
        temp_python_file.write("")
        temp_python_file.flush()
        
        result = parser.parse_file(temp_python_file.name)
        
        assert result.parse_error is None
        assert len(result.functions) == 0
        assert len(result.classes) == 0
    
    def test_parse_file_with_only_comments(self, parser, temp_python_file):
        """Test parsing a file with only comments."""
        code = '''
# This is a comment
# Another comment
'''
        temp_python_file.write(code)
        temp_python_file.flush()
        
        result = parser.parse_file(temp_python_file.name)
        
        assert result.parse_error is None
        assert len(result.functions) == 0
        assert len(result.classes) == 0
    
    def test_parse_directory(self, parser):
        """Test parsing all Python files in a directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)
            
            # Create test files
            file1 = tmpdir_path / "file1.py"
            file1.write_text('''
def func1():
    """Function 1."""
    pass
''')
            
            file2 = tmpdir_path / "file2.py"
            file2.write_text('''
class Class1:
    """Class 1."""
    pass
''')
            
            # Create subdirectory
            subdir = tmpdir_path / "subdir"
            subdir.mkdir()
            file3 = subdir / "file3.py"
            file3.write_text('''
def func2():
    """Function 2."""
    pass
''')
            
            # Parse directory recursively
            results = parser.parse_directory(str(tmpdir_path), recursive=True)
            
            assert len(results) == 3
            
            # Verify all files were parsed
            file_names = {Path(r.file_path).name for r in results}
            assert file_names == {"file1.py", "file2.py", "file3.py"}
    
    def test_parse_directory_non_recursive(self, parser):
        """Test parsing Python files in a directory without recursion."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)
            
            # Create test files
            file1 = tmpdir_path / "file1.py"
            file1.write_text('def func1(): pass')
            
            # Create subdirectory with file
            subdir = tmpdir_path / "subdir"
            subdir.mkdir()
            file2 = subdir / "file2.py"
            file2.write_text('def func2(): pass')
            
            # Parse directory non-recursively
            results = parser.parse_directory(str(tmpdir_path), recursive=False)
            
            assert len(results) == 1
            assert Path(results[0].file_path).name == "file1.py"
    
    def test_parse_directory_nonexistent(self, parser):
        """Test parsing a directory that doesn't exist."""
        with pytest.raises(FileNotFoundError):
            parser.parse_directory("/nonexistent/directory")
    
    def test_parse_directory_not_a_directory(self, parser, temp_python_file):
        """Test parsing when path is not a directory."""
        temp_python_file.write("def func(): pass")
        temp_python_file.flush()
        
        with pytest.raises(ValueError):
            parser.parse_directory(temp_python_file.name)
