"""Storage layer using S3 for persistence."""
import json
import os
from typing import Optional, List, Dict, Any
from datetime import datetime
import boto3
from botocore.exceptions import ClientError


class S3Storage:
    """S3-based storage using JSON files."""
    
    def __init__(self, bucket_name: str, prefix: str = ""):
        """Initialize S3 storage.
        
        Args:
            bucket_name: S3 bucket name (must already exist)
            prefix: Key prefix for namespacing (e.g., "demo-1/")
        """
        self.bucket_name = bucket_name
        self.prefix = prefix.rstrip('/') + '/' if prefix else ''
        self.s3_client = boto3.client(
            's3',
            endpoint_url=os.getenv('AWS_ENDPOINT_URL'),
            aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID'),
            aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY'),
            region_name=os.getenv('AWS_REGION', 'auto')
        )
        print(f"Initialized S3 storage: bucket={self.bucket_name}, prefix={self.prefix}")
    
    def get(self, key: str) -> Optional[Dict[str, Any]]:
        """Get an object from S3."""
        try:
            full_key = self.prefix + key
            response = self.s3_client.get_object(Bucket=self.bucket_name, Key=full_key)
            data = response['Body'].read().decode('utf-8')
            return json.loads(data)
        except ClientError as e:
            if e.response['Error']['Code'] == 'NoSuchKey':
                return None
            raise
    
    def put(self, key: str, data: Dict[str, Any]) -> None:
        """Put an object to S3."""
        full_key = self.prefix + key
        json_data = json.dumps(data, indent=2)
        self.s3_client.put_object(
            Bucket=self.bucket_name,
            Key=full_key,
            Body=json_data.encode('utf-8'),
            ContentType='application/json'
        )
    
    def delete(self, key: str) -> None:
        """Delete an object from S3."""
        try:
            full_key = self.prefix + key
            self.s3_client.delete_object(Bucket=self.bucket_name, Key=full_key)
        except ClientError:
            pass  # Ignore if doesn't exist
    
    def list_keys(self, prefix: str = "") -> List[str]:
        """List all keys with given prefix (relative to bucket prefix)."""
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
        except ClientError:
            return []
    
    def list_objects(self, prefix: str = "") -> List[Dict[str, Any]]:
        """List all objects with given prefix."""
        keys = self.list_keys(prefix)
        objects = []
        
        for key in keys:
            obj = self.get(key)
            if obj:
                objects.append(obj)
        
        return objects


class MetaStorage:
    """Storage for agent metadata, jobs, health checks, and commands."""
    
    def __init__(self):
        """Initialize meta storage."""
        bucket_name = os.getenv('SLATE_META_BUCKET', 'slate-demo-meta')
        prefix = os.getenv('BUCKET_PREFIX', '')
        self.storage = S3Storage(bucket_name, prefix)
    
    # Agent operations
    def save_agent(self, agent_dict: Dict[str, Any]) -> None:
        """Save an agent."""
        key = f"agents/{agent_dict['agent_id']}.json"
        self.storage.put(key, agent_dict)
    
    def get_agent(self, agent_id: str) -> Optional[Dict[str, Any]]:
        """Get an agent by ID."""
        key = f"agents/{agent_id}.json"
        return self.storage.get(key)
    
    def list_agents(self) -> List[Dict[str, Any]]:
        """List all agents."""
        return self.storage.list_objects("agents/")
    
    def delete_agent(self, agent_id: str) -> None:
        """Delete an agent."""
        key = f"agents/{agent_id}.json"
        self.storage.delete(key)
    
    # Job operations
    def save_job(self, job_dict: Dict[str, Any]) -> None:
        """Save a job."""
        key = f"jobs/{job_dict['job_id']}.json"
        self.storage.put(key, job_dict)
    
    def get_job(self, job_id: str) -> Optional[Dict[str, Any]]:
        """Get a job by ID."""
        key = f"jobs/{job_id}.json"
        return self.storage.get(key)
    
    def list_jobs(self, agent_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """List all jobs, optionally filtered by agent."""
        jobs = self.storage.list_objects("jobs/")
        
        if agent_id:
            jobs = [j for j in jobs if j.get('agent_id') == agent_id]
        
        # Sort by created_at descending
        jobs.sort(key=lambda x: x.get('created_at', ''), reverse=True)
        return jobs
    
    # Health check operations
    def save_health_check(self, health_dict: Dict[str, Any]) -> None:
        """Save a health check."""
        agent_id = health_dict['agent_id']
        timestamp = health_dict['timestamp']
        key = f"health/{agent_id}/{timestamp}.json"
        self.storage.put(key, health_dict)
    
    def get_latest_health_check(self, agent_id: str) -> Optional[Dict[str, Any]]:
        """Get the latest health check for an agent."""
        checks = self.storage.list_objects(f"health/{agent_id}/")
        if not checks:
            return None
        
        # Sort by timestamp descending
        checks.sort(key=lambda x: x.get('timestamp', ''), reverse=True)
        return checks[0]
    
    # Command operations
    def save_command(self, command_dict: Dict[str, Any]) -> None:
        """Save a command."""
        key = f"commands/{command_dict['command_id']}.json"
        self.storage.put(key, command_dict)
    
    def get_command(self, command_id: str) -> Optional[Dict[str, Any]]:
        """Get a command by ID."""
        key = f"commands/{command_id}.json"
        return self.storage.get(key)
    
    def list_pending_commands(self, agent_id: str) -> List[Dict[str, Any]]:
        """List pending commands for an agent."""
        commands = self.storage.list_objects("commands/")
        pending = [
            c for c in commands 
            if c.get('agent_id') == agent_id and not c.get('executed', False)
        ]
        pending.sort(key=lambda x: x.get('created_at', ''))
        return pending


class RunnerStorage:
    """Storage for runner state and Terraform outputs."""
    
    def __init__(self):
        """Initialize runner storage."""
        bucket_name = os.getenv('SLATE_RUNNER_BUCKET', 'slate-demo-runner')
        prefix = os.getenv('BUCKET_PREFIX', '')
        self.storage = S3Storage(bucket_name, prefix)
    
    def save_state(self, job_id: str, state_data: bytes) -> str:
        """Save Terraform state file."""
        key = f"states/{job_id}/terraform.tfstate"
        self.storage.s3_client.put_object(
            Bucket=self.storage.bucket_name,
            Key=key,
            Body=state_data,
            ContentType='application/json'
        )
        return key
    
    def get_state(self, job_id: str) -> Optional[bytes]:
        """Get Terraform state file."""
        key = f"states/{job_id}/terraform.tfstate"
        try:
            response = self.storage.s3_client.get_object(
                Bucket=self.storage.bucket_name, 
                Key=key
            )
            return response['Body'].read()
        except ClientError as e:
            if e.response['Error']['Code'] == 'NoSuchKey':
                return None
            raise
    
    def save_output(self, job_id: str, output: str) -> None:
        """Save job output."""
        key = f"outputs/{job_id}.txt"
        self.storage.s3_client.put_object(
            Bucket=self.storage.bucket_name,
            Key=key,
            Body=output.encode('utf-8'),
            ContentType='text/plain'
        )
    
    def get_output(self, job_id: str) -> Optional[str]:
        """Get job output."""
        key = f"outputs/{job_id}.txt"
        try:
            response = self.storage.s3_client.get_object(
                Bucket=self.storage.bucket_name,
                Key=key
            )
            return response['Body'].read().decode('utf-8')
        except ClientError as e:
            if e.response['Error']['Code'] == 'NoSuchKey':
                return None
            raise

    def claim_job(self, job_id: str, agent_id: str) -> tuple:
        """Atomically claim a pending job.
        
        Args:
            job_id: Job ID to claim
            agent_id: Agent claiming the job
            
        Returns:
            (success, error_message)
        """
        from models import Job, JobStatus
        
        job_data = self.get_job(job_id)
        
        if not job_data:
            return False, "Job not found"
        
        current_status = job_data.get('status')
        if current_status != JobStatus.PENDING.value:
            return False, f"Job status is {current_status}, expected pending"
        
        # Update job to running
        job = Job.from_dict(job_data)
        job.status = JobStatus.RUNNING.value
        job.started_at = datetime.utcnow().isoformat()
        job.agent_id = agent_id
        
        self.save_job(job.to_dict())
        return True, ""
    
    def transition_job_status(self, job_id: str, to_status: str, **updates) -> tuple:
        """Transition job status with validation.
        
        Valid transitions:
        - pending -> running
        - running -> completed
        - running -> failed
        
        Args:
            job_id: Job ID
            to_status: Target status
            **updates: Additional fields to update
            
        Returns:
            (success, error_message)
        """
        from models import Job, JobStatus
        
        job_data = self.get_job(job_id)
        
        if not job_data:
            return False, "Job not found"
        
        current_status = job_data.get('status')
        
        # Define valid transitions
        valid_transitions = {
            JobStatus.PENDING.value: [JobStatus.RUNNING.value],
            JobStatus.RUNNING.value: [JobStatus.COMPLETED.value, JobStatus.FAILED.value],
            JobStatus.COMPLETED.value: [],
            JobStatus.FAILED.value: []
        }
        
        allowed = valid_transitions.get(current_status, [])
        if to_status not in allowed:
            return False, f"Invalid transition from {current_status} to {to_status}"
        
        # Update job
        job = Job.from_dict(job_data)
        job.status = to_status
        
        # Set timestamps
        if to_status == JobStatus.RUNNING.value:
            job.started_at = datetime.utcnow().isoformat()
        elif to_status in [JobStatus.COMPLETED.value, JobStatus.FAILED.value]:
            job.completed_at = datetime.utcnow().isoformat()
        
        # Apply additional updates
        for key, value in updates.items():
            if hasattr(job, key):
                setattr(job, key, value)
        
        self.save_job(job.to_dict())
        return True, ""