"""Runner state management using S3."""
import json
import os
from typing import Optional, Dict, Any
from datetime import datetime
from botocore.client import Config
import boto3
from botocore.exceptions import ClientError


class RunnerStateManager:
    """Manages runner state persistence to S3."""
    
    def __init__(self, runner_id: str):
        """Initialize state manager.
        
        Args:
            runner_id: Unique runner identifier
        """
        self.runner_id = runner_id
        self.bucket_name = os.getenv('RUNNER_BUCKET', 'slate-demo-runner')
        self.prefix = os.getenv('RUNNER_BUCKET_PREFIX', '').rstrip('/') + '/' if os.getenv('RUNNER_BUCKET_PREFIX', '') else ''
        self.state_key = f"{self.prefix}runner-state/{runner_id}/state.json"
        
        session = boto3.Session(profile_name='tigris')
        self.s3_client = session.client(
            's3', config=Config(s3={'addressing_style': 'virtual'}))
        
        print(f"[StateManager] Using bucket={self.bucket_name}, prefix={self.prefix}, state_key={self.state_key}")
        self._state = self._load_state()
    
    def _load_state(self) -> Dict[str, Any]:
        """Load state from S3."""
        try:
            response = self.s3_client.get_object(
                Bucket=self.bucket_name,
                Key=self.state_key
            )
            data = response['Body'].read().decode('utf-8')
            return json.loads(data)
        except ClientError as e:
            if e.response['Error']['Code'] == 'NoSuchKey':
                # Initialize new state
                return {
                    'runner_id': self.runner_id,
                    'created_at': datetime.utcnow().isoformat(),
                    'last_sync': None,
                    'jobs_completed': 0,
                    'jobs_failed': 0,
                    'config': {},
                    'metadata': {}
                }
            raise
    
    def save(self) -> None:
        """Save current state to S3."""
        self._state['last_sync'] = datetime.utcnow().isoformat()
        
        json_data = json.dumps(self._state, indent=2)
        self.s3_client.put_object(
            Bucket=self.bucket_name,
            Key=self.state_key,
            Body=json_data.encode('utf-8'),
            ContentType='application/json'
        )
    
    def get(self, key: str, default=None) -> Any:
        """Get a value from state."""
        return self._state.get(key, default)
    
    def set(self, key: str, value: Any) -> None:
        """Set a value in state."""
        self._state[key] = value
    
    def increment(self, key: str, amount: int = 1) -> None:
        """Increment a numeric value."""
        current = self._state.get(key, 0)
        self._state[key] = current + amount
    
    def update_metadata(self, metadata: Dict[str, Any]) -> None:
        """Update metadata."""
        if 'metadata' not in self._state:
            self._state['metadata'] = {}
        self._state['metadata'].update(metadata)
    
    def get_state(self) -> Dict[str, Any]:
        """Get entire state."""
        return self._state.copy()
    
    def record_job_completion(self, job_id: str, success: bool = True) -> None:
        """Record a completed job ID.
        
        Args:
            job_id: The job ID to record
            success: Whether the job succeeded or failed
        """
        if 'completed_jobs' not in self._state:
            self._state['completed_jobs'] = []
        
        job_record = {
            'job_id': job_id,
            'completed_at': datetime.utcnow().isoformat(),
            'success': success
        }
        
        self._state['completed_jobs'].append(job_record)
        
        # Update counters
        if success:
            self.increment('jobs_completed')
        else:
            self.increment('jobs_failed')
        
        print(f"[StateManager] Recorded job {job_id} (success={success})")
        
        # Save state to S3
        self.save()