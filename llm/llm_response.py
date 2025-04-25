# from typing import Dict, List, Any, Optional
# from dataclasses import dataclass
# import json
# import re
# from transformers import AutoTokenizer, AutoModelForCausalLM
# import torch
# import markdown
# from pygments import highlight
# from pygments.lexers import PythonLexer
# from pygments.formatters import HtmlFormatter

# @dataclass
# class CodeReference:
#     """Reference to a specific piece of code in the graph"""
#     node_id: str
#     node_type: str
#     name: str
#     relevance_score: float

# @dataclass
# class ProcessedResponse:
#     """Processed and formatted LLM response"""
#     summary: str
#     code_snippets: List[str]
#     references: List[CodeReference]
#     confidence_score: float
#     markdown_content: str

# class ResponseProcessor:
#     def __init__(self):
#         # Initialize the Phi-4 model
#         self.model_name = "microsoft/Phi-4-mini-instruct"
#         self.tokenizer = AutoTokenizer.from_pretrained(self.model_name)
#         self.model = AutoModelForCausalLM.from_pretrained(self.model_name)
#         self.model.eval()
        
#         # Initialize Pygments components
#         self.python_lexer = PythonLexer()
#         self.html_formatter = HtmlFormatter(
#             style='monokai',
#             linenos=True,
#             cssclass='source'
#         )

#     async def generate_response(self, prompt: str) -> str:
#         """Generate response using Phi-3.5"""
#         inputs = self.tokenizer(prompt, return_tensors="pt", truncation=True, max_length=2048)
        
#         with torch.no_grad():
#             outputs = self.model.generate(
#                 inputs.input_ids,
#                 max_length=1024,
#                 num_return_sequences=1,
#                 temperature=0.7,
#                 top_p=0.9,
#                 do_sample=True
#             )
        
#         response = self.tokenizer.decode(outputs[0], skip_special_tokens=True)
#         return response

#     def process_response(self, 
#                         raw_response: str, 
#                         context_nodes: List[Dict[str, Any]]) -> ProcessedResponse:
#         """Process and format the raw LLM response"""
#         # Extract code snippets
#         code_snippets = self._extract_code_snippets(raw_response)
        
#         # Find references to context nodes
#         references = self._find_references(raw_response, context_nodes)
        
#         # Generate summary
#         summary = self._generate_summary(raw_response)
        
#         # Calculate confidence score
#         confidence = self._calculate_confidence(raw_response, references)
        
#         # Convert to markdown
#         markdown_content = self._format_as_markdown(
#             raw_response, 
#             code_snippets, 
#             references
#         )
        
#         return ProcessedResponse(
#             summary=summary,
#             code_snippets=code_snippets,
#             references=references,
#             confidence_score=confidence,
#             markdown_content=markdown_content
#         )

#     def _extract_code_snippets(self, text: str) -> List[str]:
#         """Extract code snippets from markdown code blocks"""
#         code_block_pattern = r"```(?:python)?\n(.*?)\n```"
#         snippets = re.findall(code_block_pattern, text, re.DOTALL)
#         return [snippet.strip() for snippet in snippets]

#     def _find_references(self, 
#                         text: str, 
#                         context_nodes: List[Dict[str, Any]]) -> List[CodeReference]:
#         """Find references to context nodes in the response"""
#         references = []
        
#         for node in context_nodes:
#             if node['name'].lower() in text.lower():
#                 references.append(CodeReference(
#                     node_id=node['id'],
#                     node_type=node['type'],
#                     name=node['name'],
#                     relevance_score=self._calculate_relevance(text, node)
#                 ))
                
#         return sorted(references, key=lambda x: x.relevance_score, reverse=True)

#     def _calculate_relevance(self, text: str, node: Dict[str, Any]) -> float:
#         """Calculate relevance score for a reference"""
#         # Basic relevance scoring based on mention frequency and context
#         name_mentions = text.lower().count(node['name'].lower())
#         context_relevance = 0.5  # Base relevance
        
#         if node.get('docstring', '').lower() in text.lower():
#             context_relevance += 0.3
            
#         return (name_mentions * 0.2) + context_relevance

#     def _generate_summary(self, text: str, max_length: int = 200) -> str:
#         """Generate a concise summary of the response"""
#         # Remove code blocks
#         text_without_code = re.sub(r"```.*?```", "", text, flags=re.DOTALL)
        
#         # Get first paragraph or sentence that makes sense as a summary
#         paragraphs = text_without_code.split('\n\n')
#         for para in paragraphs:
#             clean_para = para.strip()
#             if len(clean_para) > 20 and len(clean_para) <= max_length:
#                 return clean_para
                
#         # Fallback: truncate first paragraph
#         return paragraphs[0][:max_length] + "..."

#     def _calculate_confidence(self, 
#                             response: str, 
#                             references: List[CodeReference]) -> float:
#         """Calculate confidence score for the response"""
#         confidence = 0.5  # Base confidence
        
#         # Factors that increase confidence
#         if references:
#             confidence += 0.2
#         if self._extract_code_snippets(response):
#             confidence += 0.1
#         if len(response.split()) > 50:  # Reasonable length
#             confidence += 0.1
            
#         # Cap at 1.0
#         return min(confidence, 1.0)

#     def _format_as_markdown(self, 
#                         text: str, 
#                         code_snippets: List[str], 
#                         references: List[CodeReference]) -> str:
#         """Format the response as markdown with syntax highlighting"""
#         # Add syntax highlighting to code blocks
#         highlighted_text = text
#         for snippet in code_snippets:
#             # Use Pygments to highlight the code
#             highlighted_code = highlight(
#                 snippet,
#                 self.python_lexer,
#                 self.html_formatter
#             )
            
#             # Replace the original code block with highlighted version
#             highlighted_text = highlighted_text.replace(
#                 f"```python\n{snippet}\n```",
#                 f'<div class="highlight">{highlighted_code}</div>'
#             )
        
#         # Add reference section if there are references
#         if references:
#             highlighted_text += "\n\n### References\n"
#             for ref in references:
#                 highlighted_text += f"- [{ref.name}] ({ref.node_type})\n"
        
#         # Get Pygments CSS
#         css = self.html_formatter.get_style_defs('.highlight')
#         highlighted_text = f"<style>{css}</style>\n\n{highlighted_text}"
        
#         return markdown.markdown(
#             highlighted_text,
#             extensions=['fenced_code', 'codehilite']
#         )

#     def rank_responses(self, 
#                     responses: List[ProcessedResponse], 
#                     query: str) -> List[ProcessedResponse]:
#         """Rank multiple responses by relevance to query"""
#         scored_responses = []
        
#         for response in responses:
#             # Calculate query relevance
#             query_terms = query.lower().split()
#             content = response.markdown_content.lower()
            
#             term_matches = sum(term in content for term in query_terms)
#             code_quality = len(response.code_snippets) * 0.2
#             reference_quality = len(response.references) * 0.1
            
#             score = (term_matches * 0.4 + 
#                     code_quality + 
#                     reference_quality + 
#                     response.confidence_score * 0.3)
                    
#             scored_responses.append((score, response))
            
#         # Sort by score and return responses
#         return [r for _, r in sorted(scored_responses, reverse=True)]

from typing import Dict, List, Any, Optional
from dataclasses import dataclass
import json
import re
import markdown
from pygments import highlight
from pygments.lexers import PythonLexer
from pygments.formatters import HtmlFormatter
import httpx

@dataclass
class CodeReference:
    """Reference to a specific piece of code in the graph"""
    node_id: str
    node_type: str
    name: str
    relevance_score: float

@dataclass
class ProcessedResponse:
    """Processed and formatted LLM response"""
    summary: str
    code_snippets: List[str]
    references: List[CodeReference]
    confidence_score: float
    markdown_content: str

class ResponseProcessor:
    def __init__(self, ollama_base_url: str = "http://localhost:11434"):
        # Initialize Ollama client
        self.ollama_base_url = ollama_base_url
        self.model_name = "phi-4-mini" 

        # Initialize Pygments components
        self.python_lexer = PythonLexer()
        self.html_formatter = HtmlFormatter(
            style='monokai',
            linenos=True,
            cssclass='source'
        )

    async def generate_response(self, prompt: str) -> str:
        """Generate response using Ollama"""
        url = f"{self.ollama_base_url}/api/generate"
        data = {
            "prompt": prompt,
            "model": self.model_name,
            "stream": False,
            "options": {
                "temperature": 0.7,
                "top_p": 0.9,
                "num_predict": 1024
            }
        }
        async with httpx.AsyncClient() as client:
            response = await client.post(url, json=data)
            response.raise_for_status()
            return response.json()['response']

    def process_response(self,
                        raw_response: str,
                        context_nodes: List[Dict[str, Any]]) -> ProcessedResponse:
        """Process and format the raw LLM response"""
        # Extract code snippets
        code_snippets = self._extract_code_snippets(raw_response)

        # Find references to context nodes
        references = self._find_references(raw_response, context_nodes)

        # Generate summary
        summary = self._generate_summary(raw_response)

        # Calculate confidence score
        confidence = self._calculate_confidence(raw_response, references)

        # Convert to markdown
        markdown_content = self._format_as_markdown(
            raw_response,
            code_snippets,
            references
        )

        return ProcessedResponse(
            summary=summary,
            code_snippets=code_snippets,
            references=references,
            confidence_score=confidence,
            markdown_content=markdown_content
        )

    def _extract_code_snippets(self, text: str) -> List[str]:
        """Extract code snippets from markdown code blocks"""
        code_block_pattern = r"```(?:python)?\n(.*?)\n```"
        snippets = re.findall(code_block_pattern, text, re.DOTALL)
        return [snippet.strip() for snippet in snippets]

    def _find_references(self,
                        text: str,
                        context_nodes: List[Dict[str, Any]]) -> List[CodeReference]:
        """Find references to context nodes in the response"""
        references = []

        for node in context_nodes:
            if node['name'].lower() in text.lower():
                references.append(CodeReference(
                    node_id=node['id'],
                    node_type=node['type'],
                    name=node['name'],
                    relevance_score=self._calculate_relevance(text, node)
                ))

        return sorted(references, key=lambda x: x.relevance_score, reverse=True)

    def _calculate_relevance(self, text: str, node: Dict[str, Any]) -> float:
        """Calculate relevance score for a reference"""
        # Basic relevance scoring based on mention frequency and context
        name_mentions = text.lower().count(node['name'].lower())
        context_relevance = 0.5  # Base relevance

        if node.get('docstring', '').lower() in text.lower():
            context_relevance += 0.3

        return (name_mentions * 0.2) + context_relevance

    def _generate_summary(self, text: str, max_length: int = 200) -> str:
        """Generate a concise summary of the response"""
        # Remove code blocks
        text_without_code = re.sub(r"```.*?```", "", text, flags=re.DOTALL)

        # Get first paragraph or sentence that makes sense as a summary
        paragraphs = text_without_code.split('\n\n')
        for para in paragraphs:
            clean_para = para.strip()
            if len(clean_para) > 20 and len(clean_para) <= max_length:
                return clean_para

        # Fallback: truncate first paragraph
        return paragraphs[0][:max_length] + "..."

    def _calculate_confidence(self,
                            response: str,
                            references: List[CodeReference]) -> float:
        """Calculate confidence score for the response"""
        confidence = 0.5  # Base confidence

        # Factors that increase confidence
        if references:
            confidence += 0.2
        if self._extract_code_snippets(response):
            confidence += 0.1
        if len(response.split()) > 50:  # Reasonable length
            confidence += 0.1

        # Cap at 1.0
        return min(confidence, 1.0)

    def _format_as_markdown(self,
                            text: str,
                            code_snippets: List[str],
                            references: List[CodeReference]) -> str:
        """Format the response as markdown with syntax highlighting"""
        # Add syntax highlighting to code blocks
        highlighted_text = text
        for snippet in code_snippets:
            # Use Pygments to highlight the code
            highlighted_code = highlight(
                snippet,
                self.python_lexer,
                self.html_formatter
            )

            # Replace the original code block with highlighted version
            highlighted_text = highlighted_text.replace(
                f"```python\n{snippet}\n```",
                f'<div class="highlight">{highlighted_code}</div>'
            )

        # Add reference section if there are references
        if references:
            highlighted_text += "\n\n### References\n"
            for ref in references:
                highlighted_text += f"- [{ref.name}] ({ref.node_type})\n"

        # Get Pygments CSS
        css = self.html_formatter.get_style_defs('.highlight')
        highlighted_text = f"<style>{css}</style>\n\n{highlighted_text}"

        return markdown.markdown(
            highlighted_text,
            extensions=['fenced_code', 'codehilite']
        )

    def rank_responses(self,
                    responses: List[ProcessedResponse],
                    query: str) -> List[ProcessedResponse]:
        """Rank multiple responses by relevance to query"""
        scored_responses = []

        for response in responses:
            # Calculate query relevance
            query_terms = query.lower().split()
            content = response.markdown_content.lower()

            term_matches = sum(term in content for term in query_terms)
            code_quality = len(response.code_snippets) * 0.2
            reference_quality = len(response.references) * 0.1

            score = (term_matches * 0.4 +
                    code_quality +
                    reference_quality +
                    response.confidence_score * 0.3)

            scored_responses.append((score, response))

        # Sort by score and return responses
        return [r for _, r in sorted(scored_responses, reverse=True)]