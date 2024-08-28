from pydantic_settings import BaseSettings
from typing_extensions import Annotated


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
