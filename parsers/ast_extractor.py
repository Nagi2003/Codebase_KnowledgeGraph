import ast
import os
from typing import Dict, List, Any, Optional
from dataclasses import dataclass

@dataclass
class FunctionInfo:
    name: str
    args: List[str]
    docstring: Optional[str]
    calls: List[str]
    lineno: int
    returns: Optional[str]

@dataclass
class ClassInfo:
    name: str
    bases: List[str]
    methods: List[FunctionInfo]
    docstring: Optional[str]
    lineno: int

class ASTExtractor:
    def __init__(self):
        self.current_file: str = ""
        
    def extract_from_file(self, filepath: str) -> Dict[str, Any]:
        """Extract code structure from a Python file."""
        self.current_file = filepath
        
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                source = f.read()
            return self.extract_from_source(source)
        except Exception as e:
            return {
                'error': f'Failed to parse {filepath}: {str(e)}',
                'functions': [],
                'classes': [],
                'imports': []
            }

    def extract_from_source(self, source: str) -> Dict[str, Any]:
        """Extract code structure from source code string."""
        try:
            tree = ast.parse(source)
            
            functions = self._extract_functions(tree)
            classes = self._extract_classes(tree)
            imports = self._extract_imports(tree)
            
            return {
                'functions': functions,
                'classes': classes,
                'imports': imports
            }
        except Exception as e:
            return {
                'error': f'Failed to parse source: {str(e)}',
                'functions': [],
                'classes': [],
                'imports': []
            }

    def _extract_functions(self, tree: ast.AST) -> List[Dict[str, Any]]:
        """Extract all function definitions."""
        functions = []
        
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                # Skip methods as they'll be handled in class extraction
                if not self._is_method(node):
                    func_info = self._process_function(node)
                    functions.append(vars(func_info))
                    
        return functions

    def _extract_classes(self, tree: ast.AST) -> List[Dict[str, Any]]:
        """Extract all class definitions."""
        classes = []
        
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                class_info = self._process_class(node)
                classes.append(vars(class_info))
                
        return classes

    def _extract_imports(self, tree: ast.AST) -> List[Dict[str, Any]]:
        """Extract all imports."""
        imports = []
        
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for name in node.names:
                    imports.append({
                        'type': 'import',
                        'name': name.name,
                        'asname': name.asname,
                        'lineno': node.lineno
                    })
            elif isinstance(node, ast.ImportFrom):
                for name in node.names:
                    imports.append({
                        'type': 'importfrom',
                        'module': node.module,
                        'name': name.name,
                        'asname': name.asname,
                        'lineno': node.lineno
                    })
                    
        return imports

    def _process_function(self, node: ast.FunctionDef) -> FunctionInfo:
        """Process a function node and extract its information."""
        # Extract function arguments
        args = [arg.arg for arg in node.args.args]
        
        # Extract function calls
        calls = []
        for n in ast.walk(node):
            if isinstance(n, ast.Call):
                if isinstance(n.func, ast.Name):
                    calls.append(n.func.id)
                elif isinstance(n.func, ast.Attribute):
                    calls.append(f"{n.func.value.id}.{n.func.attr}")
        
        # Extract return type hint if available
        returns = None
        if node.returns:
            if isinstance(node.returns, ast.Name):
                returns = node.returns.id
            elif isinstance(node.returns, ast.Constant):
                returns = str(node.returns.value)
        
        return FunctionInfo(
            name=node.name,
            args=args,
            docstring=ast.get_docstring(node),
            calls=calls,
            lineno=node.lineno,
            returns=returns
        )

    def _process_class(self, node: ast.ClassDef) -> ClassInfo:
        """Process a class node and extract its information."""
        # Extract base classes
        bases = []
        for base in node.bases:
            if isinstance(base, ast.Name):
                bases.append(base.id)
            elif isinstance(base, ast.Attribute):
                bases.append(f"{base.value.id}.{base.attr}")
        
        # Extract methods
        methods = []
        for body_item in node.body:
            if isinstance(body_item, ast.FunctionDef):
                method_info = self._process_function(body_item)
                methods.append(method_info)
        
        return ClassInfo(
            name=node.name,
            bases=bases,
            methods=methods,
            docstring=ast.get_docstring(node),
            lineno=node.lineno
        )

    def _is_method(self, node: ast.FunctionDef) -> bool:
        """Check if a function definition is a method."""
        return isinstance(node.parent, ast.ClassDef) if hasattr(node, 'parent') else False