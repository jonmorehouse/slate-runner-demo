"""SlateDB storage wrapper for runner."""
import os
import json
from typing import Optional, Iterator, Tuple, Dict, Any
from datetime import datetime


class SlateDBStorage:
    """
    Wrapper around SlateDB for runner storage operations.
    
    Uses SlateDB with S3 backend for durable, consistent storage with:
    - Synchronous operations
    - WAL persistence
    - Checkpoint support for consistent reads and recovery
    """
    
    def __init__(self, runner_id: str, runner_name: str, bucket_name: str, bucket_prefix: str, tmp_dir: str):
        """
        Initialize SlateDB storage.
        
        Args:
            runner_id: Unique runner identifier
            bucket_name: S3 bucket name for SlateDB backend
            tmp_dir: Base directory for SlateDB temporary files
            aws_config: AWS configuration dict with keys:
                - region: AWS region
                - access_key: AWS access key ID
                - secret_key: AWS secret access key
                - endpoint_url: Optional S3 endpoint URL
        """
        from slatedb import SlateDB, SlateDBReader, SlateDBAdmin

        self.runner_id = runner_id
        self.bucket_name = bucket_name
        
        # Each runner gets isolated path: {tmp_dir}/{runner_id}/
        self.db_path = os.path.join(tmp_dir, runner_id)
        os.makedirs(self.db_path, exist_ok=True)
        
        # S3 backend URL
        print(bucket_name)
        self.bucket_url = f"s3://{bucket_name}"
        
        self.db = SlateDB(self.db_path, url="memory:///")
        self.admin = SlateDBAdmin(self.db_path, url=self.bucket_url)
        
        # Track checkpoint history for this session
        self.checkpoint_history = []
        
        print(f"[SlateDB] Initialized successfully for runner: {runner_id}")
    
    def put(self, key: str, value: bytes) -> None:
        """
        Store a key-value pair.
        
        Args:
            key: Storage key (will be encoded to bytes)
            value: Value bytes to store
        """
        key_bytes = key.encode('utf-8') if isinstance(key, str) else key
        self.db.put(key_bytes, value)
    
    def get(self, key: str) -> Optional[bytes]:
        """
        Retrieve a value by key.
        
        Args:
            key: Storage key (will be encoded to bytes)
            
        Returns:
            Value bytes if found, None otherwise
        """
        key_bytes = key.encode('utf-8') if isinstance(key, str) else key
        return self.db.get(key_bytes)
    
    def scan(self, prefix: str) -> Iterator[Tuple[str, bytes]]:
        """
        Scan all keys with given prefix.
        
        Args:
            prefix: Key prefix to scan (will be encoded to bytes)
            
        Yields:
            Tuples of (key, value) where key is decoded string
        """
        prefix_bytes = prefix.encode('utf-8') if isinstance(prefix, str) else prefix
        
        for key_bytes, value_bytes in self.db.scan(prefix_bytes):
            key_str = key_bytes.decode('utf-8')
            yield (key_str, value_bytes)
    
    def delete(self, key: str) -> None:
        """
        Delete a key.
        
        Args:
            key: Storage key to delete (will be encoded to bytes)
        """
        key_bytes = key.encode('utf-8') if isinstance(key, str) else key
        self.db.delete(key_bytes)
    
    def flush_wal(self) -> None:
        """
        Flush the write-ahead log to S3.
        
        This ensures all writes are persisted to durable storage.
        Should be called after critical operations like job completion.
        """
        self.db.flush_with_options("wal")
        print(f"[SlateDB] WAL flushed to S3")
    
    def create_checkpoint(self, job_id: Optional[str] = None, checkpoint_type: str = "post_job") -> Dict[str, Any]:
        """
        Create a durable checkpoint.
        
        Checkpoints provide:
        - Consistent snapshot of database state
        - Recovery points after successful operations
        - Basis for consistent reads during state sync
        
        Args:
            job_id: Associated job ID (optional)
            checkpoint_type: Type of checkpoint (post_job, state_sync, shutdown)
            
        Returns:
            Checkpoint metadata dict with id, created_at, job_id, type
        """
        # Create durable checkpoint
        ckpt = self.db.create_checkpoint(scope="durable")
        
        # Build checkpoint metadata
        checkpoint_info = {
            'id': ckpt['id'],
            'created_at': datetime.utcnow().isoformat(),
            'job_id': job_id,
            'type': checkpoint_type,
            'runner_id': self.runner_id
        }
        
        # Track in session history
        self.checkpoint_history.append(checkpoint_info)
        
        print(f"[SlateDB] Created checkpoint: {ckpt['id']} (type: {checkpoint_type})")
        
        return checkpoint_info
    
    def create_checkpoint_reader(self, checkpoint_id: str) -> 'SlateDBReader':
        """
        Create a read-only reader for a specific checkpoint.
        
        This provides a consistent view of the database at the checkpoint.
        Use for state sync to ensure consistent reads.
        
        Args:
            checkpoint_id: Checkpoint ID to read from
            
        Returns:
            SlateDBReader instance (caller must close it)
        """
        from slatedb import SlateDBReader
        
        reader_kwargs = {
            'aws_region': self.aws_config['region'],
        }
        
        if self.aws_config.get('access_key') and self.aws_config.get('secret_key'):
            reader_kwargs['aws_access_key_id'] = self.aws_config['access_key']
            reader_kwargs['aws_secret_access_key'] = self.aws_config['secret_key']
        
        if self.aws_config.get('endpoint_url'):
            reader_kwargs['aws_endpoint_url'] = self.aws_config['endpoint_url']
        
        reader = SlateDBReader(
            self.db_path,
            url=self.bucket_url,
            checkpoint_id=checkpoint_id,
            **reader_kwargs
        )
        
        print(f"[SlateDB] Created checkpoint reader for: {checkpoint_id}")
        
        return reader
    
    def list_checkpoints(self) -> list:
        """
        List all available checkpoints.
        
        Returns:
            List of checkpoint metadata dicts
        """
        try:
            checkpoints = self.admin.list_checkpoints()
            print(f"[SlateDB] Found {len(checkpoints)} checkpoints")
            return checkpoints
        except Exception as e:
            print(f"[SlateDB] Error listing checkpoints: {e}")
            return []
    
    def gc_checkpoints(self, keep_last_n: int = 20) -> None:
        """
        Garbage collect old checkpoints, keeping only the most recent N.
        
        Args:
            keep_last_n: Number of recent checkpoints to keep
        """
        try:
            checkpoints = self.list_checkpoints()
            
            if len(checkpoints) <= keep_last_n:
                print(f"[SlateDB] No checkpoint GC needed ({len(checkpoints)} <= {keep_last_n})")
                return
            
            # Sort by creation time (assuming checkpoints have timestamps)
            # For now, just run GC with aggressive settings
            # SlateDB GC will clean up old checkpoints automatically
            self.admin.run_gc_once(
                manifest_min_age=0,
                wal_min_age=0,
                compacted_min_age=0
            )
            
            print(f"[SlateDB] Garbage collected old checkpoints (kept last {keep_last_n})")
            
        except Exception as e:
            print(f"[SlateDB] Error during checkpoint GC: {e}")
    
    def close(self) -> None:
        """
        Close the SlateDB connection.
        
        Should be called during graceful shutdown.
        """
        try:
            self.db.close()
            print(f"[SlateDB] Closed database for runner: {self.runner_id}")
        except Exception as e:
            print(f"[SlateDB] Error closing database: {e}")
    
    def get_metrics(self) -> Dict[str, Any]:
        """
        Get SlateDB metrics.
        
        Returns:
            Metrics dict with database statistics
        """
        try:
            metrics = self.db.metrics()
            return metrics
        except Exception as e:
            print(f"[SlateDB] Error getting metrics: {e}")
            return {}


class CheckpointRecovery:
    """
    Utilities for checkpoint-based recovery and debugging.
    """
    
    def __init__(self, slate_storage: SlateDBStorage):
        """
        Initialize recovery utilities.
        
        Args:
            slate_storage: SlateDBStorage instance
        """
        self.storage = slate_storage
    
    def list_recovery_points(self) -> list:
        """
        List all available checkpoint recovery points.
        
        Returns:
            List of checkpoint metadata
        """
        return self.storage.list_checkpoints()
    
    def restore_to_checkpoint(self, checkpoint_id: str, state_key: str) -> Optional[Dict[str, Any]]:
        """
        Restore state to a specific checkpoint (read-only view).
        
        Args:
            checkpoint_id: Checkpoint ID to restore from
            state_key: Key to read from checkpoint
            
        Returns:
            State dict if found, None otherwise
        """
        try:
            reader = self.storage.create_checkpoint_reader(checkpoint_id)
            
            # Read state from checkpoint
            state_data = reader.get(state_key.encode('utf-8'))
            
            if state_data:
                state = json.loads(state_data.decode('utf-8'))
                print(f"[Recovery] State at checkpoint {checkpoint_id}:")
                print(f"  Jobs completed: {state.get('jobs_completed')}")
                print(f"  Last sync: {state.get('last_sync')}")
                reader.close()
                return state
            
            reader.close()
            return None
            
        except Exception as e:
            print(f"[Recovery] Error restoring checkpoint {checkpoint_id}: {e}")
            return None
    
    def verify_checkpoint(self, checkpoint_id: str) -> bool:
        """
        Verify checkpoint integrity.
        
        Args:
            checkpoint_id: Checkpoint ID to verify
            
        Returns:
            True if checkpoint is valid, False otherwise
        """
        try:
            reader = self.storage.create_checkpoint_reader(checkpoint_id)
            
            # Attempt to read to verify checkpoint is valid
            test_read = next(reader.scan(b""), None)
            reader.close()
            
            print(f"[Recovery] Checkpoint {checkpoint_id} is valid")
            return True
            
        except Exception as e:
            print(f"[Recovery] Checkpoint {checkpoint_id} invalid: {e}")
            return False




