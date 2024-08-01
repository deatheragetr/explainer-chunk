from pydantic_settings import BaseSettings
from typing_extensions import Annotated


class WasabiSettings(BaseSettings):
    wasabi_endpoint_url: str = "https://s3.wasabisys.com"
    wasabi_access_key: Annotated[str, "Wasabi access key"] = ""
    wasabi_secret_key: Annotated[str, "Wasabi secret key"] = ""
    wasabi_region: Annotated[str, "Wasabi region"] = ""
    wasabi_document_bucket: Annotated[str, "Wasabi document bucket"] = ""


class MongoSettings(BaseSettings):
    mongo_url: Annotated[str, "MongoDB connection URL"] = "mongodb://localhost:27019"
    mongo_db: Annotated[str, "MongoDB database name"] = "explainer-chonk-dev"
