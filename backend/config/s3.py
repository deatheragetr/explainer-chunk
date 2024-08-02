import boto3
from botocore.client import Config
from config.environment import S3Settings

s3_settings: S3Settings = S3Settings()

s3_client = boto3.client('s3', # type: ignore
    aws_access_key_id=s3_settings.s3_access_key,
    aws_secret_access_key=s3_settings.s3_secret_key,
    region_name=s3_settings.s3_region,
    config=Config(signature_version='s3v4')
)