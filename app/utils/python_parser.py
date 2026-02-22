"""
AST-based Python file parser for code documentation analysis.

This module provides functionality to parse Python source files using the
Abstract Syntax Tree (AST) and extract information about classes, methods,
and functions, including their docstrings.
"""

import ast
from dataclasses import dataclass
from typing import List, Optional, Dict, Any
from pathlib import Path


@dataclass
class FunctionInfo:
    """
    Information about a function or method extracted from Python code.
    
    Attributes:
        name: The name of the function or method
        line_number: The line number where the function is defined
        docstring: The docstring content, or None if not present
        is_method: True if this is a class method, False if it's a standalone function
        class_name: The name of the containing class (only for methods)
        parameters: List of parameter names
        is_async: True if this is an async function
    """
    name: str
    line_number: int
    docstring: Optional[str]
    is_method: bool
    class_name: Optional[str] = None
    parameters: List[str] = None
    is_async: bool = False
    
    def __post_init__(self):
        """Initialize default values for mutable fields."""
        if self.parameters is None:
            self.parameters = []


@dataclass
class ClassInfo:
    """
    Information about a class extracted from Python code.
    
    Attributes:
        name: The name of the class
        line_number: The line number where the class is defined
        docstring: The docstring content, or None if not present
        methods: List of methods defined in the class
        base_classes: List of base class names
    """
    name: str
    line_number: int
    docstring: Optional[str]
    methods: List[FunctionInfo] = None
    base_classes: List[str] = None
    
    def __post_init__(self):
        """Initialize default values for mutable fields."""
        if self.methods is None:
            self.methods = []
        if self.base_classes is None:
            self.base_classes = []


@dataclass
class ParseResult:
    """
    Result of parsing a Python file.
    
    Attributes:
        file_path: Path to the parsed file
        classes: List of classes found in the file
        functions: List of standalone functions found in the file
        parse_error: Error message if parsing failed, None otherwise
    """
    file_path: str
    classes: List[ClassInfo] = None
    functions: List[FunctionInfo] = None
    parse_error: Optional[str] = None
    
    def __post_init__(self):
        """Initialize default values for mutable fields."""
        if self.classes is None:
            self.classes = []
        if self.functions is None:
            self.functions = []


class PythonFileParser:
    """
    Parser for Python source files using AST.
    
    This class provides methods to parse Python files and extract information
    about classes, methods, and functions, including their docstrings.
    """
    
    def parse_file(self, file_path: str) -> ParseResult:
        """
        Parse a Python file and extract class and function information.
        
        Args:
            file_path: Path to the Python file to parse
            
        Returns:
            ParseResult containing extracted information or error details
            
        Raises:
            FileNotFoundError: If the specified file does not exist
        """
        path = Path(file_path)
        
        if not path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")
        
        try:
            with open(path, 'r', encoding='utf-8') as f:
                source_code = f.read()
            
            tree = ast.parse(source_code, filename=str(path))
            
            classes = []
            functions = []
            
            for node in ast.walk(tree):
                if isinstance(node, ast.ClassDef):
                    class_info = self._extract_class_info(node)
                    classes.append(class_info)
                elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    # Only extract top-level functions (not methods)
                    if self._is_top_level_function(node, tree):
                        function_info = self._extract_function_info(node)
                        functions.append(function_info)
            
            return ParseResult(
                file_path=str(path),
                classes=classes,
                functions=functions
            )
            
        except SyntaxError as e:
            return ParseResult(
                file_path=str(path),
                parse_error=f"Syntax error: {str(e)}"
            )
        except Exception as e:
            return ParseResult(
                file_path=str(path),
                parse_error=f"Parse error: {str(e)}"
            )
    
    def _extract_class_info(self, node: ast.ClassDef) -> ClassInfo:
        """
        Extract information from a class definition node.
        
        Args:
            node: AST ClassDef node
            
        Returns:
            ClassInfo object with extracted information
        """
        docstring = ast.get_docstring(node)
        
        # Extract base classes
        base_classes = []
        for base in node.bases:
            if isinstance(base, ast.Name):
                base_classes.append(base.id)
            elif isinstance(base, ast.Attribute):
                base_classes.append(self._get_attribute_name(base))
        
        # Extract methods
        methods = []
        for item in node.body:
            if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                method_info = self._extract_function_info(item, is_method=True, class_name=node.name)
                methods.append(method_info)
        
        return ClassInfo(
            name=node.name,
            line_number=node.lineno,
            docstring=docstring,
            methods=methods,
            base_classes=base_classes
        )
    
    def _extract_function_info(
        self,
        node: ast.FunctionDef | ast.AsyncFunctionDef,
        is_method: bool = False,
        class_name: Optional[str] = None
    ) -> FunctionInfo:
        """
        Extract information from a function or method definition node.
        
        Args:
            node: AST FunctionDef or AsyncFunctionDef node
            is_method: True if this is a class method
            class_name: Name of the containing class (for methods)
            
        Returns:
            FunctionInfo object with extracted information
        """
        docstring = ast.get_docstring(node)
        
        # Extract parameter names
        parameters = []
        if node.args.args:
            parameters = [arg.arg for arg in node.args.args]
        
        return FunctionInfo(
            name=node.name,
            line_number=node.lineno,
            docstring=docstring,
            is_method=is_method,
            class_name=class_name,
            parameters=parameters,
            is_async=isinstance(node, ast.AsyncFunctionDef)
        )
    
    def _is_top_level_function(self, node: ast.FunctionDef | ast.AsyncFunctionDef, tree: ast.Module) -> bool:
        """
        Check if a function is defined at the top level (not inside a class).
        
        Args:
            node: Function node to check
            tree: The module AST tree
            
        Returns:
            True if the function is at the top level, False otherwise
        """
        for item in tree.body:
            if item is node:
                return True
            if isinstance(item, ast.ClassDef):
                for class_item in item.body:
                    if class_item is node:
                        return False
        return False
    
    def _get_attribute_name(self, node: ast.Attribute) -> str:
        """
        Get the full name of an attribute node.
        
        Args:
            node: AST Attribute node
            
        Returns:
            String representation of the attribute
        """
        if isinstance(node.value, ast.Name):
            return f"{node.value.id}.{node.attr}"
        elif isinstance(node.value, ast.Attribute):
            return f"{self._get_attribute_name(node.value)}.{node.attr}"
        return node.attr
    
    def parse_directory(self, directory_path: str, recursive: bool = True) -> List[ParseResult]:
        """
        Parse all Python files in a directory.
        
        Args:
            directory_path: Path to the directory to parse
            recursive: If True, parse subdirectories recursively
            
        Returns:
            List of ParseResult objects for each Python file found
            
        Raises:
            FileNotFoundError: If the directory does not exist
        """
        path = Path(directory_path)
        
        if not path.exists():
            raise FileNotFoundError(f"Directory not found: {directory_path}")
        
        if not path.is_dir():
            raise ValueError(f"Not a directory: {directory_path}")
        
        results = []
        
        pattern = "**/*.py" if recursive else "*.py"
        for py_file in path.glob(pattern):
            if py_file.is_file():
                result = self.parse_file(str(py_file))
                results.append(result)
        
        return results
