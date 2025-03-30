from pydantic_settings import BaseSettings
from typing import Optional, Annotated, List


class ElasticsearchSettings(BaseSettings):
    elasticsearch_url: Annotated[
        str, "Elasticsearch URL, e.g., https://localhost:9200"
    ] = "http://localhost:9200"
    elasticsearch_user: Annotated[str, "Elasticsearch username"] = "elastic"
    elasticsearch_password: Annotated[str, "Elasticsearch password"] = "changeme"
    elasticsearch_verify_certs: Annotated[bool, "Verify SSL certificates"] = False
    elasticsearch_index_prefix: Annotated[str, "Prefix for Elasticsearch indices"] = (
        "explainer_chonk_"
    )

    # Vector search settings
    vector_dimensions: Annotated[int, "Dimensions for vector embeddings"] = (
        1536  # For OpenAI's text-embedding-3-small
    )
    vector_similarity: Annotated[str, "Similarity metric for vector search"] = (
        "cosine"  # Or "dot_product", "l2_norm"
    )

    # Search settings
    search_result_size: Annotated[int, "Default number of search results to return"] = (
        10
    )
    search_min_score: Annotated[float, "Minimum score for search results"] = 0.7


# def get_elasticsearch_settings() -> ElasticsearchSettings:
#     return ElasticsearchSettings()
