from typing import Dict, List, Any, Optional
from neo4j import GraphDatabase
from dataclasses import asdict
import logging

class GraphBuilder:
    def __init__(self, uri: str, user: str, password: str):
        """Initialize the graph builder with Neo4j connection details."""
        self.driver = GraphDatabase.driver(uri, auth=(user, password))
        self.logger = logging.getLogger(__name__)

    def close(self):
        """Close the Neo4j connection."""
        self.driver.close()

    def create_code_graph(self, ast_data: Dict[str, Any], file_path: str):
        """Create a graph representation of the code structure."""
        try:
            with self.driver.session() as session:
                # Create file node
                session.execute_write(self._create_file_node, file_path)
                
                # Create function nodes and relationships
                if 'functions' in ast_data:
                    for func in ast_data['functions']:
                        session.execute_write(self._create_function_node, func, file_path)
                
                # Create class nodes and relationships
                if 'classes' in ast_data:
                    for cls in ast_data['classes']:
                        session.execute_write(self._create_class_node, cls, file_path)
                
                # Create import relationships
                if 'imports' in ast_data:
                    for imp in ast_data['imports']:
                        session.execute_write(self._create_import_node, imp, file_path)
                
                # Create call relationships
                self._create_call_relationships(session, ast_data)
                
        except Exception as e:
            self.logger.error(f"Error creating graph: {str(e)}")
            raise

    def _create_file_node(self, tx, file_path: str):
        """Create a file node in the graph."""
        query = """
        MERGE (f:File {path: $path})
        RETURN f
        """
        tx.run(query, path=file_path)

    def _create_function_node(self, tx, func: Dict[str, Any], file_path: str):
        """Create a function node and its relationships."""
        query = """
        MATCH (f:File {path: $file_path})
        MERGE (func:Function {
            name: $name,
            fullName: $full_name,
            lineno: $lineno
        })
        SET func.docstring = $docstring,
            func.args = $args,
            func.returns = $returns
        MERGE (f)-[:CONTAINS]->(func)
        """
        tx.run(
            query,
            file_path=file_path,
            name=func['name'],
            full_name=f"{file_path}::{func['name']}",
            lineno=func['lineno'],
            docstring=func.get('docstring', ''),
            args=func.get('args', []),
            returns=func.get('returns')
        )

    def _create_class_node(self, tx, cls: Dict[str, Any], file_path: str):
        """Create a class node and its relationships."""
        # Create class node
        query = """
        MATCH (f:File {path: $file_path})
        MERGE (c:Class {
            name: $name,
            fullName: $full_name,
            lineno: $lineno
        })
        SET c.docstring = $docstring
        MERGE (f)-[:CONTAINS]->(c)
        """
        tx.run(
            query,
            file_path=file_path,
            name=cls['name'],
            full_name=f"{file_path}::{cls['name']}",
            lineno=cls['lineno'],
            docstring=cls.get('docstring', '')
        )

        # Create inheritance relationships
        if cls.get('bases'):
            query = """
            MATCH (c:Class {fullName: $full_name})
            MERGE (base:Class {name: $base_name})
            MERGE (c)-[:INHERITS]->(base)
            """
            for base in cls['bases']:
                tx.run(query, full_name=f"{file_path}::{cls['name']}", base_name=base)

        # Create method nodes
        for method in cls.get('methods', []):
            method_query = """
            MATCH (c:Class {fullName: $class_full_name})
            MERGE (m:Method {
                name: $name,
                fullName: $full_name,
                lineno: $lineno
            })
            SET m.docstring = $docstring,
                m.args = $args,
                m.returns = $returns
            MERGE (c)-[:DEFINES]->(m)
            """
            tx.run(
                method_query,
                class_full_name=f"{file_path}::{cls['name']}",
                name=method['name'],
                full_name=f"{file_path}::{cls['name']}.{method['name']}",
                lineno=method['lineno'],
                docstring=method.get('docstring', ''),
                args=method.get('args', []),
                returns=method.get('returns')
            )

    def _create_import_node(self, tx, imp: Dict[str, Any], file_path: str):
        """Create an import node and its relationships."""
        query = """
        MATCH (f:File {path: $file_path})
        MERGE (i:Import {
            name: $name,
            fullName: $full_name,
            type: $type
        })
        SET i.asname = $asname,
            i.module = $module,
            i.lineno = $lineno
        MERGE (f)-[:IMPORTS]->(i)
        """
        tx.run(
            query,
            file_path=file_path,
            name=imp['name'],
            full_name=f"{file_path}::{imp['name']}",
            type=imp['type'],
            asname=imp.get('asname'),
            module=imp.get('module'),
            lineno=imp['lineno']
        )

    def _create_call_relationships(self, session, ast_data: Dict[str, Any]):
        """Create relationships for function calls."""
        for func in ast_data.get('functions', []):
            if func.get('calls'):
                query = """
                MATCH (caller:Function {name: $caller_name})
                MATCH (callee:Function {name: $callee_name})
                MERGE (caller)-[:CALLS]->(callee)
                """
                for call in func['calls']:
                    session.execute_write(
                        lambda tx: tx.run(query, caller_name=func['name'], callee_name=call)
                    )

        # Handle method calls in classes
        for cls in ast_data.get('classes', []):
            for method in cls.get('methods', []):
                if method.get('calls'):
                    query = """
                    MATCH (caller:Method {fullName: $caller_full_name})
                    MATCH (callee:Function {name: $callee_name})
                    MERGE (caller)-[:CALLS]->(callee)
                    """
                    for call in method['calls']:
                        session.execute_write(
                            lambda tx: tx.run(
                                query,
                                caller_full_name=f"{cls['name']}.{method['name']}",
                                callee_name=call
                            )
                        )