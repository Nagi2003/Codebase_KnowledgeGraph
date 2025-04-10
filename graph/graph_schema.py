from enum import Enum
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from datetime import datetime

class NodeType(Enum):
    """Enum defining the types of nodes in the code graph."""
    FILE = "File"
    FUNCTION = "Function"
    METHOD = "Method"
    CLASS = "Class"
    IMPORT = "Import"
    MODULE = "Module"
    PACKAGE = "Package"

class RelationType(Enum):
    """Enum defining the types of relationships in the code graph."""
    CONTAINS = "CONTAINS"
    DEFINES = "DEFINES"
    IMPORTS = "IMPORTS"
    CALLS = "CALLS"
    INHERITS = "INHERITS"
    IMPLEMENTS = "IMPLEMENTS"
    DEPENDS_ON = "DEPENDS_ON"
    USES = "USES"

@dataclass
class NodeProperties:
    """Base properties for all nodes."""
    name: str
    fullName: str
    created_at: datetime = field(default_factory=datetime.now, init=False)
    updated_at: datetime = field(default_factory=datetime.now, init=False)

@dataclass
class FileProperties(NodeProperties):
    """Properties specific to File nodes."""
    path: str
    size: Optional[int] = None
    hash: Optional[str] = None
    language: Optional[str] = None

@dataclass
class FunctionProperties(NodeProperties):
    """Properties specific to Function nodes."""
    args: List[str]
    returns: Optional[str]
    docstring: Optional[str]
    lineno: int
    complexity: Optional[int] = None
    is_async: bool = False

@dataclass
class ClassProperties(NodeProperties):
    """Properties specific to Class nodes."""
    bases: List[str]
    docstring: Optional[str]
    lineno: int
    methods: List[str]
    is_abstract: bool = False

@dataclass
class ImportProperties(NodeProperties):
    """Properties specific to Import nodes."""
    module: Optional[str]
    asname: Optional[str]
    type: str  # 'import' or 'importfrom'
    lineno: int

@dataclass
class RelationshipProperties:
    """Properties for relationships between nodes."""
    type: RelationType
    created_at: datetime = field(default_factory=datetime.now)
    metadata: Optional[Dict[str, Any]] = None

class GraphSchema:
    """Defines the schema for the code knowledge graph."""

    @staticmethod
    def get_node_constraints() -> List[str]:
        """Get Cypher queries for creating node constraints."""
        return [
            "CREATE CONSTRAINT IF NOT EXISTS FOR (f:File) REQUIRE f.path IS UNIQUE",
            "CREATE CONSTRAINT IF NOT EXISTS FOR (f:Function) REQUIRE f.fullName IS UNIQUE",
            "CREATE CONSTRAINT IF NOT EXISTS FOR (c:Class) REQUIRE c.fullName IS UNIQUE",
            "CREATE CONSTRAINT IF NOT EXISTS FOR (i:Import) REQUIRE i.fullName IS UNIQUE",
            "CREATE CONSTRAINT IF NOT EXISTS FOR (m:Method) REQUIRE m.fullName IS UNIQUE"
        ]

    @staticmethod
    def get_node_indexes() -> List[str]:
        """Get Cypher queries for creating indexes."""
        return [
            "CREATE INDEX IF NOT EXISTS FOR (f:File) ON (f.path)",
            "CREATE INDEX IF NOT EXISTS FOR (f:Function) ON (f.name)",
            "CREATE INDEX IF NOT EXISTS FOR (c:Class) ON (c.name)",
            "CREATE INDEX IF NOT EXISTS FOR (i:Import) ON (i.name)",
            "CREATE INDEX IF NOT EXISTS FOR (m:Method) ON (m.name)"
        ]

    @staticmethod
    def initialize_schema(graph_builder) -> None:
        """Initialize the schema in Neo4j."""
        with graph_builder.driver.session() as session:
            for constraint in GraphSchema.get_node_constraints():
                session.run(constraint)
            for index in GraphSchema.get_node_indexes():
                session.run(index)

    @staticmethod
    def validate_node(node_type: NodeType, properties: Dict[str, Any]) -> bool:
        """Validate node properties against schema."""
        required_props = {
            NodeType.FILE: {'path', 'name', 'fullName'},
            NodeType.FUNCTION: {'name', 'fullName', 'args', 'lineno'},
            NodeType.CLASS: {'name', 'fullName', 'bases', 'lineno'},
            NodeType.IMPORT: {'name', 'fullName', 'type', 'lineno'},
            NodeType.METHOD: {'name', 'fullName', 'args', 'lineno'}
        }

        return all(prop in properties for prop in required_props.get(node_type, set()))

    @staticmethod
    def validate_relationship(rel_type: RelationType, start_type: NodeType, end_type: NodeType) -> bool:
        """Validate relationship between node types."""
        valid_relationships = {
            RelationType.CONTAINS: {
                NodeType.FILE: {NodeType.FUNCTION, NodeType.CLASS, NodeType.IMPORT},
                NodeType.CLASS: {NodeType.METHOD}
            },
            RelationType.CALLS: {
                NodeType.FUNCTION: {NodeType.FUNCTION},
                NodeType.METHOD: {NodeType.FUNCTION, NodeType.METHOD}
            },
            RelationType.INHERITS: {
                NodeType.CLASS: {NodeType.CLASS}
            },
            RelationType.IMPORTS: {
                NodeType.FILE: {NodeType.IMPORT}
            }
        }

        return end_type in valid_relationships.get(rel_type, {}).get(start_type, set())
