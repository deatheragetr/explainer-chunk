from typing import Any, Dict, List, Optional, TypedDict
from typing_extensions import NotRequired

# New type definitions
class PineconeMatch(TypedDict):
    id: str
    score: float
    # metadata: Dict[str, str]
    metadata: SimilarChunk

class PineconeQueryResult(TypedDict):
    matches: List[PineconeMatch]

class SimilarChunk(TypedDict):
    chunk_id: str
    score: float
    text: str
    document_id: str
    chunk_index: NotRequired[int]


class Index:
    def __init__(self, name: str) -> None: ...
    def upsert(self, vectors: List[Dict[str, Any]], namespace: Optional[str] = ...) -> Dict[str, Any]: ...
    def query(self, vector: List[float], top_k: int, namespace: Optional[str] = ..., include_metadata: bool = ...) -> PineconeQueryResult: ...

class Pinecone:
    def __init__(self, api_key: str, environment: str) -> None: ...
    def Index(self, name: str) -> Index: ...
    def list_indexes(self) -> Any: ...
    def create_index(self, name: str, dimension: int, metric: str, spec: Any) -> None: ...

class PodSpec:
    def __init__(self, environment: str) -> None: ...

def init(api_key: str, environment: str) -> None: ...