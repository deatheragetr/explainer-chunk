import boto3
from botocore.client import Config
from config.environment import S3Settings
from mypy_boto3_s3.client import (
    S3Client,
)  # https://youtype.github.io/boto3_stubs_docs/mypy_boto3_s3/client/#s3client_1

s3_settings: S3Settings = S3Settings()

s3_client: S3Client = boto3.client(  # type: ignore
    "s3",
    aws_access_key_id=s3_settings.s3_access_key,
    aws_secret_access_key=s3_settings.s3_secret_key,
    region_name=s3_settings.s3_region,
    config=Config(signature_version="s3v4"),
)
