import os
from bson import ObjectId
from logging import Logger
from mypy_boto3_s3.client import S3Client
from urllib.parse import urljoin, urlparse
from aiohttp import ClientSession
from db.models.document_uploads import (
    generate_s3_key_for_web_capture,
    generate_s3_url,
    AllowedFolders,
    S3Bucket,
)


async def fetch_and_store_resource(
    session: ClientSession,
    url: str,
    base_url: str,
    document_upload_id: str,
    bucket: S3Bucket,
    s3_client: S3Client,
    s3_host: str,
    logger: Logger,
) -> str | None:
    try:
        full_url = urljoin(base_url, url)
        parsed_url = urlparse(full_url)
        file_name = os.path.basename(parsed_url.path) or "index.html"

        async with session.get(full_url) as response:
            content = await response.read()

        content_type = response.headers.get(
            "content-type", "application/octet-stream"
        ).split(";")[0]

        s3_key = generate_s3_key_for_web_capture(
            folder=AllowedFolders.WEB_CAPTURES,
            object_id=ObjectId(document_upload_id),
            file_name=file_name,
        )
        s3_client.put_object(
            Bucket=bucket.value,
            Key=s3_key,
            Body=content,
            ContentType=content_type,
        )

        s3_url: str = generate_s3_url(s3_host, bucket, s3_key)
        return s3_url
    except Exception as e:
        logger.error(f"Error fetching resource {url}: {str(e)}")
        return None
