from typing import List, Dict, Any, Optional
from dataclasses import dataclass
import ast
from parsers.ast_extractor import FunctionInfo, ClassInfo
from graph.graph_builder import GraphBuilder
import json

@dataclass
class ContextNode:
    """Represents a code context node for LLM prompting"""
    type: str  # 'function', 'class', 'method'
    name: str
    code: str
    docstring: Optional[str]
    dependencies: List[str]
    importance_score: float

class PromptBuilder:
    def __init__(self, graph_builder: GraphBuilder):
        self.graph_builder = graph_builder
        self.max_context_length = 4096  # Token limit for context

    def build_prompt(self, 
                    target_functions: List[Dict[str, Any]], 
                    query: str,
                    include_dependencies: bool = True) -> str:
        """Build a structured prompt for the LLM"""
        context_nodes = self._gather_context(target_functions, include_dependencies)
        
        # Sort nodes by importance
        context_nodes.sort(key=lambda x: x.importance_score, reverse=True)
        
        # Build the prompt
        prompt = self._create_prompt_template(
            context_nodes=context_nodes,
            query=query
        )
        
        return prompt

    def _gather_context(self, 
                    target_functions: List[Dict[str, Any]], 
                    include_dependencies: bool) -> List[ContextNode]:
        """Gather relevant context nodes for the prompt"""
        context_nodes = []
        
        for func in target_functions:
            # Add the target function
            context_nodes.append(self._create_context_node(func))
            
            if include_dependencies:
                # Get dependencies from the graph
                deps = self._get_function_dependencies(func['name'])
                for dep in deps:
                    context_nodes.append(self._create_context_node(dep))
        
        return self._prune_context(context_nodes)

    def _create_context_node(self, code_info: Dict[str, Any]) -> ContextNode:
        """Create a context node from code info"""
        # Calculate importance score based on various factors
        importance = self._calculate_importance(code_info)
        
        return ContextNode(
            type=code_info.get('type', 'function'),
            name=code_info['name'],
            code=code_info['code'],
            docstring=code_info.get('docstring'),
            dependencies=code_info.get('dependencies', []),
            importance_score=importance
        )

    def _calculate_importance(self, code_info: Dict[str, Any]) -> float:
        """Calculate importance score for context prioritization"""
        score = 1.0
        
        # Factors that increase importance
        if code_info.get('docstring'):
            score += 0.3
        if code_info.get('calls', []):
            score += 0.2 * len(code_info['calls'])
        if code_info.get('dependencies', []):
            score += 0.1 * len(code_info['dependencies'])
            
        return score

    def _get_function_dependencies(self, function_name: str) -> List[Dict[str, Any]]:
        """Get function dependencies from the graph"""
        query = """
        MATCH (f:Function {name: $name})-[:CALLS|USES]->(dep)
        RETURN dep
        """
        
        with self.graph_builder.driver.session() as session:
            result = session.run(query, name=function_name)
            return [dict(record['dep']) for record in result]

    def _prune_context(self, nodes: List[ContextNode]) -> List[ContextNode]:
        """Prune context to fit within token limit"""
        pruned_nodes = []
        current_length = 0
        
        for node in nodes:
            # Estimate tokens (rough approximation)
            node_tokens = len(node.code.split()) + len(node.docstring.split() if node.docstring else [])
            
            if current_length + node_tokens <= self.max_context_length:
                pruned_nodes.append(node)
                current_length += node_tokens
            else:
                break
                
        return pruned_nodes

    def _create_prompt_template(self, 
                                context_nodes: List[ContextNode], 
                                query: str) -> str:
        """Create the final prompt template"""
        prompt_parts = [
            "You are an expert code assistant. Analyze the following code and answer the query.",
            "\nContext:",
        ]
        
        # Add context nodes
        for node in context_nodes:
            prompt_parts.extend([
                f"\n{node.type.upper()}: {node.name}",
                f"Documentation: {node.docstring if node.docstring else 'None'}",
                "Code:",
                "```python",
                node.code,
                "```\n"
            ])
        
        # Add query
        prompt_parts.extend([
            "\nQuery:",
            query,
            "\nPlease provide a detailed response based on the code context above."
        ])
        
        return "\n".join(prompt_parts)

    def format_code_for_prompt(self, code: str) -> str:
        """Format code for inclusion in the prompt"""
        try:
            # Parse and unparse to normalize formatting
            tree = ast.parse(code)
            formatted_code = ast.unparse(tree)
            return formatted_code
        except Exception:
            # Return original if parsing fails
            return code