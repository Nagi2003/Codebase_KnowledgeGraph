import ast
from typing import List, Dict, Any, Tuple
from dataclasses import dataclass
import numpy as np
from transformers import AutoTokenizer, AutoModel
import torch
from difflib import SequenceMatcher

@dataclass
class FunctionSimilarity:
    """Stores similarity scores between two functions"""
    ast_similarity: float
    semantic_similarity: float
    combined_similarity: float
    function1_name: str
    function2_name: str

class CodeSimilarityAnalyzer:
    def __init__(self):
        # Initialize CodeBERT tokenizer and model
        self.tokenizer = AutoTokenizer.from_pretrained("microsoft/codebert-base")
        self.model = AutoModel.from_pretrained("microsoft/codebert-base")
        self.model.eval()  # Set to evaluation mode

    def compute_ast_similarity(self, ast1: ast.AST, ast2: ast.AST) -> float:
        """Compute structural similarity between two ASTs"""
        # Convert ASTs to normalized string representations
        str1 = self._normalize_ast(ast1)
        str2 = self._normalize_ast(ast2)
        
        # Use SequenceMatcher for structural comparison
        matcher = SequenceMatcher(None, str1, str2)
        return matcher.ratio()

    def compute_semantic_similarity(self, code1: str, code2: str) -> float:
        """Compute semantic similarity using CodeBERT embeddings"""
        # Tokenize code snippets
        tokens1 = self.tokenizer(code1, return_tensors="pt", truncation=True, max_length=512)
        tokens2 = self.tokenizer(code2, return_tensors="pt", truncation=True, max_length=512)

        with torch.no_grad():
            # Get embeddings
            embedding1 = self.model(**tokens1).last_hidden_state.mean(dim=1)
            embedding2 = self.model(**tokens2).last_hidden_state.mean(dim=1)

            # Compute cosine similarity
            similarity = torch.nn.functional.cosine_similarity(embedding1, embedding2)
            return float(similarity[0])

    def compare_functions(self, func1: Dict[str, Any], func2: Dict[str, Any]) -> FunctionSimilarity:
        """Compare two functions using both AST and semantic similarity"""
        # Parse function code into ASTs
        ast1 = ast.parse(func1['code'])
        ast2 = ast.parse(func2['code'])

        # Compute similarities
        ast_sim = self.compute_ast_similarity(ast1, ast2)
        semantic_sim = self.compute_semantic_similarity(func1['code'], func2['code'])

        # Combine similarities (weighted average)
        combined_sim = 0.4 * ast_sim + 0.6 * semantic_sim

        return FunctionSimilarity(
            ast_similarity=ast_sim,
            semantic_similarity=semantic_sim,
            combined_similarity=combined_sim,
            function1_name=func1['name'],
            function2_name=func2['name']
        )

    def find_similar_functions(self, 
                             target_func: Dict[str, Any], 
                             function_pool: List[Dict[str, Any]], 
                             threshold: float = 0.7) -> List[FunctionSimilarity]:
        """Find similar functions in a pool of functions"""
        similarities = []
        
        for func in function_pool:
            if func['name'] != target_func['name']:  # Don't compare with self
                similarity = self.compare_functions(target_func, func)
                if similarity.combined_similarity >= threshold:
                    similarities.append(similarity)

        # Sort by combined similarity score
        return sorted(similarities, key=lambda x: x.combined_similarity, reverse=True)

    def _normalize_ast(self, tree: ast.AST) -> str:
        """Convert AST to normalized string representation"""
        class ASTNormalizer(ast.NodeVisitor):
            def __init__(self):
                self.tokens = []
                self.generic_var_counter = 0
                self.var_map = {}

            def generic_visit(self, node):
                node_type = type(node).__name__
                if isinstance(node, ast.Name):
                    # Normalize variable names
                    if node.id not in self.var_map:
                        self.var_map[node.id] = f"VAR_{self.generic_var_counter}"
                        self.generic_var_counter += 1
                    self.tokens.append(self.var_map[node.id])
                else:
                    self.tokens.append(node_type)
                ast.NodeVisitor.generic_visit(self, node)

        normalizer = ASTNormalizer()
        normalizer.visit(tree)
        return " ".join(normalizer.tokens)