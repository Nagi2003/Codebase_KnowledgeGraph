import os
import subprocess
from parsers.ast_extractor import ASTExtractor
from graph.graph_builder import GraphBuilder
from graph.graph_schema import GraphSchema

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

if __name__ == "__main__":
    # Repo and Neo4j credentials
    repo_url = "https://github.com/chinapandaman/PyPDFForm.git"
    repo_dir = "./data/code"

    neo4j_uri = "neo4j+s://ded3cc9c.databases.neo4j.io"
    neo4j_user = "neo4j"
    neo4j_password = "RK3-MvYgHJ3ovL0dVuqGkOvgAKQbBayHxYgEsRpW1qI"

    # Step 1: Clone the repo
    clone_github_repo(repo_url, repo_dir)

    # Step 2: Extract .py files
    python_files = extract_python_files(repo_dir)

    # Step 3: Initialize extractor and graph builder
    extractor = ASTExtractor()
    builder = GraphBuilder(neo4j_uri, neo4j_user, neo4j_password)

    # Step 4: Initialize schema
    GraphSchema.initialize_schema(builder)

    # Step 5: Process and store each file
    for py_file in python_files:
        ast_data = extractor.extract_from_file(py_file)
        builder.create_code_graph(ast_data, py_file)

    # Step 6: Done
    builder.close()
    print("Data successfully stored in Neo4j AuraDB!")
