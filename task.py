import os
import subprocess
import ast
import tree_sitter
from tree_sitter import Language, Parser
from neo4j import GraphDatabase
from neo4j.exceptions import ServiceUnavailable

def clone_github_repo(repo_url, repo_dir):
    if os.path.exists(repo_dir):
        print("Repository already exists. Using existing files.")
    else:
        subprocess.run(["git", "clone", repo_url, repo_dir])

def extract_python_files(repo_dir):
    python_files = []
    for root, _, files in os.walk(repo_dir):
        for file in files:
            if file.endswith(".py"):
                python_files.append(os.path.join(root, file))
    return python_files

def parse_python_file_ast(file_path):
    with open(file_path, "r", encoding="utf-8") as f:
        tree = ast.parse(f.read())
    return tree

def extract_code_components_ast(tree, file_name):
    # Initialize data structures for all node types (remove plural forms)
    nodes = {
        'File': [{'name': file_name}],
        'Module': [],
        'Class': [],
        'Function': [],
        'Variable': [],
        'Constant': [],
        'Decorator': [],
        'Exception': [],
        'Library': [],
        'Framework': [],
        'Package': [],
        'TestCase': [],
        'DataFile': [],
        'Script': [],
        'APIEndpoint': [],
        'DatabaseQuery': [],
        'EnvVariable': []
    }
    
    # Initialize relationships with uppercase names to match Neo4j conventions
    relationships = {
        'CONTAINS': [],      # (File, Class/Function/Variable)
        'BELONGS_TO': [],    # (Class, Module/File)
        'IMPORTS': [],       # (File, Module/Library)
        'EXTENDS': [],       # (Class, Class)
        'IMPLEMENTS': [],    # (Class, Interface)
        'CALLS': [],         # (Function, Function)
        'HAS_PARAMETER': [], # (Function, Variable)
        'RETURNS': [],       # (Function, Variable/Type)
        'ASSIGNS': [],       # (Variable, Value/Constant)
        'DECORATES': [],     # (Decorator, Function/Class)
        'DEPENDS_ON': [],    # (Module, Library)
        'USES': [],         # (Class/Function, Module)
        'QUERIES': [],      # (Query, Table)
        'EXECUTES': [],     # (Script, Function)
        'LISTENS_TO': [],   # (Endpoint, Function/Class)
        'READS_FROM': [],   # (File/Script, DataFile)
        'WRITES_TO': [],    # (File/Script, DataFile)
        'RAISES': []        # (Function, Exception)
    }

    # Analyze imports and modules
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                nodes['Module'].append({
                    'name': alias.name,
                    'type': 'module',
                    'line_number': node.lineno
                })
                relationships['IMPORTS'].append(('File:' + file_name, 'Module:' + alias.name))
        
        elif isinstance(node, ast.ImportFrom):
            module_name = node.module or ''
            for alias in node.names:
                nodes['Module'].append({
                    'name': f"{module_name}.{alias.name}",
                    'type': 'module',
                    'line_number': node.lineno
                })
                relationships['IMPORTS'].append(('File:' + file_name, 'Module:' + f"{module_name}.{alias.name}"))

        # Extract classes
        elif isinstance(node, ast.ClassDef):
            class_name = node.name
            nodes['Class'].append({
                'name': class_name,
                'line_number': node.lineno,
                'docstring': ast.get_docstring(node) or ''
            })
            relationships['BELONGS_TO'].append(('Class:' + class_name, 'File:' + file_name))
            
            # Handle class inheritance
            for base in node.bases:
                if isinstance(base, ast.Name):
                    relationships['EXTENDS'].append(('Class:' + class_name, 'Class:' + base.id))
            
            # Handle decorators
            for decorator in node.decorator_list:
                if isinstance(decorator, ast.Name):
                    nodes['Decorator'].append({
                        'name': decorator.id,
                        'line_number': decorator.lineno
                    })
                    relationships['DECORATES'].append(('Decorator:' + decorator.id, 'Class:' + class_name))

        # Extract functions
        elif isinstance(node, ast.FunctionDef):
            func_name = node.name
            nodes['Function'].append({
                'name': func_name,
                'line_number': node.lineno,
                'docstring': ast.get_docstring(node) or ''
            })
            relationships['BELONGS_TO'].append(('Function:' + func_name, 'File:' + file_name))
            
            # Handle function parameters
            for arg in node.args.args:
                nodes['Variable'].append({
                    'name': arg.arg,
                    'type': 'parameter',
                    'line_number': arg.lineno if hasattr(arg, 'lineno') else node.lineno
                })
                relationships['HAS_PARAMETER'].append(('Function:' + func_name, 'Variable:' + arg.arg))
            
            # Handle function decorators
            for decorator in node.decorator_list:
                if isinstance(decorator, ast.Name):
                    nodes['Decorator'].append({
                        'name': decorator.id,
                        'line_number': decorator.lineno
                    })
                    relationships['DECORATES'].append(('Decorator:' + decorator.id, 'Function:' + func_name))

        # Extract variables and constants
        elif isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name):
                    var_name = target.id
                    is_constant = var_name.isupper()
                    if is_constant:
                        nodes['Constant'].append({
                            'name': var_name,
                            'line_number': target.lineno
                        })
                    else:
                        nodes['Variable'].append({
                            'name': var_name,
                            'line_number': target.lineno,
                            'type': 'variable'
                        })

        # Extract exception handling
        elif isinstance(node, ast.Try):
            for handler in node.handlers:
                if handler.type:
                    exc_name = handler.type.id if isinstance(handler.type, ast.Name) else str(handler.type)
                    nodes['Exception'].append({
                        'name': exc_name,
                        'line_number': handler.lineno
                    })
                    if handler.name:
                        relationships['RAISES'].append(('Function:' + func_name, 'Exception:' + exc_name))

    return {
        'nodes': nodes,
        'relationships': relationships
    }

def store_in_neo4j(uri, user, password, file_data):
    driver = GraphDatabase.driver(uri, auth=(user, password))
    
    with driver.session() as session:
        # First, clear existing data 
        session.run("MATCH (n) DETACH DELETE n")
        
        # Create constraints with proper composite keys where needed
        constraints = [
            "CREATE CONSTRAINT IF NOT EXISTS FOR (f:File) REQUIRE f.name IS UNIQUE",
            "CREATE CONSTRAINT IF NOT EXISTS FOR (m:Module) REQUIRE m.name IS UNIQUE",
            "CREATE CONSTRAINT IF NOT EXISTS FOR (c:Class) REQUIRE (c.name, c.file_name) IS UNIQUE",
            "CREATE CONSTRAINT IF NOT EXISTS FOR (f:Function) REQUIRE (f.name, f.file_name) IS UNIQUE",
            "CREATE CONSTRAINT IF NOT EXISTS FOR (v:Variable) REQUIRE (v.name, v.file_name, v.line_number) IS UNIQUE"
        ]
        
        for constraint in constraints:
            try:
                session.run(constraint)
            except Exception as e:
                print(f"Warning: Couldn't create constraint: {e}")

        # Create nodes
        for data in file_data:
            file_name = data['nodes']['File'][0]['name']
            
            # Create File node
            session.run("""
                MERGE (f:File {name: $file_name})
                SET f.file_name = $file_name
            """, {'file_name': file_name})
            
            # Create other nodes
            for node_type, nodes in data['nodes'].items():
                if node_type == 'File':  # Skip File nodes as they're already created
                    continue
                    
                for node in nodes:
                    # Handle Module nodes differently (they should be unique across files)
                    if node_type == 'Module':
                        session.run("""
                            MERGE (n:Module {name: $name})
                            SET n += $properties
                        """, {
                            'name': node['name'],
                            'properties': {
                                'type': node.get('type', 'module'),
                                'line_number': node.get('line_number', 0)
                            }
                        })
                    else:
                        # For other nodes, include file_name in their identity
                        session.run(f"""
                            MERGE (n:{node_type} {{
                                name: $name,
                                file_name: $file_name
                            }})
                            SET n += $properties
                        """, {
                            'name': node['name'],
                            'file_name': file_name,
                            'properties': {
                                'line_number': node.get('line_number', 0),
                                'type': node.get('type', ''),
                                'docstring': node.get('docstring', ''),
                                'file_name': file_name
                            }
                        })
            
            # Create relationships
            for rel_type, rels in data['relationships'].items():
                for source, target in rels:
                    source_type, source_name = source.split(':')
                    target_type, target_name = target.split(':')
                    
                    # Handle Module relationships differently
                    if source_type == 'Module' or target_type == 'Module':
                        session.run(f"""
                            MATCH (s:{source_type} {{name: $source_name}})
                            MATCH (t:{target_type} {{name: $target_name}})
                            MERGE (s)-[:{rel_type}]->(t)
                        """, {
                            'source_name': source_name,
                            'target_name': target_name
                        })
                    else:
                        # For other relationships, include file_name in the match
                        session.run(f"""
                            MATCH (s:{source_type} {{name: $source_name, file_name: $file_name}})
                            MATCH (t:{target_type} {{name: $target_name, file_name: $file_name}})
                            MERGE (s)-[:{rel_type}]->(t)
                        """, {
                            'source_name': source_name,
                            'target_name': target_name,
                            'file_name': file_name
                        })
    
    driver.close()
    
if __name__ == "__main__":
    repo_url = "https://github.com/chinapandaman/PyPDFForm.git"
    repo_dir = "./sample_repo"
    
    neo4j_uri =""
    neo4j_user ="neo4j"
    neo4j_password =""
    
    clone_github_repo(repo_url, repo_dir)
    python_files = extract_python_files(repo_dir)
    
    file_data = []
    for py_file in python_files:
        tree_ast = parse_python_file_ast(py_file)
        file_data.append(extract_code_components_ast(tree_ast, os.path.basename(py_file)))
    
    store_in_neo4j(neo4j_uri, neo4j_user, neo4j_password, file_data)
    print("Data successfully stored in Neo4j AuraDB!")