## Create a virtual environment (recommended)
python -m venv venv

### On Windows:
venv\Scripts\activate
## On Unix or MacOS:
source venv/bin/activate

## clone the repo
https://github.com/Nagi2003/Codebase_KnowledgeGraph.git

## add the tokens
GITHUB_TOKEN=""
neo4j_password=""

## Install required packages
pip install -r requirements.txt

## create the instance in neo4j KnowledgeGraph and add url,password in task.py 
neo4j_uri =""
neo4j_user ="neo4j"
neo4j_password =""

## run the python file
python task.py

