"""Storage client for runner to access S3."""
import os
import boto3
from botocore.exceptions import ClientError


class RunnerS3Client:
    """S3 client for runner storage operations."""
    
    def __init__(self):
        """Initialize S3 client."""
        from botocore.client import Config
        
        self.bucket_name = os.getenv('RUNNER_BUCKET', 'slate-demo-runner')
        self.prefix = os.getenv('RUNNER_BUCKET_PREFIX', '').rstrip('/') + '/' if os.getenv('RUNNER_BUCKET_PREFIX', '') else ''

        # Use Tigris profile from ~/.aws/credentials
        session = boto3.Session(profile_name='tigris')
        self.s3_client = session.client('s3', config=Config(s3={'addressing_style': 'virtual'}))
        print(f"[Storage] Using bucket={self.bucket_name}, prefix={self.prefix}")
    
    def upload_file(self, local_path: str, s3_key: str) -> str:
        """Upload a file to S3."""
        try:
            full_key = self.prefix + s3_key
            self.s3_client.upload_file(local_path, self.bucket_name, full_key)
            return s3_key
        except ClientError as e:
            print(f"Error uploading file to S3: {e}")
            raise
    
    def upload_data(self, data: bytes, s3_key: str, content_type: str = 'application/octet-stream') -> str:
        """Upload data to S3."""
        try:
            full_key = self.prefix + s3_key
            self.s3_client.put_object(
                Bucket=self.bucket_name,
                Key=full_key,
                Body=data,
                ContentType=content_type
            )
            return s3_key
        except ClientError as e:
            print(f"Error uploading data to S3: {e}")
            raise
    
    def list_objects(self, prefix: str = '') -> list:
        """List objects in S3 with given prefix (relative to bucket prefix)."""
        try:
            full_prefix = self.prefix + prefix
            response = self.s3_client.list_objects_v2(
                Bucket=self.bucket_name,
                Prefix=full_prefix
            )
            
            if 'Contents' not in response:
                return []
            
            # Strip bucket prefix from returned keys
            prefix_len = len(self.prefix)
            return [obj['Key'][prefix_len:] for obj in response['Contents']]
        except ClientError as e:
            print(f"Error listing objects in S3: {e}")
            return []
    
    def get_object(self, s3_key: str) -> bytes:
        """Get object data from S3."""
        try:
            full_key = self.prefix + s3_key
            response = self.s3_client.get_object(
                Bucket=self.bucket_name,
                Key=full_key
            )
            return response['Body'].read()
        except ClientError as e:
            print(f"Error getting object from S3: {e}")
            raise