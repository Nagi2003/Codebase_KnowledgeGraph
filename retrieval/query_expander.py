from typing import List, Set
import nltk
from nltk.corpus import wordnet
from nltk.tokenize import word_tokenize
from nltk.tag import pos_tag
from nltk.corpus import stopwords
import re

class QueryExpander:
    def __init__(self):
        # Download required NLTK data
        nltk.download('punkt')
        nltk.download('averaged_perceptron_tagger')
        nltk.download('wordnet')
        nltk.download('stopwords')
        
        self.stop_words = set(stopwords.words('english'))
        self.code_specific_terms = self._load_code_terms()

    def expand_query(self, query: str) -> List[str]:
        """Expand a natural language query with code-relevant terms"""
        # Tokenize and tag parts of speech
        tokens = word_tokenize(query.lower())
        tagged = pos_tag(tokens)
        
        # Extract key terms and expand
        expanded_terms = set()
        for word, tag in tagged:
            if word not in self.stop_words:
                # Add original term
                expanded_terms.add(word)
                
                # Add code-specific synonyms
                code_synonyms = self._get_code_synonyms(word)
                expanded_terms.update(code_synonyms)
                
                # Add WordNet synonyms
                wordnet_synonyms = self._get_wordnet_synonyms(word, tag)
                expanded_terms.update(wordnet_synonyms)
                
                # Add camelCase and snake_case variants
                variants = self._generate_case_variants(word)
                expanded_terms.update(variants)

        return list(expanded_terms)

    def decompose_query(self, query: str) -> dict:
        """Break down query into structured components"""
        components = {
            'action_terms': set(),
            'object_terms': set(),
            'modifiers': set(),
            'technical_terms': set()
        }

        # Tokenize and tag
        tokens = word_tokenize(query.lower())
        tagged = pos_tag(tokens)

        for word, tag in tagged:
            if word in self.stop_words:
                continue

            # Classify terms based on POS tags and code terminology
            if tag.startswith('VB'):  # Verbs are usually actions
                components['action_terms'].add(word)
            elif tag.startswith('NN'):  # Nouns are usually objects
                if word in self.code_specific_terms:
                    components['technical_terms'].add(word)
                else:
                    components['object_terms'].add(word)
            elif tag.startswith('JJ'):  # Adjectives are modifiers
                components['modifiers'].add(word)

        return components

    def _get_wordnet_synonyms(self, word: str, pos_tag: str) -> Set[str]:
        """Get synonyms from WordNet based on part of speech"""
        synonyms = set()
        
        # Map POS tag to WordNet POS
        pos_map = {
            'NN': wordnet.NOUN,
            'VB': wordnet.VERB,
            'JJ': wordnet.ADJ,
            'RB': wordnet.ADV
        }
        
        # Get WordNet POS or default to NOUN
        wn_pos = pos_map.get(pos_tag[:2], wordnet.NOUN)
        
        # Get synsets and their lemmas
        for synset in wordnet.synsets(word, pos=wn_pos):
            for lemma in synset.lemmas():
                synonyms.add(lemma.name().lower())
        
        return synonyms

    def _get_code_synonyms(self, word: str) -> Set[str]:
        """Get programming-specific synonyms"""
        code_synonyms = {
            'get': {'fetch', 'retrieve', 'select', 'read'},
            'set': {'update', 'modify', 'write', 'assign'},
            'create': {'initialize', 'instantiate', 'new', 'define'},
            'delete': {'remove', 'destroy', 'drop'},
            'add': {'insert', 'append', 'push'},
            'list': {'array', 'collection', 'sequence'},
            'error': {'exception', 'fault', 'bug'},
            'function': {'method', 'procedure', 'routine'},
            'variable': {'var', 'field', 'property'},
            'class': {'type', 'struct', 'interface'}
        }
        
        return code_synonyms.get(word.lower(), set())

    def _generate_case_variants(self, word: str) -> Set[str]:
        """Generate common code case variants"""
        variants = set()
        
        # Original word
        variants.add(word)
        
        # Split on common delimiters
        parts = re.split(r'[-_\s]', word)
        
        if len(parts) > 1:
            # camelCase
            camel = parts[0].lower() + ''.join(p.capitalize() for p in parts[1:])
            variants.add(camel)
            
            # PascalCase
            pascal = ''.join(p.capitalize() for p in parts)
            variants.add(pascal)
            
            # snake_case
            snake = '_'.join(p.lower() for p in parts)
            variants.add(snake)
            
            # kebab-case
            kebab = '-'.join(p.lower() for p in parts)
            variants.add(kebab)
        
        return variants

    def _load_code_terms(self) -> Set[str]:
        """Load common programming terms and concepts"""
        return {
            # Data structures
            'array', 'list', 'stack', 'queue', 'tree', 'graph', 'hash', 'map',
            # Programming concepts
            'function', 'class', 'method', 'variable', 'loop', 'condition',
            'interface', 'module', 'package', 'library', 'framework',
            # Operations
            'sort', 'search', 'filter', 'map', 'reduce', 'transform',
            # Data types
            'string', 'integer', 'float', 'boolean', 'object', 'null',
            # Common actions
            'initialize', 'instantiate', 'implement', 'extend', 'override',
            # Web development
            'api', 'request', 'response', 'route', 'endpoint', 'middleware',
            # Database
            'query', 'table', 'index', 'key', 'join', 'transaction'
        }