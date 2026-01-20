"""Reconciliation loops for the runner."""
import time
import sys
import psutil
import requests
from datetime import datetime
from typing import Optional
from config import RunnerConfig
from storage import RunnerS3Client
from task import TaskRegistry, TaskContext, TaskStatus
from tasks import TerraformPlanTask, TerraformApplyTask, TerraformRefreshTask
from tasks.state_sync_task import StateSyncTask


class RunnerLoops:
    """Manages all reconciliation loops with task-based execution."""
    
    def __init__(self, config: RunnerConfig, state: 'RunnerStateManager'):
        """Initialize loops and task registry."""
        self.config = config
        self.state = state
        self.s3_client = RunnerS3Client()
        self.running = True
        
        # Initialize task registry
        self.task_registry = TaskRegistry()
        self._register_tasks()
    
    def _register_tasks(self):
        """Register all available task implementations."""
        # Register Terraform tasks
        self.task_registry.register(TerraformPlanTask())
        self.task_registry.register(TerraformApplyTask())
        self.task_registry.register(TerraformRefreshTask())
        
        # Register state sync task
        self.task_registry.register(StateSyncTask())
        
        print(f"[TaskRegistry] Registered tasks: {', '.join(self.task_registry.list_tasks())}")
    
    def health_check_loop(self):
        """Health check loop - reports agent health."""
        print(f"[HealthCheck] Starting health check loop (interval: {self.config.poll_interval}s)")
        
        while self.running:
            try:
                # Gather system metrics
                cpu_percent = psutil.cpu_percent(interval=1)
                memory_percent = psutil.virtual_memory().percent
                disk_percent = psutil.disk_usage('/').percent
                
                # Submit health check
                payload = {
                    'agent_id': self.config.runner_id,
                    'cpu_percent': cpu_percent,
                    'memory_percent': memory_percent,
                    'disk_percent': disk_percent,
                    'capabilities': {
                        'tasks': self.task_registry.list_tasks(),
                        'version': '1.0.0',
                        'platform': sys.platform
                    },
                    'metadata': {
                        'timestamp': datetime.utcnow().isoformat()
                    }
                }
                
                response = requests.post(
                    f"{self.config.control_plane_url}/api/health",
                    json=payload,
                    timeout=10
                )
                
                if response.status_code == 200:
                    print(f"[HealthCheck] ✓ Heartbeat sent (CPU: {cpu_percent:.1f}%, MEM: {memory_percent:.1f}%)")
                else:
                    print(f"[HealthCheck] ✗ Failed: {response.status_code}")
                    
            except Exception as e:
                print(f"[HealthCheck] ✗ Error: {e}")
            
            time.sleep(self.config.poll_interval)
    
    def operations_loop(self):
        """Operations loop - fetches and applies control commands."""
        print(f"[Operations] Starting operations loop (interval: {self.config.poll_interval}s)")
        
        while self.running:
            try:
                # Fetch agent data to sync adoption status
                try:
                    agent_response = requests.get(
                        f"{self.config.control_plane_url}/api/agents/{self.config.runner_id}",
                        timeout=10
                    )
                    
                    if agent_response.status_code == 200:
                        agent_data = agent_response.json()
                        was_adopted = self.config.adopted
                        self.config.update_from_agent_data(agent_data)
                        
                        if agent_data.get('adopted') and not was_adopted:
                            print(f"[Operations] 🎉 Runner has been ADOPTED! Can now execute jobs.")
                except Exception as e:
                    print(f"[Operations] ⚠️  Failed to sync agent status: {e}")
                
                # Fetch pending commands
                response = requests.get(
                    f"{self.config.control_plane_url}/api/agents/{self.config.runner_id}/commands",
                    timeout=10
                )
                
                if response.status_code == 200:
                    commands = response.json()
                    
                    for cmd in commands:
                        command_type = cmd.get('command_type')
                        params = cmd.get('params')
                        command_id = cmd.get('command_id')
                        
                        print(f"[Operations] Executing command: {command_type}")
                        
                        # Apply command to config
                        self.config.apply_command(command_type, params)
                        
                        # Mark as executed
                        requests.patch(
                            f"{self.config.control_plane_url}/api/commands/{command_id}",
                            json={'executed': True},
                            timeout=10
                        )
                        
                        print(f"[Operations] ✓ Command executed: {command_type}")
                        print(f"[Operations] State - Locked: {self.config.locked}, Paused: {self.config.paused}, Read-only: {self.config.read_only}")
                        
            except Exception as e:
                print(f"[Operations] ✗ Error: {e}")
            
            time.sleep(self.config.poll_interval)
    
    def job_loop(self):
        """Job polling loop - fetches and executes jobs using task system."""
        print(f"[Jobs] Starting job loop (interval: {self.config.poll_interval}s)")
        
        while self.running:
            try:
                # Check if runner is adopted before fetching jobs
                if not self.config.adopted:
                    print(f"[Jobs] ⏸️  Ignoring jobs because: runner not yet adopted by control plane")
                    time.sleep(self.config.poll_interval)
                    continue
                
                # Fetch pending job and send check timestamp
                check_timestamp = datetime.now(timezone.utc).isoformat()
                response = requests.get(
                    f"{self.config.control_plane_url}/api/jobs/pending",
                    params={
                        'agent_id': self.config.runner_id,
                        'check_timestamp': check_timestamp
                    },
                    timeout=10
                )
                
                if response.status_code != 200:
                    time.sleep(self.config.poll_interval)
                    continue
                
                job = response.json()
                
                if not job:
                    # No pending jobs
                    time.sleep(self.config.poll_interval)
                    continue
                
                job_id = job.get('job_id')
                operation = job.get('operation')
                
                print(f"\n[Jobs] 📋 Found pending job: {job_id} (operation: {operation})")
                
                # Check if we can execute THIS SPECIFIC job based on its operation type
                can_execute, reason = self.config.can_execute_jobs_with_reason(operation)
                if not can_execute:
                    print(f"[Jobs] ⏸️  Ignoring job {job_id} because: {reason}")
                    time.sleep(self.config.poll_interval)
                    continue
                
                # Claim the job atomically
                try:
                    claim_response = requests.post(
                        f"{self.config.control_plane_url}/api/jobs/{job_id}/claim",
                        json={'agent_id': self.config.runner_id},
                        timeout=10
                    )
                    
                    if claim_response.status_code == 409:
                        print(f"[Jobs] ⏭️  Job {job_id} already claimed by another runner")
                        time.sleep(self.config.poll_interval)
                        continue
                    elif claim_response.status_code == 404:
                        print(f"[Jobs] ⚠️  Job {job_id} not found")
                        time.sleep(self.config.poll_interval)
                        continue
                    elif claim_response.status_code != 200:
                        print(f"[Jobs] ✗ Failed to claim job: {claim_response.status_code}")
                        time.sleep(self.config.poll_interval)
                        continue
                    
                    # Successfully claimed, use the returned job data
                    job = claim_response.json()
                    print(f"[Jobs] ✓ Claimed job: {job_id}")
                    
                except Exception as e:
                    print(f"[Jobs] ✗ Error claiming job: {e}")
                    time.sleep(self.config.poll_interval)
                    continue
                
                print(f"[Jobs] ⚡ Starting job: {job_id} (operation: {operation})")
                
                # Get the appropriate task handler
                task = self.task_registry.get_task(operation)
                
                if not task:
                    print(f"[Jobs] ✗ Unknown task type: {operation}")
                    self._update_job_failed(job_id, f"Unknown operation: {operation}")
                    continue
                
                # Create task context
                context = TaskContext(
                    job_id=job_id,
                    task_type=operation,
                    config={
                        'repo_url': job.get('repo_url'),
                        'tfvars': job.get('tfvars'),
                        'tf_version': job.get('tf_version'),
                        'working_dir': job.get('working_dir')
                    },
                    runner_id=self.config.runner_id,
                    workdir=f"/tmp/runner-{self.config.runner_id}",
                    env_vars=job.get('env_vars'),
                    metadata={
                        **job.get('metadata', {}),
                        'state_manager': self.state,
                        'control_plane_url': self.config.control_plane_url
                    }
                )
                
                # Validate task context
                if not task.validate(context):
                    print(f"[Jobs] ✗ Task validation failed")
                    self._update_job_failed(job_id, "Task validation failed")
                    continue
                
                # Execute the task
                print(f"[Jobs] Executing task: {operation}")
                result = task.execute(context)
                
                # Cleanup
                task.cleanup(context)
                
                # Upload artifacts (state files, etc.)
                s3_state_path = None
                if result.artifacts and 'state_path' in result.artifacts:
                    try:
                        state_path = result.artifacts['state_path']
                        s3_key = f"states/{job_id}/terraform.tfstate"
                        self.s3_client.upload_file(state_path, s3_key)
                        s3_state_path = s3_key
                        print(f"[Jobs] ✓ Uploaded state to S3: {s3_key}")
                    except Exception as e:
                        print(f"[Jobs] ✗ Failed to upload state: {e}")
                
                # Upload output
                try:
                    output_key = f"outputs/{job_id}.txt"
                    self.s3_client.upload_data(
                        result.output.encode('utf-8'),
                        output_key,
                        'text/plain'
                    )
                    print(f"[Jobs] ✓ Uploaded output to S3")
                except Exception as e:
                    print(f"[Jobs] ✗ Failed to upload output: {e}")
                
                # Update job status
                if result.status == TaskStatus.SUCCESS:
                    self._update_job_completed(job_id, result.output, s3_state_path)
                    print(f"[Jobs] ✓ Job {job_id} completed\n")
                    
                    # Record job completion in runner's state store
                    self.state.record_job_completion(job_id, success=True)
                    
                    # Handle reconciliation flag based on operation type
                    if job.get('operation') == 'state_sync':
                        # State sync jobs clear the reconciliation requirement
                        if self.config.requires_reconciliation:
                            self.config.requires_reconciliation = False
                            print(f"[Jobs] ✓ State reconciled - runner can accept new jobs")
                    else:
                        # Non-state_sync jobs require reconciliation after completion
                        from datetime import datetime, timezone
                        self.config.requires_reconciliation = True
                        self.config.last_job_completed_at = datetime.now(timezone.utc).isoformat()
                        print(f"[Jobs] ⚠️  State reconciliation required before next job")
                else:
                    self._update_job_failed(job_id, result.error or result.output, s3_state_path)
                    print(f"[Jobs] ✗ Job {job_id} failed\n")
                    
                    # Record job failure in runner's state store
                    self.state.record_job_completion(job_id, success=False)
                
            except Exception as e:
                print(f"[Jobs] ✗ Error: {e}")
                import traceback
                traceback.print_exc()
            
            time.sleep(self.config.poll_interval)
    
    def _update_job_completed(self, job_id: str, output: str, state_path: Optional[str] = None):
        """Update job status to completed."""
        update_payload = {
            'status': 'completed',
            'output': output[:1000],  # Store truncated version
            'state_path': state_path
        }
        
        try:
            requests.patch(
                f"{self.config.control_plane_url}/api/jobs/{job_id}",
                json=update_payload,
                timeout=10
            )
            
            # Track in state
            self.state.increment('jobs_completed')
            self.state.save()
        except Exception as e:
            print(f"[Jobs] ✗ Failed to update job status: {e}")
    
    def _update_job_failed(self, job_id: str, error: str, state_path: Optional[str] = None):
        """Update job status to failed."""
        update_payload = {
            'status': 'failed',
            'error': error[:500],
            'state_path': state_path
        }
        
        try:
            requests.patch(
                f"{self.config.control_plane_url}/api/jobs/{job_id}",
                json=update_payload,
                timeout=10
            )
            
            # Track in state
            self.state.increment('jobs_failed')
            self.state.save()
        except Exception as e:
            print(f"[Jobs] ✗ Failed to update job status: {e}")
    
    def stop(self):
        """Stop all loops."""
        print("\n[Runner] Stopping all loops...")
        self.running = False