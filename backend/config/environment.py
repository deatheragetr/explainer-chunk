from pydantic_settings import BaseSettings
from typing_extensions import Annotated


# class WasabiSettings(BaseSettings):
#     wasabi_endpoint_url: str = "https://s3.wasabisys.com"
#     wasabi_access_key: Annotated[str, "Wasabi access key"] = ""
#     wasabi_secret_key: Annotated[str, "Wasabi secret key"] = ""
#     wasabi_region: Annotated[str, "Wasabi region"] = ""
#     wasabi_document_bucket: Annotated[str, "Wasabi document bucket"] = ""


# class S3Settings(BaseSettings):
class WasabiSettings(BaseSettings):
    wasabi_endpoint_url: str = "https://s3.wasabisys.com"
    wasabi_access_key: Annotated[str, "S3 access key"] = ""
    wasabi_secret_key: Annotated[str, "S3 secret key"] = ""
    wasabi_region: Annotated[str, "S3 region"] = ""
    wasabi_document_bucket: Annotated[str, "S3 document uploads (not public) bucket"] = ""
    s3_public_bucket: Annotated[str, "S3 document uploads (public access, e.g., web_captures) bucket"] = ""
    s3_host: Annotated[str, "S3 host"]


class MongoSettings(BaseSettings):
    mongo_url: Annotated[str, "MongoDB connection URL"] = "mongodb://localhost:27019"
    mongo_db: Annotated[str, "MongoDB database name"] = "explainer-chonk-dev"
