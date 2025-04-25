import asyncio
from typing import Dict, Any
from parsers.repo_fetch import process_github_repo
from retrieval.query_expander import QueryExpander
from retrieval.similarity import CodeSimilarityAnalyzer
from llm.llm_prompt import PromptBuilder
from llm.llm_response import ResponseProcessor
from graph.graph_builder import GraphBuilder

class CodeAssistant:
    def __init__(self):
        """Initialize the code assistant with query processing components"""
        # Initialize GraphBuilder with the same Neo4j connection details as repo_fetch.py
        self.graph_builder = GraphBuilder(
            uri="neo4j+s://ded3cc9c.databases.neo4j.io",
            user="neo4j",
            password="RK3-MvYgHJ3ovL0dVuqGkOvgAKQbBayHxYgEsRpW1qI"
        )
        
        self.query_expander = QueryExpander()
        self.similarity_analyzer = CodeSimilarityAnalyzer()
        self.prompt_builder = PromptBuilder(self.graph_builder)  
        self.response_processor = ResponseProcessor()

    def __del__(self):
        """Cleanup when the instance is destroyed"""
        if hasattr(self, 'graph_builder'):
            self.graph_builder.close()
        
    async def initialize_from_repo(self, repo_url: str) -> Dict[str, Any]:
        """Initialize the knowledge graph from a GitHub repository"""
        try:
            # Process repository and build knowledge graph using repo_fetch
            # This handles all Neo4j and graph schema initialization
            analysis_results = process_github_repo(repo_url)
            
            return {
                'status': 'success',
                'message': 'Repository processed and knowledge graph created successfully',
                'files_processed': len(analysis_results)
            }
        except Exception as e:
            return {
                'status': 'error',
                'message': f'Failed to process repository: {str(e)}'
            }

    async def process_query(self, query: str) -> Dict[str, Any]:
        """Process a user query using the existing knowledge graph"""
        try:
            # Expand query with code-relevant terms
            expanded_terms = self.query_expander.expand_query(query)
            query_components = self.query_expander.decompose_query(query)
            
            # Use existing graph through similarity analyzer
            relevant_functions = self.similarity_analyzer.find_similar_functions(
                expanded_terms,
                query_components
            )
            
            if not relevant_functions:
                return {
                    'status': 'error',
                    'message': 'No relevant code found for the query'
                }
            
            # Generate response using LLM components
            prompt = self.prompt_builder.build_prompt(
                target_functions=relevant_functions,
                query=query
            )
            
            raw_response = await self.response_processor.generate_response(prompt)
            processed_response = self.response_processor.process_response(
                raw_response,
                relevant_functions
            )
            
            return {
                'status': 'success',
                'response': {
                    'summary': processed_response.summary,
                    'markdown_content': processed_response.markdown_content,
                    'code_snippets': processed_response.code_snippets,
                    'confidence_score': processed_response.confidence_score,
                    'references': [
                        {
                            'name': ref.name,
                            'type': ref.node_type,
                            'relevance': ref.relevance_score
                        }
                        for ref in processed_response.references
                    ]
                }
            }
            
        except Exception as e:
            return {
                'status': 'error',
                'message': f'Failed to process query: {str(e)}'
            }

# Example usage
async def main():
    assistant = CodeAssistant()
    
    # One-time initialization from repository
    repo_url = "https://github.com/chinapandaman/PyPDFForm.git"
    init_result = await assistant.initialize_from_repo(repo_url)
    print("Initialization result:", init_result)
    
    # Process user queries using existing knowledge graph
    query = "expalin font.py file code from knowledge graph?"
    response = await assistant.process_query(query)
    print("Query response:", response)

if __name__ == "__main__":
    asyncio.run(main())
