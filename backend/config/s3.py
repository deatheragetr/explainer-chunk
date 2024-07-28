import boto3
from botocore.client import Config
from config.environment import WasabiSettings

s3_settings: WasabiSettings = WasabiSettings()

# Wasabi S3 client
s3_client = boto3.client('s3', # type: ignore
    endpoint_url=s3_settings.wasabi_endpoint_url,
    aws_access_key_id=s3_settings.wasabi_access_key,
    aws_secret_access_key=s3_settings.wasabi_secret_key,
    region_name=s3_settings.wasabi_region,
    config=Config(signature_version='s3v4')
)