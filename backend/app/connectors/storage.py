"""Storage connectors for cloud storage services."""

from typing import Dict, Any, Optional, BinaryIO
import boto3
from botocore.exceptions import ClientError
from app.logging_config import get_logger

logger = get_logger("storage_connector")


class StorageConnector:
    """Base class for storage connectors."""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.client = None
    
    async def connect(self):
        """Connect to storage service."""
        raise NotImplementedError
    
    async def disconnect(self):
        """Disconnect from storage service."""
        pass
    
    async def upload(self, key: str, data: BinaryIO, **kwargs):
        """Upload data to storage."""
        raise NotImplementedError
    
    async def download(self, key: str) -> bytes:
        """Download data from storage."""
        raise NotImplementedError
    
    async def delete(self, key: str):
        """Delete data from storage."""
        raise NotImplementedError
    
    async def list(self, prefix: Optional[str] = None) -> list:
        """List objects in storage."""
        raise NotImplementedError
    
    async def health_check(self) -> bool:
        """Check storage connection."""
        raise NotImplementedError


class S3StorageConnector(StorageConnector):
    """AWS S3 storage connector."""
    
    async def connect(self):
        """Connect to S3."""
        try:
            self.client = boto3.client(
                's3',
                aws_access_key_id=self.config.get("access_key"),
                aws_secret_access_key=self.config.get("secret_key"),
                region_name=self.config.get("region", "us-east-1"),
            )
            self.bucket = self.config["bucket"]
            logger.info(f"Connected to S3 bucket: {self.bucket}")
        except Exception as e:
            logger.error(f"Failed to connect to S3: {e}")
            raise
    
    async def upload(self, key: str, data: BinaryIO, **kwargs):
        """Upload file to S3."""
        if not self.client:
            raise RuntimeError("Not connected to S3")
        
        try:
            self.client.upload_fileobj(data, self.bucket, key, ExtraArgs=kwargs)
            logger.info(f"Uploaded {key} to S3")
        except ClientError as e:
            logger.error(f"S3 upload failed: {e}")
            raise
    
    async def download(self, key: str) -> bytes:
        """Download file from S3."""
        if not self.client:
            raise RuntimeError("Not connected to S3")
        
        try:
            response = self.client.get_object(Bucket=self.bucket, Key=key)
            return response['Body'].read()
        except ClientError as e:
            logger.error(f"S3 download failed: {e}")
            raise
    
    async def delete(self, key: str):
        """Delete file from S3."""
        if not self.client:
            raise RuntimeError("Not connected to S3")
        
        try:
            self.client.delete_object(Bucket=self.bucket, Key=key)
            logger.info(f"Deleted {key} from S3")
        except ClientError as e:
            logger.error(f"S3 delete failed: {e}")
            raise
    
    async def list(self, prefix: Optional[str] = None) -> list:
        """List objects in S3."""
        if not self.client:
            raise RuntimeError("Not connected to S3")
        
        try:
            kwargs = {"Bucket": self.bucket}
            if prefix:
                kwargs["Prefix"] = prefix
            
            response = self.client.list_objects_v2(**kwargs)
            return [obj["Key"] for obj in response.get("Contents", [])]
        except ClientError as e:
            logger.error(f"S3 list failed: {e}")
            raise
    
    async def health_check(self) -> bool:
        """Check S3 connection."""
        try:
            if not self.client:
                return False
            self.client.head_bucket(Bucket=self.bucket)
            return True
        except Exception as e:
            logger.error(f"S3 health check failed: {e}")
            return False


class AzureBlobStorageConnector(StorageConnector):
    """Azure Blob Storage connector (placeholder)."""
    
    async def connect(self):
        """Connect to Azure Blob Storage."""
        logger.warning("Azure Blob Storage connector not fully implemented")
        raise NotImplementedError("Azure connector requires azure-storage-blob package")
    
    async def upload(self, key: str, data: BinaryIO, **kwargs):
        """Upload to Azure Blob."""
        raise NotImplementedError
    
    async def download(self, key: str) -> bytes:
        """Download from Azure Blob."""
        raise NotImplementedError
    
    async def delete(self, key: str):
        """Delete from Azure Blob."""
        raise NotImplementedError
    
    async def list(self, prefix: Optional[str] = None) -> list:
        """List Azure Blobs."""
        raise NotImplementedError
    
    async def health_check(self) -> bool:
        """Check Azure connection."""
        return False


def create_storage_connector(storage_type: str, config: Dict[str, Any]) -> StorageConnector:
    """Factory function to create storage connector."""
    if storage_type == "s3":
        return S3StorageConnector(config)
    elif storage_type == "azure":
        return AzureBlobStorageConnector(config)
    else:
        raise ValueError(f"Unsupported storage type: {storage_type}")
