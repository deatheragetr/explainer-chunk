from pydantic_settings import BaseSettings
from typing_extensions import Annotated


class AppSettings(BaseSettings):
    api_base_url: Annotated[
        str, "Base API URL, e.g., https://api.explainerchonk.com"
    ] = ""
    app_base_url: Annotated[
        str, "Base UI URL, e.g., https://app.explainerchonk.com"
    ] = ""


class S3Settings(BaseSettings):
    s3_access_key: Annotated[str, "S3 access key"] = ""
    s3_secret_key: Annotated[str, "S3 secret key"] = ""
    s3_region: Annotated[str, "S3 region"] = ""
    s3_document_bucket: Annotated[str, "S3 document uploads (not public) bucket"] = ""
    s3_public_bucket: Annotated[
        str, "S3 document uploads (public access, e.g., web_captures) bucket"
    ] = ""
    s3_host: Annotated[str, "S3 host"] = ""


class MongoSettings(BaseSettings):
    mongo_url: Annotated[str, "MongoDB connection URL"] = "mongodb://localhost:27019"
    mongo_db: Annotated[str, "MongoDB database name"] = "explainer-chonk-dev"
    max_pool_size: Annotated[int, "MongoDB max pool size"] = 100
    min_pool_size: Annotated[int, "MongoDB min pool size"] = 1


class PineconeSettings(BaseSettings):
    pinecone_api_key: Annotated[str, "Pinecone API key"] = ""


class OpenAISettings(BaseSettings):
    openai_api_key: Annotated[str, "OpenAI API key"] = ""


class PopplerSettings(BaseSettings):
    poppler_path: Annotated[
        str,
        "The path to the poppler installation, used by pdf2image (convert_to_bytes)",
    ] = ""


class CryptoSettings(BaseSettings):
    secret_key: Annotated[str, "Encrpytion key for passwords, signatures"] = ""
    algorithm: Annotated[str, "Algorithm for encryption (passwords)"] = "HS256"
    access_token_expiration_minutes: Annotated[
        int, "Default TTL for JWT access token in minutes"
    ] = 10
    refresh_token_expiration_days: Annotated[
        int, "Default TTL for JWT refresh token"
    ] = 7


class DataSettings(BaseSettings):
    path_to_geoip_db: Annotated[str, "Path to the GeoLite MMDB of IP mappings"] = ""


class EmailSettings(BaseSettings):
    postmark_api_key: Annotated[str, "Postmark API Key"] = ""
    default_sender_email: Annotated[
        str, "Default email sender, e.g., thomas@explainerchonk.com"
    ] = ""


class ElasticsearchSettings(BaseSettings):
    elasticsearch_url: Annotated[
        str, "Elasticsearch URL, e.g., https://localhost:9200"
    ] = "https://localhost:9200"  # Changed to HTTPS
    elasticsearch_user: Annotated[str, "Elasticsearch username"] = "elastic"
    elasticsearch_password: Annotated[str, "Elasticsearch password"] = "changeme"
    elasticsearch_verify_certs: Annotated[bool, "Verify SSL certificates"] = False
    elasticsearch_index_prefix: Annotated[str, "Prefix for Elasticsearch indices"] = (
        "explainer_chonk_"
    )
    # Optional path to CA certificate for proper verification
    elasticsearch_ca_certs: Annotated[Optional[str], "Path to CA certificate file"] = (
        None
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
