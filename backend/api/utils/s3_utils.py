from botocore.exceptions import ClientError
from mypy_boto3_s3 import S3Client
from typing import Optional

async def verify_s3_object(s3_client: S3Client, bucket: str, key: str) -> bool:
    try:
        s3_client.head_object(Bucket=bucket, Key=key)
        return True
    except ClientError as e:
        response = getattr(e, 'response', {})
        error_info: dict[str, Optional[str]] = response.get('Error', {})
        error_code: Optional[str] = error_info.get('Code')
        
        if error_code == '404':
            return False
        else:
            # If there's a different error (e.g., permissions), we'll raise it
            raise
