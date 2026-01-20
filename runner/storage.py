"""Storage client for runner using SlateDB."""
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from slate_storage import SlateDBStorage


class RunnerS3Client:
    """Storage client that wraps SlateDB for all runner storage operations."""
    
    def __init__(self, slate_storage: 'SlateDBStorage', prefix: str = ''):
        """Initialize storage client.
        
        Args:
            slate_storage: SlateDBStorage instance
            prefix: Optional prefix for keys (usually empty since SlateDB handles prefixing)
        """
        self.slate_storage = slate_storage
        self.prefix = prefix.rstrip('/') + '/' if prefix else ''
        
        print(f"[Storage] Using SlateDB-backed storage, prefix={self.prefix}")
    
    def upload_file(self, local_path: str, s3_key: str) -> str:
        """Upload a file to SlateDB.
        
        Args:
            local_path: Local file path to upload
            s3_key: Key to store the file under
            
        Returns:
            The s3_key that was used
        """
        try:
            with open(local_path, 'rb') as f:
                data = f.read()
            
            full_key = self.prefix + s3_key
            self.slate_storage.put(full_key, data)
            return s3_key
        except Exception as e:
            print(f"Error uploading file to SlateDB: {e}")
            raise
    
    def upload_data(self, data: bytes, s3_key: str, content_type: str = 'application/octet-stream') -> str:
        """Upload data to SlateDB.
        
        Args:
            data: Bytes to upload
            s3_key: Key to store the data under
            content_type: Content type (ignored, for compatibility)
            
        Returns:
            The s3_key that was used
        """
        try:
            full_key = self.prefix + s3_key
            self.slate_storage.put(full_key, data)
            return s3_key
        except Exception as e:
            print(f"Error uploading data to SlateDB: {e}")
            raise
    
    def list_objects(self, prefix: str = '') -> list:
        """List objects in SlateDB with given prefix.
        
        Args:
            prefix: Prefix to filter keys (relative to storage prefix)
            
        Returns:
            List of keys (with storage prefix stripped)
        """
        try:
            full_prefix = self.prefix + prefix
            keys = []
            
            for key, _ in self.slate_storage.scan(full_prefix):
                # Strip storage prefix from returned keys
                if key.startswith(self.prefix):
                    keys.append(key[len(self.prefix):])
                else:
                    keys.append(key)
            
            return keys
        except Exception as e:
            print(f"Error listing objects in SlateDB: {e}")
            return []
    
    def get_object(self, s3_key: str) -> bytes:
        """Get object data from SlateDB.
        
        Args:
            s3_key: Key to retrieve
            
        Returns:
            Bytes of the object
        """
        try:
            full_key = self.prefix + s3_key
            data = self.slate_storage.get(full_key)
            if data is None:
                raise KeyError(f"Key not found: {s3_key}")
            return data
        except Exception as e:
            print(f"Error getting object from SlateDB: {e}")
            raise
    
    def download_file(self, s3_key: str, local_path: str) -> None:
        """Download a file from SlateDB.
        
        Args:
            s3_key: Key to download
            local_path: Local path to save to
        """
        try:
            data = self.get_object(s3_key)
            with open(local_path, 'wb') as f:
                f.write(data)
        except Exception as e:
            print(f"Error downloading file from SlateDB: {e}")
            raise
    
    def delete_object(self, s3_key: str) -> None:
        """Delete an object from SlateDB.
        
        Args:
            s3_key: Key to delete
        """
        try:
            full_key = self.prefix + s3_key
            self.slate_storage.delete(full_key)
        except Exception as e:
            print(f"Error deleting object from SlateDB: {e}")
            raise
    
    def object_exists(self, s3_key: str) -> bool:
        """Check if an object exists in SlateDB.
        
        Args:
            s3_key: Key to check
            
        Returns:
            True if exists, False otherwise
        """
        try:
            full_key = self.prefix + s3_key
            data = self.slate_storage.get(full_key)
            return data is not None
        except Exception:
            return False
    
    def flush_wal(self) -> None:
        """Flush the write-ahead log to ensure durability.
        
        This should be called after critical operations like job completion.
        """
        self.slate_storage.flush_wal()
    
    def create_checkpoint(self, job_id: str = None, checkpoint_type: str = "post_job") -> dict:
        """Create a checkpoint for recovery and consistent reads.
        
        Args:
            job_id: Associated job ID
            checkpoint_type: Type of checkpoint (post_job, state_sync, shutdown)
            
        Returns:
            Checkpoint metadata dict
        """
        return self.slate_storage.create_checkpoint(job_id, checkpoint_type)
    
    def create_checkpoint_reader(self, checkpoint_id: str):
        """Create a checkpoint reader for consistent reads.
        
        Args:
            checkpoint_id: Checkpoint ID to read from
            
        Returns:
            SlateDBReader instance
        """
        return self.slate_storage.create_checkpoint_reader(checkpoint_id)
